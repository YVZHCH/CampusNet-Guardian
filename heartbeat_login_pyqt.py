import requests
import os
import socket
import time
import threading
import pystray
from PIL import Image, ImageDraw
from PyQt5.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox,
                             QWidget, QGridLayout)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QEventLoop, QPoint
from PyQt5.QtGui import QFont
import sys
import json

# ===================== 基础缩放函数 =====================
def get_scale():
    screen = QApplication.primaryScreen()
    size = screen.size()
    base_width = 1920
    base_height = 1080
    scale_w = size.width() / base_width
    scale_h = size.height() / base_height
    return (scale_w + scale_h) / 2

# ===================== 统一样式表 =====================
def get_unified_style(scale=1.0):
    font_size = int(13 * scale)
    button_radius = int(6 * scale)
    return f"""
        QWidget {{
            background-color: #2E2E2E;
            color: #FFFFFF;
            font-family: "Microsoft YaHei";
            font-size: {font_size}px;
            border-radius: {button_radius}px;
        }}
        QLineEdit {{
            background-color: #3C3C3C;
            border: 1px solid #5A5A5A;
            padding: {int(6*scale)}px;
            border-radius: {int(4*scale)}px;
        }}
        QPushButton {{
            background-color: #0078D7;
            color: white;
            padding: {int(6*scale)}px {int(10*scale)}px;
            border: none;
            border-radius: {int(5*scale)}px;
        }}
        QPushButton:hover {{
            background-color: #1493FF;
        }}
        QPushButton:pressed {{
            background-color: #005EA6;
        }}
        QLabel {{
            color: white;
        }}
        QMessageBox {{
            background-color: #2E2E2E;
            color: white;
            font-size: {font_size}px;
        }}
    """

# ===================== 自绘Toast通知 =====================

class Toast(QWidget):
    active_toasts = []  # 当前活跃 toast 列表

    def __init__(self, title, message, duration=3000):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        scale = get_scale()
        self.duration = duration

        # === 外层主布局（透明） ===
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # === 背景容器 ===
        bg_widget = QWidget()
        # 让 bg_widget 使用自己的样式背景（避免全局 QWidget 样式影响）
        bg_widget.setAttribute(Qt.WA_StyledBackground, True)
        bg_layout = QVBoxLayout(bg_widget)
        bg_layout.setContentsMargins(int(20*scale), int(15*scale), int(20*scale), int(15*scale))
        bg_layout.setSpacing(int(8*scale))

        title_label = QLabel(f"<b>{title}</b>")
        # 强制标签背景透明并去掉多余边距
        title_label.setStyleSheet(f"background: transparent; color: white; font-size:{int(15*scale)}px;")
        title_label.setMargin(0)
        title_label.setContentsMargins(0, 0, 0, 0)
        title_label.setWordWrap(False)

        msg = QLabel(message)
        msg.setWordWrap(True)
        # 关键：将消息行设为透明背景，避免每行独立背景
        msg.setStyleSheet(f"background: transparent; color: white; font-size:{int(13*scale)}px;")
        msg.setMargin(0)
        msg.setContentsMargins(0, 0, 0, 0)

        bg_layout.addWidget(title_label)
        bg_layout.addWidget(msg)

        bg_widget.setStyleSheet("background-color:rgba(40,40,40,220);border-radius:12px;")
        outer_layout.addWidget(bg_widget)

        # === 定位到右下角（后续调整） ===
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.resize(bg_widget.sizeHint())
        self.base_x = screen.right() - self.width() - int(40*scale)
        self.base_y = screen.bottom() - self.height() - int(60*scale)

        # === 更新其他toast位置 ===
        self._adjust_existing_toasts(scale)

        # 初始位置：在屏幕右侧外
        self.move(screen.right(), self.base_y)

        # === 淡入滑入动画 ===
        self.setWindowOpacity(0)
        self.show()
        self.raise_()

        # 滑入动画（右 → 左）
        self.slide_anim = QPropertyAnimation(self, b"pos", self)
        self.slide_anim.setDuration(400)
        self.slide_anim.setStartValue(self.pos())
        self.slide_anim.setEndValue(QPoint(self.base_x, self.base_y))
        self.slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 淡入动画
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.fade_anim.start()
        self.slide_anim.start()

        # 自动关闭计时
        QTimer.singleShot(self.duration, self.close_with_fade)

        Toast.active_toasts.append(self)

    def _adjust_existing_toasts(self, scale):
        """将已有toast整体上移，避免重叠"""
        offset = int((self.height() + 15*scale))
        for toast in reversed(Toast.active_toasts):
            if toast.isVisible():
                new_y = toast.y() - offset
                anim = QPropertyAnimation(toast, b"pos", toast)
                anim.setDuration(300)
                anim.setStartValue(toast.pos())
                anim.setEndValue(QPoint(toast.x(), new_y))
                anim.setEasingCurve(QEasingCurve.OutCubic)
                anim.start()
                toast.anim_move = anim  # 防止动画对象被回收

    def close_with_fade(self):
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(400)
        fade.setStartValue(1)
        fade.setEndValue(0)
        fade.finished.connect(self._remove_self)
        fade.start()
        self.fade_out = fade

    def _remove_self(self):
        """关闭并从活跃列表中移除"""
        if self in Toast.active_toasts:
            Toast.active_toasts.remove(self)
        self.close()



