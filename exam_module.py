import json
import os
import random
import re
from PySide6.QtWidgets import (QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QLabel,
                             QRadioButton, QButtonGroup, QSizePolicy, QLineEdit, QMessageBox, QFrame)
from PySide6.QtCore import Qt
from parsers.reading_parser import parse_reading_txt
from parsers.special_practice_parser import SpecializedPracticeTextParser, SpecializedPracticeQuestion
from utils import _normalize_full_width_to_half_width, normalize_exam_text

class ExamManager:
    """
    专项练习模块核心管理器。
    已恢复：QPushButton 行选择式样，支持整行点击高亮。
    """
    PATH_MAPPING = {
        "阅读理解": "data/阅读理解",
        "七选五": "data/七选五",
        "完形填空": "data/完形填空",
        "语法填空": "data/语法填空",
        "短文改错": "data/短文改错",
        "写作续写": "data/写作续写",
    }

    def __init__(self, main_window, gaokao_ui):
        self.mw = main_window
        self.ui = gaokao_ui
        if not self.ui:
            print("ERROR: ExamManager failed to receive gaokao_ui.")
            return

        # 1. 初始化变量
        self.current_type = None
        self.user_selections = {}
        self.current_q = None
        self.current_files = []

        self.currentReadingData = None
        self.currentClozeData = None
        self.currentGrammarData = None
        self.currentClozeFillData = None

        # 2. 比例调整
        main_layout = self.ui.layout()
        if main_layout and hasattr(main_layout, 'setStretch'):
            main_layout.setStretch(0, 6)
            main_layout.setStretch(1, 4)

        # 3. 绑定信号
        self.ui.btn_gk_next.clicked.connect(self.load_and_render)
        self.ui.btn_gk_submit.clicked.connect(self.check_score)

        # 4. 绑定题型选择按钮
        self.ui.gk_btn_reading.clicked.connect(lambda: self.switch_topic("阅读理解"))
        self.ui.gk_btn_cloze.clicked.connect(lambda: self.switch_topic("完形填空"))
        self.ui.gk_btn_seven_five.clicked.connect(lambda: self.switch_topic("七选五"))
        self.ui.gk_btn_grammar.clicked.connect(lambda: self.switch_topic("语法填空"))

        # 初始清理
        self.ui.gk_question_body.clear()
        self.ui.gk_result_panel.clear()
        self.ui.gk_ai_display.clear()

        self._style_bottom_action_bar()
        self.update_nav_highlight()

    def _style_bottom_action_bar(self):
        style_submit = "QPushButton { background-color: #3498db; color: white; border-radius: 16px; font-weight: bold; height: 50px; }"
        style_next = "QPushButton { background-color: #ecf0f1; color: #2c3e50; border: 2px solid #bdc3c7; border-radius: 16px; height: 50px; }"
        if hasattr(self.ui, 'btn_gk_submit'): self.ui.btn_gk_submit.setStyleSheet(style_submit)
        if hasattr(self.ui, 'btn_gk_next'): self.ui.btn_gk_next.setStyleSheet(style_next)

    def _clear_layout(self, layout):
        if not layout: return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def fetchNewRandomFile(self, topic_name):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(base_dir, self.PATH_MAPPING.get(topic_name, ""))
        if not os.path.exists(data_path): return False

        files = [f for f in os.listdir(data_path) if f.endswith(".txt")]
        if not files: return False

        target_file = os.path.join(data_path, random.choice(files))
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()

            clean_content = normalize_exam_text(content)
            self.current_q = parse_reading_txt(clean_content)

            self.current_type = topic_name
            if topic_name == "阅读理解": self.currentReadingData = self.current_q
            elif topic_name == "七选五": self.currentClozeData = self.current_q

            return True
        except Exception as e:
            print(f"Fetch Error: {e}")
            return False

    def switch_topic(self, topic_name):
        if self.fetchNewRandomFile(topic_name):
            self.update_nav_highlight()
            self.render_passage()
            self.render_question_ui()

    def load_and_render(self):
        if self.current_type and self.fetchNewRandomFile(self.current_type):
            self.render_passage()
            self.render_question_ui()

    def render_passage(self):
        if not self.current_q: return
        raw_p = self.current_q.get('passage', '')
        formatted_p = raw_p.replace('\n', '<br>')
        html = f"<div style='font-size:16px; line-height:1.6; color:#2c3e50;'>{formatted_p}</div>"
        self.ui.gk_question_body.setHtml(html)

    def render_question_ui(self):
        target_area = self.mw.findChild(QWidget, "gk_answer_content")
        if not target_area: return
        layout = target_area.layout() or QVBoxLayout(target_area)
        self._clear_layout(layout)

        q_type = self.current_q.get('question_type', 'reading')
        items = self.current_q.get('items', [])

        if q_type == "seven_five" or self.current_type == "七选五":
            self._render_seven_five_ui(layout, items)
        elif q_type == "grammar":
            self._render_grammar_fill_ui(layout, items)
        elif q_type == "cloze":
            self._render_cloze_ui(layout, items)
        else:
            self._render_reading_ui(layout, items)

        layout.addStretch()

    def _render_reading_ui(self, layout, items):
        """渲染阅读理解 - 使用 QPushButton 整行选择模式"""
        for item in items:
            qid = item.get('q_id')
            qtext = item.get('content')

            frame = QFrame()
            frame.setStyleSheet("QFrame { border: none; margin-bottom: 20px; }")
            vbox = QVBoxLayout(frame)

            lbl = QLabel(f"<b>{qid}. {qtext}</b>")
            lbl.setWordWrap(True)
            vbox.addWidget(lbl)

            group = QButtonGroup(self.mw)
            group.setExclusive(True) # 核心：设置按钮组互斥

            opts = item.get('options', {})
            if isinstance(opts, dict):
                for k, v in sorted(opts.items()):
                    # 改回 QPushButton 以实现“选行”式样
                    btn = QPushButton(f"{k}. {v}")
                    btn.setCheckable(True)
                    btn.setStyleSheet("""
                        QPushButton {
                            text-align: left;
                            padding: 10px 15px;
                            border: 1px solid #dcdde1;
                            border-radius: 8px;
                            background-color: white;
                            color: #2f3640;
                        }
                        QPushButton:hover {
                            background-color: #f5f6fa;
                        }
                        QPushButton:checked {
                            background-color: #3498db;
                            color: white;
                            border-color: #2980b9;
                            font-weight: bold;
                        }
                    """)
                    group.addButton(btn)
                    # 记录选择逻辑
                    btn.clicked.connect(lambda ch, q=qid, a=k: self.user_selections.update({q: a}))
                    vbox.addWidget(btn)
            layout.addWidget(frame)

    def _render_seven_five_ui(self, layout, items):
        """渲染七选五 - 使用 QPushButton 整行选择模式"""
        global_options = {}
        for it in items:
            opts = it.get('options', {})
            if isinstance(opts, dict) and len(opts) >= 7:
                global_options = opts
                break
        if not global_options:
            for it in items:
                opts = it.get('options', {})
                if isinstance(opts, dict): global_options.update(opts)

        for item in items:
            qid = item.get('q_id')
            frame = QFrame()
            frame.setStyleSheet("QFrame { border: 1px solid #eee; border-radius: 8px; margin-bottom: 15px; padding: 5px; background: #fafafa; }")
            vbox = QVBoxLayout(frame)
            vbox.addWidget(QLabel(f"<b>空格 {qid}：请选择最合适的句子</b>"))

            group = QButtonGroup(self.mw)
            group.setExclusive(True)

            for k, v in sorted(global_options.items()):
                btn = QPushButton(f"{k}. {v}")
                btn.setCheckable(True)
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding: 8px 12px; border: 1px solid #dcdde1;
                        border-radius: 6px; background-color: white; font-size: 13px;
                    }
                    QPushButton:checked {
                        background-color: #3498db; color: white; font-weight: bold;
                    }
                """)
                group.addButton(btn)
                btn.clicked.connect(lambda ch, q=qid, a=k: self.user_selections.update({q: a}))
                vbox.addWidget(btn)
            layout.addWidget(frame)

    def _render_grammar_fill_ui(self, layout, items):
        self.grammar_input_fields = {}
        for item in items:
            qid = item.get('q_id')
            h_layout = QHBoxLayout()
            h_layout.addWidget(QLabel(f"{qid}."))
            edit = QLineEdit()
            edit.setPlaceholderText("填写答案...")
            edit.textChanged.connect(lambda text, q=qid: self.user_selections.update({q: text}))
            h_layout.addWidget(edit)
            self.grammar_input_fields[qid] = edit
            layout.addLayout(h_layout)

    def _render_cloze_ui(self, layout, items):
        """渲染完形填空 - 使用 QPushButton 整行选择模式"""
        grid = QHBoxLayout()
        col1, col2 = QVBoxLayout(), QVBoxLayout()
        for idx, item in enumerate(items):
            qid = item.get('q_id')
            label = QLabel(f"<b>{qid}.</b>")
            target_col = col1 if idx % 2 == 0 else col2
            target_col.addWidget(label)

            group = QButtonGroup(self.mw)
            group.setExclusive(True)

            opts = item.get('options', {})
            if isinstance(opts, dict):
                for k, v in sorted(opts.items()):
                    btn = QPushButton(f"{k}. {v}")
                    btn.setCheckable(True)
                    btn.setStyleSheet("""
                        QPushButton { text-align: left; padding: 5px 10px; border: 1px solid #eee; border-radius: 4px; background: white; }
                        QPushButton:checked { background: #3498db; color: white; }
                    """)
                    group.addButton(btn)
                    btn.clicked.connect(lambda ch, q=qid, c=k: self.user_selections.update({q: c}))
                    target_col.addWidget(btn)
        grid.addLayout(col1); grid.addLayout(col2)
        layout.addLayout(grid)

    def check_score(self):
        if not self.current_q: return
        items = self.current_q.get('items', [])
        results = []
        correct_num = 0
        for it in items:
            qid = it.get('q_id')
            ans = str(it.get('answer', '')).strip().upper()
            user = str(self.user_selections.get(qid, "未做")).strip().upper()
            is_ok = (user == ans)
            if is_ok: correct_num += 1
            status = "✅" if is_ok else "❌"
            results.append(f"Q{qid}: 你的答案[{user}] 正确答案[{ans}] {status}")

        self.ui.gk_result_panel.setHtml(f"<b>判分结果: {correct_num}/{len(items)}</b><br><br>" + "<br>".join(results))
        self._show_analysis()

    def _show_analysis(self):
        if not self.current_q: return
        html = "<h3>💡 试题详解</h3>"
        for it in self.current_q.get('items', []):
            qid = it.get('q_id')
            raw_a = it.get('analysis', '暂无解析')
            clean_a = str(raw_a).replace('\n', '<br>')
            html += f"<div style='margin-bottom:12px; padding:8px; background:#f9f9f9; border-left:4px solid #3498db;'>" \
                    f"<b>第{qid}题：</b><br>{clean_a}</div>"
        self.ui.gk_ai_display.setHtml(html)

    def update_nav_highlight(self):
        btn_map = {"阅读理解": "gk_btn_reading", "完形填空": "gk_btn_cloze", "语法填空": "gk_btn_grammar", "七选五": "gk_btn_seven_five"}
        for type_name, obj_name in btn_map.items():
            btn = getattr(self.ui, obj_name, None)
            if btn:
                if type_name == self.current_type:
                    btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; font-weight: bold;")
                else:
                    btn.setStyleSheet("background-color: #f0f0f0; color: #333; border-radius: 5px;")