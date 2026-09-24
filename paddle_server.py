import os
import sys
import json
import time
import traceback
import subprocess
import gc
import threading
import signal
import ctypes
import queue
import re
from datetime import datetime
from flask import Flask, request, jsonify, Response
import psutil

# ============== i18n ==============
_LANG = os.environ.get('PADDLECLI_LANG', 'en').lower()
if _LANG not in ('en', 'zh'):
    _LANG = 'en'

def t(key, **kwargs):
    """Get translated string by key, with optional format arguments."""
    translations = {
        'en': {
            'server_starting': '🚀 PaddleCLI server starting...',
            'server_version': 'Version: {version}',
            'server_features': 'Features: {features}',
            'server_optimization': 'Optimization: {optimization}',
            'server_stopped': 'Stop signal received, shutting down...',
            'server_internal_error': 'Internal server error: {error}',
            'server_start_failed': '[Error] Flask failed to start: {error}',
            'no_code_provided': 'No code provided',
            'execution_interrupted': 'Execution interrupted by user',
            'execution_interrupted_msg': '⚠️ Execution interrupted by user',
            'interrupt_sent': 'Interrupt signal sent',
            'interrupt_failed_msg': 'Interrupt failed, please try again later',
            'interrupt_processed': 'Interrupt request processed',
            'no_running_task': 'No running task',
            'user_interrupt': 'User interrupt',
            'server_busy': 'Another code is executing, please try again later',
            'executing_shell': 'Executing: {cmd}',
            'executing_python': 'Executing Python code...',
            'complete_shell': '✅ Done (exit code: {code}, time: {time}s)',
            'complete_python': '✅ Done (time: {time}s)',
            'error_prefix': '❌ Error: {error}',
            'interrupt_history': 'Interrupted',
            'signal_received': '[Signal] Stop signal received, shutting down...',
            'interrupt_attempt_failed': '[Interrupt] Failed to interrupt: {error}',
            'heartbeat': '[Heartbeat] {time} - Running | Directory: {directory}{exec_flag}',
            'heartbeat_error': '[Heartbeat Error] {error}',
            'interrupt_flag': ' [Executing]',
            'gpu_no_available': 'No GPU available',
            'memory_cleaned': 'Memory cleaned',
        },
        'zh': {
            'server_starting': '🚀 PaddleCLI 服务器启动中...',
            'server_version': '版本: {version}',
            'server_features': '功能: {features}',
            'server_optimization': '优化: {optimization}',
            'server_stopped': '收到停止信号，正在关闭...',
            'server_internal_error': '服务器内部错误: {error}',
            'server_start_failed': '[错误] Flask 启动失败: {error}',
            'no_code_provided': '未提供代码',
            'execution_interrupted': '执行被用户中断',
            'execution_interrupted_msg': '⚠️ 执行被用户中断',
            'interrupt_sent': '已发送中断信号',
            'interrupt_failed_msg': '中断失败，请稍后重试',
            'interrupt_processed': '中断请求已处理',
            'no_running_task': '当前没有正在执行的任务',
            'user_interrupt': '用户中断',
            'server_busy': '另一个代码正在执行中，请稍后重试',
            'executing_shell': '执行: {cmd}',
            'executing_python': '执行 Python 代码...',
            'complete_shell': '✅ 完成 (退出码: {code}, 耗时: {time}s)',
            'complete_python': '✅ 完成 (耗时: {time}s)',
            'error_prefix': '❌ 错误: {error}',
            'interrupt_history': '中断',
            'signal_received': '[信号] 收到停止信号，正在关闭...',
            'interrupt_attempt_failed': '[中断] 尝试中断失败: {error}',
            'heartbeat': '[心跳] {time} - 运行中 | 目录: {directory}{exec_flag}',
            'heartbeat_error': '[心跳错误] {error}',
            'interrupt_flag': ' [执行中]',
            'gpu_no_available': '无可用 GPU',
            'memory_cleaned': '内存已清理',
        },
    }
    template = translations.get(_LANG, translations['en']).get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template

# ============== 全局状态 ==============
runtime_variables = {}
start_time = time.time()
execution_lock = threading.Lock()
keep_running = True

