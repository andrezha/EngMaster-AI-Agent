# -*- coding: utf-8 -*-
import json
from PySide6 import QtWidgets, QtCore, QtGui
from utils import get_resource_path

# Helper function to clean irregular verb fields
def _clean_verb_field(text):
    if text is None:
        return ""
    # Remove commas, full-width commas, and trim whitespace
    return text.replace(',', '').replace('，', '').strip()


class PhraseIrregularChallengeView(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.phrases = self._load_json("assets/short_phrase.json")
        self.irregulars = self._load_json("assets/irregular_verbs.json")
        self.current_category = "phrase"
        self.active_items = self.phrases
        self.current_index = 0
        self._init_ui()
        self._load_question()

    def _init_ui(self):
        self.setObjectName("phrase_irregular_challenge_view")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(0)

        # 分类切换按钮
        tab_layout = QtWidgets.QHBoxLayout()
        tab_layout.setContentsMargins(40, 0, 40, 0)
        tab_layout.setSpacing(12)
        self.btn_phrase = QtWidgets.QPushButton("短语闯关")
        self.btn_irregular = QtWidgets.QPushButton("不规则动词")
        for button in [self.btn_phrase, self.btn_irregular]:
            button.setCheckable(True)
            button.setFixedSize(140, 36)
            button.setStyleSheet(self._tab_button_style(False))
            tab_layout.addWidget(button)
        self.btn_phrase.clicked.connect(lambda: self._switch_category("phrase"))
        self.btn_irregular.clicked.connect(lambda: self._switch_category("irregular"))
        self.btn_phrase.setChecked(True)
        self.btn_phrase.setStyleSheet(self._tab_button_style(True))
        layout.addLayout(tab_layout)

        # 闯关进度文本
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.status_label.setStyleSheet("font-size: 13px; color: #4b5563; background: transparent; padding: 0; margin: 0;")
        layout.addWidget(self.status_label)

        # 内容容器
        content_frame = QtWidgets.QFrame()
        content_frame.setStyleSheet("background: transparent; border-radius: 16px;")
        content_frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        content_layout = QtWidgets.QVBoxLayout(content_frame)
        content_layout.setContentsMargins(40, 20, 40, 40)
        content_layout.setSpacing(20)
        content_layout.addStretch(1)

        self.prompt_label = QtWidgets.QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setAlignment(QtCore.Qt.AlignCenter)
        self.prompt_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.prompt_label.setMinimumHeight(56)
        self.prompt_label.setStyleSheet(
            "font-family: \"Arial\", \"Microsoft YaHei\"; font-size: 24px; font-weight: bold; color: #111827; line-height: 32px;"
        )
        content_layout.addWidget(self.prompt_label)

        self.instruction_label = QtWidgets.QLabel("")
        self.instruction_label.setAlignment(QtCore.Qt.AlignCenter)
        self.instruction_label.setStyleSheet("font-size: 14px; color: #6b7280; padding-bottom: 6px;")
        content_layout.addWidget(self.instruction_label)

        self.feedback_label = QtWidgets.QLabel("")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(QtCore.Qt.AlignCenter)
        self.feedback_label.setStyleSheet("font-size: 14px; color: #0b6d3a; padding: 8px 0 0 0;")
        content_layout.addWidget(self.feedback_label)

        self.example_label = QtWidgets.QLabel("")
        self.example_label.setWordWrap(True)
        self.example_label.setAlignment(QtCore.Qt.AlignCenter)
        self.example_label.setStyleSheet("font-size: 13px; color: #4b5563; font-weight: bold; padding: 10px 0 0 0;")
        content_layout.addWidget(self.example_label)

        self.answer_input = QtWidgets.QLineEdit()
        self.answer_input.setFixedHeight(38)
        self.answer_input.setFixedWidth(300)
        self.answer_input.setPlaceholderText("请在此输入答案")
        self.answer_input.setStyleSheet(self._input_style())
        self.answer_input.returnPressed.connect(self._check_answer)
        self.answer_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.answer_input, alignment=QtCore.Qt.AlignCenter)

        self.irregular_input_row = QtWidgets.QHBoxLayout()
        self.irregular_input_row.setSpacing(12)
        self.irregular_input_row_widget = QtWidgets.QWidget()
        self.irregular_input_row_widget.setLayout(self.irregular_input_row)

        self.irregular_original_input = QtWidgets.QLineEdit()
        self.irregular_original_input.setFixedHeight(38)
        self.irregular_original_input.setFixedWidth(170)
        self.irregular_original_input.setReadOnly(True)
        self.irregular_original_input.setStyleSheet(self._input_style())
        self.irregular_original_input.setPlaceholderText("原型")
        self.irregular_original_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.irregular_past_input = QtWidgets.QLineEdit()
        self.irregular_past_input.setFixedHeight(38)
        self.irregular_past_input.setFixedWidth(170)
        self.irregular_past_input.setPlaceholderText("过去式")
        self.irregular_past_input.setStyleSheet(self._input_style())
        self.irregular_past_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.irregular_participle_input = QtWidgets.QLineEdit()
        self.irregular_participle_input.setFixedHeight(38)
        self.irregular_participle_input.setFixedWidth(170)
        self.irregular_participle_input.setPlaceholderText("过去分词")
        self.irregular_participle_input.setStyleSheet(self._input_style())
        self.irregular_participle_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.irregular_input_row.addWidget(self.irregular_original_input)
        self.irregular_input_row.addWidget(self.irregular_past_input)
        self.irregular_input_row.addWidget(self.irregular_participle_input)
        content_layout.addWidget(self.irregular_input_row_widget, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        content_layout.addSpacing(20)
        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(12)
        self.btn_check = QtWidgets.QPushButton("确定")
        self.btn_next = QtWidgets.QPushButton("下一题")
        for btn in [self.btn_check, self.btn_next]:
            btn.setFixedSize(140, 42)
            btn.setStyleSheet(self._confirm_button_style())
        self.btn_check.clicked.connect(self._check_answer)
        self.btn_next.clicked.connect(self._next_question)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_check)
        button_row.addWidget(self.btn_next)
        button_row.addStretch(1)
        content_layout.addLayout(button_row)
        content_layout.addStretch(1)

        layout.addWidget(content_frame)

        self.setStyleSheet("background: #f3f4f6;")

    def _load_json(self, path):
        try:
            with open(get_resource_path(path), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _switch_category(self, category):
        self.current_category = category
        self.btn_phrase.setChecked(category == "phrase")
        self.btn_irregular.setChecked(category == "irregular")
        self.btn_phrase.setStyleSheet(self._tab_button_style(category == "phrase"))
        self.btn_irregular.setStyleSheet(self._tab_button_style(category == "irregular"))
        self.active_items = self.phrases if category == "phrase" else self.irregulars
        self.current_index = 0
        self._load_question()

    def _tab_button_style(self, active: bool) -> str:
        if active:
            return (
                "QPushButton { background-color: #2196F3; color: #ffffff; "
                "border: 1px solid #2196F3; border-radius: 8px; font-size: 14px; font-weight: 600; }"
                "QPushButton:hover { background-color: #1976D2; }"
            )
        return (
            "QPushButton { background-color: #ffffff; color: #111827; "
            "border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; }"
            "QPushButton:hover { background-color: #f3f4f6; }"
        )

    def _input_style(self) -> str:
        return (
            "QLineEdit { background-color: #ffffff; border: 1px solid #d1d5db; "
            "border-radius: 10px; padding: 0 14px; font-size: 16px; color: #111827; }"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )

    def _confirm_button_style(self) -> str:
        return (
            "QPushButton { background-color: #2563eb; color: #ffffff; "
            "border: none; border-radius: 10px; font-size: 16px; font-weight: bold; padding: 0 24px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
            "QPushButton:pressed { background-color: #1e40af; }"
        )

    def _load_question(self):
        self.feedback_label.clear()
        self.example_label.clear()
        self.answer_input.clear()
        self.irregular_past_input.clear()
        self.irregular_participle_input.clear()
        if not self.active_items:
            self.prompt_label.setText("暂无可用数据。")
            self.status_label.setText("")
            return

        item = self.active_items[self.current_index % len(self.active_items)]
        total = len(self.active_items)

        if self.current_category == "phrase":
            prompt = item.get("m", "") or item.get("cn", "")
            self.prompt_label.setText(prompt)
            self.instruction_label.setText("请输入对应的英文短语。")
        else:
            self.prompt_label.setText(item.get("meaning", ""))
            self.instruction_label.setText("原型固定，请在右侧分别输入过去式和过去分词。")
            self.irregular_original_input.setText(item.get("infinitive", ""))
            self.irregular_past_input.clear()
            self.irregular_participle_input.clear()
            self.answer_input.hide()
            self.irregular_input_row_widget.show()
            self.example_label.clear()
            self.example_label.hide()

        if self.current_category == "phrase":
            self.answer_input.show()
            self.irregular_input_row_widget.hide()
            self.example_label.show()
        else:
            self.answer_input.hide()
            self.irregular_input_row_widget.show()
            self.example_label.hide()

        self.feedback_label.clear()
        self.status_label.setText(f"第 {self.current_index + 1} / {total} 题 · 当前模式：{'短语' if self.current_category == 'phrase' else '不规则动词'}")

    def _check_answer(self):
        item = self.active_items[self.current_index % len(self.active_items)]
        if self.current_category == "phrase":
            answer = self.answer_input.text().strip().lower()
            if not answer:
                self.feedback_label.setText("请先输入你的答案。")
                self.feedback_label.setStyleSheet("font-size: 13px; color: #bd3d3d;")
                return
            correct_answer = item.get("p", "")
            correct_answer_lower = correct_answer.lower()
            if answer == correct_answer_lower:
                self.feedback_label.setStyleSheet("font-size: 14px; color: #0b6d3a; font-weight: bold;")
                self.feedback_label.setText("回答正确！")
            else:
                self.feedback_label.setStyleSheet("font-size: 14px; color: #dc2626; font-weight: bold;")
                self.feedback_label.setText(f"回答错误。正确答案：{correct_answer}")
            example = item.get("en", "")
            translation = item.get("cn", "")
            self.example_label.setText(f"例句：{example}\n中文：{translation}")
        else:
            past_answer = self.irregular_past_input.text().strip().lower()
            participle_answer = self.irregular_participle_input.text().strip().lower()
            if not past_answer or not participle_answer:
                self.feedback_label.setText("请同时填写过去式和过去分词。")
                self.feedback_label.setStyleSheet("font-size: 13px; color: #bd3d3d;")
                return
            correct_past = item.get("past_tense", "").lower()
            correct_participle = item.get("past_participle", "").lower() # Removed .replace(",", "") as it's now handled by _clean_verb_field
            if past_answer == correct_past and participle_answer == correct_participle:
                self.feedback_label.setStyleSheet("font-size: 14px; color: #0b6d3a; font-weight: bold;")
                self.feedback_label.setText("回答正确！")
            else:
                self.feedback_label.setStyleSheet("font-size: 14px; color: #dc2626; font-weight: bold;")
                self.feedback_label.setText(
                    f"原型：{item.get('infinitive', '')}  过去式：{item.get('past_tense', '')}  过去分词：{item.get('past_participle', '')}"
                )
            self.example_label.clear()
            self.example_label.hide()

    def _next_question(self):
        if not self.active_items:
            return
        self.current_index = (self.current_index + 1) % len(self.active_items)
        self._load_question()

    def _return_to_word_list(self):
        if hasattr(self.main_window, '_safe_nav_to_word_list'):
            self.main_window._safe_nav_to_word_list()


class PhraseIrregularListView(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.phrases = self._load_json("assets/short_phrase.json")
        self.irregulars = self._load_json("assets/irregular_verbs.json")
        self.phrase_col_widths = {}
        self.irregular_col_widths = {}
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("phrase_irregular_list_view")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(12)
        self.btn_phrases_table = QtWidgets.QPushButton("常用短语表")
        self.btn_irregulars_table = QtWidgets.QPushButton("不规则动词表")
        for btn in [self.btn_phrases_table, self.btn_irregulars_table]:
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setStyleSheet(self._tab_button_style(False))
            button_layout.addWidget(btn)
        self.btn_phrases_table.clicked.connect(lambda: self._show_table("phrase"))
        self.btn_irregulars_table.clicked.connect(lambda: self._show_table("irregular"))
        self.btn_phrases_table.setChecked(True)
        self.btn_phrases_table.setStyleSheet(self._tab_button_style(True))
        layout.addLayout(button_layout)
        
        self._calculate_column_widths() # 计算列宽
        self._setup_table_headers() # 设置表头

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border:none; background: transparent;")
        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.table_stack = QtWidgets.QStackedWidget()

        self._setup_table_content() # 设置表格内容

        container_layout.addWidget(self.table_stack)
        self.scroll.setWidget(container)
        layout.addWidget(self.scroll)
        self.setStyleSheet("background: #f3f4f6;")

    def _calculate_column_widths(self):
        # Heuristic: 1 character ~ 8 pixels for Arial 10pt, 1 character ~ 10 pixels for Microsoft YaHei 10pt
        # Add some padding (e.g., 20 pixels)
        
        # Phrase table widths
        max_p_len = 0
        max_m_len = 0
        max_en_len = 0
        max_cn_len = 0
        for item in self.phrases:
            max_p_len = max(max_p_len, len(item.get("p", "")))
            max_m_len = max(max_m_len, len(item.get("m", "")))
            max_en_len = max(max_en_len, len(item.get("en", "")))
            max_cn_len = max(max_cn_len, len(item.get("cn", "")))
        
        self.phrase_col_widths = {
            "p": max(130, max_p_len * 8 + 20), # Min width 130 for phrase
            "m": max(150, max_m_len * 10 + 20), # Min width 150 for meaning
            "en": max(180, max_en_len * 8 + 20), # Min width 180 for English example
            "cn": max(180, max_cn_len * 10 + 20) # Min width 180 for Chinese example
        }

        # Irregular verbs table widths
        max_inf_len = 0
        max_past_len = 0
        max_part_len = 0
        max_meaning_len = 0
        for item in self.irregulars:
            max_inf_len = max(max_inf_len, len(item.get("infinitive", "")))
            max_past_len = max(max_past_len, len(_clean_verb_field(item.get("past_tense", ""))))
            max_part_len = max(max_part_len, len(_clean_verb_field(item.get("past_participle", ""))))
            max_meaning_len = max(max_meaning_len, len(item.get("meaning", "")))
        
        self.irregular_col_widths = { # Removed .replace(",", "") as it's now handled by _clean_verb_field
            "infinitive": max(100, max_inf_len * 8 + 20), # Min width 100
            "past_tense": max(90, max_past_len * 8 + 20), # Min width 90
            "past_participle": max(120, max_part_len * 8 + 20), # Min width 120
            "meaning": max(150, max_meaning_len * 10 + 20) # Min width 150
        }

    def _setup_table_headers(self):
        def _create_single_irregular_header_group(layout, single_group_headers, single_group_widths, is_last_group=False):
            for i, header_text in enumerate(single_group_headers):
                lbl = QtWidgets.QLabel(header_text)
                lbl.setAlignment(QtCore.Qt.AlignCenter if i == 0 else QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                
                style = "font-size: 10px; font-weight: bold; color: #495057;"
                if not is_last_group or (is_last_group and i < len(single_group_headers) - 1):
                    style += " border-right: 1px solid #F1F3F5;"
                
                lbl.setStyleSheet(style)
                lbl.setFixedWidth(single_group_widths[i])
                layout.addWidget(lbl)


        # Phrase table header
        self.phrase_header_frame = QtWidgets.QFrame()
        self.phrase_header_frame.setFixedHeight(30)
        self.phrase_header_frame.setStyleSheet("background: #F8F9FA; border-bottom: 1px solid #DEE2E6;")
        phrase_header_layout = QtWidgets.QHBoxLayout(self.phrase_header_frame)
        phrase_header_layout.setContentsMargins(0, 0, 0, 0)
        phrase_header_layout.setSpacing(0)
        
        headers = ["序号", "短语", "翻译", "英文例句", "中文翻译"] # Updated headers
        widths = [35, self.phrase_col_widths["p"], self.phrase_col_widths["m"], self.phrase_col_widths["en"], self.phrase_col_widths["cn"]] # Updated widths

        for i, header_text in enumerate(headers):
            lbl = QtWidgets.QLabel(header_text)
            lbl.setAlignment(QtCore.Qt.AlignCenter if i == 0 else QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #495057; border-right: 1px solid #F1F3F5;")
            if i == 0: # Index column
                lbl.setFixedWidth(widths[i])
            elif i < len(headers) - 1: # Fixed width for most columns
                lbl.setFixedWidth(widths[i])
            else: # Last column takes remaining space
                lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #495057;") # No right border for last column
                phrase_header_layout.addWidget(lbl, 1)
                continue
            phrase_header_layout.addWidget(lbl)

        # Irregular verbs table header
        self.irregular_header_frame = QtWidgets.QFrame()
        self.irregular_header_frame.setFixedHeight(30)
        self.irregular_header_frame.setStyleSheet("background: #F8F9FA; border-bottom: 1px solid #DEE2E6;")
        irregular_header_layout = QtWidgets.QHBoxLayout(self.irregular_header_frame)
        irregular_header_layout.setContentsMargins(0, 0, 0, 0)
        irregular_header_layout.setSpacing(0)

        single_group_headers = ["序号", "原型", "过去式", "过去分词", "翻译"]
        single_group_widths = [35, self.irregular_col_widths["infinitive"], self.irregular_col_widths["past_tense"], self.irregular_col_widths["past_participle"], self.irregular_col_widths["meaning"]]
        
        # First group of headers
        _create_single_irregular_header_group(irregular_header_layout, single_group_headers, single_group_widths, is_last_group=False)

        # Separator between groups
        separator_lbl = QtWidgets.QLabel("")
        separator_lbl.setFixedWidth(10) # Small fixed width for separator
        separator_lbl.setStyleSheet("border-right: 1px solid #DEE2E6;") # Visual separator
        irregular_header_layout.addWidget(separator_lbl)

        # Second group of headers
        _create_single_irregular_header_group(irregular_header_layout, single_group_headers, single_group_widths, is_last_group=True)

        irregular_header_layout.addStretch(1)

    def _setup_table_content(self):
        # 短语表页面
        phrase_page = QtWidgets.QWidget()
        phrase_layout = QtWidgets.QVBoxLayout(phrase_page)
        phrase_layout.setContentsMargins(0, 0, 0, 0)
        phrase_layout.setSpacing(0)
        phrase_layout.addWidget(self.phrase_header_frame) # Add header
        phrase_scroll_area = QtWidgets.QScrollArea()
        phrase_scroll_area.setWidgetResizable(True)
        phrase_scroll_area.setStyleSheet("border: none; background: white;")
        phrase_container = QtWidgets.QWidget()
        phrase_container_layout = QtWidgets.QVBoxLayout(phrase_container)
        phrase_container_layout.setContentsMargins(0, 0, 0, 0)
        phrase_container_layout.setSpacing(0)
        for idx, item in enumerate(self.phrases):
            row = self._create_phrase_row(item, idx, self.phrase_col_widths)
            phrase_container_layout.addWidget(row)
        phrase_container_layout.addStretch()
        phrase_scroll_area.setWidget(phrase_container)
        phrase_layout.addWidget(phrase_scroll_area)
        self.table_stack.addWidget(phrase_page)

        # 动词表页面
        irregular_page = QtWidgets.QWidget()
        irregular_layout = QtWidgets.QVBoxLayout(irregular_page)
        irregular_layout.setContentsMargins(0, 0, 0, 0)
        irregular_layout.setSpacing(0)
        irregular_layout.addWidget(self.irregular_header_frame) # Add header
        irregular_scroll_area = QtWidgets.QScrollArea()
        irregular_scroll_area.setWidgetResizable(True)
        irregular_scroll_area.setStyleSheet("border: none; background: white;")
        irregular_container = QtWidgets.QWidget()
        irregular_container_layout = QtWidgets.QVBoxLayout(irregular_container)
        irregular_container_layout.setContentsMargins(0, 0, 0, 0)
        irregular_container_layout.setSpacing(0)
        
        # Iterate in steps of 2 for irregular verbs
        for i in range(0, len(self.irregulars), 2):
            item1 = self.irregulars[i]
            item2 = self.irregulars[i+1] if i+1 < len(self.irregulars) else None
            
            row = self._create_irregular_row(item1, item2, i, i+1, self.irregular_col_widths)
            irregular_container_layout.addWidget(row)
        irregular_container_layout.addStretch()
        irregular_scroll_area.setWidget(irregular_container)
        irregular_layout.addWidget(irregular_scroll_area)
        self.table_stack.addWidget(irregular_page)

    def _show_table(self, table_type: str):
        is_phrase = table_type == "phrase"
        self.btn_phrases_table.setChecked(is_phrase)
        self.btn_irregulars_table.setChecked(not is_phrase)
        self.btn_phrases_table.setStyleSheet(self._tab_button_style(is_phrase))
        self.btn_irregulars_table.setStyleSheet(self._tab_button_style(not is_phrase))
        self.table_stack.setCurrentIndex(0 if is_phrase else 1)

    def _create_phrase_row(self, item: dict, idx: int, col_widths: dict) -> QtWidgets.QFrame:
        """创建短语表行：序号、英文、中文"""
        row = QtWidgets.QFrame()
        row.setFixedHeight(54)
        row.setStyleSheet("border-bottom: 1px solid #F1F3F5; background: white;")
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 序号列
        idx_lbl = QtWidgets.QLabel(str(idx + 1))
        idx_lbl.setFixedWidth(35)
        idx_lbl.setAlignment(QtCore.Qt.AlignCenter)
        idx_lbl.setStyleSheet("background: #F8F9FA; color: #ADB5BD; font-size: 10px; font-weight: bold;")

        # 英文列
        p_lbl = QtWidgets.QLabel(item.get("p", ""))
        p_lbl.setFixedWidth(col_widths["p"])
        font = QtGui.QFont("Arial", 11, QtGui.QFont.Bold)
        p_lbl.setFont(font)
        p_lbl.setStyleSheet("padding-left: 8px; color: #212529; border-right: 1px solid #F1F3F5;")

        # 中文列
        m_lbl = QtWidgets.QLabel(item.get("m", ""))
        m_lbl.setWordWrap(True)
        m_lbl.setFixedWidth(col_widths["m"])
        m_font = QtGui.QFont("Microsoft YaHei", 10)
        m_lbl.setFont(m_font)
        m_lbl.setStyleSheet("padding-left: 8px; color: #495057; border-right: 1px solid #F1F3F5;")

        # 英文例句列
        en_example_lbl = QtWidgets.QLabel(item.get("en", ""))
        en_example_lbl.setWordWrap(True)
        en_example_lbl.setFixedWidth(col_widths["en"])
        en_example_lbl.setFont(font)
        en_example_lbl.setStyleSheet("padding-left: 8px; color: #212529; border-right: 1px solid #F1F3F5;")

        # 中文翻译列
        cn_example_lbl = QtWidgets.QLabel(item.get("cn", ""))
        cn_example_lbl.setWordWrap(True)
        cn_example_lbl.setFont(m_font)
        cn_example_lbl.setStyleSheet("padding-left: 8px; color: #495057;") # No right border for the last column

        layout.addWidget(idx_lbl)
        layout.addWidget(p_lbl)
        layout.addWidget(m_lbl)
        layout.addWidget(en_example_lbl)
        layout.addWidget(cn_example_lbl, 1) # This column expands
        return row

    def _create_irregular_row(self, item1: dict, item2: QtCore.QObject | None, idx1: int, idx2: int, col_widths: dict) -> QtWidgets.QFrame:
        """创建动词表行：包含两组不规则动词数据"""
        row = QtWidgets.QFrame()
        row.setFixedHeight(54)
        row.setStyleSheet("border-bottom: 1px solid #F1F3F5; background: white;")
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Helper to create labels for a single irregular verb entry
        def _add_irregular_verb_labels(parent_layout, item, index, is_second_group=False):
            # 序号列
            idx_lbl = QtWidgets.QLabel(str(index + 1) if item else "")
            idx_lbl.setFixedWidth(35)
            idx_lbl.setAlignment(QtCore.Qt.AlignCenter)
            idx_lbl.setStyleSheet("background: #F8F9FA; color: #ADB5BD; font-size: 10px; font-weight: bold;")
            parent_layout.addWidget(idx_lbl)

            # 原型列
            inf_lbl = QtWidgets.QLabel(_clean_verb_field(item.get("infinitive", "")) if item else "")
            inf_lbl.setFixedWidth(col_widths["infinitive"])
            inf_font = QtGui.QFont("Arial", 10, QtGui.QFont.Bold)
            inf_lbl.setFont(inf_font)
            inf_lbl.setStyleSheet("padding-left: 6px; color: #212529; border-right: 1px solid #F1F3F5;")
            parent_layout.addWidget(inf_lbl)

            # 过去式列
            past_lbl = QtWidgets.QLabel(_clean_verb_field(item.get("past_tense", "")) if item else "")
            past_lbl.setFixedWidth(col_widths["past_tense"])
            past_font = QtGui.QFont("Arial", 10, QtGui.QFont.Bold)
            past_lbl.setFont(past_font)
            past_lbl.setStyleSheet("padding-left: 6px; color: #212529; border-right: 1px solid #F1F3F5;")
            parent_layout.addWidget(past_lbl)

            # 过去分词列
            part_lbl = QtWidgets.QLabel(_clean_verb_field(item.get("past_participle", "")) if item else "")
            part_lbl.setFixedWidth(col_widths["past_participle"])
            part_font = QtGui.QFont("Arial", 10, QtGui.QFont.Bold)
            part_lbl.setFont(part_font)
            part_lbl.setStyleSheet("padding-left: 6px; color: #212529; border-right: 1px solid #F1F3F5;")
            parent_layout.addWidget(part_lbl)

            # 中文列（固定宽度以匹配表头）
            meaning_lbl = QtWidgets.QLabel(item.get("meaning", "") if item else "")
            meaning_lbl.setWordWrap(True)
            meaning_lbl.setFixedWidth(col_widths["meaning"]) # Fixed width for meaning
            meaning_font = QtGui.QFont("Microsoft YaHei", 10)
            meaning_lbl.setFont(meaning_font)
            
            # Only add right border if it's not the last column of the entire row
            if not is_second_group: # If it's the first group, its meaning column needs a right border
                meaning_lbl.setStyleSheet("padding-left: 6px; color: #495057; border-right: 1px solid #F1F3F5;")
            else: # If it's the second group, its meaning column does not need a right border
                meaning_lbl.setStyleSheet("padding-left: 6px; color: #495057;")
            parent_layout.addWidget(meaning_lbl)

        # Add first irregular verb entry
        _add_irregular_verb_labels(layout, item1, idx1, is_second_group=False)

        # Add separator between the two groups
        separator_line = QtWidgets.QFrame()
        separator_line.setFrameShape(QtWidgets.QFrame.VLine)
        separator_line.setFrameShadow(QtWidgets.QFrame.Sunken)
        separator_line.setFixedWidth(10) # Match header separator width
        separator_line.setStyleSheet("color: #DEE2E6;")
        layout.addWidget(separator_line)

        # Add second irregular verb entry (if exists)
        _add_irregular_verb_labels(layout, item2, idx2, is_second_group=True)
        
        layout.addStretch(1) # Add stretch at the end of the row

        return row

    def _tab_button_style(self, active: bool) -> str:
        if active:
            return (
                "QPushButton { background-color: #2196F3; color: #ffffff; "
                "border: 1px solid #2196F3; border-radius: 8px; font-size: 14px; font-weight: 600; }"
                "QPushButton:hover { background-color: #1976D2; }"
            )
        return (
            "QPushButton { background-color: #ffffff; color: #111827; "
            "border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; }"
            "QPushButton:hover { background-color: #f3f4f6; }"
        )

    def _load_json(self, path):
        try:
            with open(get_resource_path(path), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _return_to_word_list(self):
        if hasattr(self.main_window, '_safe_nav_to_word_list'):
            self.main_window._safe_nav_to_word_list()
