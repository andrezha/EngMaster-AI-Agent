import sys
import os
import json
import random
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow

class EnglishAgent(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. 加载 UI 和词库
        root = os.path.dirname(os.path.abspath(__file__))
        uic.loadUi(os.path.join(root, "resources", "main_window.ui"), self)
        
        self.vocabulary = []
        try:
            with open(os.path.join(root, "vocabulary.json"), "r", encoding="utf-8") as f:
                self.vocabulary = json.load(f)
                random.shuffle(self.vocabulary)
        except:
            self.vocabulary = [{"word": "error", "content": "词库加载失败"}]

        # 2. 控件绑定 (增加对第三个按钮的绑定)
        self.stack = self.findChild(QtWidgets.QStackedWidget, "stackedWidget")
        self.btn_v = self.findChild(QtWidgets.QPushButton, "btn_nav_vocab")
        self.btn_s = self.findChild(QtWidgets.QPushButton, "btn_nav_scan")
        self.btn_t = self.findChild(QtWidgets.QPushButton, "btn_nav_test") # 第三个按钮
        
        self.v_disp = self.findChild(QtWidgets.QTextEdit, "vocab_display")
        self.v_input = self.findChild(QtWidgets.QLineEdit, "vocab_input")
        self.t_label = self.findChild(QtWidgets.QLabel, "timer_label")
        
        # 3. 导航逻辑：让左边三个按钮都动起来
        if self.stack:
            if self.btn_v: self.btn_v.clicked.connect(lambda: self.stack.setCurrentIndex(0))
            if self.btn_s: self.btn_s.clicked.connect(lambda: self.stack.setCurrentIndex(1))
            if self.btn_t: self.btn_t.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        # 4. 词汇验证逻辑
        self.current_idx = 0
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)
        
        if self.v_input:
            self.v_input.textChanged.connect(self.check_answer)

        self.show_next()

    def update_ui_display(self, error_msg=""):
        """垂直居中渲染 + 错误红字提示"""
        curr = self.vocabulary[self.current_idx]
        error_html = ""
        if error_msg:
            error_html = f"<div style='font-size:20px; color:#e74c3c; margin-top:30px; font-weight:bold;'>⚠️ 错误！正确是: {error_msg}</div>"
        
        display_html = f"""
            <div style='text-align:center; padding-top:120px; font-family: "Microsoft YaHei";'>
                <div style='font-size:34px; color:#2c3e50; font-weight:bold;'>{curr['content']}</div>
                {error_html}
            </div>
        """
        if self.v_disp: self.v_disp.setHtml(display_html)

    def show_next(self):
        """刷新下一题"""
        if self.current_idx < len(self.vocabulary):
            self.update_ui_display()
            if self.v_input:
                self.v_input.clear()
                self.v_input.setStyleSheet("font-size:24px; border:3px solid #bdc3c7; border-radius:10px; padding:8px;")
                self.v_input.setFocus()
            self.time_left = 15
            if self.t_label: self.t_label.setText(str(self.time_left))
            self.timer.start(1000)

    def check_answer(self, text):
        """对错判定逻辑"""
        if not text: 
            self.update_ui_display()
            return
        target = self.vocabulary[self.current_idx]['word'].strip().lower()
        user_input = text.strip().lower()

        if user_input == target:
            self.timer.stop()
            self.v_input.setStyleSheet("font-size:24px; border:3px solid #27ae60; background-color:#d5f5e3;")
            QtCore.QTimer.singleShot(400, self.go_to_next)
        elif not target.startswith(user_input):
            self.v_input.setStyleSheet("font-size:24px; border:3px solid #e74c3c; background-color:#fadbd8;")
            self.update_ui_display(error_msg=target)
        else:
            self.v_input.setStyleSheet("font-size:24px; border:3px solid #3498db; background-color:white;")
            self.update_ui_display()

    def go_to_next(self):
        self.current_idx = (self.current_idx + 1) % len(self.vocabulary)
        self.show_next()

    def tick(self):
        self.time_left -= 1
        if self.t_label: self.t_label.setText(str(self.time_left))
        if self.time_left <= 0:
            self.timer.stop()
            self.update_ui_display(error_msg=self.vocabulary[self.current_idx]['word'])
            QtCore.QTimer.singleShot(1500, self.go_to_next)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = EnglishAgent()
    window.show()
    sys.exit(app.exec())