# 执行状态跟踪
execution_state = {
    "current_directory": "/home/aistudio",
    "is_executing": False,
    "last_command": "",
    "last_execution_time": 0,
    "last_error": None,
    "command_history": [],
    "installed_packages": set()
}

# 当前执行的线程引用
current_execution_thread = None
interrupt_requested = False

# 流式输出队列
stream_output_queue = None
stream_active = False

# 创建 Flask 应用
app = Flask(__name__)

# ============== 心跳保活线程 ==============
def heartbeat_thread():
    """心跳线程，防止 AI Studio 休眠"""
    last_ping = time.time()

    while keep_running:
        try:
            current_time = time.strftime("%H:%M:%S")
            is_exec = execution_state['is_executing']
            exec_flag = t('interrupt_flag') if is_exec else ""
            print(t('heartbeat', time=current_time, directory=execution_state['current_directory'], exec_flag=exec_flag), flush=True)

            # 不再请求 /health 端点，避免与执行锁冲突
            # AI Studio 自身有保活机制，只需打印日志即可
            last_ping = time.time()

            time.sleep(60)  # 30→60秒，减少心跳频率
        except Exception as e:
            print(t('heartbeat_error', error=str(e)), flush=True)
            time.sleep(30)

# ============== 辅助函数 ==============
def _check_gpu():
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def _add_to_history(command, output_preview="", success=True):
    """添加命令到历史记录"""
    entry = {
        "command": command[:500],
        "output_preview": output_preview[:200],
        "timestamp": time.time(),
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "directory": execution_state["current_directory"],
        "success": success
    }
    execution_state["command_history"].append(entry)
    if len(execution_state["command_history"]) > 100:
        execution_state["command_history"] = execution_state["command_history"][-100:]

def _update_directory_from_code(code):
    """从代码中提取目录变化"""
    import re
    match = re.search(r"os\.chdir\(['\"]([^'\"]+)['\"]\)", code)
    if match:
        new_dir = match.group(1)
        execution_state["current_directory"] = new_dir
        return new_dir
    return None

def _interrupt_thread(thread):
    """尝试中断线程中的执行"""
    global interrupt_requested
    interrupt_requested = True
    if thread and thread.is_alive():
        try:
            thread_id = thread.ident
            if thread_id:
                exc = KeyboardInterrupt()
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_long(thread_id),
                    ctypes.py_object(exc)
                )
        except Exception as e:
            print(t('interrupt_attempt_failed', error=str(e)), flush=True)
    return True

# ============== API Endpoints ==============

# ====== Samai Command Envelope (SCE) v1 — quoting-proof framing (v2.1.0) ======
# Self-contained port of samaidev/samcommand internal/envelope (MIT).
# Why: AI-agent commands often travel through quote-mangling transports
# (IM gateways, chat bridges). The envelope wraps code in
#     samaicmdbegin / v=1 / enc=b64url / crc=<crc32> / <b64url payload> / samaicmdend
# so the payload contains ONLY [A-Za-z0-9-_] — nothing any gateway can mangle.
# /execute and /execute_stream accept such a body as an alternative to JSON,
# and any endpoint honours ?respenc=b64url on the way back (text fields move
# into *_b64 so the RETURN path survives chat bridges too).

_SCE_BEGIN = "samaicmdbegin"
_SCE_END = "samaicmdend"


