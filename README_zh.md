# 🚀 PaddleCLI

[![Run on AI Studio](https://img.shields.io/badge/Run%20on-Baidu%20AI%20Studio-2932e1?logo=baidu)](https://aistudio.baidu.com/)
[![GitHub](https://img.shields.io/badge/GitHub-ctz168%2Fpaddlecli-blue?logo=github)](https://github.com/ctz168/paddlecli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.1.3-green.svg)](https://github.com/ctz168/paddlecli)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

一个强大的命令行工具，在**百度 AI Studio** 上运行 Jupyter Notebook，支持按 cell 流式输出。

PaddleCLI 是 [colabcli](https://github.com/ctz168/colabcli) 的姊妹项目：把「Flask 服务器部署在云端 Notebook + 本地 CLI 通过公网隧道远程流式控制」的完整体验带到 **百度 AI Studio（BML Codelab）**，并原生适配飞桨 PaddlePaddle 生态。

```
┌─────────────────────┐         公网隧道 (aitun)        ┌──────────────────────────────┐
│  你的本地电脑         │  ────────────────────────────▶  │  百度 AI Studio (BML Codelab) │
│                     │                                 │                              │
│  paddlecli stream   │   POST /execute_stream (SSE)    │  paddle_server.py (Flask)     │
│  paddlecli remote   │  ◀────────────────────────────  │   ├─ 实时流式执行 (SSE)         │
│  paddlecli exec     │    逐 cell 实时输出              │   ├─ 变量状态 / 历史            │
│  (CLI / AI Agent)   │                                 │   └─ GPU: V100 / A100          │
└─────────────────────┘                                 └──────────────────────────────┘
```

---

## 🎯 快速开始

只需 3 步：

### 1. 在 AI Studio 上部署服务器

1. 打开 [百度 AI Studio](https://aistudio.baidu.com/)，创建/进入一个 **Notebook 项目**
2. 选择环境（建议 **V100 / A100 GPU**）
3. 上传或新建 notebook，内容与 [paddle_server.ipynb](paddle_server.ipynb) 一致（或直接上传该文件）
4. 依次运行全部 cell —— 最后一个 cell 会打印**公网 URL**，例如：

```
🎉 aitun 隧道已建立!
📡 公网 URL: https://xxxx.a.itun.im/xxxx
```

> 该 cell 内置 30 秒心跳与进程自动重启，**保持它运行**即可。隧道 URL 重启后会变化，以最新打印为准。

### 2. 本地安装 CLI

```bash
pip install git+https://github.com/ctz168/paddlecli.git
```

或从源码安装：

```bash
git clone https://github.com/ctz168/paddlecli.git
cd paddlecli
pip install -e .
```

### 3. 远程运行 Notebook

```bash
# 检查服务器健康状态
paddlecli health --url https://xxxx.a.itun.im/xxxx

# 远程运行 notebook（批量模式）
paddlecli remote notebook.ipynb -u https://xxxx.a.itun.im/xxxx

# 实时流式运行 notebook（推荐！）
paddlecli stream notebook.ipynb -u https://xxxx.a.itun.im/xxxx
```

---

## ✨ 功能特性

### 核心功能

- 📡 **实时流式执行** — 基于 SSE（Server-Sent Events），stdout/stderr 逐块实时推送，适合训练、爬虫、Bot 等长任务
- 🎛️ **按 cell 粒度控制** — 支持 `--start/--end` 只执行部分 cell，`--stop-on-error` 出错即停
- 🖥️ **本地执行引擎** — `run` 命令在本地流式执行 notebook，无需部署服务器；支持 IPython magic 命令与变量持久化
- 🔄 **magic 命令转换** — 远程模式下自动把 `%cd`、`%env`、`%pip install`、`!cmd`、`%%writefile`、`%%bash` 等转换为可远程执行的 Python
- ⏹️ **中断与状态** — 随时 `interrupt` 中断远程执行（不动服务器本身），`status`/`history`/`watch` 观察运行状态
- 🧠 **变量与会话保持** — 执行过的变量驻留服务器内存，跨请求复用；`/variables` 查看形状与长度
- 🧹 **显存/内存清理** — `/cleanup` 同时清理 paddle 与 torch 的 CUDA 缓存

### AI Agent 友好（v2.1.0）

- ✉️ **Samai Command Envelope 信封协议** — 代码以 base64url 装入 `samaicmdbegin ... samaicmdend` 信封，纯 ASCII 字符集 + CRC32 校验，经过 IM 网关/聊天桥不毁引号、不丢反斜杠
- 📤 **respenc 响应保护** — `?respenc=b64url` 把响应文本字段转成 `*_b64`，`exec --json` 原样输出单行纯 ASCII JSON，返回路径同样字节无损
- 🔢 **退出码语义** — 0 成功 / 1 执行错误 / 2 传输或参数错误，方便 agent 判断

### 其他功能

- 🈶 **中英双语** — `PADDLECLI_LANG=zh` 或 `--lang zh` 切换全部提示信息
- 📊 **notebook 工具** — `info` 查看结构、`cells` 预览内容、`convert` 转 Python 脚本
- 🔍 **环境探测** — `health` 显示 GPU/内存/Python 版本/包数量
- 🔓 **免注册隧道** — aitun 无需账号与 token；也可替换为 cloudflared / ngrok / 自有隧道

---

## 📦 安装

### 从 GitHub 安装（推荐）

```bash
pip install git+https://github.com/ctz168/paddlecli.git
```

### 从源码安装

```bash
git clone https://github.com/ctz168/paddlecli.git
cd paddlecli
pip install -e .
```

### 依赖

- Python ≥ 3.8
- `click`、`rich`、`requests`、`ipython`（CLI 自动安装）
- 服务器端另需 `flask`、`psutil`（`pip install paddlecli[server]` 或在 AI Studio 中由 notebook cell 安装）

### 语言设置

```bash
export PADDLECLI_LANG=zh        # 中文提示（默认 en）
paddlecli --lang zh --version   # 或按次指定
```

---

## 🚀 使用方法

### 本地运行 Notebook

```bash
# 基本用法
paddlecli run notebook.ipynb

# 只执行 cell 5 到 cell 9（不含 cell 10）
paddlecli run notebook.ipynb --start 5 --end 10

# 显示 markdown cell
paddlecli run notebook.ipynb --show-markdown

# 出错继续 + 保存结果到 JSON
paddlecli run notebook.ipynb --continue-on-error -o results.json
```

### 远程批量执行（AI Studio）

```bash
# 基本远程执行
paddlecli remote notebook.ipynb -u https://xxxx.a.itun.im/xxxx

# 长时间训练任务（1 小时超时）
paddlecli remote train.ipynb -u https://xxxx.a.itun.im/xxxx -t 3600

# 只执行 cell 3-4
paddlecli remote notebook.ipynb -u https://xxxx.a.itun.im/xxxx -s 3 -e 5
```

### 实时流式执行（推荐）

基于 SSE，每个 cell 的输出实时滚动显示，`Ctrl+C` 会自动向服务器发送中断：

```bash
# 实时流式输出整个 notebook
paddlecli stream notebook.ipynb -u https://xxxx.a.itun.im/xxxx

# 只流式执行 cell 3（如训练启动 cell）
paddlecli stream train.ipynb -u https://xxxx.a.itun.im/xxxx --start 3 --end 4

# 实时监控服务器状态（Ctrl+C 停止）
paddlecli watch -u https://xxxx.a.itun.im/xxxx
```

### 一发式 `exec` — AI agent 防引号地狱模式

为让 AI agent 的代码穿过 IM 网关/聊天桥不被"智能引号"、反斜杠吞噬毁掉，`exec` 提供三种输入模式（按安全性排序）：

```bash
# 1) 最安全 — 信封走 stdin（负载 base64url + CRC32 校验）：
cat env.txt | paddlecli exec -u https://xxxx.a.itun.im/xxxx

# 2) 防引号 argv — 纯 [A-Za-z0-9_-] 参数，完全无需转义：
paddlecli exec -u URL --c64 cHJpbnQoNDArMikK

# 3) 普通代码（人类便利模式）：
paddlecli exec -u URL -c 'print(40+2)'

# 实时流式输出（默认，人类友好）：
paddlecli exec -u URL -c 'for i in range(3): print(i)'

# agent 模式：单行纯 ASCII JSON（stdout_b64 等字段）+ 退出码 0/1/2：
echo samaicmdbegin... | paddlecli exec -u URL --json
paddlecli exec -u URL -c 'import os' --json --plain   # --plain 本地解码 *_b64 便于人读
```

自建信封（把 `你的Python代码` 换成要跑的代码）：

```bash
python3 -c "import zlib,base64,sys;p=sys.argv[1].encode();print('samaicmdbegin\nv=1\nenc=b64url\ncrc=%08x\n%s\nsamaicmdend'%(zlib.crc32(p)&0xffffffff,base64.urlsafe_b64encode(p).decode().rstrip('=')))" '你的Python代码' | paddlecli exec -u URL --json
```

### 其他命令

```bash
# 查看 notebook 信息
paddlecli info notebook.ipynb

# 列出并预览 cell
paddlecli cells notebook.ipynb --start 0 --end 5

# 转换为 Python 脚本
paddlecli convert notebook.ipynb -o script.py

# 交互式 Python REPL（本地）
paddlecli repl

# 查看服务器状态 / 命令历史
paddlecli status  -u https://xxxx.a.itun.im/xxxx
paddlecli history -u https://xxxx.a.itun.im/xxxx --limit 50

# 中断当前远程执行（不影响服务器本身）
paddlecli interrupt -u https://xxxx.a.itun.im/xxxx
```

---

## 📖 命令参考

### 命令概览

| 命令 | 描述 | 用途 |
|------|------|------|
| `paddlecli run` | 本地执行 notebook | 快速测试、本地开发 |
| `paddlecli remote` | 远程批量执行 | 短时间任务、数据处理 |
| `paddlecli stream` | 远程流式执行 | 长时间任务、Bot、训练 |
| `paddlecli exec` | 一发式代码执行 | AI agent、自动化脚本 |
| `paddlecli watch` | 监控服务器状态 | 查看远程执行进度 |
| `paddlecli health` | 检查服务器健康状态 | 验证连接 |
| `paddlecli status` | 获取执行状态 | 查看当前目录和状态 |
| `paddlecli interrupt` | 中断当前执行 | 停止运行中的代码 |
| `paddlecli history` | 查看命令历史 | 调试、回溯 |
| `paddlecli info` | 查看 notebook 信息 | 了解 notebook 结构 |
| `paddlecli cells` | 列出 cell 内容 | 预览代码 |
| `paddlecli convert` | 转换为 Python 脚本 | 导出代码 |
| `paddlecli repl` | 交互式 Python REPL | 本地测试 |

### `paddlecli run` 参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--start` | `-s` | 0 | 起始 cell 索引 |
| `--end` | `-e` | 最后一个 | 结束 cell 索引（不含，类似 Python slice） |
| `--show-code` | - | True | 执行前显示代码 |
| `--show-markdown` | - | False | 显示 markdown cell |
| `--stop-on-error` / `--continue-on-error` | - | True | 出错是否停止 |
| `--verbose` | `-V` | False | 详细输出（含 traceback） |
| `--output` | `-o` | - | 保存结果到 JSON 文件 |

### `paddlecli remote` 参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | `-u` | 必填 | paddlecli 服务器 URL |
| `--start` | `-s` | 0 | 起始 cell 索引 |
| `--end` | `-e` | 最后一个 | 结束 cell 索引（不含） |
| `--timeout` | `-t` | 300 | 超时时间（秒） |
| `--stop-on-error` / `--continue-on-error` | - | True | 出错是否停止 |
| `--verbose` | `-V` | False | 详细输出 |

### `paddlecli stream` 参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | `-u` | 必填 | paddlecli 服务器 URL |
| `--start` | `-s` | 0 | 起始 cell 索引 |
| `--end` | `-e` | 最后一个 | 结束 cell 索引（不含） |
| `--timeout` | `-t` | 600 | 流式超时（秒） |
| `--stop-on-error` / `--continue-on-error` | - | True | 出错是否停止后续 cell |
| `--verbose` | `-V` | False | 显示 cell 源码 |

### `paddlecli exec` 参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | `-u` | 必填 | paddlecli 服务器 URL |
| `--code` | `-c` | - | 要执行的代码（省略时读 stdin） |
| `--c64` | - | - | base64url 编码的代码（防引号 argv） |
| `--timeout` | `-t` | 600 | 超时（秒） |
| `--json` | - | False | 输出单行纯 ASCII JSON（agent 模式） |
| `--plain` | - | False | 配合 `--json`：本地解码 `*_b64` 字段 |

---

## ✉️ Samai Command Envelope 信封协议（v1）

当 AI agent 远程控制本工具时，命令文本往往要经过多层会"修复"文本的传输层：

```
agent → IM/聊天网关 → HTTP POST → 隧道 → 服务器 → 内核
```

网关会吞 `"`、把直引号变智能引号（“ ”）、剥反斜杠、重排换行——到内核时代码已面目全非（"引号地狱"）。

信封协议把代码夹在两个纯小写字母标记之间，负载 base64url 编码（只含 `[A-Za-z0-9-_]`，任何网关都无从下手），再用 CRC32 兜底校验：

```
samaicmdbegin
v=1
enc=b64url
crc=1a2b3c4d
<b64url 负载，76 字符换行>
samaicmdend
```

- **用法**：把信封作为 `text/plain` body POST 到 `/execute`（或 `/execute_stream`），不是 JSON
- **校验**：`crc` = `zlib.crc32(payload) & 0xffffffff` 的 8 位小写 hex；CRC 不符即拒收，agent 应重发
- **超时**：URL 追加 `?timeout=N`（默认 600，上限 1800）
- **响应保护**：URL 追加 `&respenc=b64url`，响应中的 `stdout/stderr/error/error_type/traceback` 移入 `*_b64`（无填充 urlsafe base64），返回路径同样字节无损
- **兼容**：`enc=raw`（原文直传）、`enc=b64`、`enc=hex` 均可解析；负载中的空白在 b64 模式下被忽略，重排换行无害
- **上限**：负载 16 MiB

CLI 的 `exec --json` 已自动完成"信封请求 + respenc 响应 + 纯 ASCII 单行输出"全链路，agent 只需解码 `*_b64`（或加 `--plain`）。

---

## 🔍 服务器 API 参考

服务器（`paddle_server.py`）暴露以下端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务器信息 + 信封协议说明 |
| `/health` | GET | 健康检查（GPU/内存/运行时长） |
| `/probe` | GET | 环境探测（GPU 型号/Python 版本/包列表） |
| `/execute` | POST | 执行代码（JSON `{"code": "...", "timeout": N}` 或信封 body） |
| `/execute_stream` | POST | SSE 流式执行（支持 `!cmd` 与 Python 代码） |
| `/interrupt` | POST | 中断当前执行（不影响服务器） |
| `/status` | GET | 当前目录/是否执行中/最近命令 |
| `/history` | GET | 命令历史（`?limit=N`，最多 100） |
| `/variables` | GET | 已保存变量（类型/形状/长度） |
| `/files` | GET | 列出当前目录文件（`?dir=` 指定目录） |
| `/cleanup` | POST | 清空变量 + gc + 清理 paddle/torch CUDA 缓存 |

所有端点均支持 `?respenc=b64url` 响应保护。JSON 模式下代码可以包含 `!shell` 与 magic 命令，服务器按 CLI `remote`/`stream` 的同一条路径执行。

---

## 🆚 与 colabcli 的关系

| | colabcli | paddlecli |
|---|---|---|
| 目标平台 | Google Colab | 百度 AI Studio (BML Codelab) |
| 部署 notebook | `colab_server.ipynb` | `paddle_server.ipynb` |
| CLI 命令 | `colabmcp` | `paddlecli` |
| CLI 包 | `colabmcp_cli` | `paddlemcp_cli` |
| 语言环境变量 | `COLABMCP_LANG` | `PADDLECLI_LANG` |
| 服务器默认目录 | `/content` | `/home/aistudio` |
| 显存清理 | torch | paddle + torch |
| 信封协议 / SSE / CLI 用法 | ✅ | ✅ 完全一致 |

二者协议互通：只要服务器端是 colabcli 或 paddlecli 之一，任何一家的 CLI 都可以按相同 API 连接执行。

---

## ❓ 常见问题

**Q: AI Studio 上运行 notebook cell 时 `aitun` 找不到 / 安装失败？**
A: v2.1.3 已针对真机实测的 AI Studio 出口网络全面加固。实测特征：`pypi.org` 索引可达但包文件域名 `files.pythonhosted.org` 被掐断（curl 返回 000）、`mirror.baidu.com` 对 aitun 返回 403、清华 / 阿里镜像完全可达且文件走镜像自身域名。因此 notebook 从 v2.1.3 起：① 所有 pip 子进程剥离平台注入的 `PIP_*` 环境变量与 pip.conf（避免 403 的 extra-index 拖垮整个解析），显式传 `--trusted-host`；② 清华源优先、阿里源其次、官方源仅兜底；③ pip 全败时自动解析清华 `/simple/aitun/` 页面，直连下载最新 wheel 并以 `--no-index` 离线安装（aitun wheel 零依赖，完全不碰索引）；④ 最后保留 `aitun.cc/downloads` 原生二进制直连。报错不再静默（`-q` 失败时透传 pip 尾部日志）。手动安装：`pip install aitun -i https://pypi.tuna.tsinghua.edu.cn/simple`，或改用免注册的 cloudflared：`cloudflared tunnel --url http://localhost:5000`。

**Q: 日志里出现 "Cannot run import torch because of system compatibility"？**
A: 这是 AI Studio 的平台策略 —— PaddlePaddle 专用环境拦截 `import torch` 并打印该横幅。v2.1.1 起服务器的显存清理已改为静默探测，不再刷出该横幅；若你在自己远程执行的代码里看到它，说明那段代码用了 torch，AI Studio 上请改用 PaddlePaddle 生态（PaddleNLP / PaddleOCR / PaddleDetection 等），或改在本地运行 torch 代码。

**Q: 隧道连不上 / URL 失效？**
A: 隧道 URL 在进程重启后会变化。查看 notebook 最新一次打印的 URL；保活循环会自动重连并打印 `[重启] 新公网 URL`。也可换用 cloudflared：`cloudflared tunnel --url http://localhost:5000`。

**Q: 提示 409 / "另一个代码正在执行中"？**
A: 服务器同一时刻只执行一段代码。等待完成，或 `paddlecli interrupt -u URL` 中断后重试。

**Q: 免费 GPU 额度用完了？**
A: AI Studio 每日算力有限额。任务完成后请停止运行（点击 ■ 或 Ctrl+C），并可在项目中切换 CPU 环境跑轻量任务。

**Q: 如何让 agent 全自动干活？**
A: agent 侧只需拿到隧道 URL，然后全程使用 `exec --json`（信封 stdin 或 `--c64`），解析单行 JSON、按退出码判断成败即可，无需处理引号转义。

---

## 📄 许可证

MIT License - 见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 架构与协议同源：[colabcli](https://github.com/ctz168/colabcli) / [colabmcp](https://github.com/ctz168/colabmcp)
- 构建于 [Click](https://click.palletsprojects.com/)、[Rich](https://github.com/Textualize/rich) 与 [IPython](https://ipython.org/)
- 平台生态：[百度 AI Studio](https://aistudio.baidu.com/) / [PaddlePaddle](https://www.paddlepaddle.org.cn/)
