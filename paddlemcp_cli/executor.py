#!/usr/bin/env python3
"""
Execution Engine for Jupyter Notebooks

Supports both local and remote execution with streaming output.
"""

import io
import sys
import time
import traceback
import threading
import queue
import json
import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, TextIO, Union

from .notebook import Notebook, NotebookCell, CellType
from .i18n import t


class ExecutionStatus(Enum):
    """Status of cell execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class CellOutput:
    """Output from a cell execution"""
    cell_index: int
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    traceback: Optional[str] = None
    execution_time: float = 0.0
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_index": self.cell_index,
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "error_type": self.error_type,
            "traceback": self.traceback,
            "execution_time": self.execution_time,
            "outputs": self.outputs,
            "variables": self.variables,
        }


@dataclass
class StreamChunk:
    """A chunk of streaming output"""
    cell_index: int
    stream_type: str  # 'stdout', 'stderr', 'status', 'error'
    content: str
    timestamp: float = field(default_factory=time.time)


class StreamingCapture:
    """Capture stdout/stderr and stream chunks"""

    def __init__(self, cell_index: int, output_queue: queue.Queue):
        self.cell_index = cell_index
        self.output_queue = output_queue
        self.buffer = io.StringIO()

    def write(self, text: str) -> int:
        if text:
            self.buffer.write(text)
            # Send streaming chunk
            self.output_queue.put(StreamChunk(
                cell_index=self.cell_index,
                stream_type='stdout',
                content=text
            ))
        return len(text)

    def flush(self):
        pass

    def getvalue(self) -> str:
        return self.buffer.getvalue()


class ExecutionEngine(ABC):
    """Abstract base class for execution engines"""

    def __init__(self):
        self.global_vars: Dict[str, Any] = {}
        self.output_queue: queue.Queue = queue.Queue()
        self.on_cell_start: Optional[Callable[[NotebookCell], None]] = None
        self.on_cell_complete: Optional[Callable[[NotebookCell, CellOutput], None]] = None
        self.on_stream: Optional[Callable[[StreamChunk], None]] = None
        self.stop_on_error: bool = True
        self.timeout: int = 300
        self._stop_requested = False

    @abstractmethod
    def execute_cell(self, cell: NotebookCell) -> CellOutput:
        """Execute a single cell"""
        pass

    def execute_notebook(
        self,
        notebook: Notebook,
        start_cell: int = 0,
        end_cell: Optional[int] = None,
        skip_markdown: bool = True,
        cell_filter: Optional[Callable[[NotebookCell], bool]] = None,
    ) -> Generator[CellOutput, None, None]:
        """
        Execute all cells in a notebook, yielding results as they complete.

        Args:
            notebook: The notebook to execute
            start_cell: Index of first cell to execute
            end_cell: Index of last cell (exclusive)
            skip_markdown: Skip markdown cells
            cell_filter: Optional filter function for cells
        """
        cells = notebook.cells[start_cell:end_cell]

        for cell in cells:
            if self._stop_requested:
                break

            # Skip markdown cells if requested
            if skip_markdown and cell.is_markdown:
                continue

            # Apply custom filter
            if cell_filter and not cell_filter(cell):
                continue

            # Callback for cell start
            if self.on_cell_start:
                self.on_cell_start(cell)

            # Execute cell
            output = self.execute_cell(cell)

            # Callback for cell complete
            if self.on_cell_complete:
                self.on_cell_complete(cell, output)

            yield output

            # Stop on error if configured
            if self.stop_on_error and output.status == ExecutionStatus.ERROR:
                break

    def stop(self):
        """Request execution to stop"""
        self._stop_requested = True

    def get_stream(self) -> Generator[StreamChunk, None, None]:
        """Get streaming output from queue"""
        while True:
            try:
                chunk = self.output_queue.get(timeout=0.1)
                yield chunk
            except queue.Empty:
                continue


class LocalExecutionEngine(ExecutionEngine):
    """
    Execute notebook cells locally with streaming output.

    Supports:
    - IPython magic commands
    - Variable persistence between cells
    - Streaming stdout/stderr
    """

    def __init__(self):
        super().__init__()
        self.global_vars = {'__builtins__': __builtins__}
        self._setup_ipython()

    def _setup_ipython(self):
        """Setup IPython shell for magic commands"""
        try:
            from IPython import get_ipython
            from IPython.core.interactiveshell import InteractiveShell

            # Get or create IPython instance
            self.shell = get_ipython()
            if self.shell is None:
                self.shell = InteractiveShell.instance()

            self.has_ipython = True
        except ImportError:
            self.shell = None
            self.has_ipython = False

    def execute_cell(self, cell: NotebookCell) -> CellOutput:
        """Execute a single cell locally"""
        if not cell.is_code:
            return CellOutput(
                cell_index=cell.index,
                status=ExecutionStatus.SKIPPED
            )

        if self._stop_requested:
            return CellOutput(
                cell_index=cell.index,
                status=ExecutionStatus.SKIPPED
            )

        start_time = time.time()
        stdout_capture = StreamingCapture(cell.index, self.output_queue)
        stderr_capture = StreamingCapture(cell.index, self.output_queue)

        # Redirect stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        try:
            # Send status update
            self.output_queue.put(StreamChunk(
                cell_index=cell.index,
                stream_type='status',
                content='running'
            ))

            code = cell.source

            # Check for magic commands
            if cell.has_magic_commands() and self.has_ipython:
                # Use IPython to run cells with magic
                result = self.shell.run_cell(code)
                if not result.success:
                    raise result.error_in_exec if result.error_in_exec else Exception(t('execution_failed'))
            else:
                # Regular Python execution
                exec_globals = {**self.global_vars}
                exec_locals = {}

                exec(code, exec_globals, exec_locals)

                # Save variables to global scope
                for key, value in exec_locals.items():
                    if not key.startswith('_'):
                        self.global_vars[key] = value

            # Build output
            output = CellOutput(
                cell_index=cell.index,
                status=ExecutionStatus.SUCCESS,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                execution_time=time.time() - start_time,
                variables=[k for k in self.global_vars.keys() if not k.startswith('_')]
            )

            self.output_queue.put(StreamChunk(
                cell_index=cell.index,
                stream_type='status',
                content='success'
            ))

            return output

        except Exception as e:
            error_output = CellOutput(
                cell_index=cell.index,
                status=ExecutionStatus.ERROR,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
                execution_time=time.time() - start_time
            )

            self.output_queue.put(StreamChunk(
                cell_index=cell.index,
                stream_type='error',
                content=str(e)
            ))

            return error_output

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def get_variable(self, name: str) -> Any:
        """Get a variable from the global scope"""
        return self.global_vars.get(name)

    def set_variable(self, name: str, value: Any):
        """Set a variable in the global scope"""
        self.global_vars[name] = value


class RemoteExecutionEngine(ExecutionEngine):
    """
    Execute notebook cells on a remote PaddleCLI server with streaming output.

    Uses Server-Sent Events (SSE) or polling for streaming output.
    Supports execution interruption and status tracking.
    """

    def __init__(self, base_url: str, timeout: int = 300):
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._setup_session()
        self._execution_state = {
            "current_directory": "/home/aistudio",
            "command_history": [],
            "installed_packages": set(),
            "last_execution_time": None,
            "is_executing": False
        }

    def _setup_session(self):
        """Setup HTTP session"""
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PaddleCLI/2.1.3'
        })

    def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def execute_cell(self, cell: NotebookCell) -> CellOutput:
        """Execute a single cell on remote server"""
        if not cell.is_code:
            return CellOutput(
                cell_index=cell.index,
                status=ExecutionStatus.SKIPPED
            )

        if self._stop_requested:
            return CellOutput(
                cell_index=cell.index,
                status=ExecutionStatus.SKIPPED
            )

        start_time = time.time()

        # Send status update
        self.output_queue.put(StreamChunk(
            cell_index=cell.index,
            stream_type='status',
            content='running'
        ))

        try:
            # Prepare code - handle magic commands
            code = self._prepare_code(cell.source)

            # Execute on remote server
            response = self.session.post(
                f"{self.base_url}/execute",
                json={
                    "code": code,
                    "timeout": self.timeout
                },
                timeout=self.timeout + 30
            )
            response.raise_for_status()
            result = response.json()

            # Check if server was busy
            if result.get("error") == t('server_busy'):
                self.output_queue.put(StreamChunk(
                    cell_index=cell.index,
                    stream_type='error',
                    content=t('server_busy_waiting') + '\n'
                ))
                # Wait and retry once
                time.sleep(2)
                response = self.session.post(
                    f"{self.base_url}/execute",
                    json={"code": code, "timeout": self.timeout},
                    timeout=self.timeout + 30
                )
                result = response.json()

            # Stream output in real-time (simulated for non-streaming server)
            stdout_content = result.get("stdout", "")
            stderr_content = result.get("stderr", "")

            if stdout_content:
                self.output_queue.put(StreamChunk(
                    cell_index=cell.index,
                    stream_type='stdout',
                    content=stdout_content
                ))

            if stderr_content:
                self.output_queue.put(StreamChunk(
                    cell_index=cell.index,
                    stream_type='stderr',
                    content=stderr_content
                ))

            # Update local state tracking
            self._update_state_from_code(code, stdout_content)

            # Build output
            if result.get("success"):
                output = CellOutput(
                    cell_index=cell.index,
                    status=ExecutionStatus.SUCCESS,
                    stdout=stdout_content,
                    stderr=stderr_content,
                    execution_time=result.get("execution_time_sec", time.time() - start_time),
                    variables=result.get("variables", [])
                )

                self.output_queue.put(StreamChunk(
                    cell_index=cell.index,
                    stream_type='status',
                    content='success'
                ))
            else:
                output = CellOutput(
                    cell_index=cell.index,
                    status=ExecutionStatus.ERROR,
                    stdout=stdout_content,
                    stderr=stderr_content,
                    error=result.get("error"),
                    error_type=result.get("error_type"),
                    traceback=result.get("traceback"),
                    execution_time=result.get("execution_time_sec", time.time() - start_time)
                )

                self.output_queue.put(StreamChunk(
                    cell_index=cell.index,
                    stream_type='error',
                    content=result.get("error", t('unknown_error'))
                ))

            return output

        except Exception as e:
            error_output = CellOutput(
                cell_index=cell.index,
                status=ExecutionStatus.ERROR,
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
                execution_time=time.time() - start_time
            )

            self.output_queue.put(StreamChunk(
                cell_index=cell.index,
                stream_type='error',
                content=str(e)
            ))

            return error_output

    def _prepare_code(self, code: str) -> str:
        """
        Prepare code for remote execution.

        Convert magic commands to regular Python where possible.
        Supports: %cd, %pwd, %env, %set_env, !cmd, %pip, %%writefile, %%bash
        """
        import re

        lines = code.split('\n')
        prepared_lines = []
        in_cell_magic = False
        cell_magic_content = []
        cell_magic_type = None
        cell_magic_arg = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Handle cell magics (%%)
            if stripped.startswith('%%'):
                if in_cell_magic:
                    # End previous cell magic
                    prepared_lines.extend(self._process_cell_magic(cell_magic_type, cell_magic_arg, cell_magic_content))
                    cell_magic_content = []

                parts = stripped[2:].split(None, 1)
                cell_magic_type = parts[0].lower() if parts else ''
                cell_magic_arg = parts[1] if len(parts) > 1 else ''
                in_cell_magic = True
                continue

            # Collect cell magic content
            if in_cell_magic:
                cell_magic_content.append(line)
                continue

            # Handle %cd - change directory
            if stripped.startswith('%cd '):
                dir_path = stripped[4:].strip()
                # Remove quotes if present
                dir_path = dir_path.strip('"\'')
                _tpl = t('magic_cd')
                prepared_lines.append(f'import os; os.chdir({repr(dir_path)}); print({repr(_tpl)}.format(dir=os.getcwd()))')
            elif stripped == '%cd':
                _tpl = t('magic_pwd')
                prepared_lines.append(f'import os; print({repr(_tpl)}.format(dir=os.getcwd()))')

            # Handle %pwd - print working directory
            elif stripped == '%pwd':
                prepared_lines.append('import os; print(os.getcwd())')

            # Handle %env - show environment variables
            elif stripped == '%env':
                prepared_lines.append('import os; [print(f"{k}={v}") for k, v in sorted(os.environ.items())]')
            elif stripped.startswith('%env '):
                var_name = stripped[5:].strip()
                prepared_lines.append(f'import os; print(os.environ.get({repr(var_name)}, ""))')

            # Handle %set_env - set environment variable
            elif stripped.startswith('%set_env '):
                match = re.match(r'%set_env\s+(\w+)\s*(.*)', stripped)
                if match:
                    var_name, var_value = match.groups()
                    _tpl = t('magic_set_env')
                    prepared_lines.append(f'import os; os.environ[{repr(var_name)}] = {repr(var_value)}; print({repr(_tpl)}.format(name={repr(var_name)}, value={repr(var_value)}))')

            # Handle %pip install with full argument support
            elif stripped.startswith('%pip install') or stripped.startswith('%pip uninstall'):
                cmd_parts = stripped[5:].strip()  # Remove '%pip '
                prepared_lines.append(f'import subprocess, sys; result = subprocess.run([sys.executable, "-m", "pip"] + {repr(cmd_parts.split())}, capture_output=False); print()')

            # Handle !pip install with better support
            elif stripped.startswith('!pip install') or stripped.startswith('!pip uninstall'):
                cmd_parts = stripped[1:].strip()  # Remove '!'
                prepared_lines.append(f'import subprocess, sys; result = subprocess.run([sys.executable, "-m", "pip"] + {repr(cmd_parts.split()[1:])}, capture_output=False); print()')

            # Handle !shell_command with output capture
            elif stripped.startswith('!'):
                cmd = stripped[1:].strip()
                prepared_lines.append(f'''import subprocess; result = subprocess.run({repr(cmd)}, shell=True, capture_output=True, text=True); print(result.stdout, end=''); result.stderr and print(result.stderr, end='')''')

            # Handle other line magics
            elif stripped.startswith('%'):
                magic_match = re.match(r'%(\w+)\s*(.*)', stripped)
                if magic_match:
                    magic_name, magic_args = magic_match.groups()
                    # Try to convert known magics
                    if magic_name == 'time':
                        # %time command - just run the code with timing
                        _tpl = t('magic_time')
                        prepared_lines.append(f'import time; _start = time.time(); {magic_args}; print({repr(_tpl)}.format(time=round(time.time() - _start, 3)))')
                    elif magic_name == 'who':
                        _tpl = t('magic_who')
                        prepared_lines.append(f'print({repr(_tpl)}.format(vars=[k for k in dir() if not k.startswith("_")]))')
                    elif magic_name == 'reset':
                        prepared_lines.append(f'print({repr(t("magic_reset_skipped"))})')
                    elif magic_name == 'load':
                        prepared_lines.append(f'print({repr(t("magic_load_skipped", file=magic_args))})')
                    else:
                        prepared_lines.append(f'print({repr(t("magic_unknown", name=magic_name))})')
                else:
                    prepared_lines.append(f'# [Magic skipped]: {stripped}')

            else:
                prepared_lines.append(line)

        # Process any remaining cell magic content
        if in_cell_magic and cell_magic_content:
            prepared_lines.extend(self._process_cell_magic(cell_magic_type, cell_magic_arg, cell_magic_content))

        return '\n'.join(prepared_lines)

    def _process_cell_magic(self, magic_type: str, magic_arg: str, content: List[str]) -> List[str]:
        """Process cell magic content and return Python code lines."""
        result = []

        if magic_type == 'writefile':
            filename = magic_arg.strip()
            file_content = '\n'.join(content)
            _msg = t('magic_writefile', file=filename, size=len(file_content))
            result.append(f'''import os; _dir = os.path.dirname({repr(filename)}); _dir and os.makedirs(_dir, exist_ok=True); open({repr(filename)}, 'w').write({repr(file_content)}); print({repr(_msg)})''')

        elif magic_type == 'bash':
            bash_script = '\n'.join(content)
            result.append(f'''import subprocess; result = subprocess.run({repr(bash_script)}, shell=True, capture_output=True, text=True); print(result.stdout, end=''); result.stderr and print(result.stderr, end='')''')

        elif magic_type == 'html':
            html_content = '\n'.join(content)
            result.append(f'print({repr(html_content)})')

        elif magic_type == 'javascript' or magic_type == 'js':
            result.append(f'print({repr(t("magic_js_unavailable"))})')

        elif magic_type == 'timeit':
            code_to_time = '\n'.join(content)
            _tpl = t('magic_timeit')
            result.append(f'''import timeit; _result = timeit.timeit({repr(code_to_time)}, number=100); print({repr(_tpl)}.format(time=_result/100*1000))''')

        else:
            # Unknown cell magic - skip with warning
            result.append(f'# [Cell magic {magic_type} skipped]: {magic_arg}')
            result.extend([f'# {line}' for line in content])

        return result

    def probe_environment(self) -> Dict[str, Any]:
        """Probe remote environment"""
        try:
            response = self.session.get(
                f"{self.base_url}/probe",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def list_variables(self) -> Dict[str, Any]:
        """List variables on remote server"""
        try:
            response = self.session.get(
                f"{self.base_url}/variables",
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def cleanup(self) -> Dict[str, Any]:
        """Cleanup remote memory"""
        try:
            response = self.session.post(
                f"{self.base_url}/cleanup",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def interrupt(self) -> Dict[str, Any]:
        """
        Interrupt the current execution on the remote server.
        Does NOT stop the server itself, only the running code.
        """
        try:
            response = self.session.post(
                f"{self.base_url}/interrupt",
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            # Update local state
            if result.get("success"):
                self._execution_state["is_executing"] = False
            return result
        except Exception as e:
            return {"error": str(e), "success": False}

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current execution status from the remote server.
        Returns: current directory, running status, last command, etc.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/status",
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            # Sync local state
            if "current_directory" in result:
                self._execution_state["current_directory"] = result["current_directory"]
            if "is_executing" in result:
                self._execution_state["is_executing"] = result["is_executing"]
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_history(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get command execution history from the remote server.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/history",
                params={"limit": limit},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def sync_state(self) -> Dict[str, Any]:
        """
        Synchronize local state with remote server.
        Returns current directory and execution status.
        """
        status = self.get_status()
        if "error" not in status:
            self._execution_state["current_directory"] = status.get("current_directory", "/home/aistudio")
            self._execution_state["is_executing"] = status.get("is_executing", False)
        return status

    def _update_state_from_code(self, code: str, stdout: str = ""):
        """
        Update local state tracking based on executed code.
        Track directory changes, pip installs, etc.
        """
        # Track cd commands
        if "os.chdir(" in code:
            import re
            match = re.search(r"os\.chdir\(['\"]([^'\"]+)['\"]\)", code)
            if match:
                self._execution_state["current_directory"] = match.group(1)

        # Track pip installs
        if "pip install" in code or "pip uninstall" in code:
            import re
            # Extract package names
            matches = re.findall(r'pip\s+(?:install|uninstall)\s+([^\s]+)', code)
            for pkg in matches:
                if "install" in code:
                    self._execution_state["installed_packages"].add(pkg)

        # Add to history
        self._execution_state["command_history"].append({
            "code": code[:200] + "..." if len(code) > 200 else code,
            "timestamp": time.time(),
            "output_preview": stdout[:100] if stdout else ""
        })
        # Keep only last 50 commands
        if len(self._execution_state["command_history"]) > 50:
            self._execution_state["command_history"] = self._execution_state["command_history"][-50:]

    def execute_streaming(self, cell: NotebookCell, on_output: Callable[[Dict[str, Any]], None] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Execute a cell with streaming output using SSE.
        
        Args:
            cell: The notebook cell to execute
            on_output: Optional callback for each output chunk
            
        Yields:
            Dict with 'type' and 'content' keys for each output chunk
        """
        if not cell.is_code:
            yield {"type": "skipped", "content": t('non_code_cell')}
            return

        if self._stop_requested:
            yield {"type": "skipped", "content": t('execution_stopped')}
            return

        # Prepare code
        code = self._prepare_code(cell.source)
        
        # Send status update
        yield {"type": "status", "content": "running", "cell_index": cell.index}

        try:
            # Use SSE endpoint for streaming
            response = self.session.post(
                f"{self.base_url}/execute_stream",
                json={"code": code, "timeout": self.timeout},
                stream=True,
                timeout=self.timeout + 60,
                headers={'Accept': 'text/event-stream', 'Cache-Control': 'no-cache'}
            )
            response.raise_for_status()
            
            # Parse SSE events manually (more reliable than sseclient)
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            msg = json.loads(data_str)
                            if on_output:
                                on_output(msg)
                            yield msg
                        except json.JSONDecodeError:
                            yield {"type": "raw", "content": data_str}
                    elif line.startswith(':'):
                        # Heartbeat comment, ignore
                        pass
                        
        except Exception as e:
            yield {"type": "error", "content": str(e), "error_type": type(e).__name__}

    def _execute_streaming_manual(self, code: str, cell_index: int, on_output: Callable[[Dict[str, Any]], None] = None) -> Generator[Dict[str, Any], None, None]:
        """Manual SSE parsing fallback"""
        try:
            response = self.session.post(
                f"{self.base_url}/execute_stream",
                json={"code": code, "timeout": self.timeout},
                stream=True,
                timeout=self.timeout + 60,
                headers={'Accept': 'text/event-stream'}
            )
            response.raise_for_status()
            
            buffer = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            msg = json.loads(data_str)
                            if on_output:
                                on_output(msg)
                            yield msg
                        except json.JSONDecodeError:
                            yield {"type": "raw", "content": data_str}
                    elif line.startswith(':'):
                        # Heartbeat comment, ignore
                        pass
                        
        except Exception as e:
            yield {"type": "error", "content": str(e), "error_type": type(e).__name__}


