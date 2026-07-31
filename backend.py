"""
RainTranslater 后端服务
- llama-server (C++ llama.cpp) 本地推理
- MyMemory 在线兜底
- 自动下载模型
"""
import os
import sys
import json
import time
import signal
import socket
import threading
import subprocess
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__, static_folder=None)
CORS(app)

BASE_DIR = Path(__file__).parent
# PyInstaller bundle: data files are in sys._MEIPASS
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
BIN_DIR = BASE_DIR / "bin"
MODELS_DIR = BASE_DIR / "models"
UI_DIR = BASE_DIR / "ui"

# 模型配置
MODEL_REPO = "tencent/Hy-MT2-1.8B-GGUF"
MODEL_FILENAME = None  # auto-discover
MODEL_PATH = None  # resolved at startup

def find_model_file():
    """只在 models 目录中找通过软件下载的指定模型文件"""
    target = MODELS_DIR / MODEL_FILENAME_DL
    if target.exists():
        return target
    return None

# llama-server 进程管理
LLAMA_SERVER_PORT = 18766
llama_process = None
model_loaded = False
load_error = None

# ==================== llama-server 管理 ====================

def find_llama_server():
    """找到 llama-server 可执行文件"""
    candidates = [
        BIN_DIR / "llama-server.exe",
        BIN_DIR / "bin" / "llama-server.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # 递归搜索
    for root, dirs, files in os.walk(str(BIN_DIR)):
        for f in files:
            if f == "llama-server.exe":
                return os.path.join(root, f)
    return None

def is_port_open(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_llama_server():
    """启动 llama-server 进程"""
    global llama_process, model_loaded, load_error
    
    if model_loaded:
        return True
    
    server_exe = find_llama_server()
    if not server_exe:
        load_error = "未找到 llama-server.exe，请先下载 llama.cpp"
        log.error(load_error)
        return False
    
    model_file = find_model_file()
    if not model_file:
        load_error = "未找到模型文件，请先下载模型"
        log.error(load_error)
        return False
    
    # 如果端口已被占用，说明之前的实例还在运行
    if is_port_open(LLAMA_SERVER_PORT):
        log.info(f"端口 {LLAMA_SERVER_PORT} 已被占用，尝试复用...")
        model_loaded = True
        return True
    
    cmd = [
        server_exe,
        "-m", str(model_file),
        "--host", "127.0.0.1",
        "--port", str(LLAMA_SERVER_PORT),
        "-c", "2048",
        "-t", "4",
        "-b", "512",
        "-np", "1",        # 单并行请求
        "--no-webui",      # 不启动内置 WebUI
    ]
    
    log.info(f"启动 llama-server: {' '.join(cmd)}")
    try:
        llama_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(BASE_DIR),
        )
        
        # 等待服务器就绪
        for i in range(30):
            time.sleep(1)
            if is_port_open(LLAMA_SERVER_PORT):
                model_loaded = True
                load_error = None
                log.info("[OK] llama-server 已就绪")
                return True
        
        load_error = "llama-server 启动超时"
        log.error(load_error)
        return False
    except Exception as e:
        load_error = f"启动 llama-server 失败: {e}"
        log.error(load_error)
        return False

def stop_llama_server():
    """停止 llama-server 进程"""
    global llama_process, model_loaded
    if llama_process:
        try:
            llama_process.terminate()
            llama_process.wait(timeout=5)
        except Exception:
            try:
                llama_process.kill()
            except Exception:
                pass
        llama_process = None
    model_loaded = False

# ==================== 模型下载 ====================

import requests as _requests_module  # for download progress

MODEL_REPO_ID = "tencent/Hy-MT2-1.8B-GGUF"
MODEL_FILENAME_DL = "Hy-MT2-1.8B-Q4_K_M.gguf"
MODEL_DOWNLOAD_URL = f"https://huggingface.co/{MODEL_REPO_ID}/resolve/main/{MODEL_FILENAME_DL}"

# 下载状态（含速度、ETA）
download_state = {
    "downloading": False,
    "progress": 0,          # 百分比 0-100
    "downloaded_mb": 0,
    "total_mb": 0,
    "speed_mbps": 0,
    "eta_seconds": 0,
    "source": "HuggingFace (hf-mirror.com)",
    "error": None,
    "done": False,
}

def download_model():
    """从 HuggingFace 下载模型（后台线程，带进度追踪）"""
    global download_state
    
    if download_state["downloading"]:
        return
    
    download_state = {
        "downloading": True, "progress": 0, "downloaded_mb": 0,
        "total_mb": 0, "speed_mbps": 0, "eta_seconds": 0,
        "source": "HuggingFace (hf-mirror.com)", "error": None, "done": False,
    }
    
    def _run():
        global download_state
        try:
            MODELS_DIR.mkdir(exist_ok=True)
            out_path = MODELS_DIR / MODEL_FILENAME_DL
            
            # 先尝试 HF 镜像
            url = MODEL_DOWNLOAD_URL
            mirror = "https://hf-mirror.com/" + "/".join(MODEL_DOWNLOAD_URL.split("/")[3:])
            
            log.info(f"开始下载模型: {MODEL_REPO_ID}/{MODEL_FILENAME_DL}")
            
            # 获取文件大小
            try:
                head = _requests_module.head(mirror, timeout=10, allow_redirects=True)
                if head.status_code == 200:
                    url = mirror
                    download_state["source"] = "hf-mirror.com"
                else:
                    head = _requests_module.head(url, timeout=10, allow_redirects=True)
            except Exception:
                head = _requests_module.head(url, timeout=10, allow_redirects=True)
            
            total_size = int(head.headers.get("content-length", 0))
            download_state["total_mb"] = round(total_size / 1024 / 1024, 1)
            
            # 流式下载
            resp = _requests_module.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            
            downloaded = 0
            start_time = time.time()
            last_update = start_time
            
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        now = time.time()
                        if now - last_update >= 0.5:  # 每0.5秒更新状态
                            elapsed = now - start_time
                            speed = downloaded / elapsed / 1024 / 1024  # MB/s
                            progress = int(downloaded / total_size * 100) if total_size else 0
                            eta = (total_size - downloaded) / (speed * 1024 * 1024) if speed > 0 else 0
                            
                            download_state["downloaded_mb"] = round(downloaded / 1024 / 1024, 1)
                            download_state["progress"] = progress
                            download_state["speed_mbps"] = round(speed, 2)
                            download_state["eta_seconds"] = int(eta)
                            last_update = now
            
            download_state["done"] = True
            download_state["downloading"] = False
            download_state["progress"] = 100
            download_state["downloaded_mb"] = download_state["total_mb"]
            download_state["speed_mbps"] = 0
            download_state["eta_seconds"] = 0
            
            log.info(f"模型下载完成: {out_path}")
            
            # 自动启动 llama-server
            if find_model_file():
                start_llama_server()
        except Exception as e:
            log.error(f"模型下载失败: {e}")
            download_state["error"] = str(e)
            download_state["downloading"] = False
    
    threading.Thread(target=_run, daemon=True).start()

# ==================== 翻译模式 ====================
translation_mode = "auto"  # auto | local | online
last_engine = None  # 追踪上次使用的引擎，用于检测切换

# ==================== 翻译引擎 ====================

def translate_local(text: str, source_lang: str, target_lang: str) -> str:
    """使用 llama-server (OpenAI 兼容 API) 翻译"""
    import requests
    
    if not model_loaded:
        raise RuntimeError("本地模型未就绪")
    
    # Hy-MT2 prompt — 严格翻译指令
    prompt = f"<|im_start|>user\nTranslate the following text to {target_lang}. Output ONLY the translation, nothing else:\n{text}\n<|im_end|>\n<|im_start|>assistant\n"
    
    resp = requests.post(
        f"http://127.0.0.1:{LLAMA_SERVER_PORT}/v1/completions",
        json={
            "prompt": prompt,
            "max_tokens": 1024,
            "temperature": 0.3,
            "top_p": 0.6,
            "top_k": 20,
            "repeat_penalty": 1.05,
            "stop": ["<|im_end|>", "<|im_start|>", "<|endoftext|>", "\n\n\n", "\n<|", "Translate"],
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    result = data["choices"][0]["text"].strip()
    return result

def translate_api(text: str, source_lang: str, target_lang: str) -> str:
    """使用 MyMemory 免费翻译 API（兜底）"""
    import requests
    import urllib.parse
    
    # 语言代码映射
    lang_map = {
        "中文": "zh-CN", "英语": "en-GB", "日语": "ja", "韩语": "ko",
        "法语": "fr", "德语": "de", "西班牙语": "es", "俄语": "ru",
        "葡萄牙语": "pt", "意大利语": "it", "阿拉伯语": "ar",
        "zh": "zh-CN", "en": "en-GB", "ja": "ja", "ko": "ko",
        "fr": "fr", "de": "de", "es": "es", "ru": "ru",
        "pt": "pt", "it": "it", "ar": "ar",
    }
    
    src = lang_map.get(source_lang, source_lang)
    tgt = lang_map.get(target_lang, target_lang)
    
    # MyMemory 免费 API (1000字/天免key)
    params = {
        "q": text,
        "langpair": f"{src}|{tgt}",
        "de": "rain@translater.com",  # 用于统计，提升限额
    }
    
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("responseStatus") == 200:
            return data["responseData"]["translatedText"]
        else:
            raise RuntimeError(data.get("responseDetails", "未知错误"))
    except Exception as e:
        raise RuntimeError(f"MyMemory API 失败: {e}")

def translate(text: str, source_lang: str = "自动检测", target_lang: str = "中文") -> dict:
    """翻译入口：按模式执行（auto/local/online）"""
    global last_engine
    start_time = time.time()
    model_file = find_model_file()
    
    notification = None  # 引擎切换通知
    
    def try_local():
        """尝试本地翻译"""
        nonlocal model_file
        if not model_loaded:
            if model_file:
                if not start_llama_server():
                    return None
            else:
                return None
        if not model_loaded:
            return None
        try:
            return translate_local(text, source_lang, target_lang)
        except Exception as e:
            log.warning(f"本地翻译失败: {e}")
            return None
    
    def try_online():
        """尝试在线翻译"""
        try:
            return translate_api(text, source_lang, target_lang)
        except Exception as e:
            return None
    
    # --- 按模式执行 ---
    
    if translation_mode == "local":
        # 仅本地
        result = try_local()
        if result is None:
            if not model_file:
                return {"text": "", "error": "本地模型未下载，请先下载模型或切换为在线模式", "time": 0}
            if not model_loaded:
                return {"text": "", "error": "本地模型加载失败，请稍后重试或切换为在线模式", "time": 0}
            return {"text": "", "error": "本地翻译失败", "time": round(time.time() - start_time, 2)}
        
        engine = "Hy-MT2 (本地)"
        if last_engine and last_engine != engine:
            notification = "已切换回本地翻译"
        last_engine = engine
        return {"text": result, "engine": engine, "time": round(time.time() - start_time, 2), "notification": notification}
    
    elif translation_mode == "online":
        # 仅在线
        result = try_online()
        if result is None:
            return {"text": "", "error": "在线翻译失败，请检查网络连接", "time": round(time.time() - start_time, 2)}
        
        engine = "MyMemory (在线)"
        if last_engine and last_engine != engine:
            notification = "已切换为在线翻译"
        last_engine = engine
        return {"text": result, "engine": engine, "time": round(time.time() - start_time, 2), "notification": notification}
    
    else:  # auto 模式：本地优先，失败则在线兜底
        result = try_local()
        if result is not None:
            engine = "Hy-MT2 (本地)"
            if last_engine and last_engine != engine:
                notification = "本地模型已恢复，已切回本地翻译"
            last_engine = engine
            return {"text": result, "engine": engine, "time": round(time.time() - start_time, 2), "notification": notification}
        
        # 本地失败，在线兜底
        result = try_online()
        if result is not None:
            engine = "MyMemory (在线)"
            if last_engine != engine:
                notification = "本地模型不可用，已自动切换为在线翻译"
            last_engine = engine
            return {"text": result, "engine": engine, "time": round(time.time() - start_time, 2), "notification": notification}
        
        return {"text": "", "error": "本地和在线翻译均失败", "time": round(time.time() - start_time, 2)}

# ==================== API 路由 ====================

@app.route("/")
def index():
    return send_from_directory(str(UI_DIR), "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(UI_DIR), filename)

@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json()
    text = data.get("text", "").strip()
    source_lang = data.get("source", "自动检测")
    target_lang = data.get("target", "中文")
    
    if not text:
        return jsonify({"error": "请输入要翻译的文本"}), 400
    if len(text) > 5000:
        return jsonify({"error": "文本过长，最多5000字符"}), 400
    
    result = translate(text, source_lang, target_lang)
    return jsonify(result)

@app.route("/api/status")
def api_status():
    model_file = find_model_file()
    return jsonify({
        "model_loaded": model_loaded,
        "model_path": str(model_file) if model_file else None,
        "model_name": model_file.name if model_file else None,
        "load_error": load_error,
        "llama_server": find_llama_server() is not None,
        "version": "2.0.0",
    })

@app.route("/api/mode", methods=["GET", "POST"])
def api_mode():
    global translation_mode, last_engine
    if request.method == "POST":
        data = request.get_json()
        mode = data.get("mode", "auto")
        if mode in ("auto", "local", "online"):
            if mode != translation_mode:
                last_engine = None  # 手动切换时重置，确保下次翻译发出通知
            translation_mode = mode
            return jsonify({"mode": translation_mode, "changed": True})
        return jsonify({"error": "无效模式，可选: auto, local, online"}), 400
    return jsonify({
        "mode": translation_mode,
        "model_loaded": model_loaded,
        "has_model": find_model_file() is not None,
    })

@app.route("/api/model/download/start", methods=["POST"])
def api_download_start():
    """手动触发模型下载"""
    if find_model_file():
        return jsonify({"error": "模型已存在"}), 400
    download_model()
    return jsonify({"status": "started"})

@app.route("/api/model/status")
def api_download_status():
    """模型下载状态（含速度、进度、ETA）"""
    return jsonify(download_state)

@app.route("/api/languages")
def api_languages():
    return jsonify({
        "languages": [
            {"code": "中文", "name": "中文"},
            {"code": "英语", "name": "English"},
            {"code": "日语", "name": "日本語"},
            {"code": "韩语", "name": "한국어"},
            {"code": "法语", "name": "Français"},
            {"code": "德语", "name": "Deutsch"},
            {"code": "西班牙语", "name": "Español"},
            {"code": "俄语", "name": "Русский"},
            {"code": "葡萄牙语", "name": "Português"},
            {"code": "意大利语", "name": "Italiano"},
            {"code": "阿拉伯语", "name": "العربية"},
            {"code": "泰语", "name": "ไทย"},
            {"code": "越南语", "name": "Tiếng Việt"},
            {"code": "印尼语", "name": "Bahasa Indonesia"},
        ]
    })

# ==================== 后台预加载 ====================

def preload_async():
    """后台线程：检测模型 → 有则启动 llama-server，无则等待用户操作"""
    time.sleep(1)
    model_file = find_model_file()
    if model_file:
        log.info(f"发现本地模型: {model_file.name}，启动 llama-server...")
        start_llama_server()
    else:
        log.info("未发现本地模型，请通过界面下载")

# ==================== 启动 ====================

if __name__ == "__main__":
    threading.Thread(target=preload_async, daemon=True).start()
    port = int(os.environ.get("PORT", 18765))
    log.info(f"RainTranslater 后端启动于 http://127.0.0.1:{port}")
    try:
        app.run(host="127.0.0.1", port=port, debug=False)
    finally:
        stop_llama_server()
