import json
import random
import os
from PySide6 import QtCore, QtWidgets, QtGui

class VocabManager:
    """
    词汇学习模块管理器，负责加载词汇、显示单词、检查用户输入和计时。
    """
    def __init__(self, main_win):
        self.win = main_win
        self.current_idx = 0
        self.time_left = 15
        
        # 查找控件
        self.v_input = self.win.findChild(QtWidgets.QLineEdit, "vocab_input")
        self.v_disp = self.win.findChild(QtWidgets.QTextEdit, "vocab_display")
        self.t_label = self.win.findChild(QtWidgets.QLabel, "timer_label")
        self.btn_confirm = self.win.findChild(QtWidgets.QPushButton, "btn_confirm")
        
        # 获取 page_vocab 的布局
        page_vocab = self.win.findChild(QtWidgets.QWidget, "page_vocab")
        self.main_layout = page_vocab.layout() if page_vocab else None

        # 初始化计时器
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.tick)

        # 绑定逻辑
        if self.btn_confirm:
            self.btn_confirm.clicked.connect(self.check_answer)
        if self.v_input:
            self.v_input.returnPressed.connect(self.check_answer)

        # 加载词库
        self.load_vocabulary()
        
        # 执行显示逻辑
        if self.v_disp:
            self.show_next()
            self.timer.start(1000)
        
        # 重构布局
        self._rebuild_layout()
        
        # 统一样式
        self._style_components()

    def _rebuild_layout(self):
        """
        重构词汇学习页面的布局，实现倒计时置顶、单词居中等效果。
        """
        """重构布局：倒计时红色置顶，黄金重心上移，大间距"""
        if not self.main_layout or not self.v_disp or not self.v_input or not self.btn_confirm:
            return
        
        # 清空现有布局（但不删除我们要用的控件）
        widgets_to_keep = {self.v_disp, self.v_input, self.btn_confirm, self.t_label}
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget and widget not in widgets_to_keep:
                widget.deleteLater()
        
        # 1. 倒计时 - 红色置顶，右上角
        timer_row = QtWidgets.QHBoxLayout()
        timer_row.addStretch(1)
        timer_row.addWidget(self.t_label)
        self.main_layout.addLayout(timer_row)
        self.main_layout.addSpacing(15)  # 与窗口顶部保持约15px边距
        
        # 2. 顶部弹簧 - 黄金重心（上移）
        self.main_layout.addStretch(1)
        
        # 3. 单词显示区 - 居中
        self.main_layout.addWidget(self.v_disp, alignment=QtCore.Qt.AlignCenter)
        
        # 4. 巨大间距 - 拒绝拥挤
        self.main_layout.addSpacing(80)  # 单词和输入框之间
        
        # 5. 输入框 - 限宽 300px，居中
        self.v_input.setFixedWidth(300)
        self.main_layout.addWidget(self.v_input, alignment=QtCore.Qt.AlignCenter)
        
        # 6. 间距
        self.main_layout.addSpacing(40)  # 输入框和按钮之间
        
        # 7. 确认按钮 - 限宽 300px，居中
        self.btn_confirm.setFixedWidth(300)
        self.main_layout.addWidget(self.btn_confirm, alignment=QtCore.Qt.AlignCenter)
        
        # 8. 底部弹簧 - 黄金重心（2倍，使内容上移）
        self.main_layout.addStretch(2)

    def _style_components(self):
        """
        为词汇学习模块的UI组件应用统一的样式。
        """
        """统一样式规范：现代、简洁、专业"""
        
        # 倒计时标签 - 红色置顶，醒目
        if self.t_label:
            self.t_label.setStyleSheet("""
                QLabel {
                    color: #E74C3C;
                    font-size: 18px;
                    font-weight: bold;
                    background: transparent;
                    padding: 4px 12px;
                }
            """)
        
        # 输入框 - 38px 高度，现代边框
        if self.v_input:
            self.v_input.setFixedHeight(38)
            self.v_input.setStyleSheet("""
                QLineEdit {
                    background-color: #fafafa;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 18px;
                    padding: 0px 16px;
                    color: #333333;
                }
                QLineEdit:focus {
                    border: 1px solid #2196F3;
                    background-color: #ffffff;
                    outline: none;
                }
            """)
        
        # 确认按钮 - 42px 高度
        if self.btn_confirm:
            self.btn_confirm.setFixedHeight(42)
            self.btn_confirm.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #1565C0;
                }
            """)
        
        # 显示区域 - 透明背景，无边框，固定宽度防止滚动条
        if self.v_disp:
            self.v_disp.setAlignment(QtCore.Qt.AlignCenter)
            self.v_disp.setFixedWidth(600)  # 固定宽度，防止出现滚动条
            self.v_disp.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)  # 禁用水平滚动条
            self.v_disp.setStyleSheet("""
                QTextEdit {
                    background-color: transparent;
                    border: none;
                }
            """)

    def load_vocabulary(self):
        """
        从 assets/vocabulary.json 文件加载词汇表并随机打乱。
        """
        try:
            if hasattr(self.win, 'base_path') and self.win.base_path:
                vocab_path = os.path.join(self.win.base_path, "assets", "vocabulary.json")
            else:
                vocab_path = os.path.join(os.path.dirname(__file__), "..", "assets", "vocabulary.json")
                vocab_path = os.path.normpath(vocab_path)
            
            with open(vocab_path, "r", encoding="utf-8") as f:
                self.vocabulary = json.load(f)
                random.shuffle(self.vocabulary)
        except Exception as e:
            print(f"加载词汇表失败: {e}")
            self.vocabulary = [{"word": "apple", "content": "苹果"}]

    def show_next(self, error_msg=""):
        """
        显示下一个词汇的中文释义，并根据需要显示错误提示。
        """
        if not self.v_disp or not self.v_input:
            return

        curr = self.vocabulary[self.current_idx]
        
        # 构建 HTML 内容
        hint_line = ""
        if error_msg:
            hint_line = f"""
                <div style='margin-top: 16px;'>
                    <span style='font-size: 16px; color: #d32f2f; font-weight: bold;'>
                        ✅ 正确答案: {error_msg.capitalize()}
                    </span>
                </div>
            """
        
        html = f"""
            <html>
            <head>
                <style>
                    body {{
                        margin: 0;
                        padding: 0;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    }}
                </style>
            </head>
            <body>
                <div style='text-align: center; padding: 20px;'>
                    <div style='font-size: 14px; color: #999999; font-weight: 600; margin-bottom: 16px;'>
                        第 {self.current_idx + 1} 关
                    </div>
                    <div style='font-size: 32px; color: #333333; font-weight: 500; line-height: 1.4;'>
                        {curr['content']}
                    </div>
                    {hint_line}
                </div>
            </body>
            </html>
        """
        self.v_disp.setHtml(html)

        if not error_msg:
            self.v_input.clear()
            self.v_input.setFocus()
            self.time_left = 15
            if self.t_label:
                self.t_label.setText(str(self.time_left))
            
            if self.win.findChild(QtWidgets.QStackedWidget, "stackedWidget").currentIndex() == 0:
                self.timer.start(1000)

    def tick(self):
        """
        计时器滴答事件处理函数，更新倒计时显示，并在时间到时自动显示答案。
        """
        self.time_left -= 1
        if self.t_label:
            self.t_label.setText(str(self.time_left))
        if self.time_left <= 0:
            self.timer.stop()
            target = self.vocabulary[self.current_idx]['word'].strip()
            self.show_next(error_msg=target)
            QtCore.QTimer.singleShot(2000, self.go_next)

    def check_answer(self):
        """
        检查用户输入的答案是否正确，并根据结果更新UI样式。
        """
        self.timer.stop()
        user_in = self.v_input.text().strip().lower()
        if not user_in:
            return
        target = self.vocabulary[self.current_idx]['word'].strip().lower()

        if user_in == target:
            self.v_input.setStyleSheet("""
                QLineEdit {
                    font-size: 18px;
                    border: 1px solid #4CAF50;
                    background-color: #f1f8f4;
                    border-radius: 6px;
                    padding: 0px 16px;
                    color: #333333;
                    outline: none;
                }
            """)
            QtCore.QTimer.singleShot(600, self.go_next)
        else:
            self.v_input.setStyleSheet("""
                QLineEdit {
                    font-size: 18px;
                    border: 1px solid #f44336;
                    background-color: #fef1f1;
                    border-radius: 6px;
                    padding: 0px 16px;
                    color: #333333;
                    outline: none;
                }
            """)
            self.show_next(error_msg=target)
            QtCore.QTimer.singleShot(2000, self.go_next)

    def go_next(self):
        """
        切换到下一个词汇。
        """
        self.current_idx = (self.current_idx + 1) % len(self.vocabulary)
        self.show_next()