def _sce_parse(text):
    """Decode the first Samai Command Envelope in *text*; returns payload bytes.

    Faithful port of the Go parser semantics: only v=/enc=/crc= are headers;
    b64/b64url/hex payloads ignore ALL whitespace (re-wrapped lines are
    harmless), padding is optional, both base64 alphabets auto-detected;
    raw payloads join lines with \n; CRC32 verified when present."""
    import base64 as _b64
    import binascii as _ba
    import zlib as _zlib
    lines = text.replace("\r\n", "\n").split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == _SCE_BEGIN), -1)
    if start < 0:
        raise ValueError("envelope: no '%s' marker found" % _SCE_BEGIN)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == _SCE_END), -1)
    if end < 0:
        raise ValueError("envelope: no '%s' marker found" % _SCE_END)
    ver, enc, crc = "1", "b64url", ""
    body = start + 1
    while body < end:
        s = lines[body].lstrip(" \t")
        if s.startswith("v="):
            ver = s[2:].strip()
            if ver != "1":
                raise ValueError("envelope: unsupported v= (only v=1): %r" % ver)
        elif s.startswith("enc="):
            enc = s[4:].strip().lower()
        elif s.startswith("crc="):
            crc = s[4:].strip().lower()
        else:
            break
        body += 1
    body_lines = lines[body:end]
    if not body_lines or all(not ln.strip() for ln in body_lines):
        raise ValueError("envelope: empty payload")
    joined = "\n".join(body_lines)
    if enc == "raw":
        for ln in body_lines:
            if ln.strip() == _SCE_END:
                raise ValueError("envelope: raw payload contains the end marker")
        payload = joined.encode("utf-8")
    elif enc in ("b64", "b64url", "hex"):
        s = re.sub(r"[ \t\r\n\v\f]+", "", joined).rstrip("=")
        try:
            if enc == "hex":
                payload = _ba.unhexlify(s.lower())
            elif enc == "b64url":
                try:
                    if re.search(r"[+/]", s):
                        raise ValueError("std alphabet")
                    payload = _b64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
                except Exception:
                    payload = _b64.b64decode(s + "=" * (-len(s) % 4))
            else:
                dec = _b64.urlsafe_b64decode if re.search(r"[-_]", s) else _b64.b64decode
                payload = dec(s + "=" * (-len(s) % 4))
        except Exception as e:
            raise ValueError("envelope: payload decode failed (%s): %s" % (enc, e))
    else:
        raise ValueError("envelope: unknown enc= (use raw | b64url | b64 | hex): %r" % enc)
    if crc:
        want = "%08x" % (_zlib.crc32(payload) & 0xFFFFFFFF)
        if want != crc:
            raise ValueError("envelope: crc mismatch — payload corrupted in transit "
                             "(want %s, got %s) — re-send with enc=b64url" % (crc, want))
    if len(payload) > (16 << 20):
        raise ValueError("envelope: payload too large")
    return payload


def _parse_exec_request():
    """Shared body parser for /execute and /execute_stream.

    Accepts:
      1. legacy JSON body: {"code": "...", "timeout": N}
      2. a Samai Command Envelope as the raw text body (quoting-proof agent
         input); optional ?timeout=N query param applies in envelope mode.
    Returns (code, timeout, error_response_or_None)."""
    raw = request.get_data(cache=True, as_text=True) or ""
    if _SCE_BEGIN in raw:
        try:
            code = _sce_parse(raw).decode("utf-8", "replace")
        except Exception as e:
            return "", 600, {"success": False, "error": str(e), "error_type": "EnvelopeError"}
        try:
            timeout = min(int(request.args.get("timeout", 600)), 1800)
        except (TypeError, ValueError):
            timeout = 600
        return code, timeout, None
    data = request.get_json(silent=True) or {}
    try:
        timeout = min(int(data.get("timeout", 600)), 1800)
    except (TypeError, ValueError):
        timeout = 600
    return data.get("code", ""), timeout, None


@app.after_request
def _sce_respenc(response):
    """?respenc=b64url — move JSON text fields into *_b64 (base64url) so the
    return path through quote-mangling transports stays byte-exact.
    SSE streams are untouched (clients needing respenc should use /execute)."""
    try:
        if request.args.get("respenc", "") != "b64url":
            return response
        if response.mimetype != "application/json":
            return response
        data = response.get_json(silent=True)
        if not isinstance(data, dict):
            return response
        import base64 as _b64
        changed = False
        for k in ("stdout", "stderr", "error", "error_type", "traceback"):
            v = data.get(k)
            if isinstance(v, str) and v:
                data[k + "_b64"] = _b64.urlsafe_b64encode(v.encode("utf-8")).decode("ascii").rstrip("=")
                data[k] = ""
                changed = True
        if changed:
            response.data = json.dumps(data, ensure_ascii=False)
    except Exception:
        pass
    return response

