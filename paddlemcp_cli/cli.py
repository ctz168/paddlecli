#!/usr/bin/env python3
"""
PaddleCLI CLI - Command Line Interface

Run Jupyter Notebooks (.ipynb) with streaming output per cell.
"""

import json
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout

from .notebook import NotebookParser, Notebook, NotebookCell, CellType
from .executor import (
    LocalExecutionEngine,
    RemoteExecutionEngine,
    StreamingExecutor,
    CellOutput,
    ExecutionStatus,
    StreamChunk
)
from .i18n import t, set_lang, get_lang


console = Console()


def print_banner():
    """Print CLI banner"""
    banner = """
[bold cyan]╔═══════════════════════════════════════════════════════════════╗
║            🚀 PaddleCLI CLI - Notebook Runner                   ║
║         Run .ipynb files with streaming output                 ║
╚═══════════════════════════════════════════════════════════════╝[/bold cyan]
"""
    console.print(banner)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        mins, secs = divmod(seconds, 60)
        return f"{int(mins)}m {secs:.1f}s"


class StreamingRunner:
    """Run notebook with real-time streaming output display"""

    def __init__(
        self,
        engine,
        show_code: bool = True,
        show_markdown: bool = False,
        show_timing: bool = True,
        verbose: bool = False
    ):
        self.engine = engine
        self.show_code = show_code
        self.show_markdown = show_markdown
        self.show_timing = show_timing
        self.verbose = verbose
        self.results = []

        # Setup callbacks
        self.engine.on_cell_start = self._on_cell_start
        self.engine.on_cell_complete = self._on_cell_complete

    def _on_cell_start(self, cell: NotebookCell):
        """Handle cell start"""
        if cell.is_code:
            console.print(f"\n[bold blue]{t('cell_header', index=cell.index)}[/bold blue]")
            if self.show_code:
                syntax = Syntax(cell.source, "python", theme="monokai", line_numbers=False)
                console.print(Panel(syntax, border_style="blue", padding=(0, 1)))
            console.print(f"[dim]{t('cell_running')}[/dim]")

    def _on_cell_complete(self, cell: NotebookCell, output: CellOutput):
        """Handle cell complete"""
        if output.status == ExecutionStatus.SUCCESS:
            # Show output
            if output.stdout:
                console.print(output.stdout, end='')
            if output.stderr:
                console.print(f"[yellow]{output.stderr}[/yellow]", end='')

            # Show timing
            if self.show_timing:
                console.print(f"[dim]{t('cell_done', duration=format_duration(output.execution_time))}[/dim]")

        elif output.status == ExecutionStatus.ERROR:
            console.print(f"\n[bold red]{t('cell_error', index=cell.index)}[/bold red]")
            if output.error:
                console.print(f"[red]{output.error_type}: {output.error}[/red]")
            if output.traceback and self.verbose:
                console.print(f"\n[dim]{output.traceback}[/dim]")
            if output.stdout:
                console.print(f"[dim]{output.stdout}[/dim]")

        elif output.status == ExecutionStatus.SKIPPED:
            if self.verbose:
                console.print(f"[dim]{t('cell_skipped')}[/dim]")

        self.results.append(output)

    def run(self, notebook: Notebook, stop_on_error: bool = True,
            start_cell: int = 0, end_cell: Optional[int] = None) -> list:
        """Run the notebook"""
        self.engine.stop_on_error = stop_on_error
        self.results = []

        for output in self.engine.execute_notebook(
            notebook,
            start_cell=start_cell,
            end_cell=end_cell,
            skip_markdown=not self.show_markdown
        ):
            pass  # Callbacks handle output

        return self.results


