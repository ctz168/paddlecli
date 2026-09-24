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
