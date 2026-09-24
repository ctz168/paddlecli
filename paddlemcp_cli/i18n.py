#!/usr/bin/env python3
"""i18n module for PaddleCLI CLI - supports English (default) and Chinese.

Usage:
    import i18n
    i18n.t('loading_notebook', name='notebook.ipynb')

Set the language via the PADDLECLI_LANG environment variable (e.g. 'zh'),
or at runtime via i18n.set_lang('zh').
"""

import os

# Default language loaded from environment (English unless PADDLECLI_LANG=zh)
_LANG = os.environ.get('PADDLECLI_LANG', 'en').lower()
if _LANG not in ('en', 'zh'):
    _LANG = 'en'

TRANSLATIONS = {
    'en': {
        'exec_cell_error': 'Execution error: {err}',
        'exec_envelope_bad': 'Envelope rejected: {err}',
        'exec_envelope_ok': 'Envelope accepted — CRC verified, quoting-proof payload decoded',
        'exec_bad_c64': 'Invalid --c64 (not valid base64url): {err}',
        'exec_no_input': 'No input: use -c \'code\', --c64 <b64url>, or pipe code/envelope to stdin',
        # ============ Generic ============
        'loading_notebook': '📖 Loading notebook: {name}',
        'failed_load': '❌ Failed to load notebook: {error}',
        'found_cells': '✓ Found {total} cells ({code} code cells)',
        'found_cells_stream': '✓ Found {total} cells ({code} code cells to stream)',
        'executing': '🚀 Executing notebook...',
        'executing_remote': '🚀 Executing notebook remotely...',
        'executing_stream': '🚀 Starting streaming execution...',
        'execution_summary': '📊 Execution Summary:',
        'streaming_summary': '📊 Streaming Summary:',
        'total_time': 'Total Time',
        'cells_executed': 'Cells Executed',
        'success': '✅ Success',
        'errors': '❌ Errors',
        'skipped': '⏭️ Skipped',
        'output_saved': '💾 Output saved to: {path}',
        'converting': '📖 Converting: {name}',
        'converted_to': '✓ Converted to: {path}',
        'analyzing': '📖 Analyzing: {name}',
        'reading': '📖 Reading: {name}',
        'notebook_info': 'Notebook Information',
        'path': 'Path',
        'format': 'Format',
        'total_cells': 'Total Cells',
        'code_cells': 'Code Cells',
        'markdown_cells': 'Markdown Cells',
        'kernel': 'Kernel',
        'language': 'Language',
        'unknown': 'Unknown',
        'cell_overview': 'Cell Overview:',
        'tags_found': 'Tags found: {tags}',
        'total_shown': 'Total: {total} cells shown',
        'version': 'paddlecli version {version}',
        'heartbeat': '[Heartbeat] {time} - Running | Directory: {directory}{exec_flag}',
        'heartbeat_error': '[Heartbeat Error] {error}',
        'interrupt_flag': ' [Executing]',
        'watch_duration_reached': '⏰ Watch duration reached',
        'watch_stopped': '👋 Watch stopped',
        'watch_running': '🔄 Running',
        'watch_idle': '✅ Idle',
        'goodbye': '👋 Goodbye!',
        'interrupted': 'Interrupted',

        # ============ Local execution (StreamingRunner) ============
        'cell_running': '⏳ Running...',
        'cell_streaming': '⏳ Streaming...',
        'cell_done': '✅ Done ({duration})',
        'cell_error': '❌ Error in Cell [{index}]:',
        'cell_skipped': '⏭️ Skipped',
        'cell_header': '━━━ Cell [{index}] ━━━',

        # ============ Remote execution ============
        'connecting': '🔗 Connecting to: {url}',
        'connected': '✓ Connected! Server uptime: {uptime} min',
        'failed_connect': '❌ Failed to connect: {error}',
        'health_checking': '🔍 Checking server: {url}',
        'connection_failed': '❌ Connection failed: {error}',
        'probing_environment': '🔍 Probing environment...',
        'server_health': 'Server Health',
        'status': 'Status',
        'uptime': 'Uptime',
        'memory_available': 'Memory Available',
        'memory_total': 'Memory Total',
        'memory_used': 'Memory Used',
        'gpu_available': 'GPU Available',
        'yes': '✅ Yes',
        'no': '❌ No',
        'python': 'Python: {version}',
        'total_packages': 'Total packages: {count}',
        'gpu_info': '🎮 GPU Info:',

        # ============ Streaming execution ============
        'streaming': '⏳ Streaming...',
        'interrupting': '⚠️ Interrupting...',
        'interrupted_by_user': '⏹️ Execution interrupted by user',
        'stream_summary': '📊 Streaming Summary:',
        'output_lines': 'Output Lines',
        'press_ctrl_c': 'Press Ctrl+C to interrupt',
        'stream_error': '❌ Error: {error}',
        'stream_stopped_on_error': '🛑 Stopping further cells (stop-on-error; use --continue-on-error to override)',

        # ============ Status / Interrupt ============
        'interrupting_exec': '⏹️ Interrupting execution on: {url}',
        'exec_interrupted': '✅ Execution interrupted',
        'interrupt_failed': '❌ Interrupt failed: {error}',
        'getting_status': '📊 Getting status from: {url}',
        'status_failed': '❌ Failed to get status: {error}',
        'server_status': 'Server Status',
        'is_executing': 'Is Executing',
        'current_directory': 'Current Directory',
        'last_command': 'Last Command',
        'last_execution_time': 'Last Execution Time',
        'recent_commands': '📜 Recent Commands:',
        'getting_history': '📜 Getting history from: {url}',
        'history_failed': '❌ Failed to get history: {error}',
        'no_command_history': 'No command history found.',
        'command_history': 'Command History ({count} entries):',
        'time': 'Time',
        'directory': 'Directory',
        'command_preview': 'Command Preview',
        'watching_server': '👀 Watching server: {url}',
        'duration': 'Duration: {duration}s (0 = infinite)',
        'watch_error': '❌ Error: {error}',
        'get_status_failed': '❌ Failed to get status: {error}',

        # ============ REPL ============
        'repl_title': 'Interactive Python REPL',
        'repl_exit_hint': "Type 'exit' or press Ctrl+D to exit",
        'repl_prompt': '>>> ',

        # ============ Server side (paddle_server.py response messages) ============
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
        'server_busy_waiting': '⚠️ Server busy, waiting...',
        'unknown_error': 'Unknown error',
        'memory_cleaned': 'Memory cleaned',
        'executing_shell': 'Executing: {cmd}',
        'executing_python': 'Executing Python code...',
        'complete_shell': '✅ Done (exit code: {code}, time: {time}s)',
        'complete_python': '✅ Done (time: {time}s)',
        'error_prefix': '❌ Error: {error}',
        'interrupt_history': 'Interrupted',
        'signal_received': '[Signal] Stop signal received, shutting down...',
        'interrupt_attempt_failed': '[Interrupt] Failed to interrupt: {error}',
        'gpu_no_available': 'No GPU available',

        # ============ Executor magic command translations ============
        'magic_cd': '📁 Changed directory to: {dir}',
        'magic_pwd': 'Current directory: {dir}',
        'magic_set_env': '✅ Set environment variable: {name}={value}',
        'magic_time': '⏱️ Execution time: {time}s',
        'magic_who': 'Variables: {vars}',
        'magic_reset_skipped': '⚠️ %reset is skipped in remote execution',
        'magic_load_skipped': '⚠️ %load requires manual file loading: {file}',
        'magic_unknown': '⚠️ Unknown magic command: %{name}',
        'magic_js_unavailable': '⚠️ JavaScript cell magic is not available in Python environment',
        'magic_writefile': '✅ File written: {file} ({size} bytes)',
        'magic_timeit': '⏱️ Average execution time: {time:.3f}ms (100 runs)',
        'execution_failed': 'Execution failed',
        'non_code_cell': 'Non-code cell',
        'execution_stopped': 'Execution stopped',
    },
    'zh': {
        # ============ exec 命令（与 en 对齐） ============
        'exec_cell_error': '执行错误: {err}',
        'exec_envelope_bad': '信封被拒收: {err}',
        'exec_envelope_ok': '信封已接收 — CRC 校验通过，防引号负载已解码',
        'exec_bad_c64': '无效的 --c64（不是合法 base64url）: {err}',
        'exec_no_input': '没有输入：使用 -c \'代码\'、--c64 <b64url>，或将代码/信封通过管道送入 stdin',
        # ============ 通用 ============
        'loading_notebook': '📖 正在加载笔记本: {name}',
        'failed_load': '❌ 加载笔记本失败: {error}',
        'found_cells': '✓ 发现 {total} 个单元格 ({code} 个代码单元格)',
        'found_cells_stream': '✓ 发现 {total} 个单元格 ({code} 个待流式执行的代码单元格)',
        'executing': '🚀 正在执行笔记本...',
        'executing_remote': '🚀 正在远程执行笔记本...',
        'executing_stream': '🚀 开始流式执行...',
        'execution_summary': '📊 执行摘要:',
        'streaming_summary': '📊 流式摘要:',
        'total_time': '总耗时',
        'cells_executed': '已执行单元格',
        'success': '✅ 成功',
        'errors': '❌ 错误',
        'skipped': '⏭️ 已跳过',
        'output_saved': '💾 输出已保存到: {path}',
        'converting': '📖 正在转换: {name}',
        'converted_to': '✓ 已转换为: {path}',
        'analyzing': '📖 正在分析: {name}',
        'reading': '📖 正在读取: {name}',
        'notebook_info': '笔记本信息',
        'path': '路径',
        'format': '格式',
        'total_cells': '总单元格数',
        'code_cells': '代码单元格',
        'markdown_cells': 'Markdown 单元格',
        'kernel': '内核',
        'language': '语言',
        'unknown': '未知',
        'cell_overview': '单元格概览:',
        'tags_found': '找到标签: {tags}',
        'total_shown': '共显示 {total} 个单元格',
        'version': 'paddlecli 版本 {version}',
        'heartbeat': '[心跳] {time} - 运行中 | 目录: {directory}{exec_flag}',
        'heartbeat_error': '[心跳错误] {error}',
        'interrupt_flag': ' [执行中]',
        'watch_duration_reached': '⏰ 已达到监控时长',
        'watch_stopped': '👋 监控已停止',
        'watch_running': '🔄 运行中',
        'watch_idle': '✅ 空闲',
        'goodbye': '👋 再见!',
        'interrupted': '已中断',

        # ============ 本地执行 ============
        'cell_running': '⏳ 运行中...',
        'cell_streaming': '⏳ 流式执行中...',
        'cell_done': '✅ 完成 ({duration})',
        'cell_error': '❌ 单元格 [{index}] 出错:',
        'cell_skipped': '⏭️ 已跳过',
        'cell_header': '━━━ 单元格 [{index}] ━━━',

        # ============ 远程执行 ============
        'connecting': '🔗 正在连接: {url}',
        'connected': '✓ 已连接! 服务器运行时长: {uptime} 分钟',
        'failed_connect': '❌ 连接失败: {error}',
        'health_checking': '🔍 正在检查服务器: {url}',
        'connection_failed': '❌ 连接失败: {error}',
        'probing_environment': '🔍 正在探测环境...',
        'server_health': '服务器健康状态',
        'status': '状态',
        'uptime': '运行时长',
        'memory_available': '可用内存',
        'memory_total': '总内存',
        'memory_used': '已用内存',
        'gpu_available': 'GPU 可用',
        'yes': '✅ 是',
        'no': '❌ 否',
        'python': 'Python: {version}',
        'total_packages': '包总数: {count}',
        'gpu_info': '🎮 GPU 信息:',

        # ============ 流式执行 ============
        'streaming': '⏳ 流式执行中...',
        'interrupting': '⚠️ 正在中断...',
        'interrupted_by_user': '⏹️ 已被用户中断',
        'stream_summary': '📊 流式摘要:',
        'output_lines': '输出行数',
        'press_ctrl_c': '按 Ctrl+C 中断',
        'stream_error': '❌ 错误: {error}',
        'stream_stopped_on_error': '🛑 已停止执行后续 cell（stop-on-error；可用 --continue-on-error 跳过此行为）',

        # ============ 状态/中断 ============
        'interrupting_exec': '⏹️ 正在中断执行: {url}',
        'exec_interrupted': '✅ 执行已中断',
        'interrupt_failed': '❌ 中断失败: {error}',
        'getting_status': '📊 正在获取状态: {url}',
        'status_failed': '❌ 获取状态失败: {error}',
        'server_status': '服务器状态',
        'is_executing': '正在执行',
        'current_directory': '当前目录',
        'last_command': '最后命令',
        'last_execution_time': '最后执行时间',
        'recent_commands': '📜 最近命令:',
        'getting_history': '📜 正在获取历史: {url}',
        'history_failed': '❌ 获取历史失败: {error}',
        'no_command_history': '未找到命令历史。',
        'command_history': '命令历史 ({count} 条):',
        'time': '时间',
        'directory': '目录',
        'command_preview': '命令预览',
        'watching_server': '👀 正在监控服务器: {url}',
        'duration': '时长: {duration} 秒 (0 = 无限)',
        'watch_error': '❌ 错误: {error}',
        'get_status_failed': '❌ 获取状态失败: {error}',

        # ============ REPL ============
        'repl_title': '交互式 Python REPL',
        'repl_exit_hint': "输入 'exit' 或按 Ctrl+D 退出",
        'repl_prompt': '>>> ',

        # ============ 服务器端 ============
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
        'server_busy_waiting': '⚠️ 服务器繁忙，正在等待...',
        'unknown_error': '未知错误',
        'memory_cleaned': '内存已清理',
        'executing_shell': '执行: {cmd}',
        'executing_python': '执行 Python 代码...',
        'complete_shell': '✅ 完成 (退出码: {code}, 耗时: {time}s)',
        'complete_python': '✅ 完成 (耗时: {time}s)',
        'error_prefix': '❌ 错误: {error}',
        'interrupt_history': '中断',
        'signal_received': '[信号] 收到停止信号，正在关闭...',
        'interrupt_attempt_failed': '[中断] 尝试中断失败: {error}',
        'gpu_no_available': '无可用 GPU',

        # ============ executor 中的 magic 命令翻译 ============
        'magic_cd': '📁 切换到目录: {dir}',
        'magic_pwd': '当前目录: {dir}',
        'magic_set_env': '✅ 设置环境变量: {name}={value}',
        'magic_time': '⏱️ 执行时间: {time}s',
        'magic_who': '变量: {vars}',
        'magic_reset_skipped': '⚠️ %reset 在远程执行中被跳过',
        'magic_load_skipped': '⚠️ %load 需要手动加载文件: {file}',
        'magic_unknown': '⚠️ 未知 magic command: %{name}',
        'magic_js_unavailable': '⚠️ JavaScript cell magic 在 Python 环境中不可用',
        'magic_writefile': '✅ 写入文件: {file} ({size} bytes)',
        'magic_timeit': '⏱️ 平均执行时间: {time:.3f}ms (100次)',
        'execution_failed': '执行失败',
        'non_code_cell': '非代码单元格',
        'execution_stopped': '执行已停止',
    },
}


def t(key, **kwargs):
    """Get translated string by key.

    Args:
        key: Translation key (lowercase_underscore).
        **kwargs: Format arguments for placeholders in the string.

    Returns:
        The translated string. Falls back to the English string, then to the
        key itself, if the key is missing.
    """
    lang_dict = TRANSLATIONS.get(_LANG, {})
    template = lang_dict.get(key)
    if template is None:
        # Fall back to English, then to the raw key
        template = TRANSLATIONS.get('en', {}).get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def set_lang(lang):
    """Switch the language at runtime.

    Args:
        lang: 'en' or 'zh'. Other values are ignored.

    Returns:
        The active language code.
    """
    global _LANG
    lang = (lang or '').lower()
    if lang in ('en', 'zh'):
        _LANG = lang
    return _LANG


def get_lang():
    """Get the current language code ('en' or 'zh')."""
    return _LANG