@click.group(invoke_without_command=True)
@click.option('--version', '-v', is_flag=True, help='Show version')
@click.option('--lang', '-l', default=None, help='Language: en (default) or zh')
@click.pass_context
def main(ctx, version, lang):
    """PaddleCLI CLI - Run Jupyter Notebooks with streaming output"""
    if lang:
        set_lang(lang)
    if version:
        from . import __version__
        console.print(t('version', version=__version__))
        return

    if ctx.invoked_subcommand is None:
        # Show help when no subcommand
        console.print(ctx.get_help())


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--start', '-s', default=0, help='Start from cell index')
@click.option('--end', '-e', default=None, type=int, help='End at cell index')
@click.option('--show-code', is_flag=True, default=True, help='Show code before execution')
@click.option('--show-markdown', is_flag=True, help='Show markdown cells')
@click.option('--stop-on-error/--continue-on-error', default=True, help='Stop on error')
@click.option('--verbose', '-V', is_flag=True, help='Verbose output')
@click.option('--output', '-o', type=click.Path(), help='Save output to file')
def run(notebook, start, end, show_code, show_markdown, stop_on_error, verbose, output):
    """
    Run a Jupyter Notebook locally with streaming output.

    Example:
        paddlecli run notebook.ipynb
        paddlecli run notebook.ipynb --start 5 --end 10
        paddlecli run notebook.ipynb --show-markdown
    """
    print_banner()

    # Parse notebook
    notebook_path = Path(notebook)
    console.print(f"[cyan]{t('loading_notebook', name=notebook_path.name)}[/cyan]")

    try:
        nb = NotebookParser.parse_file(notebook_path)
    except Exception as e:
        console.print(f"[red]{t('failed_load', error=str(e))}[/red]")
        sys.exit(1)

    console.print(f"[green]{t('found_cells', total=len(nb.cells), code=len(nb.code_cells))}[/green]")

    # Create engine and runner
    engine = LocalExecutionEngine()
    runner = StreamingRunner(
        engine,
        show_code=show_code,
        show_markdown=show_markdown,
        verbose=verbose
    )

    # Run notebook
    console.print(f"\n[bold cyan]{t('executing')}[/bold cyan]\n")

    start_time = time.time()
    results = runner.run(nb, stop_on_error=stop_on_error, start_cell=start, end_cell=end)
    total_time = time.time() - start_time

    # Summary
    console.print(f"\n[bold]{'─' * 50}[/bold]")
    console.print(f"\n[bold cyan]{t('execution_summary')}[/bold cyan]")

    success_count = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)
    error_count = sum(1 for r in results if r.status == ExecutionStatus.ERROR)
    skipped_count = sum(1 for r in results if r.status == ExecutionStatus.SKIPPED)

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row(t('total_time'), format_duration(total_time))
    table.add_row(t('cells_executed'), str(len(results)))
    table.add_row(t('success'), str(success_count))
    if error_count > 0:
        table.add_row(t('errors'), f"[red]{error_count}[/red]")
    if skipped_count > 0:
        table.add_row(t('skipped'), str(skipped_count))

    console.print(table)

    # Save output if requested
    if output:
        output_data = {
            "notebook": str(notebook_path),
            "total_time": total_time,
            "results": [r.to_dict() for r in results]
        }
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        console.print(f"\n[green]{t('output_saved', path=output)}[/green]")

    # Exit with error code if there were errors
    if error_count > 0:
        sys.exit(1)


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--url', '-u', required=True, help='PaddleCLI server URL')
@click.option('--start', '-s', default=0, help='Start from cell index')
@click.option('--end', '-e', default=None, type=int, help='End at cell index')
@click.option('--show-code', is_flag=True, default=True, help='Show code before execution')
@click.option('--stop-on-error/--continue-on-error', default=True, help='Stop on error')
@click.option('--timeout', '-t', default=300, help='Timeout in seconds')
@click.option('--verbose', '-V', is_flag=True, help='Verbose output')
def remote(notebook, url, start, end, show_code, stop_on_error, timeout, verbose):
    """
    Run a Jupyter Notebook on a remote PaddleCLI server.

    Example:
        paddlecli remote notebook.ipynb --url https://xxxxxx.a.trycloudflare.com
        paddlecli remote notebook.ipynb -u https://aitun.cc/your-code -t 600
    """
    print_banner()

    # Parse notebook
    notebook_path = Path(notebook)
    console.print(f"[cyan]{t('loading_notebook', name=notebook_path.name)}[/cyan]")

    try:
        nb = NotebookParser.parse_file(notebook_path)
    except Exception as e:
        console.print(f"[red]{t('failed_load', error=str(e))}[/red]")
        sys.exit(1)

    console.print(f"[green]{t('found_cells', total=len(nb.cells), code=len(nb.code_cells))}[/green]")

    # Create remote engine
    console.print(f"\n[cyan]{t('connecting', url=url)}[/cyan]")
    engine = RemoteExecutionEngine(url, timeout=timeout)

    # Health check
    health = engine.health_check()
    if "error" in health:
        console.print(f"[red]{t('failed_connect', error=health['error'])}[/red]")
        sys.exit(1)

    console.print(f"[green]{t('connected', uptime=health.get('uptime_minutes', 'N/A'))}[/green]")

    # Create runner
    runner = StreamingRunner(
        engine,
        show_code=show_code,
        verbose=verbose
    )

    # Run notebook
    console.print(f"\n[bold cyan]{t('executing_remote')}[/bold cyan]\n")

    start_time = time.time()
    results = runner.run(nb, stop_on_error=stop_on_error, start_cell=start, end_cell=end)
    total_time = time.time() - start_time

    # Summary
    console.print(f"\n[bold]{'─' * 50}[/bold]")
    console.print(f"\n[bold cyan]{t('execution_summary')}[/bold cyan]")

    success_count = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)
    error_count = sum(1 for r in results if r.status == ExecutionStatus.ERROR)

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row(t('total_time'), format_duration(total_time))
    table.add_row(t('cells_executed'), str(len(results)))
    table.add_row(t('success'), str(success_count))
    if error_count > 0:
        table.add_row(t('errors'), f"[red]{error_count}[/red]")

    console.print(table)

    if error_count > 0:
        sys.exit(1)


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output Python file')
def convert(notebook, output):
    """
    Convert a Jupyter Notebook to a Python script.

    Example:
        paddlecli convert notebook.ipynb -o script.py
    """
    print_banner()

    notebook_path = Path(notebook)
    console.print(f"[cyan]{t('converting', name=notebook_path.name)}[/cyan]")

    try:
        nb = NotebookParser.parse_file(notebook_path)
    except Exception as e:
        console.print(f"[red]{t('failed_load', error=str(e))}[/red]")
        sys.exit(1)

    # Extract code
    code = NotebookParser.extract_code(nb, skip_markdown=False)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = notebook_path.with_suffix('.py')

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)

    console.print(f"[green]{t('converted_to', path=output_path)}[/green]")


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
def info(notebook):
    """
    Show information about a Jupyter Notebook.

    Example:
        paddlecli info notebook.ipynb
    """
    print_banner()

    notebook_path = Path(notebook)
    console.print(f"[cyan]{t('analyzing', name=notebook_path.name)}[/cyan]\n")

    try:
        nb = NotebookParser.parse_file(notebook_path)
    except Exception as e:
        console.print(f"[red]{t('failed_load', error=str(e))}[/red]")
        sys.exit(1)

    # Notebook info table
    table = Table(title=t('notebook_info'), show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row(t('path'), str(nb.path))
    table.add_row(t('format'), f"nbformat {nb.nbformat}.{nb.nbformat_minor}")
    table.add_row(t('total_cells'), str(len(nb.cells)))
    table.add_row(t('code_cells'), str(len(nb.code_cells)))
    table.add_row(t('markdown_cells'), str(len(nb.markdown_cells)))

    # Kernel info
    kernel = nb.metadata.get('kernelspec', {})
    if kernel:
        table.add_row(t('kernel'), kernel.get('display_name', t('unknown')))
        table.add_row(t('language'), kernel.get('language', t('unknown')))

    console.print(table)

    # Cell list
    if nb.cells:
        console.print(f"\n[bold]{t('cell_overview')}[/bold]\n")

        cell_table = Table(show_header=True, header_style="bold cyan")
        cell_table.add_column("#", justify="right", width=4)
        cell_table.add_column(t('path'), width=10)
        cell_table.add_column("Lines", justify="right", width=6)
        cell_table.add_column("Preview")

        for cell in nb.cells:
            preview = cell.source[:50].replace('\n', ' ')
            if len(cell.source) > 50:
                preview += "..."

            cell_table.add_row(
                str(cell.index),
                cell.cell_type.value,
                str(len(cell.get_source_lines())),
                preview
            )

        console.print(cell_table)

    # Tags
    tags = set()
    for cell in nb.code_cells:
        cell_tags = cell.metadata.get('tags', [])
        tags.update(cell_tags)

    if tags:
        console.print(f"\n[bold]{t('tags_found', tags=', '.join(sorted(tags)))}[/bold]")


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--start', '-s', default=0, help='Start from cell index')
@click.option('--end', '-e', default=None, type=int, help='End at cell index')
@click.option('--verbose', '-V', is_flag=True, help='Verbose output')
def cells(notebook, start, end, verbose):
    """
    List and preview cells in a notebook.

    Example:
        paddlecli cells notebook.ipynb
        paddlecli cells notebook.ipynb --start 5 --end 10
    """
    print_banner()

    notebook_path = Path(notebook)
    console.print(f"[cyan]{t('reading', name=notebook_path.name)}[/cyan]\n")

    try:
        nb = NotebookParser.parse_file(notebook_path)
    except Exception as e:
        console.print(f"[red]{t('failed_load', error=str(e))}[/red]")
        sys.exit(1)

    cells_to_show = nb.cells[start:end]

    for cell in cells_to_show:
        # Header
        cell_type_emoji = "📝" if cell.is_markdown else "🐍"
        console.print(f"\n[bold blue]{'─' * 50}[/bold blue]")
        console.print(f"[bold]{cell_type_emoji} {t('cell_header', index=cell.index)} - {cell.cell_type.value}[/bold]")

        # Metadata
        if verbose and cell.metadata:
            console.print(f"[dim]Metadata: {cell.metadata}[/dim]")

        # Content
        if cell.is_code:
            syntax = Syntax(cell.source, "python", theme="monokai", line_numbers=True)
            console.print(syntax)
        elif cell.is_markdown:
            md = Markdown(cell.source)
            console.print(md)
        else:
            console.print(cell.source)

    console.print(f"\n[bold]{'─' * 50}[/bold]")
    console.print(f"\n[cyan]{t('total_shown', total=len(cells_to_show))}[/cyan]")


@main.command()
@click.option('--url', '-u', required=True, help='PaddleCLI server URL')
def health(url):
    """
    Check health of a PaddleCLI server.

    Example:
        paddlecli health --url https://xxxxxx.a.trycloudflare.com
    """
    print_banner()

    console.print(f"[cyan]{t('health_checking', url=url)}[/cyan]\n")

    engine = RemoteExecutionEngine(url)
    result = engine.health_check()

    if "error" in result:
        console.print(f"[red]{t('connection_failed', error=result['error'])}[/red]")
        sys.exit(1)

    # Display health info
    table = Table(title=t('server_health'), show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row(t('status'), f"[green]{result.get('status', t('unknown'))}[/green]")
    table.add_row(t('uptime'), f"{result.get('uptime_minutes', 'N/A')} minutes")
    table.add_row(t('memory_available'), f"{result.get('memory_available_gb', 'N/A')} GB")
    table.add_row(t('memory_total'), f"{result.get('memory_total_gb', 'N/A')} GB")
    table.add_row(t('memory_used'), f"{result.get('memory_used_pct', 'N/A')}%")
    table.add_row(t('gpu_available'), t('yes') if result.get('gpu_available') else t('no'))

    console.print(table)

    # Probe environment
    console.print(f"\n[cyan]{t('probing_environment')}[/cyan]\n")

    probe = engine.probe_environment()
    if "error" not in probe:
        console.print(f"[dim]{t('python', version=probe.get('python_version', 'N/A')[:60])}...[/dim]")
        console.print(f"[dim]{t('total_packages', count=probe.get('total_packages', 'N/A'))}[/dim]")

        gpu_info = probe.get('gpu_info', '')
        if gpu_info and 'No GPU' not in gpu_info:
            console.print(f"\n[bold]{t('gpu_info')}[/bold]")
            for line in gpu_info.strip().split('\n')[:5]:
                console.print(f"  [dim]{line}[/dim]")


@main.command()
def repl():
    """
    Start an interactive REPL for executing Python code.

    Example:
        paddlecli repl
    """
    print_banner()

    console.print(f"[bold]{t('repl_title')}[/bold]")
    console.print(f"[dim]{t('repl_exit_hint')}[/dim]\n")

    engine = LocalExecutionEngine()

    while True:
        try:
            # Read multi-line input
            console.print(f"[bold cyan]{t('repl_prompt')}[/bold cyan] ", end='')
            lines = []
            while True:
                try:
                    line = input()
                    if not lines and not line:
                        break
                    lines.append(line)
                    if not line.endswith(':') and (not lines or lines[-1] == ''):
                        break
                    if lines and not line.startswith(' ') and lines[-1] and not lines[-1].endswith(':'):
                        break
                except EOFError:
                    if not lines:
                        raise
                    break

            code = '\n'.join(lines)

            if code.strip().lower() in ('exit', 'quit', 'q'):
                console.print(f"\n[green]{t('goodbye')}[/green]")
                break

            if not code.strip():
                continue

            # Create a fake cell and execute
            from .notebook import NotebookCell
            cell = NotebookCell(
                index=0,
                cell_type=CellType.CODE,
                source=code
            )

            output = engine.execute_cell(cell)

            if output.stdout:
                console.print(output.stdout, end='')
            if output.stderr:
                console.print(f"[yellow]{output.stderr}[/yellow]", end='')
            if output.error:
                console.print(f"[red]{output.error_type}: {output.error}[/red]")

        except KeyboardInterrupt:
            console.print(f"\n[red]{t('interrupted')}[/red]")
            continue
        except EOFError:
            console.print(f"\n[green]{t('goodbye')}[/green]")
            break


@main.command()
@click.option('--url', '-u', required=True, help='PaddleCLI server URL')
def interrupt(url):
    """
    Interrupt the current execution on the remote server.
    Does NOT stop the server, only the running code.

    Example:
        paddlecli interrupt --url https://aitun.cc/your-code
    """
    print_banner()

    console.print(f"[yellow]{t('interrupting_exec', url=url)}[/yellow]\n")

    engine = RemoteExecutionEngine(url)
    result = engine.interrupt()

    if result.get("success"):
        console.print(f"[green]{t('exec_interrupted')}[/green]")
        if result.get("message"):
            console.print(f"[dim]{result['message']}[/dim]")
    else:
        error = result.get("error", t('unknown_error'))
        console.print(f"[red]{t('interrupt_failed', error=error)}[/red]")
        sys.exit(1)


@main.command()
@click.option('--url', '-u', required=True, help='PaddleCLI server URL')
def status(url):
    """
    Get the current execution status from the remote server.
    Shows current directory, running status, last command, etc.

    Example:
        paddlecli status --url https://aitun.cc/your-code
    """
    print_banner()

    console.print(f"[cyan]{t('getting_status', url=url)}[/cyan]\n")

    engine = RemoteExecutionEngine(url)
    result = engine.get_status()

    if "error" in result:
        console.print(f"[red]{t('get_status_failed', error=result['error'])}[/red]")
        sys.exit(1)

    # Display status info
    table = Table(title=t('server_status'), show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row(t('is_executing'), "🔄 Yes" if result.get("is_executing") else "✅ No")
    table.add_row(t('current_directory'), result.get("current_directory", "N/A"))
    table.add_row(t('last_command'), result.get("last_command", "N/A")[:80])
    table.add_row(t('last_execution_time'), f"{result.get('last_execution_time', 0):.2f}s")

    console.print(table)

    # Show recent history
    history = result.get("recent_history", [])
    if history:
        console.print(f"\n[bold]{t('recent_commands')}[/bold]\n")
        for i, cmd in enumerate(history[-5:]):
            console.print(f"  [dim]{i+1}.[/dim] {cmd[:100]}{'...' if len(cmd) > 100 else ''}")


@main.command()
@click.option('--url', '-u', required=True, help='PaddleCLI server URL')
@click.option('--limit', '-l', default=20, help='Number of history entries to show')
def history(url, limit):
    """
    Get command execution history from the remote server.

    Example:
        paddlecli history --url https://aitun.cc/your-code
        paddlecli history --url https://aitun.cc/your-code --limit 50
    """
    print_banner()

    console.print(f"[cyan]{t('getting_history', url=url)}[/cyan]\n")

    engine = RemoteExecutionEngine(url)
    result = engine.get_history(limit=limit)

    if "error" in result:
        console.print(f"[red]{t('history_failed', error=result['error'])}[/red]")
        sys.exit(1)

    history_entries = result.get("history", [])
    if not history_entries:
        console.print(f"[dim]{t('no_command_history')}[/dim]")
        return

    console.print(f"[bold]{t('command_history', count=len(history_entries))}[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right", width=4)
    table.add_column(t('time'), width=10)
    table.add_column(t('directory'), width=20)
    table.add_column(t('command_preview'))

    for i, entry in enumerate(history_entries):
        timestamp = entry.get("timestamp", "")
        if isinstance(timestamp, (int, float)):
            from datetime import datetime
            timestamp = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        
        directory = entry.get("directory", "")[-20:]
        cmd_preview = entry.get("command", "")[:60]
        if len(entry.get("command", "")) > 60:
            cmd_preview += "..."

        table.add_row(str(i + 1), str(timestamp), directory, cmd_preview)

    console.print(table)


@main.command()
@click.argument('notebook', type=click.Path(exists=True))
@click.option('--url', '-u', required=True, help='PaddleCLI server URL')
@click.option('--start', '-s', default=0, help='Start from cell index')
@click.option('--end', '-e', default=None, type=int, help='End at cell index (exclusive)')
@click.option('--timeout', '-t', default=600, help='Timeout in seconds for streaming')
@click.option('--verbose', '-V', is_flag=True, help='Verbose output')
@click.option('--stop-on-error/--continue-on-error', default=True, help='Stop on error')
def stream(notebook, url, start, end, timeout, verbose, stop_on_error):
    """
    Run a Jupyter Notebook with REAL-TIME STREAMING output.
    
    Uses SSE (Server-Sent Events) for live output - perfect for 
    long-running tasks like training, bots, or continuous processes.

    Example:
        paddlecli stream notebook.ipynb -u https://aitun.cc/your-code
        paddlecli stream notebook.ipynb -u https://aitun.cc/your-code --start 3 --end 4
    """
    print_banner()

    # Parse notebook
    notebook_path = Path(notebook)
    console.print(f"[cyan]{t('loading_notebook', name=notebook_path.name)}[/cyan]")

    try:
        nb = NotebookParser.parse_file(notebook_path)
    except Exception as e:
        console.print(f"[red]{t('failed_load', error=str(e))}[/red]")
        sys.exit(1)

    code_cells = [c for c in nb.cells[start:end] if c.is_code]
    console.print(f"[green]{t('found_cells_stream', total=len(nb.cells), code=len(code_cells))}[/green]")

    # Create remote engine
    console.print(f"\n[cyan]{t('connecting', url=url)}[/cyan]")
    engine = RemoteExecutionEngine(url, timeout=timeout)

    # Health check
    health = engine.health_check()
    if "error" in health:
        console.print(f"[red]{t('failed_connect', error=health['error'])}[/red]")
        sys.exit(1)

    console.print(f"[green]{t('connected', uptime=health.get('uptime_minutes', 'N/A'))}[/green]")

    # Stream each cell
    console.print(f"\n[bold cyan]{t('executing_stream')}[/bold cyan]")
    console.print(f"[dim]{t('press_ctrl_c')}[/dim]\n")

    start_time = time.time()
    total_outputs = 0
    execution_stopped = False

    for cell in code_cells:
        if execution_stopped:
            break
        console.print(f"\n[bold blue]{t('cell_header', index=cell.index)}[/bold blue]")
        if verbose:
            syntax = Syntax(cell.source, "python", theme="monokai", line_numbers=False)
            console.print(Panel(syntax, border_style="blue", padding=(0, 1)))
        
        console.print(f"[dim]{t('cell_streaming')}[/dim]")

        try:
            for msg in engine.execute_streaming(cell):
                msg_type = msg.get("type", "unknown")
                content = msg.get("content", "")

                if msg_type == "stdout":
                    console.print(content, end='')
                    total_outputs += 1
                elif msg_type == "stderr":
                    console.print(f"[yellow]{content}[/yellow]", end='')
                elif msg_type == "status":
                    console.print(f"[dim]📌 {content}[/dim]")
                elif msg_type == "complete":
                    console.print(f"\n[green]{content}[/green]")
                elif msg_type == "error":
                    console.print(f"\n[red]❌ {content}[/red]")
                    if stop_on_error:
                        execution_stopped = True
                        break
                elif msg_type == "skipped":
                    console.print(f"[dim]⏭️ {content}[/dim]")

            if execution_stopped and stop_on_error:
                console.print(f"\n[yellow]{t('stream_stopped_on_error')}[/yellow]")
                break

        except KeyboardInterrupt:
            console.print(f"\n[yellow]{t('interrupting')}[/yellow]")
            # Send interrupt to server
            engine.interrupt()
            console.print(f"[yellow]{t('interrupted_by_user')}[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]{t('stream_error', error=str(e))}[/red]")
            if verbose:
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            if stop_on_error:
                execution_stopped = True

    total_time = time.time() - start_time

    # Summary
    console.print(f"\n[bold]{'─' * 50}[/bold]")
    console.print(f"\n[bold cyan]{t('stream_summary')}[/bold cyan]")

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row(t('total_time'), format_duration(total_time))
    table.add_row(t('output_lines'), str(total_outputs))

    console.print(table)


@main.command()
@click.option('--url', '-u', required=True, help='PaddleCLI server URL')
@click.option('--duration', '-d', default=300, help='Duration to watch in seconds (0 = infinite)')
def watch(url, duration):
    """
    Watch the remote server status in real-time.
    
    Useful for monitoring long-running executions.

    Example:
        paddlecli watch -u https://aitun.cc/your-code
        paddlecli watch -u https://aitun.cc/your-code -d 60
    """
    print_banner()
    
    console.print(f"[cyan]{t('watching_server', url=url)}[/cyan]")
    console.print(f"[dim]{t('duration', duration=duration)}[/dim]\n")

    engine = RemoteExecutionEngine(url)
    start_time = time.time()
    
    try:
        iteration = 0
        while True:
            elapsed = time.time() - start_time
            if duration > 0 and elapsed > duration:
                console.print(f"\n[yellow]{t('watch_duration_reached')}[/yellow]")
                break

            status = engine.get_status()
            if "error" in status:
                console.print(f"[red]{t('watch_error', error=status['error'])}[/red]")
                time.sleep(5)
                continue

            # Build status line
            is_exec = status.get("is_executing", False)
            exec_status = t('watch_running') if is_exec else t('watch_idle')
            cwd = status.get("current_directory", "/home/aistudio")
            last_cmd = status.get("last_command", "")[:50]
            
            # Clear line and print
            console.print(
                f"\r[dim][{format_duration(elapsed)}][/dim] "
                f"{exec_status} | 📁 {cwd[-30:]} | "
                f"[dim]{last_cmd}[/dim]",
                end=""
            )
            
            iteration += 1
            time.sleep(2)
            
    except KeyboardInterrupt:
        console.print(f"\n\n[yellow]{t('watch_stopped')}[/yellow]")




@main.command(name='exec')
@click.option('--url', '-u', required=True, help='paddlecli server URL')
@click.option('--code', '-c', default=None, help='Code to execute (stdin is read when omitted)')
@click.option('--c64', default=None, help='base64url-encoded code — quoting-proof argv for agents')
@click.option('--timeout', '-t', default=600, help='Timeout in seconds')
@click.option('--json', 'json_out', is_flag=True, default=False,
              help='Emit the raw server JSON result (agent-friendly; exit 0 success / 1 error)')
@click.option('--plain', is_flag=True, default=False,
              help='With --json: decode *_b64 fields back to plain text locally '
                   '(human-readable; NOT safe through quote-mangling transports)')
def exec_code(url, code, c64, timeout, json_out, plain):
    """
    Execute ONE code snippet on the paddlecli server — one-shot, quoting-proof.

    Built for AI agents whose command text must survive quote-mangling
    transports (IM gateways, chat bridges). Three input modes, safest first:

    \b
      1. Samai Command Envelope on stdin — payload is base64url, CRC-checked:

             cat env.txt | paddlecli exec -u URL

      2. --c64 <base64url-of-code> — a pure [A-Za-z0-9_-] argv, no quoting

      3. -c 'code' or plain stdin — convenience for humans

    The envelope is auto-detected on stdin; plain stdin is sent as-is.

    \b
    With --json, stdout is ONE JSON object, pure printable ASCII:
      - the server is asked for respenc=b64url, so text fields come back as
        stdout_b64/stderr_b64/... (plain fields blanked) — decode them with
        unpadded urlsafe base64;
      - any non-ASCII content is escaped as \\uXXXX sequences in JSON strings; failures also emit JSON
        (exit 0 success / 1 exec error / 2 transport-setup error).
      - add --plain to decode *_b64 locally (readable, but the text then
        travels unprotected through whatever returns it to you).
    """
    import base64 as b64mod
    from . import envelope as sce

    def _json_error(err, etype="ClientError", exit_code=2):
        # --json must ALWAYS answer with one parseable JSON object on stdout;
        # ensure_ascii=True keeps it byte-exact through any return transport.
        print(json.dumps({"success": False, "error": err, "error_type": etype},
                         ensure_ascii=True))
        sys.exit(exit_code)

    source_desc = "-c"
    if c64:
        try:
            code = b64mod.urlsafe_b64decode(c64 + "=" * (-len(c64) % 4)).decode("utf-8")
        except Exception as e:
            if json_out:
                _json_error(str(e), "BadC64")
            console.print(f"[red]{t('exec_bad_c64', err=str(e))}[/red]")
            sys.exit(2)
        source_desc = "--c64"
    else:
        from_stdin = code is None and not sys.stdin.isatty()
        raw = code if code is not None else (sys.stdin.read() if from_stdin else "")
        if not raw:
            if json_out:
                _json_error(t('exec_no_input'), "NoInput")
            console.print(f"[red]{t('exec_no_input')}[/red]")
            sys.exit(2)
        if sce.sniff(raw):
            try:
                code = sce.parse(raw).decode("utf-8", "replace")
            except sce.EnvelopeError as e:
                if json_out:
                    _json_error(str(e), "EnvelopeError")
                console.print(f"[red]{t('exec_envelope_bad', err=str(e))}[/red]")
                sys.exit(2)
            source_desc = "envelope (CRC OK)"
            if not json_out:
                console.print(f"[dim]{t('exec_envelope_ok')}[/dim]")
        else:
            code = raw
            source_desc = "stdin" if from_stdin else "-c"

    engine = RemoteExecutionEngine(url, timeout=timeout)

    if json_out:
        try:
            code = engine._prepare_code(code)   # magic/!cmd support, same as cells
            resp = engine.session.post(
                f"{engine.base_url}/execute",
                params={"respenc": "b64url"},
                json={"code": code, "timeout": timeout},
                timeout=timeout + 30,
            )
        except Exception as e:
            _json_error(str(e), "ConnectionError")

        if resp.status_code >= 400:
            # surface the server's own error body when it is JSON (respenc
            # armed error responses keep *_b64 fields); never hide it behind
            # a bare raise_for_status()
            try:
                body = resp.json()
            except Exception:
                body = None
            if isinstance(body, dict) and body:
                body.setdefault("success", False)
                body["http_status"] = resp.status_code
                print(json.dumps(sce.decode_respenc(body, plain=plain),
                                 ensure_ascii=not plain))
                sys.exit(1)
            _json_error("HTTP %s from server" % resp.status_code, "HTTPError")

        try:
            result = resp.json()
        except Exception as e:
            _json_error("server returned a non-JSON body: %s" % e, "BadResponse")

        # v2.1.0 fix ("response unreliable though execution effective"):
        # print the respenc-armed response VERBATIM — *_b64 fields stay
        # byte-exact and ensure_ascii=True keeps the whole line pure ASCII,
        # so the return path through chat bridges cannot mangle it.
        # The OLD code decoded *_b64 back to plain text here, re-exposing
        # it to quote-mangling transports right before the last hop.
        result = sce.decode_respenc(result, plain=plain)
        print(json.dumps(result, ensure_ascii=not plain))
        sys.exit(0 if result.get("success") else 1)

    # human mode: live-stream via SSE
    health = engine.health_check()
    if "error" in health:
        console.print(f"[red]{t('failed_connect', error=health['error'])}[/red]")
        sys.exit(2)

    cell = NotebookCell(index=0, cell_type=CellType.CODE, source=code)
    had_error = False
    try:
        for msg in engine.execute_streaming(cell):
            mtype = msg.get("type", "unknown")
            content = msg.get("content", "")
            if mtype == "stdout":
                console.print(content, end="")
            elif mtype == "stderr":
                console.print(f"[yellow]{content}[/yellow]", end="")
            elif mtype == "error":
                had_error = True
                console.print(f"\n[red]{t('exec_cell_error', err=content)}[/red]")
            elif mtype == "status":
                console.print(f"[dim]{content}[/dim]")
    except KeyboardInterrupt:
        console.print(f"\n[yellow]{t('execution_interrupted')}[/yellow]")
        sys.exit(130)
    sys.exit(1 if had_error else 0)


if __name__ == '__main__':
    main()