# 续航 · YanamiPilot

![YanamiPilot](docs/assets/banner.svg)

**浏览器任务，持续推进。遇到异常，有据可查。**

[English](README.en.md) · [验证记录](docs/VALIDATION.md) · [路线图](docs/ROADMAP.md) · [贡献指南](CONTRIBUTING.md)

YanamiPilot 是一个本地 Python / Playwright 浏览器任务助手。它把重复操作交给脚本，把加载故障、进度停滞和需要人工接管的情况明确记录下来。

首版从实际课程播放问题中提取，提供一个智慧树视频适配器和完全本地的演示。常规运行不调用云端模型，也不需要 OpenAI API Key。项目目前为 **0.1.0 实验版本**。

## 已实现

- **实际进度监控**：区分脚本心跳、状态持续时间与媒体播放时间，读取真实倍速及菜单文字。
- **有上限的故障恢复**：目录、播放器加载超时及播放停滞可自动刷新，重试耗尽明确报错。
- **独立浏览器会话**：保留本地登录配置，使用单实例锁，清理本会话内重复课程页。
- **随堂练习策略**：默认关闭 AI 随堂练习弹窗，也可配置等待人工或选择首项；限定于该弹窗，不处理章节考试。
- **人工接管与续播**：遇到验证码暂停播放，记录当前挑战；人工完成后检测媒体是否继续推进。
- **可选本地识别桥接**：支持有限的颜色与大写字母点选识别；当次确认、图片绑定、一次尝试、120 秒授权有效期。滑块须人工处理。
- **本地状态接口**：原子写入 JSON 状态，JSONL 仅记录状态转换，方便外部监控接入。

验证码识别在自制测试页面上验证过，**尚无真实平台自动通过的验收结论**。点击后弹窗消失和媒体继续播放仅属于行为证据，不等于检查了平台验证接口。首版没有内置云端模型、即时唤醒 Codex、消息通知服务或通用网站适配器。

## 30 秒了解工作方式

```text
启动浏览器 → 登录 → 核对目录 → 选择待完成视频 → 检查实际播放
                           ↑                       │
                           └── 播放结束后复核标记 ─┘
加载超时 → 有限刷新 → 恢复 / 明确报错
验证弹窗 → 暂停并记录 → 人工接管或当次批准本地识别 → 验证续播
```

## 安装与本地演示

需要 Python 3.11+ 和 [uv](https://docs.astral.sh/uv/)。在源码目录执行：

```bash
uv sync --locked
uv run playwright install chromium
uv run yanamipilot demo
```

演示仅访问临时的 `127.0.0.1` 页面，生成并播放两段本地视频，经过练习弹窗、章节切换和完成复核；不需要平台账号。退出后清理临时浏览器配置和服务器。Linux 系统可能还需要 `uv run playwright install --with-deps chromium`，涉及系统包安装时按本机权限处理。

已有兼容的 Chromium 时，可以给演示设置 `BROWSER_EXECUTABLE` 环境变量，实际运行则设置配置里的 `executable_path`，避免重复下载。

## 运行自己的课程

```bash
cp examples/config.toml config.toml
# 编辑 url、expected_videos 以及需要的本机路径
uv run yanamipilot --config config.toml run
```

默认打开可见的独立浏览器，请在该窗口登录。`expected_videos` 应填写实际目录视频数：目录数量不符时不会宣布完成。仅在平台允许、你有权操作的场景使用。

```bash
uv run yanamipilot --config config.toml status
uv run yanamipilot --config config.toml stop
```

状态文件位于配置指定的本地目录。`time` 是心跳；`state_since` 是同一状态的开始时间；`media.time` 是视频播放进度。`catalog` 是最近一次目录核查结果，并非每两秒重新查询平台成绩。

## 可选 OCR

```bash
uv sync --locked --extra ocr
```

也可以把 OCR 依赖装在另一个独立环境或外置盘，只需该环境安装本项目的 `ocr` extra。配置 `ocr_python` 指向该 Python 解释器；路径不会写死。识别进程按需启动，完成后退出，不常驻。

验证发生时查看当前浏览器与 `challenge-screen.png`。确认处理当前挑战后执行：

```bash
uv run yanamipilot --config config.toml approve CURRENT_CHALLENGE_ID
```

命令会显示提示并要求输入 `yes`。授权绑定当前挑战，一次消费；过期、图片变化、候选不唯一或不支持的类型需要人工处理。人工完成后会自动尝试续播。

## 开发

```bash
uv sync --locked
uv run playwright install chromium
uv run python -m unittest discover -s tests -v
uv build
```

测试使用原创本地页面，不访问真实课程、不读取个人配置。仓库配有 GitHub Actions 工作流；只有远程实际运行成功后，才能称为 CI 通过。

## 来源与许可

MIT。项目在使用 [university-helper](https://github.com/sweetcornna/university-helper) 的实际维护过程中形成，浏览器执行器在本地单独编写后提取为独立 Python 包，运行时不依赖其后端。本项目没有把上游完整代码库改名发布。

Playwright、ddddocr 及其依赖保留各自许可；完整来源与第三方说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。YanamiPilot 与课程平台、OpenAI 均无官方隶属或背书关系。
