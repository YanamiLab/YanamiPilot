# Zhihuishu Course Assistant · YanamiPilot

![智慧树刷课助手](https://raw.githubusercontent.com/YanamiLab/YanamiPilot/a22a4f7d6e8d29aedacd91685cd2615c6fae8a41/docs/assets/banner.svg)

**A Python + Playwright assistant for Zhihuishu (Zhidao) video courses: 1.5× playback, automatic lesson switching, AI practice pop-up handling, and recovery from playback stalls.**

[中文使用说明](README.md) · [Issues](https://github.com/YanamiLab/YanamiPilot/issues) · [Releases](https://github.com/YanamiLab/YanamiPilot/releases)

Run the assistant on your computer, sign in through its browser window, and let it handle the repeated playback controls. It keeps a local browser profile, checks actual playback speed and progress, and verifies completion markers before switching lessons. Routine playback runs entirely through local scripts.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/YanamiLab/YanamiPilot.git
cd YanamiPilot
uv sync --locked
uv run playwright install chromium
cp examples/config.toml config.toml
```

Fill in your course URL and the actual video count (`expected_videos`) in `config.toml`, then start:

```bash
uv run yanamipilot --config config.toml run
```

Use `yanamipilot status` to inspect progress and `yanamipilot stop` to stop. To try the two-video local demo, run `uv run yanamipilot demo`.

## Optional local OCR (experimental)

**Runs on CPU, with about 88 MB of bundled models.** Enable it in an existing project environment with `uv sync --locked --extra ocr`; pretrained models are included in the dependency installation. The measured local OCR environment uses about 340 MB including dependencies, with the browser installed separately. Sizes vary by platform and dependency versions. Recognition starts on demand and exits when finished.

Color and uppercase-character recognition runs locally through ddddocr. Each attempt requires confirmation for the current challenge. Sliders and uncertain matches use manual completion, followed by automatic playback resumption.

Recognition and clicking have passed synthetic local tests; real-platform automatic CAPTCHA acceptance remains to be verified. Version **0.1.0 is a prerelease**. The original runner has real-course playback records; the extracted package has been exercised through the local demo and automated tests. See [validation details](docs/VALIDATION.md).

## Contributing

Bug reports, adapter improvements, tests, and documentation are welcome. See [contributing](CONTRIBUTING.md) and the [roadmap](docs/ROADMAP.md). Keep browser profiles, login state, and personal course data private.

```bash
uv run python -m unittest discover -s tests -v
uv build
```

## Credits and license

[MIT](LICENSE). The project grew out of browser-playback improvements made while using [university-helper](https://github.com/sweetcornna/university-helper), and is packaged as an independent Python application. Thanks to Playwright, ddddocr, and the projects listed in [third-party notices](THIRD_PARTY_NOTICES.md).

Use with courses you are authorized to access and where automation is permitted.
