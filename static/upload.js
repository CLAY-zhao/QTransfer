// 进度条
class DownloadProgress {
    constructor() {
        this.lastUpdate = 0;
        this.lastBytes = 0;
        this.speed = 0;
        this.totalSize = 0; // 示例总大小

        // 获取DOM元素
        this.elements = {
            container: document.querySelector('.download-progress'),
            filename: document.querySelector('.filename'),
            percentage: document.querySelector('.percentage'),
            progressBar: document.querySelector('.progress-bar'),
            indicator: document.querySelector('.progress-indicator'),
            transferred: document.querySelector('.transferred'),
            speed: document.querySelector('.speed'),
            remaining: document.querySelector('.remaining'),
            total: document.querySelector('.total'),
            filename: document.querySelector('.filename')
        };

        // 初始化显示
        this.elements.total.textContent = this.formatSize(this.totalSize);
    }

    setTotalSize(totalSize) {
        this.totalSize = totalSize
        this.elements.total.textContent = this.formatSize(this.totalSize)
    }

    setDownloadTitle(title) {
        this.elements.container.style.display = 'block'
        this.elements.filename.textContent = `正在下载: ${title}`
    }

    update(currentBytes) {
        const now = Date.now();
        const elapsed = (now - this.lastUpdate) / 1000; // 转换为秒

        // 计算速度（至少1秒更新一次）
        if (elapsed >= 1) {
            this.speed = (currentBytes - this.lastBytes) / elapsed;
            this.lastUpdate = now;
            this.lastBytes = currentBytes;
        }

        // 计算进度和剩余时间
        const percent = Math.min(100, (currentBytes / this.totalSize) * 100);
        const remaining = this.speed > 0
            ? this.formatTime((this.totalSize - currentBytes) / this.speed)
            : '--';

        // 更新UI
        this.elements.percentage.textContent = `${Math.floor(percent)}%`;
        this.elements.progressBar.style.width = `${percent}%`;
        this.elements.indicator.style.display = percent >= 100 ? 'none' : 'block';
        this.elements.transferred.textContent = this.formatSize(currentBytes);
        this.elements.speed.textContent = `${this.formatSize(this.speed)}/s`;
        this.elements.remaining.textContent = `剩余: ${remaining}`;

        // 添加激活状态类
        this.elements.container.classList.add('active-transfer');

        // 传输完成时移除动画
        if (percent >= 100) {
            this.elements.container.classList.remove('active-transfer');
            this.elements.progressBar.style.background = '#00d97e';
            this.elements.container.style.display = 'none'
        }
    }

    formatSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    formatTime(seconds) {
        if (seconds > 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
        if (seconds > 60) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
        return `${Math.floor(seconds)}s`;
    }
}

const progress = new DownloadProgress();

class FileReceiver {
    constructor() {
        this.chunks = [];
        this.fileSize = 0;
        this.receivedSize = 0;
        this.fileName = '';
    }

    async startTransfer(metadata) {
        this.fileName = metadata.filename;
        this.fileSize = metadata.filesize;
        progress.setTotalSize(this.fileSize)
        progress.setDownloadTitle(this.fileName)

        if (this.canUseFileSystemAPI()) {
            try {
                this.fileHandle = await window.showSaveFilePicker({
                    suggestedName: this.fileName
                });
                this.writer = await this.fileHandle.createWritable();
                return true;
            } catch (err) {
                console.warn("无法使用文件系统API:", err);
                return this.useFallback();
            }
        } else {
            return this.useFallback();
        }
    }

    canUseFileSystemAPI() {
        return 'showSaveFilePicker' in window && window.isSecureContext;
    }

    useFallback() {
        this.chunks = [];
        this.receivedSize = 0;
        return true;
    }

    async receiveChunk(chunk) {
        if (this.writer) {
            await this.writer.write(chunk);
        } else {
            this.chunks.push(chunk);
        }
        this.receivedSize += chunk.byteLength;

        progress.update(Math.min(this.receivedSize, progress.totalSize));
    }

