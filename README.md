# 🚀 PaddleCLI

[![Run on AI Studio](https://img.shields.io/badge/Run%20on-Baidu%20AI%20Studio-2932e1?logo=baidu)](https://aistudio.baidu.com/)
[![GitHub](https://img.shields.io/badge/GitHub-ctz168%2Fpaddlecli-blue?logo=github)](https://github.com/ctz168/paddlecli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.1.4-green.svg)](https://github.com/ctz168/paddlecli)

一个强大的命令行工具，在**百度 AI Studio** 上运行 Jupyter Notebook，支持按 cell 流式输出、公网隧道远程控制与 AI Agent 防引号一发式执行。

A powerful command-line tool to run Jupyter Notebooks on **Baidu AI Studio**, with streaming output per cell, remote control over a public tunnel, and quoting-proof one-shot execution for AI agents.

> PaddleCLI 是 [colabcli](https://github.com/ctz168/colabcli) 的姊妹项目，把同样的「服务器部署在云端 Notebook + 本地 CLI 远程流式控制」体验带到百度 AI Studio（BML Codelab / 飞桨 AI Studio）。

## 📖 文档 | Documentation

- **[中文文档](README_zh.md)** - 完整中文文档
- **[English](README_en.md)** - Full documentation in English

## 🎯 快速开始

### 中文
1. 在 AI Studio 上部署服务器（打开 [paddle_server.ipynb](paddle_server.ipynb)，选择 GPU 环境运行）
2. 本地安装 CLI：`pip install git+https://github.com/ctz168/paddlecli.git`
3. 流式运行：`paddlecli stream notebook.ipynb -u https://your-tunnel-url`
4. AI agent 一发式执行（防引号地狱）：`echo samaicmdbegin... | paddlecli exec -u https://your-tunnel-url --json`

### English
1. Deploy the server on Baidu AI Studio (open [paddle_server.ipynb](paddle_server.ipynb), pick a GPU environment and run)
2. Install the CLI locally: `pip install git+https://github.com/ctz168/paddlecli.git`
3. Stream: `paddlecli stream notebook.ipynb -u https://your-tunnel-url`
4. One-shot for AI agents (quoting-proof): `echo samaicmdbegin... | paddlecli exec -u https://your-tunnel-url --json`

## ✨ 亮点

- 📡 **远程流式执行** — cell 逐个实时推送 stdout/stderr，训练进度一目了然
- 🖥️ **本地也能跑** — 不部署服务器也能用 `run` 在本地流式执行 notebook
- 🤖 **Agent 友好** — Samai Command Envelope 信封协议（base64url + CRC32），过 IM 网关不毁引号
- 🔓 **免注册隧道** — 内置 aitun 隧道支持，无需账号/token 即可拿到公网 URL
- 🈶 **中英双语** — `PADDLECLI_LANG=zh` 或 `--lang zh` 一键切换
- ⚡ **飞桨生态** — 面向 PaddlePaddle / AI Studio 用户，GPU 显存清理同时覆盖 paddle 与 torch

## 📄 许可证

MIT License - 见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 架构与协议同源：[colabcli](https://github.com/ctz168/colabcli) / [colabmcp](https://github.com/ctz168/colabmcp)
- 构建于 [Click](https://click.palletsprojects.com/)、[Rich](https://github.com/Textualize/rich) 与 [IPython](https://ipython.org/)
- 平台生态：[百度 AI Studio](https://aistudio.baidu.com/) / [PaddlePaddle](https://www.paddlepaddle.org.cn/)
