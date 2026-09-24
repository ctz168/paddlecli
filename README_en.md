# 🚀 PaddleCLI

[![Run on AI Studio](https://img.shields.io/badge/Run%20on-Baidu%20AI%20Studio-2932e1?logo=baidu)](https://aistudio.baidu.com/)
[![GitHub](https://img.shields.io/badge/GitHub-ctz168%2Fpaddlecli-blue?logo=github)](https://github.com/ctz168/paddlecli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.1.5-green.svg)](https://github.com/ctz168/paddlecli)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

A powerful command-line tool to run Jupyter Notebooks on **Baidu AI Studio** with streaming output per cell.

PaddleCLI is the sister project of [colabcli](https://github.com/ctz168/colabcli): it brings the full "Flask server deployed in a cloud notebook + local CLI streaming control over a public tunnel" experience to **Baidu AI Studio (BML Codelab)**, natively fitted into the PaddlePaddle ecosystem.

```
┌─────────────────────┐      Public tunnel (aitun)      ┌──────────────────────────────┐
│  Your local machine │  ────────────────────────────▶  │  Baidu AI Studio (Codelab)   │
│                     │                                 │                              │
│  paddlecli stream   │   POST /execute_stream (SSE)    │  paddle_server.py (Flask)     │
│  paddlecli remote   │  ◀────────────────────────────  │   ├─ real-time SSE streaming  │
│  paddlecli exec     │    per-cell live output         │   ├─ variables / history      │
│  (CLI / AI Agent)   │                                 │   └─ GPU: V100 / A100          │
└─────────────────────┘                                 └──────────────────────────────┘
```

---

## 🎯 Quick Start

Only 3 steps:

### 1. Deploy the server on AI Studio

1. Open [Baidu AI Studio](https://aistudio.baidu.com/) and create/enter a **Notebook project**
2. Pick an environment (**V100 / A100 GPU** recommended)
3. Upload or create a notebook identical to [paddle_server.ipynb](paddle_server.ipynb) (or just upload that file)
4. Run all cells in order — the last cell prints the **public URL**, e.g.:

```
🎉 Tunnel established!
📡 Public URL: https://xxxx.a.itun.im/xxxx
```

> That cell has a built-in 30s heartbeat and auto-restarts crashed processes. **Keep it running.** The tunnel URL changes after a restart — always use the latest printed one.

### 2. Install the CLI locally

```bash
pip install git+https://github.com/ctz168/paddlecli.git
```

Or from source:

```bash
git clone https://github.com/ctz168/paddlecli.git
cd paddlecli
pip install -e .
```

### 3. Run a notebook remotely

```bash
# Check server health
paddlecli health --url https://xxxx.a.itun.im/xxxx

# Run notebook remotely (batch mode)
paddlecli remote notebook.ipynb -u https://xxxx.a.itun.im/xxxx

# Real-time streaming (recommended!)
paddlecli stream notebook.ipynb -u https://xxxx.a.itun.im/xxxx
```

---

## ✨ Features

### Core

- 📡 **Real-time streaming execution** — SSE (Server-Sent Events) pushes stdout/stderr chunk by chunk, perfect for training, crawlers and long-running bots
- 🎛️ **Per-cell control** — `--start/--end` to run a cell range, `--stop-on-error` to halt on the first failure
- 🖥️ **Local execution engine** — the `run` command streams notebooks locally without any server; supports IPython magics and variable persistence
- 🔄 **Magic command translation** — remote mode auto-converts `%cd`, `%env`, `%pip install`, `!cmd`, `%%writefile`, `%%bash`, etc. into remotely runnable Python
- ⏹️ **Interrupt & status** — `interrupt` stops the running code (not the server); `status`/`history`/`watch` report what's going on
- 🧠 **Stateful sessions** — executed variables stay in server memory across requests; `/variables` shows types/shapes
- 🧹 **GPU/memory cleanup** — `/cleanup` clears CUDA caches of both PaddlePaddle and PyTorch

### AI-agent friendly (v2.1.0)

- ✉️ **Samai Command Envelope** — code is wrapped between `samaicmdbegin ... samaicmdend` markers as base64url (pure `[A-Za-z0-9-_]` alphabet) with a CRC32 check, so IM gateways / chat bridges cannot mangle quotes or backslashes
- 📤 **respenc response protection** — `?respenc=b64url` moves text fields into `*_b64`; `exec --json` prints ONE pure-ASCII JSON line, so the return path is byte-exact too
- 🔢 **Exit-code semantics** — 0 success / 1 exec error / 2 transport-or-argument error

### More

- 🈶 **Bilingual EN/ZH** — `PADDLECLI_LANG=zh` or `--lang zh`
- 📊 **Notebook utilities** — `info`, `cells`, `convert`
- 🔍 **Environment probing** — `health` shows GPU/memory/Python/packages
- 🔓 **Registration-free tunnel** — `aitun` needs no account or token; cloudflared / ngrok / your own tunnel work too

---

## 📦 Installation

### From GitHub (recommended)

```bash
pip install git+https://github.com/ctz168/paddlecli.git
```

### From source

```bash
git clone https://github.com/ctz168/paddlecli.git
cd paddlecli
pip install -e .
```

### Dependencies

- Python ≥ 3.8
- `click`, `rich`, `requests`, `ipython` (installed with the CLI)
- Server side additionally needs `flask`, `psutil` (`pip install paddlecli[server]`, or installed by the notebook cell on AI Studio)

### Language

```bash
export PADDLECLI_LANG=zh        # Chinese messages (default: en)
paddlecli --lang zh --version   # or per-invocation
```

---

## 🚀 Usage

### Run locally

```bash
# Basic
paddlecli run notebook.ipynb

# Cells 5..9 only (end exclusive)
paddlecli run notebook.ipynb --start 5 --end 10

# Show markdown cells
paddlecli run notebook.ipynb --show-markdown

# Continue on error + save results to JSON
paddlecli run notebook.ipynb --continue-on-error -o results.json
```

### Run remotely (batch)

```bash
# Basic
paddlecli remote notebook.ipynb -u https://xxxx.a.itun.im/xxxx

# Long training run (1h timeout)
paddlecli remote train.ipynb -u https://xxxx.a.itun.im/xxxx -t 3600

# Only cells 3-4
paddlecli remote notebook.ipynb -u https://xxxx.a.itun.im/xxxx -s 3 -e 5
```

### Real-time streaming (recommended)

SSE-based; each cell's output scrolls live. `Ctrl+C` sends an interrupt to the server automatically:

```bash
# Stream a whole notebook
paddlecli stream notebook.ipynb -u https://xxxx.a.itun.im/xxxx

# Stream only cell 3 (e.g. the training launcher)
paddlecli stream train.ipynb -u https://xxxx.a.itun.im/xxxx --start 3 --end 4

# Watch server status live (Ctrl+C to stop)
paddlecli watch -u https://xxxx.a.itun.im/xxxx
```

### One-shot `exec` — quoting-proof mode for AI agents

When agent command text travels through IM gateways / chat bridges, smart quotes and backslash stripping destroy code ("quoting hell"). `exec` offers three input modes, safest first:

```bash
# 1) Safest — envelope on stdin (base64url payload + CRC32):
cat env.txt | paddlecli exec -u https://xxxx.a.itun.im/xxxx

# 2) Quoting-proof argv — pure [A-Za-z0-9_-], zero escaping:
paddlecli exec -u URL --c64 cHJpbnQoNDArMikK

# 3) Plain code (human convenience):
paddlecli exec -u URL -c 'print(40+2)'

# Live streaming output (default, human-friendly):
paddlecli exec -u URL -c 'for i in range(3): print(i)'

# Agent mode: ONE pure-ASCII JSON line (stdout_b64 fields) + exit code 0/1/2:
echo samaicmdbegin... | paddlecli exec -u URL --json
paddlecli exec -u URL -c 'import os' --json --plain   # --plain decodes *_b64 locally
```

Build an envelope yourself (replace `YOUR_PYTHON_CODE`):

```bash
python3 -c "import zlib,base64,sys;p=sys.argv[1].encode();print('samaicmdbegin\nv=1\nenc=b64url\ncrc=%08x\n%s\nsamaicmdend'%(zlib.crc32(p)&0xffffffff,base64.urlsafe_b64encode(p).decode().rstrip('=')))" 'YOUR_PYTHON_CODE' | paddlecli exec -u URL --json
```

### Other commands

```bash
# Notebook info
paddlecli info notebook.ipynb

# List & preview cells
paddlecli cells notebook.ipynb --start 0 --end 5

# Convert to a Python script
paddlecli convert notebook.ipynb -o script.py

# Interactive local REPL
paddlecli repl

# Server status / command history
paddlecli status  -u https://xxxx.a.itun.im/xxxx
paddlecli history -u https://xxxx.a.itun.im/xxxx --limit 50

# Interrupt the current remote execution (server keeps running)
paddlecli interrupt -u https://xxxx.a.itun.im/xxxx
```

---

## 📖 Command Reference

### Overview

| Command | Description | Use case |
|---------|-------------|----------|
| `paddlecli run` | Execute notebook locally | quick tests, local dev |
| `paddlecli remote` | Execute remotely (batch) | short tasks, data processing |
| `paddlecli stream` | Execute remotely (streaming) | long tasks, bots, training |
| `paddlecli exec` | One-shot code execution | AI agents, automation |
| `paddlecli watch` | Watch server status | monitor remote progress |
| `paddlecli health` | Server health check | verify connectivity |
| `paddlecli status` | Execution status | current dir & state |
| `paddlecli interrupt` | Interrupt execution | stop running code |
| `paddlecli history` | Command history | debugging |
| `paddlecli info` | Notebook info | inspect structure |
| `paddlecli cells` | List cells | preview code |
| `paddlecli convert` | Convert to script | export code |
| `paddlecli repl` | Interactive REPL | local testing |

### `paddlecli run`

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--start` | `-s` | 0 | first cell index |
| `--end` | `-e` | last | end cell index (exclusive, Python-slice style) |
| `--show-code` | - | True | show code before execution |
| `--show-markdown` | - | False | show markdown cells |
| `--stop-on-error` / `--continue-on-error` | - | True | stop on first error |
| `--verbose` | `-V` | False | verbose (with tracebacks) |
| `--output` | `-o` | - | save results to a JSON file |

### `paddlecli remote`

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--url` | `-u` | required | paddlecli server URL |
| `--start` | `-s` | 0 | first cell index |
| `--end` | `-e` | last | end cell index (exclusive) |
| `--timeout` | `-t` | 300 | timeout in seconds |
| `--stop-on-error` / `--continue-on-error` | - | True | stop on first error |
| `--verbose` | `-V` | False | verbose output |

### `paddlecli stream`

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--url` | `-u` | required | paddlecli server URL |
| `--start` | `-s` | 0 | first cell index |
| `--end` | `-e` | last | end cell index (exclusive) |
| `--timeout` | `-t` | 600 | streaming timeout in seconds |
| `--stop-on-error` / `--continue-on-error` | - | True | stop remaining cells on error |
| `--verbose` | `-V` | False | show cell source |

### `paddlecli exec`

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--url` | `-u` | required | paddlecli server URL |
| `--code` | `-c` | - | code to execute (stdin read when omitted) |
| `--c64` | - | - | base64url-encoded code (quoting-proof argv) |
| `--timeout` | `-t` | 600 | timeout in seconds |
| `--json` | - | False | emit one pure-ASCII JSON line (agent mode) |
| `--plain` | - | False | with `--json`: decode `*_b64` fields locally |

---

## ✉️ Samai Command Envelope (SCE) v1

When an AI agent remote-controls this tool, the command text usually passes through layers that re-parse or "repair" text:

```
agent → IM/chat gateway → HTTP POST → tunnel → server → kernel
```

Gateways routinely eat `"`, convert straight quotes to smart quotes (“ ”), strip backslashes, and re-wrap lines — by the time code reaches the kernel, quoting is destroyed.

The envelope wraps the code between two plain lowercase markers; the payload is base64url (only `[A-Za-z0-9-_]`, nothing any gateway considers special), with a CRC32 as a final integrity check:

```
samaicmdbegin
v=1
enc=b64url
crc=1a2b3c4d
<b64url payload, 76 chars per line>
samaicmdend
```

- **Usage**: POST the envelope as the raw `text/plain` body to `/execute` (or `/execute_stream`) — not JSON
- **Checksum**: `crc` = 8 lowercase hex of `zlib.crc32(payload) & 0xffffffff`; on mismatch the server rejects and the agent should re-send
- **Timeout**: append `?timeout=N` (default 600, cap 1800)
- **Response protection**: append `&respenc=b64url` to move `stdout/stderr/error/error_type/traceback` into `*_b64` (unpadded urlsafe base64) so the return path stays byte-exact
- **Compatibility**: `enc=raw` (literal text), `enc=b64`, `enc=hex` are also parsed; in b64 modes all whitespace is ignored, so re-wrapped lines are harmless
- **Limit**: 16 MiB payload

The CLI's `exec --json` already chains "envelope request + respenc response + single-line ASCII output"; agents only need to decode `*_b64` (or add `--plain`).

---

## 🔍 Server API Reference

The server (`paddle_server.py`) exposes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | server info + envelope protocol description |
| `/health` | GET | health check (GPU/memory/uptime) |
| `/probe` | GET | environment probe (GPU model/Python/packages) |
| `/execute` | POST | execute code (JSON `{"code": "...", "timeout": N}` or envelope body) |
| `/execute_stream` | POST | SSE streaming execution (supports `!cmd` and Python) |
| `/interrupt` | POST | interrupt the current execution (server keeps running) |
| `/status` | GET | current directory / executing flag / recent commands |
| `/history` | GET | command history (`?limit=N`, max 100) |
| `/variables` | GET | saved variables (type/shape/length) |
| `/files` | GET | list files in a directory (`?dir=`) |
| `/cleanup` | POST | clear variables + gc + flush Paddle/PyTorch CUDA caches |

All endpoints support `?respenc=b64url`. In JSON mode the code may contain `!shell` lines and magics — the server follows the same path as CLI `remote`/`stream`.

---

## 🆚 Relation to colabcli

| | colabcli | paddlecli |
|---|---|---|
| Target platform | Google Colab | Baidu AI Studio (BML Codelab) |
| Deployment notebook | `colab_server.ipynb` | `paddle_server.ipynb` |
| CLI command | `colabmcp` | `paddlecli` |
| CLI package | `colabmcp_cli` | `paddlemcp_cli` |
| Language env var | `COLABMCP_LANG` | `PADDLECLI_LANG` |
| Server default dir | `/content` | `/home/aistudio` |
| GPU cache cleanup | torch | paddle + torch |
| Envelope / SSE / CLI usage | ✅ | ✅ identical |

The two are wire-compatible: any colabcli or paddlecli server can be driven by either CLI using the same API.

---

## ❓ FAQ

**Q: `aitun` not found / install fails in an AI Studio cell?**
A: v2.1.3 is hardened against AI Studio's egress network as measured on a real machine: the `pypi.org` index is reachable but the package-file host `files.pythonhosted.org` is cut off (curl returns 000), `mirror.baidu.com` answers 403 for aitun, while the Tsinghua / Aliyun mirrors are fully reachable and serve files from their own domains. Since v2.1.3 the notebooks therefore: (1) strip platform-injected `PIP_*` env vars and pip.conf from every pip subprocess (a stale 403 extra-index can poison resolution) and pass explicit `--trusted-host` flags; (2) try Tsinghua first, Aliyun next, official last; (3) if pip fails everywhere, parse the TUNA `/simple/aitun/` page, direct-download the newest wheel and install it offline with `--no-index` (the aitun wheel has zero dependencies); (4) keep the native-binary direct download from `aitun.cc/downloads` as the last resort. pip errors are no longer swallowed — the tail of the log is printed on failure. Manual install: `pip install aitun -i https://pypi.tuna.tsinghua.edu.cn/simple`, or switch to the registration-free cloudflared: `cloudflared tunnel --url http://localhost:5000`.

**Q: Why do I see "Cannot run import torch because of system compatibility"?**
A: That is an AI Studio platform policy — PaddlePaddle-only environments intercept `import torch` and print this banner. Since v2.1.1 the server's VRAM cleanup probes frameworks silently (`redirect_stdout/stderr`), but on real machines the banner may still be printed by the platform at a lower level (file-descriptor level) that Python-side redirection cannot fully capture. It is cosmetic and harmless — ignore it. If you see it in your own remote code, that code imports torch — on AI Studio switch to the PaddlePaddle ecosystem (PaddleNLP / PaddleOCR / PaddleDetection, etc.), or run torch code locally instead.

**Q: Flask keeps flapping "stopped"/restarting and aitun says "No service is listening on localhost:5000", yet no error is shown?**
A: In v2.1.4 and earlier, the start cell piped the Flask subprocess's stdout/stderr into a pipe nobody read, so a crash-on-startup traceback was swallowed entirely and the keep-alive loop just restarted blindly. v2.1.5 fixes this for good: (1) a pre-flight check — whether `paddle_server.py` exists in the current directory (skipping the "Create Server Code" %%writefile cell is the most common cause), and whether flask/psutil truly import from the subprocess's point of view: if the inherited env fails but a sanitized env works, the platform-injected `PYTHONPATH` is stripped automatically (stale/broken copies under external-libraries can shadow pip-installed deps — an in-kernel `__import__` probe cannot see this); (2) the Flask output is teed to `paddle_server.log`, and the log tail is printed whenever the health handshake fails within 15s, the process exits abnormally, or before every restart. Fix: switch to the v2.1.5 notebooks; on older versions run `!python paddle_server.py` in the foreground for ~8s to see the crash directly.

**Q: Tunnel unreachable / URL expired?**
A: The tunnel URL changes whenever the process restarts. Check the latest URL printed in the notebook; the keep-alive loop reconnects and prints `[Restart] New URL`. You can also switch to cloudflared: `cloudflared tunnel --url http://localhost:5000`.

**Q: 409 / "another code is executing"?**
A: The server runs one snippet at a time. Wait for it to finish or `paddlecli interrupt -u URL`.

**Q: Free GPU quota exhausted?**
A: AI Studio enforces daily compute quotas. Stop the run when done (■ button or Ctrl+C) and switch to a CPU environment for light tasks.

**Q: How do I let an agent work fully autonomously?**
A: Give the agent the tunnel URL, then use `exec --json` exclusively (envelope stdin or `--c64`), parse the single-line JSON and branch on the exit code — no quote escaping involved.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file.

## 🙏 Credits

- Architecture & protocol lineage: [colabcli](https://github.com/ctz168/colabcli) / [colabmcp](https://github.com/ctz168/colabmcp)
- Built with [Click](https://click.palletsprojects.com/), [Rich](https://github.com/Textualize/rich), and [IPython](https://ipython.org/)
- Platform ecosystem: [Baidu AI Studio](https://aistudio.baidu.com/) / [PaddlePaddle](https://www.paddlepaddle.org.cn/)