    async completeTransfer() {
        if (this.writer) {
            await this.writer.close();
        } else {
            // 传统下载方式
            const blob = new Blob(this.chunks);
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = this.fileName;
            a.click();
            URL.revokeObjectURL(url);
        }
    }
}

const panelTitleEle = document.querySelector('.panel-title')

fetch('/record_ip')

// =============================== websocket ===============================

let fileWriter = null
let receivedFile = null
let filenames = null
const socket = new WebSocket(`ws://${window.location.host}/ws/connect`)
const fileReceiver = new FileReceiver()
socket.onmessage = async (event) => {
    if (event.data.startsWith !== undefined && event.data.startsWith("file_request:")) {
        const [_, filename, sender] = event.data.split(":")
        filenames = filename
        showFileRequestDialog(filename, sender)
    } else if (typeof event.data === "string") {
        const data = JSON.parse(event.data)
        if (data.type === "file_metadata") {
            await fileReceiver.startTransfer(data)
        } else if (data.type === "transfer_complete") {
            await fileReceiver.completeTransfer()
        } else if (data.type === "clipboard_metadata") {
            updateClipboardContent(data.text)
        }
    } else {
        await fileReceiver.receiveChunk(await event.data.arrayBuffer())
    }
}

function showFileRequestDialog(filename, sender) {
    if (confirm(`是否接收来自 ${sender} 的文件 ${filename}？`)) {
        socket.send(`file_response:${sender}:accept`)
    } else {
        socket.send(`file_response:${sender}:reject`)
    }
}

// =============================== websocket ===============================

async function getAndReportIP() {
    // 获取并上报当前设备IP
    try {
        // 尝试通过WebRTC获取内网IP
        const localIP = await new Promise((resolve) => {
            const pc = new RTCPeerConnection({ iceServers: [] });
            pc.createDataChannel("");
            pc.createOffer().then(offer => pc.setLocalDescription(offer));

            pc.onicecandidate = ice => {
                if (ice.candidate) {
                    const match = /([0-9]{1,3}(\.[0-9]{1,3}){3})/.exec(ice.candidate.candidate);
                    if (match) resolve(match[1]);
                }
            };

            setTimeout(() => resolve(null), 2000);
        });

        // 获取后端检测到的IP
        const res = await fetch('/detect_ip');
        const { ip: serverDetectedIP } = await res.json();

        // 优先使用WebRTC获取的IP，失败则使用后端检测的IP
        const finalIP = localIP || serverDetectedIP;
        document.getElementById('your-ip').textContent = finalIP || '未知';

        // 上报IP到服务器
        if (finalIP) {
            await fetch(`/record_ip?ip=${encodeURIComponent(finalIP)}`);
        }
    } catch (e) {
        console.warn("IP获取失败:", e);
    }
}

async function updateDeviceList() {
    // 获取并显示设备列表
    try {
        const res = await fetch('/get_ips');
        const { devices } = await res.json();
        panelTitleEle.innerText = `📱 当前连接设备（${devices.length}）`

        const deviceList = document.getElementById('device-list');
        if (devices && devices.length > 0) {
            deviceList.innerHTML = devices.map(ip => `
                        <div class="device-item">
                            <span class="device-icon">📱</span>
                            <span>${ip}</span>
                        </div>
                    `).join('');
        } else {
            deviceList.innerHTML = '<div class="device-item">暂无其他设备连接</div>';
        }
    } catch (e) {
        console.error("获取设备列表失败:", e);
    }
}

// 3. 初始化设备列表和IP显示
getAndReportIP();
updateDeviceList();

// 每5秒刷新一次设备列表
setInterval(updateDeviceList, 5000);

// 4. 文件上传功能（保持原有逻辑）
const fileInput = document.getElementById('file-input');
const selectedFiles = document.getElementById('selected-files');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress');
const status = document.getElementById('status');

fileInput.addEventListener('change', function (e) {
    if (this.files.length > 0) {
        let fileNames = [];
        for (let i = 0; i < this.files.length; i++) {
            fileNames.push(this.files[i].name);
        }
        selectedFiles.textContent = "已选择: " + fileNames.join(", ");
        uploadFiles(this.files);
    }
});

async function uploadFiles(files) {
    progressContainer.style.display = "block";
    status.textContent = "准备上传...";

    const formData = new FormData();
    formData.append('file', files[0]);

    try {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', function (e) {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = percent + '%';
                progressBar.textContent = percent + '%';
            }
        });

        xhr.addEventListener('load', function () {
            if (xhr.status === 200) {
                status.textContent = "上传成功!";
                setTimeout(() => {
                    progressContainer.style.display = "none";
                    selectedFiles.textContent = "";
                    fileInput.value = "";
                }, 2000);
            } else {
                status.textContent = "上传失败: " + xhr.responseText;
            }
        });

        xhr.open('POST', '/upload', true);
        xhr.send(formData);

        status.textContent = "上传中...";
    } catch (error) {
        status.textContent = "上传出错: " + error.message;
    }
}

