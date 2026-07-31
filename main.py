"""
RainTranslator - macOS 毛玻璃风格翻译工具
本地 Hy-MT2 模型 + MyMemory 在线兜底

启动方式:
    python main.py              # 开发模式
    python main.py --no-window   # 仅启动后端（调试用）
"""
import os
import sys
import time
import json
import socket
import threading
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
PORT = 18765

def find_free_port(start=18765):
    """找一个空闲端口"""
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return start

def start_backend():
    """启动 Flask 后端服务器"""
    import backend
    backend.app.run(host="127.0.0.1", port=PORT, debug=False)

def wait_for_backend(timeout=15):
    """等待后端启动就绪"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=2)
            if req.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    print("=" * 50)
    print("  RainTranslator v1.0")
    print("  本地模型: Tencent Hy-MT2-1.8B")
    print("  在线兜底: MyMemory")
    print("=" * 50)
    
    # 确保在项目目录
    os.chdir(str(BASE_DIR))
    
    # 安装依赖（如果需要）
    req_file = BASE_DIR / "requirements.txt"
    if req_file.exists():
        try:
            import flask
            import webview
        except ImportError:
            print("\n[...] 首次运行，正在安装依赖...")
            subprocess.run([
                sys.executable, "-m", "pip", "install",
                "-i", "https://mirrors.aliyun.com/pypi/simple/",
                "--trusted-host", "mirrors.aliyun.com",
                "-r", str(req_file),
            ], check=True)
            print("[OK] 依赖安装完成\n")
    
    # 启动后端线程
    print(f"[...] 启动后端服务 (127.0.0.1:{PORT})...")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # 等待后端就绪
    print("[...] 等待后端就绪...")
    if not wait_for_backend():
        print("[ERROR] 后端启动超时！请检查 backend.py")
        sys.exit(1)
    
    print(f"[OK] 后端就绪: http://127.0.0.1:{PORT}")
    
    # 创建窗口
    if "--no-window" not in sys.argv:
        import webview
        
        # 读取窗口配置
        config_path = BASE_DIR / "window_config.json"
        if config_path.exists():
            with open(config_path) as f:
                cfg = json.load(f)
        else:
            cfg = {"width": 820, "height": 680, "x": None, "y": None}
        
        print(f"[Window] 创建窗口 ({cfg['width']}x{cfg['height']})...")
        
        window = webview.create_window(
            title="RainTranslator",
            url=f"http://127.0.0.1:{PORT}/?port={PORT}",
            width=cfg["width"],
            height=cfg["height"],
            x=cfg.get("x"),
            y=cfg.get("y"),
            min_size=(560, 480),
            resizable=True,
            frameless=False,
            easy_drag=False,
            background_color='#1E1E20',
        )
        
        # 窗口关闭时保存位置
        def on_closing():
            try:
                cfg["width"] = window.width
                cfg["height"] = window.height
                cfg["x"] = window.x
                cfg["y"] = window.y
                with open(config_path, 'w') as f:
                    json.dump(cfg, f)
            except Exception:
                pass
        
        window.events.closing += on_closing
        
        print("RainTranslator 已启动！")
        webview.start(debug=False)
    else:
        print("[Server] 后端运行中 (无窗口模式)，按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 再见！")

if __name__ == "__main__":
    main()
