# Worklog

## 2026-09-24 - PaddleCLI v2.1.0 创建（基于 colabcli 镜像移植）

### 任务
- 参考 ctz168/colabcli（Google Colab 版），创建 paddlecli：面向百度 AI Studio (BML Codelab) 的同架构远程执行 CLI

### 命名映射
| colabcli | paddlecli |
|---|---|
| `colabmcp`（命令）/ `colabmcp_cli`（包） | `paddlecli` / `paddlemcp_cli` |
| `colab_server.py` / `colab_server.ipynb` | `paddle_server.py` / `paddle_server.ipynb` |
| `COLABMCP_LANG` | `PADDLECLI_LANG` |
| 默认目录 `/content` | `/home/aistudio` |
| 版本 2.2.2 | 2.1.0（全文件统一：`__init__`/pyproject/server 徽章/notebook） |

### 平台适配
1. **paddle_server.py**：默认目录 `/home/aistudio`；`/cleanup` 先清 paddle 再清 torch 的 CUDA 缓存；心跳注释改 AI Studio
2. **paddle_server.ipynb**：AI Studio 部署四步（安装依赖 → writefile → 启动 Flask+aitun 隧道+保活循环 → 完成），横幅全部命令示例改为 `paddlecli`；新增 AI Studio 算力限额/隧道 URL 漂移提示
3. **paddlecli.ipynb**：一体化四 cell 部署笔记本，与磁盘 paddle_server.py 字节一致
4. **隧道**：沿用免注册 aitun 方案（`pip install aitun`），cloudflared 作为备选写入提示

### 工程配置
- pyproject.toml：PyPI 名 `paddlecli`，入口 `paddlecli = paddlemcp_cli.cli:main`，可选依赖组 `[server]`（flask/psutil）
- CI：`.github/workflows/tests.yml`（py3.8/3.10/3.12 矩阵 + CLI 冒烟）、`publish.yml`（打 tag `v*` 触发，测试→build→twine check→PyPI trusted publishing→GitHub Release）
- 测试：`tests/test_envelope.py`（19 项，移植）+ `test_notebook.py`（8 项，新增）+ `test_server.py`（10 项，新增：Flask test client 全端点，含信封/respenc/SSE/CRC 拒收）+ `test_i18n_cli.py`（9 项，新增：版本一致性、双语键对齐、CLI 冒烟）

### 验证（2026-09-24 本机实跑）
- ✅ pytest 47/47 全绿（envelope 19 + notebook 8 + server 10 + i18n/cli 10）
- ✅ 端到端（本地真实服务器）：`health` / `exec --json`（`NDIK`→"42\n"）/ 信封 stdin（`ZTJlIE9LCg`→"e2e OK\n"）/ `interrupt` / `stream`（SSE 逐 cell 实时）/ `remote`（批量 2/2 成功）
- ✅ 中文模式 `PADDLECLI_LANG=zh` 提示语正常
- ✅ 两个 notebook 的 `%%writefile paddle_server.py` 单元与磁盘文件字节一致（由 gen 脚本生成并断言）
- ✅ 全部代码 cell 通过 ast 语法检查
- ✅ 无 colab/Colab 残留引用

### 移植中发现并修复的上游问题
- **i18n 键不对齐**：colabcli 的 zh 字典缺 5 个 exec 相关键（`exec_cell_error`/`exec_envelope_bad`/`exec_envelope_ok`/`exec_bad_c64`/`exec_no_input`），中文模式下 `exec` 命令会回退英文。已补齐并通过 en/zh 键集合一致性测试
- **版本号统一**：colabcli 曾存在 `__init__`/pyproject/server 三处版本不一致（worklog 有记录）；paddlecli 用 `test_i18n_cli.py::test_version` 锁死 `__init__` = pyproject = server 三处一致

## 2026-09-24 - CI 首跑修正（GitHub Actions）

1. **py3.8/3.10 失败**：`tests/test_i18n_cli.py` 直接 `import tomllib`（3.11+ 标准库）→ 加 try/except 优雅降级，低版本跳过 pyproject 版本校验。修复后 Tests 矩阵 3.8/3.10/3.12 全绿
2. **publish.yml 启动失败（total_jobs=0）**：step 级 `if:` 不允许 `secrets` 上下文 → 改为 workflow 级 `env.HAS_PYPI_TOKEN` 间接判断
3. **PyPI 上传步骤失败（预期）**：trusted publishing 需仓库所有者在 pypi.org/manage/account/publishing 登记 pending publisher（GitHub token 无法代办）；登记后重跑 workflow 即可，或改配 `PYPI_API_TOKEN` secret（workflow 已二选一兼容）
4. **GitHub Release v2.1.0 已创建**（`if: always()` 保证 tag 必出 Release）

## 2026-09-24 - PaddleCLI v2.1.1 补丁（aitun 自举 + torch 横幅抑制）

### 问题报告（AI Studio 真机）
1. 启动隧道 cell 报 `FileNotFoundError: 'aitun'` —— AI Studio 默认 pip 源未同步 aitun，`!pip install ... -q` 失败不中断后续 cell，直到 Popen 才暴露
2. 日志刷 "Cannot run import torch because of system compatibility" —— AI Studio 平台策略：Paddle 专用环境拦截 `import torch` 并打印横幅，服务器 /cleanup 每次显存清理都触发

