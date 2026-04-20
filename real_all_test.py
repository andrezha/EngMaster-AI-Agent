import sys
import os
import re
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextBrowser, QScrollArea, QStackedWidget,
                             QPushButton, QLabel, QFrame, QMessageBox, QButtonGroup, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# ==========================================
# 1. 你的解析器逻辑 (已整合)
# ==========================================
# 此处省略你提供的 parse_reading_txt, _parse_reading_items 等函数内容
# 实际运行时请确保这些函数在代码中

# [此处插入你提供的所有解析函数代码...]

# ==========================================
# 2. 动态题目卡片 (支持选择题与填空题)
# ==========================================
class QuestionCard(QFrame):
    def __init__(self, item, weight, q_type):
        super().__init__()
        self.item = item
        self.weight = weight
        self.q_type = q_type
        self.user_choice = None
        self.setMinimumHeight(150)
        self.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 8px; margin: 5px;")
        
        layout = QVBoxLayout(self)
        self.title = QLabel(f"<b>Q{item['q_id']}. {item.get('content', '')}</b>")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)

        if q_type == "grammar":
            # 语法填空：显示输入框
            self.input = QLineEdit()
            self.input.setPlaceholderText("请输入答案...")
            self.input.setMinimumHeight(35)
            self.input.textChanged.connect(self.save_input)
            layout.addWidget(self.input)
        else:
            # 选择题：显示 A-D 或 A-G 按钮
            self.group = QButtonGroup(self)
            btn_layout = QVBoxLayout() # 垂直排列选项，阅读理解更清晰
            opts = item.get('options', {})
            # 处理列表形式（七选五）或字典形式（阅读/完形）
            if isinstance(opts, list):
                for opt in opts: self._add_opt_btn(opt['label'], opt['content'], btn_layout)
            else:
                for label, content in opts.items(): self._add_opt_btn(label, content, btn_layout)
            layout.addLayout(btn_layout)

    def _add_opt_btn(self, label, content, layout):
        btn = QPushButton(f"{label}. {content}")
        btn.setCheckable(True)
        btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; } QPushButton:checked { background: #e3f2fd; border: 1.5px solid #2196F3; }")
        btn.clicked.connect(lambda _, l=label: self.save_choice(l))
        self.group.addButton(btn)
        layout.addWidget(btn)

    def save_choice(self, label): self.user_choice = label
    def save_input(self, text): self.user_choice = text.strip()

# ==========================================
# 3. 成绩报告页 (ResultPage)
# ==========================================
class ResultPage(QWidget):
    def __init__(self, parent_ui):
        super().__init__()
        self.parent_ui = parent_ui
        self.layout = QVBoxLayout(self)

    def generate_report(self, score, used_time, wrong_items):
        for i in reversed(range(self.layout.count())): self.layout.itemAt(i).widget().setParent(None)
        
        title = QLabel("🎉 考试结算报告"); title.setFont(QFont("Arial", 22, QFont.Bold)); title.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title)

        info_box = QLabel(f"最终得分：{score} / 80\n本次耗时：{used_time}\n理想得分：80.0")
        info_box.setStyleSheet("background: #f1f8e9; padding: 20px; border-radius: 10px; font-size: 16px;")
        info_box.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(info_box)

        self.layout.addWidget(QLabel(f"<b>错题清单 ({len(wrong_items)} 题):</b>"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); l = QVBoxLayout(content)
        for w in wrong_items:
            l.addWidget(QLabel(f"❌ Q{w['id']} | 你的答案: {w['user']} | 正确答案: {w['correct']}"))
        scroll.setWidget(content)
        self.layout.addWidget(scroll)

        btn_box = QHBoxLayout()
        exit_btn = QPushButton("结束本次考试")
        exit_btn.clicked.connect(self.parent_ui.close)
        exit_btn.setMinimumHeight(45); exit_btn.setStyleSheet("background: #555; color: white;")
        btn_box.addWidget(exit_btn)
        self.layout.addLayout(btn_box)

# ==========================================
# 4. 主系统 (ExamSystem)
# ==========================================
class HSEExamSystem(QMainWindow):
    def __init__(self, data_list):
        super().__init__()
        self.setWindowTitle("HSE-AI 英语全项模拟系统")
        self.resize(1200, 850)
        self.data_list = data_list
        self.pages = []
        self.start_time = time.time()
        
        # UI 构建
        central = QWidget(); self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # 动态创建篇章页
        for data in data_list:
            page = self._create_page(data)
            self.stack.addWidget(page)
            self.pages.append(page)
            
        # 结果页预留
        self.res_page = ResultPage(self)
        self.stack.addWidget(self.res_page)

        # 控制栏
        self.ctrl = QHBoxLayout()
        self.info = QLabel(f"进度: 1 / {len(data_list)}")
        self.next_btn = QPushButton("下一页")
        self.next_btn.setFixedSize(150, 45)
        self.next_btn.clicked.connect(self.go_next)
        self.ctrl.addWidget(self.info); self.ctrl.addStretch(); self.ctrl.addWidget(self.next_btn)
        self.main_layout.addLayout(self.ctrl)

    def _create_page(self, data):
        page_widget = QWidget()
        l = QHBoxLayout(page_widget)
        # 左原文
        view = QTextBrowser()
        view.setHtml(f"<h3>{data['category']}</h3>{data['passage']}")
        view.setStyleSheet("font-size: 16px; padding: 15px;")
        l.addWidget(view, 3)
        # 右题目
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); ql = QVBoxLayout(container)
        page_widget.cards = []
        weight = 2.5 if data['question_type'] in ['reading', 'seven_five'] else (1.0 if data['question_type']=='cloze' else 1.5)
        for itm in data['items']:
            card = QuestionCard(itm, weight, data['question_type'])
            ql.addWidget(card); page_widget.cards.append(card)
        scroll.setWidget(container); l.addWidget(scroll, 2)
        return page_widget

    def go_next(self):
        curr_idx = self.stack.currentIndex()
        curr_page = self.pages[curr_idx]
        
        # 漏题校验
        if not all(c.user_choice for c in curr_page.cards):
            QMessageBox.warning(self, "漏题", "本页还有题目未完成，请全部完成后再继续！")
            return

        if curr_idx == len(self.pages) - 1:
            self.show_result()
        else:
            self.stack.setCurrentIndex(curr_idx + 1)
            self.info.setText(f"进度: {self.stack.currentIndex()+1} / {len(self.pages)}")
            if self.stack.currentIndex() == len(self.pages) - 1: self.next_btn.setText("提交试卷")

    def show_result(self):
        score = 0; wrongs = []
        for p in self.pages:
            for c in p.cards:
                if str(c.user_choice).strip().upper() == str(c.item['answer']).strip().upper():
                    score += c.weight
                else:
                    wrongs.append({"id": c.item['q_id'], "user": c.user_choice, "correct": c.item['answer']})
        
        elapsed = int(time.time() - self.start_time)
        self.res_page.generate_report(score, f"{elapsed//60}分{elapsed%60}秒", wrongs)
        self.stack.setCurrentWidget(self.res_page)
        self.ctrl.hide()

# ==========================================
# 5. 启动入口
# ==========================================
if __name__ == "__main__":
    # 解析本地 data 目录
    data_folder = "data"
    parsed_all = []
    if os.path.exists(data_folder):
        for file in sorted(os.listdir(data_folder)):
            if file.endswith(".txt"):
                with open(os.path.join(data_folder, file), 'r', encoding='utf-8') as f:
                    parsed_all.append(parse_reading_txt(f.read()))
    
    if not parsed_all:
        print("错误: data 文件夹为空或没有有效的 txt 文件。")
    else:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        gui = HSEExamSystem(parsed_all)
        gui.show()
        sys.exit(app.exec())