# ====== end Samai Command Envelope block ======


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "name": "PaddleCLI Server",
        "version": "2.1.1",
        "status": "running",
        "uptime_minutes": round((time.time() - start_time) / 60, 2),
        "current_directory": execution_state["current_directory"],
        "is_executing": execution_state["is_executing"],
        "endpoints": ["/health", "/probe", "/execute", "/execute_stream", "/interrupt", "/status", "/history", "/variables", "/files", "/cleanup"],
        "envelope": {
            "name": "Samai Command Envelope - quoting-proof raw-text exec for AI agents",
            "format": "samaicmdbegin / v=1 / enc=b64url / crc=<crc32(payload) as 8 lowercase hex> / <b64url payload, 76 chars per line> / samaicmdend",
            "usage": "POST /execute (or /execute_stream) with the envelope as the raw text/plain body; payload is python code; crc = zlib.crc32(payload) & 0xffffffff; timeout via ?timeout=N (default 600, cap 1800)",
            "response": "append ?respenc=b64url to move stdout/stderr/error/error_type/traceback into *_b64 (unpadded urlsafe b64) so quote-mangling transports stay byte-exact; CLI `exec --json` prints this response verbatim as one pure-ASCII JSON line (decode *_b64 yourself, or add --plain to decode locally)"
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    mem = psutil.virtual_memory()
    return jsonify({
        "status": "ok",
        "uptime_minutes": round((time.time() - start_time) / 60, 2),
        "memory_available_gb": round(mem.available / (1024**3), 2),
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "memory_used_pct": round(mem.percent, 2),
        "gpu_available": _check_gpu(),
        "current_directory": execution_state["current_directory"],
        "is_executing": execution_state["is_executing"]
    })

@app.route('/status', methods=['GET'])
def get_status():
    """获取详细执行状态"""
    return jsonify({
        "status": "ok",
        "current_directory": execution_state["current_directory"],
        "is_executing": execution_state["is_executing"],
        "last_command": execution_state["last_command"],
        "last_execution_time": execution_state["last_execution_time"],
        "last_error": execution_state["last_error"],
        "recent_history": [h["command"] for h in execution_state["command_history"][-5:]],
        "uptime_minutes": round((time.time() - start_time) / 60, 2)
    })

@app.route('/history', methods=['GET'])
def get_history():
    """获取命令历史"""
    limit = request.args.get('limit', 20, type=int)
    limit = min(limit, 100)
    history = execution_state["command_history"][-limit:]
    return jsonify({"history": history, "total": len(execution_state["command_history"])})

@app.route('/interrupt', methods=['POST'])
def interrupt_execution():
    """中断当前执行（不停止服务器）"""
    global interrupt_requested, current_execution_thread

    if not execution_state["is_executing"]:
        return jsonify({"success": True, "message": t('no_running_task')})

    interrupt_requested = True

    if current_execution_thread and current_execution_thread.is_alive():
        success = _interrupt_thread(current_execution_thread)
        if success:
            execution_state["is_executing"] = False
            execution_state["last_error"] = t('user_interrupt')
            return jsonify({"success": True, "message": t('interrupt_sent')})
        else:
            return jsonify({"success": False, "message": t('interrupt_failed_msg')})

    return jsonify({"success": True, "message": t('interrupt_processed')})

@app.route('/probe', methods=['GET'])
def probe_environment():
    gpu_info = ""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.free', '--format=csv'],
                              capture_output=True, text=True, timeout=10)
        gpu_info = result.stdout
    except:
        gpu_info = t('gpu_no_available')

    installed_packages = []
    try:
        result = subprocess.run(['pip', 'list', '--format=freeze'], capture_output=True, text=True, timeout=30)
        for line in result.stdout.split('\n'):
            if '==' in line:
                installed_packages.append(line.strip())
    except:
        pass

    mem = psutil.virtual_memory()

    return jsonify({
        "gpu_info": gpu_info,
        "memory_total_gb": round(mem.total / (1024**3), 2),
        "memory_available_gb": round(mem.available / (1024**3), 2),
        "python_version": sys.version,
        "current_directory": execution_state["current_directory"],
        "installed_packages": installed_packages[:100],
        "total_packages": len(installed_packages)
    })

