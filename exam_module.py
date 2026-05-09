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
    已修复：解决得分重叠、内容下移、完形填空结果双列排布、补全截断逻辑。
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

            if topic_name == "阅读理解":
                metadata, passage, qs = SpecializedPracticeTextParser().parse_file(target_file)
                items = [{
                    'q_id': str(q.question_number),
                    'content': q.question_text,
                    'options': q.options,
                    'answer': str(q.correct_answer).strip().upper(),
                    'analysis': q.analysis_text
                } for q in qs]
                self.current_q = {'passage': passage, 'items': items, 'question_type': 'reading'}
            else:
                parsed_data = parse_reading_txt(clean_content)
                items = parsed_data.get('items', [])
                global_analysis = str(parsed_data.get('original_analysis', ''))
                if global_analysis and items:
                    for item in items:
                        qid = item.get('q_id')
                        pattern = rf"(?:^|\n)\s*{qid}\.?\s*(.*?)(?=\n\s*\d+\.?\s*|\Z)"
                        match = re.search(pattern, global_analysis, re.S)
                        item['analysis'] = match.group(1).strip() if match else global_analysis
                self.current_q = parsed_data

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
        for item in items:
            qid, qtext = item.get('q_id'), item.get('content')
            frame = QFrame()
            frame.setStyleSheet("QFrame { border: none; margin-bottom: 20px; }")
            vbox = QVBoxLayout(frame)
            lbl = QLabel(f"<b>{qid}. {qtext}</b>")
            lbl.setWordWrap(True)
            vbox.addWidget(lbl)
            group = QButtonGroup(self.mw)
            group.setExclusive(True)
            opts = item.get('options', {})
            if isinstance(opts, dict):
                for k, v in sorted(opts.items()):
                    btn = QPushButton(f"{k}. {v}")
                    btn.setCheckable(True)
                    btn.setStyleSheet("QPushButton { text-align: left; padding: 10px; border: 1px solid #dcdde1; border-radius: 8px; background: white; } "
                                    "QPushButton:checked { background-color: #3498db; color: white; font-weight: bold; }")
                    group.addButton(btn)
                    btn.clicked.connect(lambda ch, q=qid, a=k: self.user_selections.update({q: a}))
                    vbox.addWidget(btn)
            layout.addWidget(frame)

    def _render_seven_five_ui(self, layout, items):
        global_options = {}
        for it in items:
            opts = it.get('options', {})
            if isinstance(opts, dict) and len(opts) >= 7:
                global_options = opts
                break
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
                btn.setStyleSheet("QPushButton { text-align: left; padding: 8px; border: 1px solid #d1d5db; background: white; } "
                                "QPushButton:checked { background: #3498db; color: white; }")
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
        grid = QHBoxLayout()
        col1, col2 = QVBoxLayout(), QVBoxLayout()
        for idx, item in enumerate(items):
            qid = item.get('q_id')
            col = col1 if idx % 2 == 0 else col2
            col.addWidget(QLabel(f"<b>{qid}.</b>"))
            group = QButtonGroup(self.mw)
            group.setExclusive(True)
            opts = item.get('options', {})
            if isinstance(opts, dict):
                for k, v in sorted(opts.items()):
                    btn = QPushButton(f"{k}. {v}")
                    btn.setCheckable(True)
                    btn.setStyleSheet("QPushButton { text-align: left; padding: 5px; background: white; border: 1px solid #eee; } "
                                    "QPushButton:checked { background: #3498db; color: white; }")
                    group.addButton(btn)
                    btn.clicked.connect(lambda ch, q=qid, c=k: self.user_selections.update({q: c}))
                    col.addWidget(btn)
        grid.addLayout(col1); grid.addLayout(col2)
        layout.addLayout(grid)

    def check_score(self):
        """判分与展示解析 - 彻底解决重叠与位置下移问题。"""
        if not self.current_q: return
        items = self.current_q.get('items', [])
        panel = self.ui.gk_result_panel

        # 🚨 1. 彻底清除原有文本内容，解决重叠遮挡
        panel.clear()
        panel.setHtml("")

        # 2. 准备或清理布局
        if not panel.layout():
            layout = QVBoxLayout(panel)
            panel.setLayout(layout)
        else:
            layout = panel.layout()
            self._clear_layout(layout)

        # 🎯 3. 【核心修正】在顶部添加一个较大的间距，将得分和列表向下移动
        layout.addSpacing(40)

        layout.setContentsMargins(15, 5, 15, 15)
        layout.setSpacing(6)

        # 4. 计算得分
        correct_num = 0
        for it in items:
            ans = str(it.get('answer', '')).strip().upper()
            user = str(self.user_selections.get(it.get('q_id'), "未做")).strip().upper()
            if user == ans: correct_num += 1

        # 5. 得分置顶（左对齐，加一点底部间距）
        score_label = QLabel(f"最终得分: {correct_num} / {len(items)}")
        score_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(score_label)

        # 6. 判分明细容器（完形填空双列，其他单列）
        is_cloze = (self.current_type == "完形填空")
        if is_cloze:
            container = QWidget()
            cont_lay = QHBoxLayout(container)
            cont_lay.setContentsMargins(0, 0, 0, 0)
            col1 = QVBoxLayout()
            col2 = QVBoxLayout()
            cont_lay.addLayout(col1)
            cont_lay.addLayout(col2)
            layout.addWidget(container)
        else:
            col1 = layout
            col2 = None

        # 7. 填充题目明细对比结果
        for idx, it in enumerate(items):
            qid = it.get('q_id')
            ans = str(it.get('answer', '')).strip().upper()
            user = str(self.user_selections.get(qid, "未做")).strip().upper()
            is_ok = (user == ans)

            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 2, 0, 2)
            color = "#27ae60" if is_ok else "#e74c3c"
            status = "✅" if is_ok else "❌"

            info = QLabel(f"Q{qid}: {user} | {ans} {status}")
            info.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
            row_lay.addWidget(info, 1)

            btn = QPushButton("📖 解析")
            btn.setFixedWidth(65)
            btn.setStyleSheet("QPushButton { background: #f8f9fa; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; padding: 2px; }")

            # 闭包绑定解析
            atext = it.get('analysis', '暂无详细解析内容')
            btn.clicked.connect(lambda checked=False, q=qid, t=atext: self._show_single_analysis(q, t))
            row_lay.addWidget(btn)

            if is_cloze and col2:
                if idx % 2 == 0: col1.addWidget(row)
                else: col2.addWidget(row)
            else:
                col1.addWidget(row)

        layout.addStretch()

        # 自动滚回顶部
        panel.verticalScrollBar().setValue(0)

    def _show_single_analysis(self, qid, text):
        """在右侧解析区显示选定题目的解析"""
        clean_text = str(text).replace('\n', '<br>')
        html = f"""
            <div style='background:#fdf6ec; border-left:5px solid #e67e22; padding:15px; border-radius:8px;'>
                <h4 style='color:#e67e22; margin-top:0;'>第 {qid} 题 详解</h4>
                <p style='color:#5d6d7e; line-height:1.6; font-size:14px;'>{clean_text}</p>
            </div>
        """
        self.ui.gk_ai_display.setHtml(html)

    def update_nav_highlight(self):
        """顶部菜单按钮高亮控制"""
        btn_map = {"阅读理解": "gk_btn_reading", "完形填空": "gk_btn_cloze",
                 "语法填空": "gk_btn_grammar", "七选五": "gk_btn_seven_five"}
        for type_name, obj_name in btn_map.items():
            btn = getattr(self.ui, obj_name, None)
            if btn:
                if type_name == self.current_type:
                    btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; font-weight: bold; padding: 5px;")
                else:
                    btn.setStyleSheet("background-color: #f0f0f0; color: #333; border-radius: 5px; padding: 5px;")