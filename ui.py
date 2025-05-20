import os

import requests
import qrcode
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import ImageTk

from config import connected_devices


def center_window(window, width: int, height: int) -> None:
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    window.geometry(f"{width}x{height}+{x}+{y}")


def show_upload_dialog(parent=None, message="文件发送中..."):
    """显示上传状态对话框"""
    dialog = tk.Toplevel(parent)
    dialog.title("文件传输")
    dialog.resizable(False, False)
    
    # 内容区域
    frame = ttk.Frame(dialog, padding=10)
    frame.pack()
    
    ttk.Label(frame, text=message).grid(row=0, column=0, pady=5)
    
    # 进度条
    progress = ttk.Progressbar(frame, mode='indeterminate')
    progress.grid(row=1, column=0, pady=5)
    progress.start()
    
    # 取消按钮
    btn = ttk.Button(frame, text="取消", command=dialog.destroy)
    btn.grid(row=2, column=0, pady=(5,0))
    return dialog


def show_qrcode(url):
    root = tk.Tk()
    root.title("📱 设备连接管理器")
    root.configure(bg="#f5f7fa")  # 浅灰色背景
    
    # 窗口设置
    center_window(root, 350, 550)
    root.resizable(False, False)
    
    # 主容器
    main_frame = tk.Frame(root, bg="#f5f7fa", padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 二维码卡片
    qr_card = tk.Frame(main_frame, 
                      bg="white", 
                      padx=15, 
                      pady=15,
                      relief=tk.FLAT,
                      highlightbackground="#e0e6ed",
                      highlightthickness=1)
    qr_card.pack(fill=tk.X, pady=(0, 20))
    
    # 生成二维码
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#3a7bd5", back_color="white")  # 蓝色二维码
    tk_image = ImageTk.PhotoImage(img)
    
    tk.Label(qr_card, 
            image=tk_image, 
            bg="white").pack()
    
    tk.Label(qr_card, 
            text="扫描二维码连接设备", 
            font=("Arial", 10), 
            fg="#666",
            bg="white").pack(pady=(10,0))
    
    # 设备列表标题
    header = tk.Frame(main_frame, bg="#f5f7fa")
    header.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(header, 
            text="已连接设备 ({}台)".format(len(connected_devices)), 
            font=("Arial", 11, "bold"), 
            fg="#333",
            bg="#f5f7fa").pack(side=tk.LEFT)
    
    # 设备列表容器
    device_container = tk.Canvas(main_frame, 
                               bg="#f5f7fa",
                               highlightthickness=0)
    scrollbar = tk.Scrollbar(main_frame, 
                           orient="vertical", 
                           command=device_container.yview)
    device_frame = tk.Frame(device_container, bg="#f5f7fa")
    
    device_container.create_window((0, 0), 
                                 window=device_frame, 
                                 anchor="nw")
    device_container.configure(yscrollcommand=scrollbar.set)
    
    def on_frame_configure(event):
        device_container.configure(scrollregion=device_container.bbox("all"))
    
    device_frame.bind("<Configure>", on_frame_configure)
    
    device_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 创建设备卡片
    def create_device_card(ip):
        card = tk.Frame(device_frame,
                       bg="white",
                       padx=15,
                       pady=12,
                       relief=tk.FLAT,
                       highlightbackground="#e0e6ed",
                       highlightthickness=1)
        
        # 设备图标和IP
        icon_label = tk.Label(card, 
                            text="📱", 
                            font=("Arial", 14),
                            bg="white")
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ip_label = tk.Label(card,
                          text=f"{ip}  ",
                          font=("Arial", 10),
                          fg="#333",
                          bg="white",
                          anchor="w")
        ip_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 操作按钮容器
        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(side=tk.RIGHT)
        
        send_btn = tk.Button(btn_frame,
                       text="发送文件",
                       command=lambda: send_to_device(ip),
                       font=("Arial", 9),
                       bg="#4CAF50",
                       fg="white",
                       activebackground="#45a049",
                       bd=0,
                       padx=12,
                       cursor="hand2")  # 鼠标指针变为手型
        send_btn.pack(side=tk.LEFT, padx=(0, 5))

        def send_to_device(ip):
            # 弹出文件选择框
            filepath = filedialog.askopenfilename(
                title=f"选择要发送到 {ip} 的文件",
                filetypes=[
                    ("所有文件", "*.*"),
                    ("文本文件", "*.txt"),
                    ("图片文件", "*.jpg *.png"),
                    ("视频文件", "*.mp4 *.avi")
                ]
            )
            
            if not filepath:  # 用户取消选择
                return

            filename = os.path.basename(filepath)
            response = requests.post(
                f"http://localhost:8000/send_file",
                json={"client_ip": ip, "filename": filename, "filepath": filepath}
            )           
            if response.json().get("status") == "request_sent":
                dialog = show_upload_dialog(message="等待对方接受...")
                root.after(3000, lambda: dialog.destroy())
        
        # 断开按钮
        disconnect_btn = tk.Button(btn_frame,
                                 text="断开",
                                 command=lambda: disconnect_device(ip),
                                 font=("Arial", 9),
                                 bg="#f44336",
                                 fg="white",
                                 activebackground="#d32f2f",
                                 bd=0,
                                 padx=12,
                                 pady=2)
        disconnect_btn.pack(side=tk.LEFT)
        
        card.pack(fill=tk.X, pady=(0, 8))
        return card
    
    def disconnect_device(ip):
        pass
    
    # 更新设备列表函数
    def update_device_list():
        # 清空现有设备
        for widget in device_frame.winfo_children():
            widget.destroy()
        
        # 添加当前所有设备
        for ip in connected_devices:
            create_device_card(ip)
        
        # 更新标题数量
        header.children['!label'].config(
            text="已连接设备 ({}台)".format(len(connected_devices)))
        
        # 2秒后刷新
        root.after(2000, update_device_list)
    
    # 初始加载
    update_device_list()
    
    # 保持引用
    root.tk_image = tk_image
    root.mainloop()