@app.route('/execute', methods=['POST'])
def execute_code():
    """执行 Python 代码，带错误隔离和状态跟踪"""
    global current_execution_thread, interrupt_requested

    if not execution_lock.acquire(blocking=False):
        return jsonify({"success": False, "error": t('server_busy')})

    interrupt_requested = False
    current_execution_thread = threading.current_thread()

    try:
        code, timeout, _env_err = _parse_exec_request()
        if _env_err is not None:
            return jsonify(_env_err)

        if not code:
            return jsonify({"success": False, "error": "No code provided"})

        execution_state["is_executing"] = True
        execution_state["last_command"] = code[:200] + "..." if len(code) > 200 else code

        exec_globals = {'__builtins__': __builtins__, **runtime_variables}
        exec_locals = {}

        from io import StringIO
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = captured_stdout = StringIO()
        sys.stderr = captured_stderr = StringIO()

        start_exec_time = time.time()

        try:
            if interrupt_requested:
                raise KeyboardInterrupt(t('execution_interrupted'))

            exec(code, exec_globals, exec_locals)

            if interrupt_requested:
                raise KeyboardInterrupt(t('execution_interrupted'))

            for key, value in exec_locals.items():
                if not key.startswith('_'):
                    try:
                        json.dumps({key: str(type(value))})
                        runtime_variables[key] = value
                    except:
                        pass

            _update_directory_from_code(code)
            stdout_val = captured_stdout.getvalue()
            _add_to_history(code, stdout_val, success=True)

            execution_state["last_execution_time"] = time.time() - start_exec_time
            execution_state["last_error"] = None

            return jsonify({
                "success": True,
                "stdout": stdout_val,
                "stderr": captured_stderr.getvalue(),
                "execution_time_sec": round(time.time() - start_exec_time, 3),
                "variables": list(exec_locals.keys()),
                "current_directory": execution_state["current_directory"]
            })

        except KeyboardInterrupt:
            stdout_val = captured_stdout.getvalue()
            _add_to_history(code, stdout_val, success=False)
            execution_state["last_error"] = t('user_interrupt')
            return jsonify({
                "success": False,
                "error": t('execution_interrupted'),
                "error_type": "KeyboardInterrupt",
                "stdout": stdout_val,
                "stderr": captured_stderr.getvalue(),
                "execution_time_sec": round(time.time() - start_exec_time, 3)
            })

        except Exception as e:
            stdout_val = captured_stdout.getvalue()
            _add_to_history(code, stdout_val, success=False)
            execution_state["last_error"] = str(e)
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "stdout": stdout_val,
                "stderr": captured_stderr.getvalue(),
                "execution_time_sec": round(time.time() - start_exec_time, 3)
            })

        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            execution_state["is_executing"] = False

    except Exception as e:
        execution_state["is_executing"] = False
        return jsonify({
            "success": False,
            "error": t('server_internal_error', error=str(e)),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })

    finally:
        execution_lock.release()
        current_execution_thread = None