# =================================================
running = True
username = ''
password = ''
login_IP = ''
check_interval = 30
max_attempts = 9999
current_status = "监控中"
countdown_seconds = check_interval
CONFIG_FILE = "config.json"
app = None

class UiSignal(QObject):
    show_param_dialog = pyqtSignal()
    show_about_dialog = pyqtSignal()

class ToastSignal(QObject):
    show_toast_signal = pyqtSignal(str, str)

toast_signal = None

def show_toast(title, message):
    global toast_signal
    if toast_signal is None:
        print(f"[Toast未初始化] {title}: {message}")
        return
    toast_signal.show_toast_signal.emit(title, message)
    QApplication.processEvents()

# ===================== 参数配置窗口 =====================
class ParameterDialog(QDialog):
    def __init__(self, parent=None, current_username=None, current_password=None, current_login_ip=None):
        super().__init__(parent)
        scale = get_scale()
        self.setWindowTitle("修改登录信息")
        self.resize(int(500*scale), int(250*scale))
        self.setStyleSheet(get_unified_style(scale))
        font = QFont("Microsoft YaHei", int(10*scale))
        self.setFont(font)
        self.current_username = current_username
        self.current_password = current_password
        self.current_login_ip = current_login_ip
        self.result_username = None
        self.result_password = None
        self.result_login_ip = None
        self.init_ui(scale)
        self.center_window()

    def center_window(self):
        frame_geometry = self.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def init_ui(self, scale):
        main_layout = QVBoxLayout()
        title_label = QLabel("请修改登录信息:")
        title_label.setStyleSheet(f"font-size: {int(16*scale)}px; font-weight: bold; margin-bottom: {int(10*scale)}px;")
        main_layout.addWidget(title_label)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(int(10*scale))
        username_label = QLabel("用户名:")
        self.username_input = QLineEdit(self.current_username)
        password_label = QLabel("密码:")
        self.password_input = QLineEdit(self.current_password)
        self.password_input.setEchoMode(QLineEdit.Password)
        login_ip_label = QLabel("登录服务器IP:")
        self.login_ip_input = QLineEdit(self.current_login_ip)
        grid_layout.addWidget(username_label, 0, 0)
        grid_layout.addWidget(self.username_input, 0, 1)
        grid_layout.addWidget(password_label, 1, 0)
        grid_layout.addWidget(self.password_input, 1, 1)
        grid_layout.addWidget(login_ip_label, 2, 0)
        grid_layout.addWidget(self.login_ip_input, 2, 1)
        main_layout.addLayout(grid_layout)

        ok_btn = QPushButton("确认")
        ok_btn.clicked.connect(self.on_confirm)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def on_confirm(self):
        self.result_username = self.username_input.text()
        self.result_password = self.password_input.text()
        self.result_login_ip = self.login_ip_input.text()
        self.accept()

    def get_parameters(self):
        return self.result_username, self.result_password, self.result_login_ip

# ===================== 核心逻辑 =====================
def encrypt_data(data):
    encrypted = ""
    for char in data:
        ascii_val = ord(char)
        xor_result = ascii_val ^ 22
        hex_str = format(xor_result, '02X')
        encrypted += hex_str
    return encrypted

