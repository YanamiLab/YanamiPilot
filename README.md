# 智慧树刷课助手 · YanamiPilot

![智慧树刷课助手：1.5 倍速、自动切课、随堂练习、卡顿恢复](https://raw.githubusercontent.com/YanamiLab/YanamiPilot/a22a4f7d6e8d29aedacd91685cd2615c6fae8a41/docs/assets/banner.svg)

**智慧树（知到）视频自动播放助手，支持 1.5 倍速、自动切课、AI 随堂练习弹窗处理和卡顿恢复。**

[快速开始](#快速开始) · [常用设置](#常用设置) · [问题反馈](https://github.com/YanamiLab/YanamiPilot/issues) · [下载版本](https://github.com/YanamiLab/YanamiPilot/releases) · [English](README.en.md)

播放完一节还要点下一节，看到一半弹出练习，挂着挂着又卡在加载页——这个助手就是为这些重复操作写的。基于 Python + Playwright，在本机打开浏览器，登录课程后自动接着播放。

## 功能

- **1.5 倍速播放**：自动设置倍速，同时检查播放器的实际速度。
- **自动切换视频**：按目录寻找待完成的视频，播放结束后核对完成标记，再继续下一节。
- **处理随堂练习**：自动关闭 AI 随堂练习弹窗，也可设置为选择首项或手动作答。
- **卡顿自动恢复**：加载超时、播放停滞时自动刷新重试，并保存故障记录。
- **保留登录状态**：使用独立浏览器目录，方便下次继续运行。
- **查看运行进度**：记录当前章节、视频进度和实际倍速，支持接入外部监控。
- **验证后自动续播**：完成安全验证后继续播放；可选本地 OCR 辅助点选识别（实验功能）。
- **轻量本地识别**：CPU 即可运行，随包模型合计约 **88 MB**，一条命令安装，按需加载、用完退出。

日常播放由本地脚本每 2 秒检查一次，云端模型调用费用为零。当前版本为 **v0.1.0 预发布版**；适配范围为智慧树视频学习页及其中的 AI 随堂练习弹窗。原型已有实课运行记录，独立包已完成本地演示与自动测试，详细结果见[验证记录](docs/VALIDATION.md)。

## 快速开始

准备好 Python 3.11+ 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)，然后下载并安装：

```bash
git clone https://github.com/YanamiLab/YanamiPilot.git
cd YanamiPilot
uv sync --locked
uv run playwright install chromium
cp examples/config.toml config.toml
```

打开 `config.toml`，填写：

- `url`：浏览器中打开的智慧树课程学习页地址。
- `expected_videos`：这门课目录中的视频总数。

启动助手，在弹出的浏览器中登录课程：

```bash
uv run yanamipilot --config config.toml run
```

助手会核对目录、找到待完成视频，并按配置继续播放。查看进度或停止运行：

```bash
uv run yanamipilot --config config.toml status
uv run yanamipilot --config config.toml stop
```

想先试试？运行 `uv run yanamipilot demo`，即可体验本地两段视频的播放、练习弹窗处理和自动切换。

## 常用设置

| 配置项 | 默认值 | 作用 |
| --- | --- | --- |
| `speed` | `1.5` | 视频播放倍速 |
| `exercise_action` | `"close"` | AI 随堂练习：`close` 关闭、`first_option` 选择首项、`manual` 手动作答 |
| `poll_seconds` | `2` | 页面检查间隔，单位为秒 |
| `load_timeout` | `90` | 持续加载超过这个秒数后尝试刷新 |
| `stall_timeout` | `120` | 视频进度停滞超过这个秒数后尝试刷新 |
| `max_reloads` | `3` | 连续异常时的刷新次数上限 |
| `headless` | `false` | 默认显示浏览器，方便登录与处理验证 |

完整示例见 [examples/config.toml](examples/config.toml)。登录状态、截图和进度文件保存在本机，请妥善保管。

<details>
<summary>浏览器安装与状态文件</summary>

Linux 可使用 `uv run playwright install --with-deps chromium` 安装浏览器及系统依赖。

已有兼容 Chromium 时，设置 `executable_path` 指向其可执行文件。本地演示支持通过 `BROWSER_EXECUTABLE` 指定浏览器。

状态文件中的 `media.time` 表示视频进度，`time` 表示脚本最近一次检查时间，`state_since` 表示当前状态开始时间；`catalog` 保存最近一次目录核查结果。可据此接入自己的监控工具。

</details>

## 本地 OCR 辅助验证（实验）

**CPU 即可运行，模型约 88 MB，已有助手环境下一条命令装好。**

使用 ddddocr 在本机识别颜色与大写字母，预训练模型随依赖一起安装，装好即可调用。识别进程按需启动，完成后退出。

| 部署项 | 说明 |
| --- | --- |
| 计算设备 | 默认使用 CPU |
| 模型体积 | ddddocr 1.6.1 随包模型合计约 88 MB（83.8 MiB） |
| 环境占用 | 本机 OCR 独立环境含模型与依赖约 340 MB（324 MiB），浏览器另计；随系统与依赖版本有所变化 |
| 安装方式 | 在项目目录执行下方命令，模型随依赖安装 |
| 运行方式 | 图片在本机处理，模型按需加载，调用费用为零 |

```bash
uv sync --locked --extra ocr
```

遇到验证时，查看浏览器和 `challenge-screen.png`，确认当前验证内容后运行：

```bash
uv run yanamipilot --config config.toml approve CURRENT_CHALLENGE_ID
```

按提示输入 `yes`，脚本会对当前验证码尝试一次识别与点击。每次确认绑定当前图片，有效期为 120 秒；滑块及识别结果存疑的情况由用户在浏览器中完成，随后助手尝试续播。

**测试进度：本地模拟页面上的识别与点击已通过，真实平台自动通过仍待验证。** 也可将 OCR 安装在独立环境或外置盘，通过 `ocr_python` 指定该环境的 Python 路径。

## 反馈与参与

遇到卡顿、弹窗或页面改版，欢迎[提交 Issue](https://github.com/YanamiLab/YanamiPilot/issues)，附上助手版本、系统、问题描述和脱敏后的日志。欢迎补充适配、测试用例和使用教程，详见[贡献指南](CONTRIBUTING.md)与[后续计划](docs/ROADMAP.md)。

```bash
uv run python -m unittest discover -s tests -v
uv build
```

## 致谢与许可

[MIT](LICENSE) 开源。项目起于使用 [university-helper](https://github.com/sweetcornna/university-helper) 时对浏览器播放流程的改进，现已整理为独立 Python 包。感谢 Playwright、ddddocr 等开源项目，来源与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

请在平台允许且有权操作的课程中使用。
