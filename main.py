import os
import sys
import ctypes
import tkinter as tk
from threading import Thread, Event

import uvicorn
import pystray
import qrcode
from qrcode.constants import ERROR_CORRECT_L
from PIL import Image, ImageTk
from fastapi import FastAPI, UploadFile, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from utils import get_static_path, get_local_ip

app = FastAPI()

UPLOAD_DIR = "uploads"
STATIC_PATH = get_static_path("static")  # 直接指向static目录
UPLOAD_HTML_PATH = get_static_path("static/upload.html")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# 存储所有连接的设备
connected_devices: set = set()

ip = get_local_ip()
port = 8000
url = f"http://{ip}:{port}"


def center_window(window, width: int, height: int) -> None:
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    window.geometry(f"{width}x{height}+{x}+{y}")


def show_qrcode(url: str) -> None:
    # 生成二维码
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_L,
        box_size=10,
        border=4
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    
    root = tk.Tk()
    root.title("手机扫码上传文件")

    center_window(root, 400, 450)

    tk_image = ImageTk.PhotoImage(image)

    label = tk.Label(root, image=tk_image)
    label.pack()

    url_label = tk.Label(root, text=f"或访问: {url}", font=("Arial", 10))
    url_label.pack()

    clost_btn = tk.Button(root, text="关闭", command=root.destroy)
    clost_btn.pack()

    root.mainloop()


@app.get("/upload")
async def upload_page():
    if not UPLOAD_HTML_PATH.exists():
        raise RuntimeError(status_code=500, detail="传输页面丢失!")
    
    return FileResponse(str(UPLOAD_HTML_PATH))


@app.post("/upload")
async def upload_file(file: UploadFile):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb+") as buffer:
        content = await file.read()
        buffer.write(content)
    return {"info": f"文件 '{file.filename}' 上传成功", "filename": file.filename}


@app.get("/record_ip")
async def record_ip(request: Request):
    client_ip = (
        request.headers.get("X-Real-IP") or
        request.headers.get("X-Forwarded-For", "").split(",")[0] or
        request.client.host
    )
    connected_devices.add(client_ip)
    return {"status": "IP记录成功", "ip": client_ip}


@app.get("/remove_ip")
async def remove_ip(request: Request):
    client_ip = (
        request.headers.get("X-Real-IP") or
        request.headers.get("X-Forwarded-For", "").split(",")[0] or
        request.client.host
    )
    if client_ip in connected_devices:
        connected_devices.remove(client_ip)
    return {"status": "IP已移除", "ip": None}


@app.get("/get_ips")
async def get_ips():
    return {"devices": list(connected_devices)}


def create_tray_icon(stop_event) -> None:
    """创建带自定义图标的系统托盘图标"""
    try:
        # 尝试加载自定义ICO文件（兼容打包环境）
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            icon_path = os.path.join(sys._MEIPASS, 'logo.ico')
        else:
            # 开发环境的路径
            icon_path = 'logo.ico'
            
        image = Image.open(icon_path)
    except Exception as e:
        print(f"无法加载自定义图标: {e}")
        # 回退到默认白色图标
        image = Image.new('RGB', (64, 64), 'white')
    
    menu = pystray.Menu(
        pystray.MenuItem("显示二维码", lambda: show_qrcode(url + "/static/upload.html")),
        pystray.MenuItem("退出", lambda: stop_server(stop_event))
    )
    icon = pystray.Icon(
        "file_transfer",
        image,  # 使用Image对象
        "文件传输工具",
        menu
    )

    icon.run()

def stop_server(stop_event) -> None:
    """停止服务器"""
    stop_event.set()
    os._exit(0)


app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")


def check_windows_version() -> None:
    if sys.getwindowsversion().major < 6:
        ctypes.windll.user32.MessageBoxW(0, "需要Windows 7或更高版本", "错误", 0x10)
        sys.exit(-1)


def main():
    check_windows_version()
    
    stop_event: Event = Event()

    Thread(
        target=create_tray_icon,
        args=(stop_event,),
        daemon=True
    ).start()
    
    Thread(
        target=show_qrcode,
        args=(url + "/static/upload.html",),
        daemon=False
    ).start()

    def run_server() -> None:
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_config=None, access_log=False)
        server = uvicorn.Server(config)
        while not stop_event.is_set():
            server.run()

    run_server()


if __name__ == "__main__":
    main()
