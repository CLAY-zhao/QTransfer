import os
import sys
import ctypes
from threading import Thread, Event
from typing import Dict

import uvicorn
import pystray
from PIL import Image
from fastapi import FastAPI, UploadFile, Request, WebSocket, WebSocketDisconnect, Body
from fastapi.staticfiles import StaticFiles

from ui import show_qrcode
from utils import get_static_path, get_local_ip
from config import connected_devices

app = FastAPI()

UPLOAD_DIR = "uploads"
STATIC_PATH = get_static_path("static")  # 直接指向static目录

os.makedirs(UPLOAD_DIR, exist_ok=True)

ip = get_local_ip()
port = 8000
url = f"http://{ip}:{port}"


class ConnectionManager(object):

    CHUNK_SIZE: int = 1024 * 64

    def __init__(self):
        self.active_connections: Dict[str: WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_ip: str):
        await websocket.accept()
        self.active_connections[client_ip] = websocket

    def disconnect(self, client_ip: str):
        self.active_connections.pop(client_ip)

    async def send_personal_message(self, message: str, client_ip: str, filepath: str):
        if client_ip in self.active_connections:
            websocket = self.active_connections[client_ip]
            websocket.filepath = filepath
            await websocket.send_text(message)

    async def transfer_file(self, client_ip: str):
        websocket: WebSocket = self.active_connections[client_ip]

        await websocket.send_json({
            "type": "file_metadata",
            "filename": os.path.basename(websocket.filepath),
            "filesize": os.path.getsize(websocket.filepath)
        })

        with open(websocket.filepath, "rb") as file:
            while True:
                chunk = file.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                print(chunk)
                await websocket.send_bytes(chunk)

        # 发送完成标记
        await websocket.send_json({
            "type": "transfer_complete",
        })

        return {"status": "success"}


manager: ConnectionManager = ConnectionManager()


@app.websocket("/ws/connect")
async def websocket_endpoint(websocket: WebSocket):
    client_ip = (
        websocket.headers.get("X-Real-IP") or
        websocket.headers.get("X-Forwarded-For", "").split(",")[0] or
        websocket.client.host
    )
    await manager.connect(websocket, client_ip)
    try:
        while True:
            data = await websocket.receive_text()
            file_response, _, status = data.split(":")
            if file_response == "file_response" and status == "accept":
                await manager.transfer_file(client_ip)
    except WebSocketDisconnect:
        manager.disconnect(client_ip)


@app.post("/send_file")
async def send_file_request(
    client_ip: str = Body(title="连接设备IP", embed=True),
    filename: str = Body(title="文件名", embed=True),
    filepath: str = Body(title="发送文件路径", embed=True)
):
    if client_ip in manager.active_connections:
        await manager.send_personal_message(
            f"file_request:{filename}:{get_local_ip()}",
            client_ip,
            filepath
        )
        return {"status": "request_sent"}
    else:
        return {"status": "device_offline"}


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