def get_local_ipv4():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return ""

def get_local_ipv6():
    try:
        for addr_info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET6):
            ipv6 = addr_info[4][0]
            if not ipv6.startswith('fe80::') and not ipv6 == '::1':
                return ipv6
        return ""
    except Exception:
        return ""

def generate_sign_parameter():
    global username, password, login_IP
    if not username or not password:
        show_toast("错误", "登录信息不完整")
        return None
    ipv4 = get_local_ipv4()
    ipv6 = get_local_ipv6()
    modified_username = f',0,{username}'
    encrypted_username = encrypt_data(modified_username)
    encrypted_password = encrypt_data(password)
    encrypted_ipv4 = encrypt_data(ipv4)
    encrypted_ipv6 = encrypt_data(ipv6) if ipv6 else ""
    url = (f"https://{login_IP}:802/eportal/portal/login?callback=726427262623&login_method=27"
           f"&user_account={encrypted_username}&user_password={encrypted_password}"
           f"&wlan_user_ip={encrypted_ipv4}&wlan_user_ipv6={encrypted_ipv6}"
           f"&wlan_user_mac=262626262626262626262626&wlan_vlan_id=26&wlan_ac_ip="
           f"&wlan_ac_name=&authex_enable=&jsVersion=2238243824&login_ip_type=26&terminal_type=27"
           f"&lang=6c7e3b7578&program_index=79225954737327212323222f212e2723"
           f"&page_index=755e577b7c4e27212323222f212e2320&encrypt=1&v=692&lang=zh")
    return url

def load_config():
    global username, password, login_IP
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                username = config.get('username', username)
                password = config.get('password', password)
                login_IP = config.get('login_IP', login_IP)
        except Exception as e:
            show_toast("配置错误", f"加载配置文件失败: {str(e)}")

def save_config():
    global username, password, login_IP
    try:
        config = {'username': username, 'password': password, 'login_IP': login_IP}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        show_toast("配置错误", f"保存配置文件失败: {str(e)}")

def show_about_dialog():
    scale = get_scale()
    msg_box = QMessageBox()
    msg_box.setWindowTitle("关于校园网助手")
    msg_box.setStyleSheet(get_unified_style(scale))
    msg_box.setTextFormat(Qt.RichText)
    msg_box.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
    msg_box.setText(
        """
        <html>
        <body>
        <p><b>校园网助手 v2.1.3</b></p>
        <p>自动监控并维护校园网连接</p>
        <p>Powered by 羽中
        <a href='https://space.bilibili.com/353357823'>↗</a> & 猪肉四喜丸子
        <a href='https://space.bilibili.com/363076511'>↗</a>
        </p>
        <p>© 2025 校园网助手</p>
        </body>
        </html>
        """
    )
    msg_box.exec_()

def is_connected():
    test_urls = ["https://www.baidu.com", "https://www.aliyun.com", "https://www.bing.com", "https://www.google.com"]
    timeout = 1
    for url in test_urls:
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
            if 200 <= response.status_code < 300:
                return True
        except requests.exceptions.RequestException:
            continue
    return False

def login_campus_network(result_return):
    sign_parameter = generate_sign_parameter()
    if not sign_parameter:
        return False

    try:
        r = requests.get(sign_parameter, timeout=5)
        req = r.text
        content_ok = result_return in req
        net_ok = is_connected()
        if content_ok or net_ok:
            if content_ok and not net_ok:
                show_toast("校园网状态", "登录成功，但联网检测未通过")
            elif not content_ok and net_ok:
                show_toast("校园网状态", "联网正常，但登录返回检测未通过")
            else:
                show_toast("校园网状态", "登录成功")
            return True
        else:
            show_toast("校园网状态", "登录失败")
            return False
    except Exception as e:
        show_toast("校园网状态", f"登录错误: {str(e)}")
        return False

