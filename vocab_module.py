import json
import random
import os
from PyQt5 import QtCore, QtWidgets

class VocabManager:
    def __init__(self, main_win):
        # 1. 先存下主窗口引用
        self.win = main_win
        self.current_idx = 0
        self.time_left = 15
        
        # 2. 【核心修复】必须先找控件！一个都不能少
        self.v_input = self.win.findChild(QtWidgets.QLineEdit, "vocab_input")
        self.v_disp = self.win.findChild(QtWidgets.QTextEdit, "vocab_display")
        self.t_label = self.win.findChild(QtWidgets.QLabel, "timer_label")
        self.btn_confirm = self.win.findChild(QtWidgets.QPushButton, "btn_confirm")

        # 3. 初始化计时器
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)

        # 4. 绑定逻辑 (加个判断防止 UI 还没加载好)
        if self.btn_confirm:
            self.btn_confirm.clicked.connect(self.check_answer)
        if self.v_input:
            self.v_input.returnPressed.connect(self.check_answer)

        # 5. 加载词库
        self.load_vocabulary()
        
        # 6. 【最后】只有控件都找完了，才准执行显示逻辑
        if self.v_disp:
            self.show_next()
            self.timer.start(1000)

    def load_vocabulary(self):
        try:
            path = os.path.join(os.path.dirname(__file__), "vocabulary.json")
            with open(path, "r", encoding="utf-8") as f:
                self.vocabulary = json.load(f)
                random.shuffle(self.vocabulary)
        except:
            self.vocabulary = [{"word": "apple", "content": "苹果"}]

    def show_next(self, error_msg=""):
        # 安全检查：如果控件还没抓到，直接跳过不执行
        if not self.v_disp or not self.v_input:
            return

        curr = self.vocabulary[self.current_idx]
        
        hint_html = ""
        if error_msg:
            hint_html = f"<div style='font-size:26px; color:#e74c3c; margin-top:25px; font-weight:bold;'>正确答案: {error_msg.capitalize()}</div>"
        
        html = f"""
            <div style='text-align:center; padding-top:80px;'>
                <div style='font-size:45px; color:#2c3e50; font-weight:bold;'>{curr['content']}</div>
                {hint_html}
            </div>
        """
        self.v_disp.setHtml(html)

        if not error_msg:
            self.v_input.clear()
            self.v_input.setStyleSheet("font-size:24px; border:2px solid #bdc3c7;")
            self.v_input.setFocus()
            self.time_left = 15
            if self.t_label: self.t_label.setText(str(self.time_left))
            
            # 只有在单词页才启动
            if self.win.findChild(QtWidgets.QStackedWidget, "stackedWidget").currentIndex() == 0:
                self.timer.start(1000)

    def tick(self):
        self.time_left -= 1
        if self.t_label: self.t_label.setText(str(self.time_left))
        if self.time_left <= 0:
            self.timer.stop()
            target = self.vocabulary[self.current_idx]['word'].strip()
            self.show_next(error_msg=target)
            QtCore.QTimer.singleShot(2000, self.go_next)

    def check_answer(self):
        self.timer.stop()
        user_in = self.v_input.text().strip().lower()
        # 🚀 核心修改：如果用户啥也没填，点确定直接无视，不准看答案
        if not user_in:
            return
        target = self.vocabulary[self.current_idx]['word'].strip().lower()

        if user_in == target:
            self.v_input.setStyleSheet("font-size:24px; border:3px solid #27ae60; background-color:#d5f5e3;")
            QtCore.QTimer.singleShot(600, self.go_next)
        else:
            self.v_input.setStyleSheet("font-size:24px; border:3px solid #e74c3c; background-color:#fadbd8;")
            self.show_next(error_msg=target)
            QtCore.QTimer.singleShot(2000, self.go_next)

    def go_next(self):
        self.current_idx = (self.current_idx + 1) % len(self.vocabulary)
        self.show_next()