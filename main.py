import os
import sys
import socket
from pathlib import Path
import tkinter as tk
from typing import Union
from threading import Thread, Event

import uvicorn
import pystray
import qrcode
from qrcode.constants import ERROR_CORRECT_L
from PIL import Image, ImageTk
from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_static_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    return base_path / relative_path


STATIC_PATH = get_static_path("static")  # 直接指向static目录
UPLOAD_HTML_PATH = get_static_path("static/upload.html")


def get_local_ip() -> Union[None, str]:
    # 获取本机IP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 并不会真正建立连接
        sock.connect(("10.255.255.255", 1))
        ip = sock.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        sock.close()
    
    return ip


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


if __name__ == "__main__":
    ip = get_local_ip()
    port = 8000
    url = f"http://{ip}:{port}"
    
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
