# RainTranslater

[English](README_EN.md)

本地 AI 翻译工具，使用腾讯混元 Hy-MT2 模型进行离线翻译，MyMemory 免费 API 在线兜底。

## 功能特性

- **本地翻译**：腾讯 Hy-MT2-1.8B 模型 + llama.cpp 推理引擎，毫秒级响应
- **在线兜底**：MyMemory 免费翻译 API，本地不可用时自动切换
- **三种模式**：自动（本地优先/在线兜底）、仅本地、仅在线
- **33 种语言**：中/英/日/韩/法/德/西/俄/葡/意/阿等
- **模型下载**：一键下载，实时显示来源、速度、进度条、剩余时间
- **干净卸载**：彻底清除模型文件、快捷方式和注册表

## 快速开始

1. 从 [Releases](https://github.com/DWK66614/RainTranslater/releases) 下载 `RainTranslater_Setup.exe`
2. 安装并启动
3. 点击「本地」模式下载翻译模型（约 1GB）
4. 开始翻译

## 从源码构建

需要 Python 3.10+ 和 NSIS 3.x。

```
pip install -r requirements.txt
python main.py
```

构建安装包：

```
python -m PyInstaller --noconfirm RainTranslater.spec
makensis.exe /INPUTCHARSET UTF8 setup.nsi
```

## 技术栈

- Python + Flask 后端
- C++ llama.cpp 推理引擎 (llama-server)
- WebView2 桌面窗口 (pywebview)
- HTML/CSS/JS 毛玻璃风格界面
- NSIS 安装器 (LZMA 压缩)
- MyMemory 免费翻译 API

## 鸣谢

- **Hy-MT2 模型**：腾讯混元翻译模型 2.0
- **llama.cpp**：本地 LLM 推理引擎
- **MyMemory**：免费翻译 API

## 许可证

MIT
