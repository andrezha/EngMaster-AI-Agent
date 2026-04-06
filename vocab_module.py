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
        
        # 7. 🎯 统一底部按钮样式（56px 高度，大圆角，全宽布局）
        self._style_action_buttons()

    def _style_action_buttons(self):
        """
        统一按钮样式规范：
        - 所有按钮高度固定为 56px
        - 大圆角（16px）和实色背景
        - 全宽布局，方便单手操作
        - 输入框与按钮高度对齐
        """
        # 闯关模式输入框 - 56px 高度，大圆角，与按钮对齐
        if self.v_input:
            self.v_input.setFixedHeight(56)
            self.v_input.setStyleSheet("""
                QLineEdit {
                    background-color: #f8f9fa;
                    border: 2px solid #dee2e6;
                    border-radius: 16px;
                    font-size: 24px;
                    padding: 0px 20px;
                    color: #2c3e50;
                }
                QLineEdit:focus {
                    border: 2px solid #27ae60;
                    background-color: #ffffff;
                }
            """)
        
        # 闯关模式确认按钮 - 醒目绿色，全宽大按钮
        if self.btn_confirm:
            self.btn_confirm.setFixedHeight(56)
            self.btn_confirm.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
                QPushButton:pressed {
                    background-color: #1e8449;
                }
            """)

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
            hint_html = f"""
                <div style='text-align:center; margin-top:20px;'>
                    <div style='font-size:22px; color:#e74c3c; font-weight:bold; 
                        background:#fadbd8; padding:12px 24px; border-radius:12px; display:inline-block;'>
                        ✅ 正确答案: {error_msg.capitalize()}
                    </div>
                </div>
            """
        
        # 🎯 题目垂直居中显示（使用 flexbox 实现垂直居中）
        html = f"""
            <div style='display:flex; flex-direction:column; justify-content:center; 
                align-items:center; height:100%; min-height:400px; padding:20px;'>
                <div style='text-align:center;'>
                    <div style='font-size:18px; color:#7f8c8d; font-weight:bold; 
                        margin-bottom:15px;'>⚡ 第 {self.current_idx + 1} 关 ⚡</div>
                    <div style='font-size:48px; color:#2c3e50; font-weight:bold; 
                        line-height:1.4; margin:20px 0;'>{curr['content']}</div>
                    {hint_html}
                </div>
            </div>
        """
        self.v_disp.setHtml(html)

        if not error_msg:
            self.v_input.clear()
            self.v_input.setFocus()
            self.time_left = 15
            if self.t_label:
                # 🎯 倒计时样式：透明背景 + 深红色 + 加粗
                self.t_label.setText(str(self.time_left))
                self.t_label.setStyleSheet("""
                    QLabel {
                        color: #D32F2F;
                        font-size: 32px;
                        font-weight: bold;
                        padding: 5px 10px;
                        background: transparent;
                    }
                """)
            
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