@app.route('/execute_stream', methods=['POST'])
def execute_code_stream():
    """
    流式执行代码 - 使用 SSE 实时推送输出。
    支持：
    1. shell 命令 (!cmd) - 使用 Popen 实时读取
    2. Python 代码 - 使用线程实时推送 stdout
    """
    global stream_output_queue, stream_active, interrupt_requested

    def generate_sse(output_queue):
        """SSE 生成器"""
        try:
            while True:
                try:
                    msg = output_queue.get(timeout=0.5)
                    if msg is None:  # 结束信号
                        break
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    # 发送心跳保持连接
                    yield f": heartbeat\n\n"
                    continue
        except GeneratorExit:
            pass

    # 创建输出队列
    stream_output_queue = queue.Queue()
    stream_active = True
    interrupt_requested = False

    code, timeout, _env_err = _parse_exec_request()
    if _env_err is not None:
        stream_output_queue.put({"type": "error", "content": str(_env_err.get("error", "bad request"))})
        stream_output_queue.put(None)
        return Response(generate_sse(stream_output_queue), mimetype='text/event-stream')

    if not code:
        stream_output_queue.put({"type": "error", "content": "No code provided"})
        stream_output_queue.put(None)
        return Response(generate_sse(stream_output_queue), mimetype='text/event-stream')

    execution_state["is_executing"] = True
    execution_state["last_command"] = code[:200] + "..." if len(code) > 200 else code

    # 检测是否是 shell 命令
    stripped_code = code.strip()

    # 情况1: 单独的 shell 命令 (以 ! 开头)
    shell_match = re.match(r'^import subprocess; result = subprocess\.run\([\'"](.+?)[\'"], shell=True', stripped_code)
    if shell_match:
        shell_cmd = shell_match.group(1)

        def run_shell_command():
            global stream_active
            start_time = time.time()
            stream_output_queue.put({"type": "status", "content": t('executing_shell', cmd=shell_cmd)})

            try:
                process = subprocess.Popen(
                    shell_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # 行缓冲
                    cwd=execution_state["current_directory"]
                )

                # 实时读取输出
                import select
                while True:
                    if interrupt_requested:
                        process.terminate()
                        stream_output_queue.put({"type": "error", "content": t('execution_interrupted')})
                        break

                    # 检查进程是否结束
                    retcode = process.poll()
                    read_ready, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)

                    for stream in read_ready:
                        if stream == process.stdout:
                            line = process.stdout.readline()
                            if line:
                                stream_output_queue.put({"type": "stdout", "content": line})
                        elif stream == process.stderr:
                            line = process.stderr.readline()
                            if line:
                                stream_output_queue.put({"type": "stderr", "content": line})

                    if retcode is not None:
                        # 读取剩余输出
                        remaining_stdout, remaining_stderr = process.communicate()
                        if remaining_stdout:
                            stream_output_queue.put({"type": "stdout", "content": remaining_stdout})
                        if remaining_stderr:
                            stream_output_queue.put({"type": "stderr", "content": remaining_stderr})
                        break

                elapsed = time.time() - start_time
                stream_output_queue.put({
                    "type": "complete",
                    "content": t('complete_shell', code=process.returncode, time=f"{elapsed:.2f}")
                })
                _add_to_history(code, f"shell: {shell_cmd}", success=True)
                execution_state["last_execution_time"] = elapsed

            except Exception as e:
                stream_output_queue.put({"type": "error", "content": str(e)})
                _add_to_history(code, str(e), success=False)
            finally:
                stream_output_queue.put(None)  # 结束信号
                stream_active = False
                execution_state["is_executing"] = False

        thread = threading.Thread(target=run_shell_command, daemon=True)
        thread.start()

    # 情况2: Python 代码执行
    else:
        class StreamingOutput:
            """流式输出捕获器"""
            def __init__(self, q, stream_type):
                self.queue = q
                self.stream_type = stream_type
                self.buffer = []

            def write(self, text):
                if text:
                    self.buffer.append(text)
                    self.queue.put({"type": self.stream_type, "content": text})

            def flush(self):
                pass

            def getvalue(self):
                return ''.join(self.buffer)

        def run_python_code():
            global stream_active
            start_time = time.time()
            stream_output_queue.put({"type": "status", "content": t('executing_python')})

            old_stdout = sys.stdout
            old_stderr = sys.stderr
            stdout_capture = StreamingOutput(stream_output_queue, 'stdout')
            stderr_capture = StreamingOutput(stream_output_queue, 'stderr')
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            exec_globals = {'__builtins__': __builtins__, **runtime_variables}
            exec_locals = {}

            try:
                if interrupt_requested:
                    raise KeyboardInterrupt(t('execution_interrupted'))

                exec(code, exec_globals, exec_locals)

                if interrupt_requested:
                    raise KeyboardInterrupt(t('execution_interrupted'))

                # 保存变量
                for key, value in exec_locals.items():
                    if not key.startswith('_'):
                        try:
                            runtime_variables[key] = value
                        except:
                            pass

                _update_directory_from_code(code)
                elapsed = time.time() - start_time
                stream_output_queue.put({
                    "type": "complete",
                    "content": t('complete_python', time=f"{elapsed:.2f}"),
                    "variables": list(exec_locals.keys())
                })
                _add_to_history(code, ''.join(stdout_capture.buffer)[:200], success=True)
                execution_state["last_execution_time"] = elapsed

            except KeyboardInterrupt:
                stream_output_queue.put({"type": "error", "content": t('execution_interrupted_msg')})
                _add_to_history(code, t('interrupt_history'), success=False)
            except Exception as e:
                stream_output_queue.put({
                    "type": "error",
                    "content": t('error_prefix', error=f"{type(e).__name__}: {str(e)}")
                })
                _add_to_history(code, str(e), success=False)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                stream_output_queue.put(None)  # 结束信号
                stream_active = False
                execution_state["is_executing"] = False

        thread = threading.Thread(target=run_python_code, daemon=True)
        thread.start()

    return Response(generate_sse(stream_output_queue), mimetype='text/event-stream')

