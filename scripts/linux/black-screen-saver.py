#!/usr/bin/env python3
# ==============================================================================
# black-screen-saver.py: OLED 纯黑屏省电与防烧屏挂机工具 (Wayland 原生)
# 特性:
# 1. 0x000000 纯黑全屏窗口，OLED 像素点硬件级断电熄灭，实现极致省电；
# 2. 原生监听屏幕触控手势 (TouchBegin/TouchEnd)、鼠标按键、键盘按键，轻触即醒；
# 3. 柔和居中提示在 2.5 秒后平滑淡出至全黑；
# 4. 单实例互斥锁，挂机结束后退出进程，常驻物理内存 0 开销。
# ==============================================================================

import sys
import os
import fcntl

# 单实例互斥锁
LOCK_FILE = "/run/user/1000/black-screen-saver.lock"
try:
    lock_fd = open(LOCK_FILE, "w")
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except (IOError, OSError):
    # 已有实例运行，静默退出
    sys.exit(0)

# 确保运行于 KDE Plasma Wayland 会话
os.environ["XDG_RUNTIME_DIR"] = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
os.environ["WAYLAND_DISPLAY"] = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
os.environ["QT_QPA_PLATFORM"] = "wayland"

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QFont

class BlackScreenSaver(QMainWindow):
    def __init__(self):
        super().__init__()
        # 无边框、全屏置顶
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #000000;")
        self.setCursor(Qt.BlankCursor)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        
        # 居中提示布局
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setAlignment(Qt.AlignCenter)
        
        # 启动时柔和淡入提示
        self.label = QLabel("🌙 OLED 纯黑屏挂机已开启\n\n轻触屏幕任意位置 或 按任意键 唤醒退出")
        self.label.setAlignment(Qt.AlignCenter)
        font = QFont("Sans Serif", 18, QFont.Bold)
        self.label.setFont(font)
        self.label.setStyleSheet("color: rgba(180, 180, 180, 220); background: transparent;")
        layout.addWidget(self.label)
        
        # 2.5 秒后文字平滑淡出，达到 100% 纯黑
        self.fade_step = 10
        self.fade_timer = None
        QTimer.singleShot(2500, self.start_fade_out)
        
        # 全屏展示
        self.showFullScreen()

    def start_fade_out(self):
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.do_fade)
        self.fade_timer.start(50)

    def do_fade(self):
        self.fade_step -= 1
        if self.fade_step <= 0:
            if self.fade_timer:
                self.fade_timer.stop()
            self.label.setText("")
            self.label.hide()
        else:
            alpha = int(220 * (self.fade_step / 10.0))
            self.label.setStyleSheet(f"color: rgba(180, 180, 180, {alpha}); background: transparent;")

    def mousePressEvent(self, event):
        self.close()
        QApplication.instance().quit()

    def keyPressEvent(self, event):
        self.close()
        QApplication.instance().quit()

    def event(self, event):
        # 监听触控屏触摸事件
        if event.type() in [QEvent.TouchBegin, QEvent.TouchEnd]:
            self.close()
            QApplication.instance().quit()
            return True
        return super().event(event)

def main():
    app = QApplication(sys.argv)
    saver = BlackScreenSaver()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
