# 来源与第三方组件

## 项目来源

YanamiPilot 的起点是为一次真实浏览器任务单独编写的 Python 自动化脚本。该工作同时使用了 sweetcornna/university-helper，因此在此注明来源背景并保留其许可副本。当前独立包的运行代码来自该独立脚本及本项目新增模块，**没有捆绑 university-helper 后端或它的题库代码**。

- 背景项目：[sweetcornna/university-helper](https://github.com/sweetcornna/university-helper)
- 当时使用的提交：`6c10c06409d23b1feddce9e6f34a0ece76ff5feb`
- 许可：MIT，副本见 [docs/UPSTREAM_LICENSE.txt](docs/UPSTREAM_LICENSE.txt)

新增代码采用根目录 LICENSE 所述 MIT 许可。维护者需继续保留后来引入代码的原始归属与许可。

## 安装依赖

依赖由包管理器安装，仓库不复制第三方包源码、浏览器二进制或模型权重。确切版本与包哈希见 `uv.lock`。

| 组件 | 用途 | 上游 |
|---|---|---|
| Playwright | 浏览器驱动 | https://github.com/microsoft/playwright-python |
| filelock | 本机跨进程单实例锁 | https://github.com/tox-dev/filelock |
| ddddocr（可选） | 本地识别模型与推理接口 | https://github.com/sml2h3/ddddocr |
| NumPy / OpenCV / Pillow / ONNX Runtime（OCR 传递依赖） | 图像处理与本地推理 | 各安装包自带许可与 uv.lock |

ddddocr 的模型随其安装包提供；本仓库不另行转载权重。将来若制作包含模型、浏览器或依赖的独立安装包，发布前须再次核对并随包提供相关许可。

测试页面、SVG 图像和生成的视频由本项目编写，不包含课程素材、平台验证码或个人截图。