class StreamingExecutor:
    """
    High-level streaming executor that handles output display.

    Combines execution engine with output formatting.
    """

    def __init__(
        self,
        engine: ExecutionEngine,
        show_markdown: bool = False,
        show_timing: bool = True,
        color_output: bool = True
    ):
        self.engine = engine
        self.show_markdown = show_markdown
        self.show_timing = show_timing
        self.color_output = color_output

        # Setup callbacks
        self.engine.on_cell_start = self._on_cell_start
        self.engine.on_cell_complete = self._on_cell_complete
        self.engine.on_stream = self._on_stream

    def _on_cell_start(self, cell: NotebookCell):
        """Handle cell start event"""
        pass  # Will be overridden by CLI

    def _on_cell_complete(self, cell: NotebookCell, output: CellOutput):
        """Handle cell complete event"""
        pass  # Will be overridden by CLI

    def _on_stream(self, chunk: StreamChunk):
        """Handle streaming output"""
        pass  # Will be overridden by CLI

    def run(
        self,
        notebook: Notebook,
        start_cell: int = 0,
        end_cell: Optional[int] = None,
        stop_on_error: bool = True
    ) -> List[CellOutput]:
        """Run notebook and collect all outputs"""
        self.engine.stop_on_error = stop_on_error
        results = []

        for output in self.engine.execute_notebook(
            notebook,
            start_cell=start_cell,
            end_cell=end_cell,
            skip_markdown=not self.show_markdown
        ):
            results.append(output)

        return results