### 修复
1. **安装 cell**：`!pip install` 改为 Python cell —— 先默认源安装全部依赖，`shutil.which('aitun')` 自检失败时自动用官方 PyPI 源（`-i https://pypi.org/simple`）重装 aitun，双语打印就绪/失败状态
2. **启动 cell（aitun 自举）**：新增 `find_aitun()`（which → `~/.local/bin` → 环境 scripts 目录 → `python -m aitun.cli` 模块兜底）与 `ensure_aitun()`（缺包自动 pip 重装，默认源→官方源）；隧道与心跳重启统一使用解析到的命令；心跳循环 None 安全 + try/except；aitun 彻底不可用时打印双语修复指引后 SystemExit(1)
3. **/cleanup 静默探测**：paddle/torch 的 import 探测包进 `contextlib.redirect_stdout/stderr`，AI Studio 横幅不再刷屏（paddle 清理逻辑保留）
4. 实测验证：aitun 4.12.4 wheel 内嵌 linux-amd64 二进制；`python -m aitun.cli -p 5000` 真实隧道输出 `Proxy URL: https://aitun.cc/XXXX`，与 URL 正则匹配
5. all-in-one（paddlecli.ipynb）同步自举逻辑；版本号 `__VER__` 占位符化

### 版本与验证
- 版本 2.1.0 → 2.1.1：`__init__` / executor User-Agent / pyproject / paddle_server.py（/health version + 启动横幅）/ tests 断言 / README×3 徽章 / notebook 标题
- pytest 47/47 全绿；本地烟测 /health、/cleanup 通过且服务器日志无横幅
- gen_notebooks.py 断言：writefile == 磁盘 paddle_server.py（双 notebook）+ 隧道 cell 含 ensure_aitun
- README FAQ 更新（zh/en）：aitun 自举说明 + torch 横幅成因与替代方案（PaddleNLP/PaddleOCR 等）

## 2026-09-24 - PaddleCLI v2.1.2 补丁（aitun 多镜像 + 二进制直连兜底）

### 问题报告（AI Studio 真机，v2.1.1 自检生效后）
- 安装 cell 正确报出「默认源未找到 aitun」，但官方 PyPI 源（pypi.org / files.pythonhosted.org）在 AI Studio 网络也不可达 —— 官方源重试不够

### 修复
1. **多镜像 pip**：百度（AI Studio 默认）→ 清华 TUNA → 阿里云 → 官方，逐个尝试带 `--timeout 30`
2. **二进制直连兜底 `download_aitun_binary()`**：pip 全败时按平台映射 suffix，从 `aitun.cc/downloads` 直连下载原生二进制（aitun wheel 内嵌的正是它），GitHub releases 兜底，落盘 `~/.local/bin/aitun` + chmod 755；实测无需 `-s`（二进制默认服务器即 aitun.cc:6639）
3. all-in-one notebook 同步；find_aitun / 心跳重启链路不变

### 实测（沙箱默认源恰为百度镜像，完整复现 AI Studio 场景）
- 百度源：aitun 不存在（复现根因）→ 清华源：海外 IP 403（国内网络正常）→ 后续源装上 console script
- ensure_aitun() 返回 `/home/z/.venv/bin/aitun`，真实隧道建立 `https://aitun.cc/7JJJEDAU`，URL 正则命中 —— END-TO-END OK
- 版本 2.1.1 → 2.1.2 全套统一；pytest 47/47 全绿；README FAQ（zh/en）更新多镜像 + 二进制兜底说明

## 2026-09-24 - PaddleCLI v2.1.3 补丁（AI Studio 出口网络真机实测加固）

### 真机诊断结论（用户提供 curl 实测）
- `mirror.baidu.com/pypi/simple/aitun/` → **403**（百度镜像无 aitun 或拒绝 listing）
- `pypi.tuna.tsinghua.edu.cn/simple/aitun/` → **200**；`mirrors.aliyun.com/pypi/simple/aitun/` → **200**
- `pypi.org/simple/aitun/` → **200**，但 `files.pythonhosted.org` → **000**（索引可达、包文件域名被掐 → 官方源装任何包必失败，v2.1.1 官方源重试方案的死因）
- 结论：不是 pip 被整体禁止，是官方文件域名被墙 + 百度镜像 403；清华/阿里路是通的

### v2.1.3 修复
1. **pip 环境消毒**：安装 cell 与隧道 cell 所有 pip 子进程剥离 `PIP_*` 环境变量 + `PIP_CONFIG_FILE=os.devnull`（防平台注入的 403 extra-index 污染解析），显式 `--trusted-host` ×5、`--timeout 120 --retries 2`
2. **清华优先**：MIRRORS/PIP_INDEXES 改为 清华→阿里→官方（百度镜像移出 aitun 安装链）；flask/aitun/requests/psutil 一把从清华装齐，flask 缺失时阿里重试
3. **新增清华 wheel 直连兜底 `_wheel_fallback()`**：pip 全败时解析清华 `/simple/aitun/` 页面取最新 wheel（aitun-4.12.4-py3-none-any.whl，31MB，实测零依赖），分块下载后 `--no-index` 离线安装，完全不碰 pip 索引
4. **报错透传**：pip 重试去掉静默 `-q`，失败时打印 stderr 尾部 500 字符
5. 版本 2.1.2 → 2.1.3 全套统一；README FAQ（zh/en）重写 aitun 问题条目

### 验证
- pytest 47/47 全绿；gen_notebooks.py 断言全过（writefile 字节一致 + 新函数标记 + 语法检查）
- 污染环境烟测：`PIP_INDEX_URL/PIP_EXTRA_INDEX_URL=403百度镜像 + 假 pip.conf` 下安装 cell 一把成功
- wheel 离线安装烟测：`pip install /tmp/aitun-4.12.4-py3-none-any.whl --no-index` 成功，`aitun` 入口与 `python -m aitun.cli` 均可运行