@app.route('/variables', methods=['GET'])
def list_variables():
    vars_info = {}
    for key, value in runtime_variables.items():
        try:
            var_info = {"type": str(type(value).__name__)}
            if hasattr(value, 'shape'):
                var_info["shape"] = list(value.shape) if hasattr(value.shape, '__iter__') else str(value.shape)
            if hasattr(value, '__len__'):
                try:
                    var_info["length"] = len(value)
                except:
                    pass
            vars_info[key] = var_info
        except:
            vars_info[key] = {"type": str(type(value).__name__)}

    return jsonify({
        "variables": vars_info,
        "count": len(vars_info),
        "current_directory": execution_state["current_directory"]
    })

@app.route('/files', methods=['GET'])
def list_files():
    content_dir = execution_state.get("current_directory", "/home/aistudio")
    dir_param = request.args.get('dir', None)
    if dir_param:
        content_dir = dir_param

    files = []
    try:
        for f in os.listdir(content_dir):
            path = os.path.join(content_dir, f)
            try:
                size = os.path.getsize(path)
                files.append({
                    "name": f,
                    "path": path,
                    "size_bytes": size,
                    "size_readable": f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB",
                    "is_dir": os.path.isdir(path)
                })
            except:
                pass
    except Exception as e:
        return jsonify({"error": str(e), "files": [], "directory": content_dir})

    return jsonify({"files": files, "count": len(files), "directory": content_dir})

@app.route('/cleanup', methods=['POST'])
def cleanup():
    global runtime_variables
    runtime_variables = {}
    gc.collect()

    # 静默探测框架：AI Studio 会拦截 import torch 并打印兼容性横幅（v2.1.1 修复）
    # Silent framework probe: AI Studio intercepts `import torch` with a banner (fixed in v2.1.1)
    import contextlib
    import io as _io
    with contextlib.redirect_stdout(_io.StringIO()), contextlib.redirect_stderr(_io.StringIO()):
        try:
            import paddle
            if paddle.device.is_compiled_with_cuda():
                paddle.device.cuda.empty_cache()
        except Exception:
            pass

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    mem = psutil.virtual_memory()
    return jsonify({
        "success": True,
        "message": t('memory_cleaned'),
        "memory_available_gb": round(mem.available / (1024**3), 2)
    })

def signal_handler(sig, frame):
    global keep_running
    print("\n" + t('signal_received'))
    keep_running = False
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n" + "="*60)
    print(t('server_starting'))
    print("="*60)
    print(t('server_version', version='2.1.1'))
    print(t('server_features', features='Heartbeat + Error isolation + Interrupt + Status tracking + SSE streaming'))
    print(t('server_optimization', optimization='Long-task stability + Non-blocking heartbeat + 600s timeout'))
    print("="*60 + "\n")

    heartbeat = threading.Thread(target=heartbeat_thread, daemon=True)
    heartbeat.start()

    try:
        app.run(port=5000, host='0.0.0.0', threaded=True)
    except Exception as e:
        print(t('server_start_failed', error=str(e)))
        raise
