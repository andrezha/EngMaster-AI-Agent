import sys
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextBrowser, QScrollArea, QStackedWidget,
                             QPushButton, QLabel, QFrame, QMessageBox, QButtonGroup)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# ================= 模拟数据 =================
MOCK_EXAM_DATA = [
    {
        "id": 1, "instruction": "阅读 A 篇", "passage": "<h2>Passage 1</h2>",
        "items": [{"q_id": "21", "content": "Question 1?", "options": {"A": "A", "B": "B", "C": "C", "D": "D"}, "answer": "A"}],
        "weight": 2.5
    }
]

# ================= 题目组件 =================
class QuestionCard(QFrame):
    """
    用于显示单个题目及其选项的 UI 组件。
    """
    def __init__(self, item, weight):
        super().__init__()
        self.item = item
        self.weight = weight
        self.user_choice = None
        self.setMinimumHeight(150)
        self.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 8px; margin: 5px;")
        
        layout = QVBoxLayout(self)
        self.q_label = QLabel(f"<b>Q{item['q_id']}. {item['content']}</b>")
        layout.addWidget(self.q_label)
        
        self.btns = {}
        for label in ['A', 'B', 'C', 'D']:
            btn = QPushButton(f"{label}. {item['options'].get(label, '')}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, l=label: self.save_ans(l))
            layout.addWidget(btn)
            self.btns[label] = btn

    def save_ans(self, label): self.user_choice = label

    def show_review(self):
        """判分后样式：绿色对，红色错"""
        correct = self.item['answer']
        for label, btn in self.btns.items():
            btn.setEnabled(False)
            if label == correct:
                btn.setStyleSheet("background-color: #c8e6c9; color: green; font-weight: bold;")
            if label == self.user_choice and label != correct:
                btn.setStyleSheet("background-color: #ffcdd2; color: red;")

# ================= 成绩报告页 (ResultPage) =================
class ResultPage(QWidget):
    """
    显示考试成绩报告的页面，包括得分、耗时和错题列表。
    """
    def __init__(self, parent_ui):
        super().__init__()
        self.parent_ui = parent_ui
        self.layout = QVBoxLayout(self)
        self.setStyleSheet("background-color: white;")

    def generate_report(self, score, used_time, total_possible, wrong_items):
        """
        生成并显示考试报告。
        """
        # 清空旧布局
        for i in reversed(range(self.layout.count())): 
            self.layout.itemAt(i).widget().setParent(None)

        # 1. 分数头部
        header = QLabel(f"考试结束 - 成绩报告")
        header.setFont(QFont("Arial", 20, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(header)

        # 2. 核心指标卡片
        stats = QFrame()
        stats.setStyleSheet("background: #f8f9fa; border: 1px solid #eee; border-radius: 10px;")
        stats_layout = QHBoxLayout(stats)
        
        def add_stat(label, val, color="#333"):
            v_layout = QVBoxLayout()
            l1 = QLabel(label); l1.setAlignment(Qt.AlignCenter)
            l2 = QLabel(str(val)); l2.setAlignment(Qt.AlignCenter)
            l2.setFont(QFont("Arial", 18, QFont.Bold)); l2.setStyleSheet(f"color: {color};")
            v_layout.addWidget(l1); v_layout.addWidget(l2)
            stats_layout.addLayout(v_layout)

        add_stat("您的得分", score, "#d32f2f")
        add_stat("理想分数", 80, "#2e7d32") # 假设客观题满分 80
        add_stat("完成耗时", used_time, "#1976d2")
        self.layout.addWidget(stats)

        # 3. 错题列表
        self.layout.addWidget(QLabel(f"<b>错题回顾 ({len(wrong_items)} 题):</b>"))
        scroll = QScrollArea()
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        for itm in wrong_items:
            w_lab = QLabel(f"❌ 第 {itm['id']} 题 | 您的选择: {itm['user']} | 正确答案: {itm['correct']}")
            w_lab.setStyleSheet("color: #d32f2f; padding: 5px; border-bottom: 1px solid #eee;")
            scroll_layout.addWidget(w_lab)
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        self.layout.addWidget(scroll)

        # 4. 底部按钮
        self.review_btn = QPushButton("试卷回看 (查看原文解析)")
        self.review_btn.setMinimumHeight(45)
        self.review_btn.setStyleSheet("background: #2196F3; color: white; font-weight: bold;")
        self.review_btn.clicked.connect(self.parent_ui.go_to_review)
        self.layout.addWidget(self.review_btn)

# ================= 主界面 =================
class ExamSystem(QMainWindow):
    """
    主考试系统窗口，负责管理试卷的加载、页面的切换和最终成绩的计算。
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HSE-AI 英语机考系统")
        self.resize(1100, 800)
        self.start_time = time.time()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)

        self.stack = QStackedWidget()
        self.pages = []
        for data in MOCK_EXAM_DATA:
            # 这里的 PassagePage 代码同上一轮
            from __main__ import PassagePage 
            page = PassagePage(data)
            self.stack.addWidget(page)
            self.pages.append(page)
        
        # 添加结果页
        self.result_page = ResultPage(self)
        self.stack.addWidget(self.result_page)
        
        self.main_layout.addWidget(self.stack)

        # 控制栏
        self.ctrl_bar = QHBoxLayout()
        self.next_btn = QPushButton("下一页")
        self.next_btn.clicked.connect(self.handle_next)
        self.ctrl_bar.addStretch()
        self.ctrl_bar.addWidget(self.next_btn)
        self.main_layout.addLayout(self.ctrl_bar)

    def handle_next(self):
        """
        处理“下一页”按钮点击事件，切换到下一页试卷或提交试卷。
        """
        curr = self.stack.currentIndex()
        if not self.pages[curr].is_all_answered():
            QMessageBox.warning(self, "漏题", "请完成本页所有题目！")
            return

        if curr == len(self.pages) - 1:
            self.submit_and_show_report()
        else:
            self.stack.setCurrentIndex(curr + 1)
            if self.stack.currentIndex() == len(self.pages) - 1:
                self.next_btn.setText("提交试卷")

    def submit_and_show_report(self):
        """
        提交试卷，计算得分，生成报告，并切换到结果页面。
        """
        # 1. 计算
        score = 0
        wrong_items = []
        for p in self.pages:
            for c in p.cards:
                c.show_review() # 预处理样式
                if c.user_choice == c.item['answer']:
                    score += c.weight
                else:
                    wrong_items.append({"id": c.item['q_id'], "user": c.user_choice, "correct": c.item['answer']})
        
        # 2. 统计时间
        used = int(time.time() - self.start_time)
        time_str = f"{used//60}分{used%60}秒"
        
        # 3. 渲染结果页并切换
        self.result_page.generate_report(score, time_str, 80, wrong_items)
        self.stack.setCurrentWidget(self.result_page)
        self.ctrl_bar.hide() # 报告页不需要底部的“下一页”按钮

    def go_to_review(self):
        """
        切换到试卷回看模式，从第一页开始回顾。
        """
        """返回第一页开始回看"""
        self.stack.setCurrentIndex(0)
        self.ctrl_bar.show()
        self.next_btn.setText("查看下一篇")
        # 修改逻辑：回看模式下不再校验是否答题（因为已经答完了）
        self.is_review_mode = True 

class PassagePage(QWidget):
    """
    显示单个试卷板块（文章和题目）的页面。
    """
    def __init__(self, data):
        """
        初始化 PassagePage。
        """
        super().__init__()
        layout = QHBoxLayout(self)
        self.p_view = QTextBrowser(); self.p_view.setHtml(data['passage'])
        layout.addWidget(self.p_view, 3)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        q_container = QWidget(); self.q_layout = QVBoxLayout(q_container)
        self.cards = []
        for itm in data['items']:
            card = QuestionCard(itm, data['weight'])
            self.q_layout.addWidget(card); self.cards.append(card)
        scroll.setWidget(q_container); layout.addWidget(scroll, 2)
    def is_all_answered(self):
        """检查当前页面所有题目是否都已作答。"""
        return all(c.user_choice is not None for c in self.cards)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ExamSystem()
    win.show()
    sys.exit(app.exec())