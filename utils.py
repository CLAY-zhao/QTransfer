import sys
import socket
from pathlib import Path
from typing import Union


def get_static_path(relative_path) -> Path:
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    return base_path / relative_path


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