def create_tray_icon(signal):
    width, height = 64, 64
    image = Image.new('RGB', (width, height), "blue")
    dc = ImageDraw.Draw(image)
    dc.ellipse((16, 16, 48, 48), fill="white")
    dc.ellipse((24, 24, 40, 40), fill="blue")

    def on_quit(icon, item):
        global running
        running = False
        icon.stop()
        QApplication.quit()
        os._exit(0)

    def on_modify_parameter(icon, item):
        signal.show_param_dialog.emit()

    def on_about(icon, item):
        signal.show_about_dialog.emit()

    menu = pystray.Menu(
        pystray.MenuItem("修改登录信息", on_modify_parameter),
        pystray.MenuItem("关于", on_about),
        pystray.MenuItem("退出", on_quit)
    )

    icon = pystray.Icon("校园网助手", image, "校园网助手", menu)

    def update_tooltip(icon):
        global current_status, countdown_seconds, running
        while running:
            if "网络已连接" in current_status:
                icon.title = f"校园网助手 - {current_status}，下次检测: {countdown_seconds}秒"
            else:
                icon.title = f"校园网助手 - {current_status}"
            time.sleep(1)

    threading.Thread(target=update_tooltip, args=(icon,), daemon=True).start()
    return icon

def update_countdown():
    global countdown_seconds, running, check_interval
    while running:
        if "网络已连接" in current_status:
            countdown_seconds -= 1
            if countdown_seconds <= 0:
                countdown_seconds = check_interval
        time.sleep(1)

def network_monitor():
    global current_status, running, countdown_seconds, check_interval, login_IP
    not_sign_in_title = '上网登录页'
    result_return = '成功'
    signed_in_title = '用户信息页'
    attempt_count = 0
    show_toast("校园网助手", "开始网络监控")
    countdown_thread = threading.Thread(target=update_countdown, daemon=True)
    countdown_thread.start()

    while running:
        if is_connected():
            current_status = "网络已连接"
            time.sleep(check_interval)
            countdown_seconds = check_interval
            continue
        else:
            current_status = "网络断开，尝试重连"
            while attempt_count < max_attempts and running:
                attempt_count += 1
                show_toast("校园网状态", f"未检测到网络连接，尝试登录 ({attempt_count}/{max_attempts})")
                if login_campus_network(result_return):
                    time.sleep(5)
                    if is_connected():
                        show_toast("校园网状态", "登录后网络已连接")
                        attempt_count = 0
                        current_status = "网络已连接"
                        countdown_seconds = check_interval
                        break
            if attempt_count >= max_attempts and not is_connected() and running:
                show_toast("校园网状态", f"达到最大尝试次数({max_attempts})，网络仍未连接")
                current_status = f"达到最大尝试次数({max_attempts})"
                attempt_count = 0
        time.sleep(1)

def main():
    global app, username, password, login_IP, toast_signal
    load_config()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    ui_signal = UiSignal()
    toast_signal = ToastSignal()

    # 绑定信号
    toast_signal.show_toast_signal.connect(lambda t, m: Toast(t, m).show())

    if not os.path.exists(CONFIG_FILE):
        show_toast("首次启动", "未检测到配置文件，请填写登录信息")
        dialog = ParameterDialog(current_username=username, current_password=password, current_login_ip=login_IP)
        if dialog.exec_():
            username, password, login_IP = dialog.get_parameters()
            save_config()
            show_toast("设置保存", "配置文件已创建")
        else:
            show_toast("提示", "未填写登录信息，程序退出")
            loop = QEventLoop()
            QTimer.singleShot(5000, loop.quit)
            loop.exec_()
            sys.exit(0)
    else:
        load_config()

    def handle_param_dialog():
        global username, password, login_IP
        dialog = ParameterDialog(current_username=username, current_password=password, current_login_ip=login_IP)
        if dialog.exec_():
            new_username, new_password, new_login_ip = dialog.get_parameters()
            if new_username:
                username = new_username
            if new_password:
                password = new_password
            if new_login_ip:
                login_IP = new_login_ip
            save_config()
            show_toast("设置修改", "登录信息已更新")

    def handle_about_dialog():
        show_about_dialog()

    ui_signal.show_param_dialog.connect(handle_param_dialog)
    ui_signal.show_about_dialog.connect(handle_about_dialog)

    monitor_thread = threading.Thread(target=network_monitor, daemon=True)
    monitor_thread.start()

    def run_tray():
        icon = create_tray_icon(ui_signal)
        icon.run()

    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

    app.exec_()
    monitor_thread.join()
    tray_thread.join()
    os._exit(0)

if __name__ == '__main__':
    main()
