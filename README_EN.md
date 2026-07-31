# RainTranslater

[中文](README.md)

Local AI translation tool powered by Tencent Hy-MT2 with MyMemory free API fallback.

## Features

- **Local Translation**: Tencent Hy-MT2-1.8B via llama.cpp, sub-second inference
- **Online Fallback**: MyMemory free translation API, auto-switch when local unavailable
- **Three Modes**: Auto (local first, online backup), Local only, Online only
- **33 Languages**: Chinese, English, Japanese, Korean, French, German, Spanish, etc.
- **Model Download**: One-click download with source, speed, progress bar, ETA
- **Clean Uninstall**: Removes model files, shortcuts, and registry entries

## Quick Start

1. Download `RainTranslater_Setup.exe` from [Releases](https://github.com/DWK66614/RainTranslater/releases)
2. Install and launch
3. Click "Local" mode to download the translation model (~1 GB)
4. Start translating

## Build from Source

Requires Python 3.10+ and NSIS 3.x.

```
pip install -r requirements.txt
python main.py
```

To build the installer:

```
python -m PyInstaller --noconfirm RainTranslater.spec
makensis.exe /INPUTCHARSET UTF8 setup.nsi
```

## Tech Stack

- Python + Flask backend
- C++ llama.cpp inference engine (llama-server)
- WebView2 desktop window (pywebview)
- HTML/CSS/JS frosted glass UI
- NSIS installer with LZMA compression
- MyMemory free translation API

## Credits

- **Hy-MT2 Model**: Tencent Hunyuan Translation Model 2.0
- **llama.cpp**: Local LLM inference engine
- **MyMemory**: Free translation API

## License

MIT