function handlePageUnload() {
    // 离开页面时移除IP
    fetch('/remove_ip', {
        method: 'GET',
        keepalive: true
    }).catch((e) => { console.log(e) })
}

window.addEventListener('beforeunload', handlePageUnload)
window.addEventListener('pagehide', handlePageUnload)
window.addEventListener('unload', handlePageUnload)
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
        handlePageUnload()
    }
})

// 剪贴板内容显示处理
function updateClipboardContent(text) {
    const container = document.getElementById('clipboard-content');
    const timestamp = document.getElementById('clipboard-timestamp');

    if (!text) {
        container.innerHTML = '<div class="empty-state">暂无同步内容</div>';
        timestamp.textContent = '';
        return;
    }

    // 格式化时间
    const now = new Date();
    timestamp.textContent = now.toLocaleTimeString();

    // 处理文本显示（自动换行+省略）
    const maxLines = 5;
    const lineHeight = 20; // 根据实际CSS调整
    const maxHeight = maxLines * lineHeight;

    container.innerHTML = text;
    container.classList.toggle('truncated', container.scrollHeight > maxHeight);
    container.style.maxHeight = `${maxHeight}px`;
}

function copyToClipboard(text) {
    // 方法1：使用现代Clipboard API（首选）
    if (navigator.clipboard) {
        return navigator.clipboard.writeText(text).then(() => {
            return true;
        }).catch(err => {
            console.error('Clipboard API failed:', err);
            return false;
        });
    }

    // 方法2：document.execCommand备用方案
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';  // 避免滚动到底部
    textarea.style.left = '-9999px';
    textarea.style.top = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();

    try {
        const successful = document.execCommand('copy');
        document.body.removeChild(textarea);
        return successful ? Promise.resolve() : Promise.reject();
    } catch (err) {
        document.body.removeChild(textarea);
        return Promise.reject(err);
    }
}

// 更新复制按钮事件处理
document.getElementById('copy-clipboard-btn').addEventListener('click', async function () {
    const btn = this;
    const content = document.getElementById('clipboard-content').innerText;

    try {
        await copyToClipboard(content);

        // 视觉反馈
        btn.innerHTML = '<span class="btn-icon">✓</span> 已复制';
        btn.classList.add('copied');

        // 3秒后恢复原状
        setTimeout(() => {
            btn.innerHTML = '<span class="btn-icon">⎘</span> 复制';
            btn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        console.error('复制失败:', err);
        btn.innerHTML = '<span class="btn-icon">✗</span> 复制失败';
        setTimeout(() => {
            btn.innerHTML = '<span class="btn-icon">⎘</span> 复制';
        }, 2000);
    }
});