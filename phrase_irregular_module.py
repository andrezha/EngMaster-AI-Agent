# -*- coding: utf-8 -*-
import json
from PySide6 import QtWidgets, QtCore, QtGui
from utils import get_resource_path, get_writable_data_path

# Helper function to clean irregular verb fields
def _clean_verb_field(text):
    if text is None:
        return ""
    # Remove commas, full-width commas, and trim whitespace
    return text.replace(',', '').replace('，', '').strip()


class _LegacyPhraseIrregularChallengeView(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.phrases = self._load_json("assets/short_phrase.json")
        self.irregulars = self._load_json("assets/irregular_verbs.json")
        self.phrase_mistake_file_path = get_writable_data_path("mistake_phrases.json")
        self.irregular_mistake_file_path = get_writable_data_path("mistake_irregular_verbs.json")
        self.phrase_mistakes = self._load_mistake_json(self.phrase_mistake_file_path)
        self.irregular_mistakes = self._load_mistake_json(self.irregular_mistake_file_path)
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
        layout.addSpacing(12)

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

    def _load_mistake_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            for item in data:
                if isinstance(item, dict):
                    item.setdefault("correct_count", 0)
            return [item for item in data if isinstance(item, dict)]
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"DEBUG: 加载错题表失败 {path}: {e}")
            return []

    def _save_mistake_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self.main_window, "错误", f"保存错题表失败:\n{e}")
        self._update_mistake_count_labels()

    def _count_label_style(self):
        return (
            "QLabel { color: #777777; font-size: 13px; padding: 4px 8px; "
            "border: 1px solid #cccccc; border-radius: 4px; background-color: #f5f5f5; }"
        )

    def _update_mistake_count_labels(self):
        if hasattr(self, "lbl_phrase_mistake_count"):
            self.lbl_phrase_mistake_count.setText(f"短语错题 ({len(self.phrase_mistakes)} 个)")
        if hasattr(self, "lbl_irregular_mistake_count"):
            self.lbl_irregular_mistake_count.setText(f"不规则动词错题 ({len(self.irregular_mistakes)} 个)")

    def _phrase_key(self, item):
        return str(item.get("p", "")).strip().lower()

    def _irregular_key(self, item):
        return str(item.get("infinitive", "")).strip().lower()

    def _add_or_reset_mistake_item(self, item, data, key_func, save_path):
        key = key_func(item)
        if not key:
            return
        for mistake in data:
            if key_func(mistake) == key:
                mistake["correct_count"] = 0
                self._save_mistake_json(save_path, data)
                return
        new_item = dict(item)
        new_item["correct_count"] = 0
        data.append(new_item)
        self._save_mistake_json(save_path, data)

    def _increment_mistake_correct_count(self, item, data, key_func, save_path):
        key = key_func(item)
        for index, mistake in enumerate(data):
            if key_func(mistake) == key:
                mistake["correct_count"] = int(mistake.get("correct_count", 0)) + 1
                correct_count = mistake["correct_count"]
                removed = correct_count >= 3
                if removed:
                    del data[index]
                self._save_mistake_json(save_path, data)
                return correct_count, removed
        return 0, False

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
            "QPushButton { background-color: #2196F3; color: #ffffff; "
            "border: 1px solid #2196F3; border-radius: 10px; font-size: 16px; font-weight: bold; padding: 0 24px; }"
            "QPushButton:hover { background-color: #1976D2; }"
            "QPushButton:pressed { background-color: #155abe; }"
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


class PhraseIrregularChallengeView(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.phrases = self._load_json("assets/short_phrase.json")
        self.irregulars = self._load_json("assets/irregular_verbs.json")
        self.phrase_mistake_file_path = get_writable_data_path("mistake_phrases.json")
        self.irregular_mistake_file_path = get_writable_data_path("mistake_irregular_verbs.json")
        self.phrase_mistakes = self._load_mistake_json(self.phrase_mistake_file_path)
        self.irregular_mistakes = self._load_mistake_json(self.irregular_mistake_file_path)
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

        tab_layout = QtWidgets.QHBoxLayout()
        tab_layout.setContentsMargins(40, 0, 40, 0)
        tab_layout.setSpacing(12)
        self.btn_phrase = QtWidgets.QPushButton("短语闯关")
        self.btn_phrase_mistake = QtWidgets.QPushButton("短语错词闯关")
        self.btn_irregular = QtWidgets.QPushButton("不规则动词闯关")
        self.btn_irregular_mistake = QtWidgets.QPushButton("不规则动词错词闯关")
        for button in [self.btn_phrase, self.btn_phrase_mistake, self.btn_irregular, self.btn_irregular_mistake]:
            button.setCheckable(True)
            button.setMinimumWidth(140)
            button.setFixedHeight(36)
            tab_layout.addWidget(button)

        self.btn_phrase.clicked.connect(lambda: self._switch_category("phrase"))
        self.btn_phrase_mistake.clicked.connect(lambda: self._switch_category("phrase_mistake"))
        self.btn_irregular.clicked.connect(lambda: self._switch_category("irregular"))
        self.btn_irregular_mistake.clicked.connect(lambda: self._switch_category("irregular_mistake"))

        tab_layout.addSpacing(8)
        self.lbl_phrase_mistake_count = QtWidgets.QLabel()
        self.lbl_irregular_mistake_count = QtWidgets.QLabel()
        for label in [self.lbl_phrase_mistake_count, self.lbl_irregular_mistake_count]:
            label.setStyleSheet(self._count_label_style())
            tab_layout.addWidget(label)
        layout.addLayout(tab_layout)
        layout.addSpacing(12)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.status_label.setStyleSheet("font-size: 13px; color: #4b5563; background: transparent; padding: 0; margin: 0;")
        layout.addWidget(self.status_label)

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
        self.answer_input.setPlaceholderText("请输入答案")
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
        self.irregular_original_input.setPlaceholderText("原形")
        self.irregular_original_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.irregular_past_input = QtWidgets.QLineEdit()
        self.irregular_past_input.setFixedHeight(38)
        self.irregular_past_input.setFixedWidth(170)
        self.irregular_past_input.setPlaceholderText("过去式")
        self.irregular_past_input.setStyleSheet(self._input_style())
        self.irregular_past_input.returnPressed.connect(self._check_answer)
        self.irregular_past_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.irregular_participle_input = QtWidgets.QLineEdit()
        self.irregular_participle_input.setFixedHeight(38)
        self.irregular_participle_input.setFixedWidth(170)
        self.irregular_participle_input.setPlaceholderText("过去分词")
        self.irregular_participle_input.setStyleSheet(self._input_style())
        self.irregular_participle_input.returnPressed.connect(self._check_answer)
        self.irregular_participle_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.irregular_input_row.addWidget(self.irregular_original_input)
        self.irregular_input_row.addWidget(self.irregular_past_input)
        self.irregular_input_row.addWidget(self.irregular_participle_input)
        content_layout.addWidget(self.irregular_input_row_widget, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        content_layout.addSpacing(20)
        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(12)
        self.btn_check = QtWidgets.QPushButton("确认")
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
        self._update_mode_buttons()
        self._update_mistake_count_labels()

    def _load_json(self, path):
        try:
            with open(get_resource_path(path), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _load_mistake_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            for item in data:
                if isinstance(item, dict):
                    item.setdefault("correct_count", 0)
            return [item for item in data if isinstance(item, dict)]
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"DEBUG: 加载错题表失败 {path}: {e}")
            return []

    def _save_mistake_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self.main_window, "错误", f"保存错题表失败:\n{e}")
        self._update_mistake_count_labels()

    def _phrase_key(self, item):
        return str(item.get("p", "")).strip().lower()

    def _irregular_key(self, item):
        return str(item.get("infinitive", "")).strip().lower()

    def _add_or_reset_mistake_item(self, item, data, key_func, save_path):
        key = key_func(item)
        if not key:
            return
        for mistake in data:
            if key_func(mistake) == key:
                mistake["correct_count"] = 0
                self._save_mistake_json(save_path, data)
                return
        new_item = dict(item)
        new_item["correct_count"] = 0
        data.append(new_item)
        self._save_mistake_json(save_path, data)

    def _increment_mistake_correct_count(self, item, data, key_func, save_path):
        key = key_func(item)
        for index, mistake in enumerate(data):
            if key_func(mistake) == key:
                mistake["correct_count"] = int(mistake.get("correct_count", 0)) + 1
                correct_count = mistake["correct_count"]
                removed = correct_count >= 3
                if removed:
                    del data[index]
                self._save_mistake_json(save_path, data)
                return correct_count, removed
        return 0, False

    def _switch_category(self, category):
        if category == "phrase_mistake":
            self.phrase_mistakes = self._load_mistake_json(self.phrase_mistake_file_path)
            if not self.phrase_mistakes:
                QtWidgets.QMessageBox.information(self.main_window, "提示", "短语错词表为空，已切换到短语闯关。")
                category = "phrase"
        elif category == "irregular_mistake":
            self.irregular_mistakes = self._load_mistake_json(self.irregular_mistake_file_path)
            if not self.irregular_mistakes:
                QtWidgets.QMessageBox.information(self.main_window, "提示", "不规则动词错词表为空，已切换到不规则动词闯关。")
                category = "irregular"

        self.current_category = category
        if category == "phrase":
            self.active_items = self.phrases
        elif category == "phrase_mistake":
            self.active_items = self.phrase_mistakes
        elif category == "irregular_mistake":
            self.active_items = self.irregular_mistakes
        else:
            self.active_items = self.irregulars
        self.current_index = 0
        self._update_mode_buttons()
        self._update_mistake_count_labels()
        self._load_question()

    def _update_mode_buttons(self):
        modes = [
            (self.btn_phrase, "phrase"),
            (self.btn_phrase_mistake, "phrase_mistake"),
            (self.btn_irregular, "irregular"),
            (self.btn_irregular_mistake, "irregular_mistake"),
        ]
        for button, mode in modes:
            active = self.current_category == mode
            button.setChecked(active)
            button.setStyleSheet(self._tab_button_style(active))

    def _is_phrase_mode(self):
        return self.current_category in ["phrase", "phrase_mistake"]

    def _update_mistake_count_labels(self):
        if hasattr(self, "lbl_phrase_mistake_count"):
            self.lbl_phrase_mistake_count.setText(f"短语错题 ({len(self.phrase_mistakes)} 个)")
        if hasattr(self, "lbl_irregular_mistake_count"):
            self.lbl_irregular_mistake_count.setText(f"不规则动词错题 ({len(self.irregular_mistakes)} 个)")

    def _load_question(self):
        self.feedback_label.clear()
        self.example_label.clear()
        self.answer_input.clear()
        self.irregular_past_input.clear()
        self.irregular_participle_input.clear()
        if not self.active_items:
            self.prompt_label.setText("暂无可用题目")
            self.instruction_label.setText("")
            self.status_label.setText("")
            return

        item = self.active_items[self.current_index % len(self.active_items)]
        total = len(self.active_items)
        if self._is_phrase_mode():
            self.prompt_label.setText(item.get("m", "") or item.get("cn", ""))
            self.instruction_label.setText("请输入对应的英文短语。")
            self.answer_input.show()
            self.irregular_input_row_widget.hide()
            self.example_label.show()
        else:
            self.prompt_label.setText(item.get("meaning", ""))
            self.instruction_label.setText("原形固定，请填写过去式和过去分词。")
            self.irregular_original_input.setText(item.get("infinitive", ""))
            self.answer_input.hide()
            self.irregular_input_row_widget.show()
            self.example_label.hide()

        mode_name = {
            "phrase": "短语闯关",
            "phrase_mistake": "短语错词闯关",
            "irregular": "不规则动词闯关",
            "irregular_mistake": "不规则动词错词闯关",
        }.get(self.current_category, "")
        self.status_label.setText(f"第 {self.current_index + 1} / {total} 题 · 当前模式：{mode_name}")

    def _check_answer(self):
        if not self.active_items:
            return

        item = self.active_items[self.current_index % len(self.active_items)]
        if self._is_phrase_mode():
            answer = self.answer_input.text().strip().lower()
            if not answer:
                self.feedback_label.setText("请输入答案。")
                self.feedback_label.setStyleSheet("font-size: 13px; color: #bd3d3d;")
                return
            correct_answer = item.get("p", "")
            if answer == correct_answer.lower():
                self.feedback_label.setStyleSheet("font-size: 14px; color: #0b6d3a; font-weight: bold;")
                if self.current_category == "phrase_mistake":
                    count, removed = self._increment_mistake_correct_count(
                        item, self.phrase_mistakes, self._phrase_key, self.phrase_mistake_file_path
                    )
                    self.feedback_label.setText(
                        "回答正确。连续 3 次答对，已从短语错词表删除。"
                        if removed else f"回答正确。连续答对 {count} / 3 次。"
                    )
                else:
                    self.feedback_label.setText("回答正确。")
            else:
                self._add_or_reset_mistake_item(
                    item, self.phrase_mistakes, self._phrase_key, self.phrase_mistake_file_path
                )
                self.feedback_label.setStyleSheet("font-size: 14px; color: #dc2626; font-weight: bold;")
                self.feedback_label.setText(f"回答错误。已加入短语错词表。正确答案：{correct_answer}")
            self.example_label.setText(f"例句：{item.get('en', '')}\n中文：{item.get('cn', '')}")
        else:
            past_answer = self.irregular_past_input.text().strip().lower()
            participle_answer = self.irregular_participle_input.text().strip().lower()
            if not past_answer or not participle_answer:
                self.feedback_label.setText("请同时填写过去式和过去分词。")
                self.feedback_label.setStyleSheet("font-size: 13px; color: #bd3d3d;")
                return
            correct_past = _clean_verb_field(item.get("past_tense", "")).lower()
            correct_participle = _clean_verb_field(item.get("past_participle", "")).lower()
            if past_answer == correct_past and participle_answer == correct_participle:
                self.feedback_label.setStyleSheet("font-size: 14px; color: #0b6d3a; font-weight: bold;")
                if self.current_category == "irregular_mistake":
                    count, removed = self._increment_mistake_correct_count(
                        item, self.irregular_mistakes, self._irregular_key, self.irregular_mistake_file_path
                    )
                    self.feedback_label.setText(
                        "回答正确。连续 3 次答对，已从不规则动词错词表删除。"
                        if removed else f"回答正确。连续答对 {count} / 3 次。"
                    )
                else:
                    self.feedback_label.setText("回答正确。")
            else:
                self._add_or_reset_mistake_item(
                    item, self.irregular_mistakes, self._irregular_key, self.irregular_mistake_file_path
                )
                self.feedback_label.setStyleSheet("font-size: 14px; color: #dc2626; font-weight: bold;")
                self.feedback_label.setText(
                    f"回答错误。已加入不规则动词错词表。原形：{item.get('infinitive', '')}  "
                    f"过去式：{item.get('past_tense', '')}  过去分词：{item.get('past_participle', '')}"
                )
            self.example_label.clear()
            self.example_label.hide()

    def _next_question(self):
        if not self.active_items:
            return
        self.current_index = (self.current_index + 1) % len(self.active_items)
        if self.current_index >= len(self.active_items):
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

    def _count_label_style(self):
        return (
            "QLabel { color: #777777; font-size: 13px; padding: 4px 8px; "
            "border: 1px solid #cccccc; border-radius: 4px; background-color: #f5f5f5; }"
        )

    def _input_style(self) -> str:
        return (
            "QLineEdit { background-color: #ffffff; border: 1px solid #d1d5db; "
            "border-radius: 10px; padding: 0 14px; font-size: 16px; color: #111827; }"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )

    def _confirm_button_style(self) -> str:
        return (
            "QPushButton { background-color: #2196F3; color: #ffffff; "
            "border: 1px solid #2196F3; border-radius: 10px; font-size: 16px; font-weight: bold; padding: 0 24px; }"
            "QPushButton:hover { background-color: #1976D2; }"
            "QPushButton:pressed { background-color: #155abe; }"
        )

    def _return_to_word_list(self):
        if hasattr(self.main_window, '_safe_nav_to_word_list'):
            self.main_window._safe_nav_to_word_list()


class PhraseIrregularListView(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.phrases = self._load_json("assets/short_phrase.json")
        self.irregulars = self._load_json("assets/irregular_verbs.json")
        self.phrase_mistake_file_path = get_writable_data_path("mistake_phrases.json")
        self.irregular_mistake_file_path = get_writable_data_path("mistake_irregular_verbs.json")
        self.phrase_mistakes = self._load_mistake_json(self.phrase_mistake_file_path)
        self.irregular_mistakes = self._load_mistake_json(self.irregular_mistake_file_path)
        self.phrase_col_widths = {}
        self.irregular_col_widths = {}
        self._init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_mistake_tables()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "phrase_table") and self.phrase_table.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self._apply_phrase_column_widths(self.phrase_table))
        if hasattr(self, "phrase_mistake_table") and self.phrase_mistake_table.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self._apply_phrase_column_widths(self.phrase_mistake_table))

    def _init_ui(self):
        self.setObjectName("phrase_irregular_list_view")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(12)
        self.btn_phrases_table = QtWidgets.QPushButton("常用短语表")
        self.btn_phrase_mistake_table = QtWidgets.QPushButton("短语错词表")
        self.btn_irregulars_table = QtWidgets.QPushButton("不规则动词表")
        self.btn_irregular_mistake_table = QtWidgets.QPushButton("不规则动词错词表")
        for btn in [self.btn_phrases_table, self.btn_phrase_mistake_table, self.btn_irregulars_table, self.btn_irregular_mistake_table]:
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setStyleSheet(self._tab_button_style(False))
            button_layout.addWidget(btn)
        self.btn_phrases_table.clicked.connect(lambda: self._show_table("phrase"))
        self.btn_phrase_mistake_table.clicked.connect(lambda: self._show_table("phrase_mistake"))
        self.btn_irregulars_table.clicked.connect(lambda: self._show_table("irregular"))
        self.btn_irregular_mistake_table.clicked.connect(lambda: self._show_table("irregular_mistake"))
        self.btn_phrases_table.setChecked(True)
        self.btn_phrases_table.setStyleSheet(self._tab_button_style(True))
        layout.addLayout(button_layout)
        
        self._calculate_column_widths() # 计算列宽

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
        def _text_width(text: str, font: QtGui.QFont) -> int:
            metrics = QtGui.QFontMetrics(font)
            return metrics.horizontalAdvance(str(text or ""))

        def _bounded_content_width(measured_width: int, padding: int, minimum: int, maximum: int) -> int:
            return max(minimum, min(measured_width + padding, maximum))

        english_font = QtGui.QFont("Arial", 11, QtGui.QFont.Bold)
        chinese_font = QtGui.QFont("Microsoft YaHei", 10)
        
        # Phrase table widths
        max_p_len = 0
        max_m_len = 0
        max_en_len = 0
        max_cn_len = 0
        for item in self.phrases:
            max_p_len = max(max_p_len, _text_width(item.get("p", ""), english_font))
            max_m_len = max(max_m_len, _text_width(item.get("m", ""), chinese_font))
            max_en_len = max(max_en_len, _text_width(item.get("en", ""), english_font))
            max_cn_len = max(max_cn_len, _text_width(item.get("cn", ""), chinese_font))
        
        self.phrase_col_widths = {
            "p": _bounded_content_width(max_p_len, 24, 130, 240),
            "m": _bounded_content_width(max_m_len, 24, 150, 260),
            "en": max(180, max_en_len + 28),
            "cn": _bounded_content_width(max_cn_len, 24, 180, 340)
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

    def _setup_table_content(self):
        # Phrase table page
        phrase_page = QtWidgets.QWidget()
        phrase_layout = QtWidgets.QVBoxLayout(phrase_page)
        phrase_layout.setContentsMargins(0, 0, 0, 0)
        phrase_layout.setSpacing(0)

        self.phrase_table = QtWidgets.QTableWidget(len(self.phrases), 5)
        self.phrase_table.setHorizontalHeaderLabels(["序号", "短语", "翻译", "英文例句", "中文翻译"])
        self.phrase_table.verticalHeader().setVisible(False)
        self.phrase_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.phrase_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.phrase_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.phrase_table.setWordWrap(True)
        self.phrase_table.setFocusPolicy(QtCore.Qt.NoFocus)
        self.phrase_table.setStyleSheet(
            "QTableWidget { background: white; border: none; }"
            "QHeaderView::section { background: #F8F9FA; border: 1px solid #DEE2E6; padding: 4px; font-weight: bold; }"
        )

        for row_idx, item in enumerate(self.phrases):
            self._set_phrase_table_row(row_idx=row_idx, item=item, table=self.phrase_table)

        phrase_header = self.phrase_table.horizontalHeader()
        for column in range(4):
            phrase_header.setSectionResizeMode(column, QtWidgets.QHeaderView.Fixed)
        phrase_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self._apply_phrase_column_widths(self.phrase_table)
        self.phrase_table.resizeRowsToContents()

        phrase_layout.addWidget(self.phrase_table)
        self.table_stack.addWidget(phrase_page)

        # Phrase mistake table page
        phrase_mistake_page = QtWidgets.QWidget()
        phrase_mistake_layout = QtWidgets.QVBoxLayout(phrase_mistake_page)
        phrase_mistake_layout.setContentsMargins(0, 0, 0, 0)
        phrase_mistake_layout.setSpacing(0)

        self.phrase_mistake_table = QtWidgets.QTableWidget(len(self.phrase_mistakes), 5)
        self.phrase_mistake_table.setHorizontalHeaderLabels(["序号", "短语", "翻译", "英文例句", "中文翻译"])
        self.phrase_mistake_table.verticalHeader().setVisible(False)
        self.phrase_mistake_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.phrase_mistake_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.phrase_mistake_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.phrase_mistake_table.setWordWrap(True)
        self.phrase_mistake_table.setFocusPolicy(QtCore.Qt.NoFocus)
        self.phrase_mistake_table.setStyleSheet(
            "QTableWidget { background: white; border: none; }"
            "QHeaderView::section { background: #F8F9FA; border: 1px solid #DEE2E6; padding: 4px; font-weight: bold; }"
        )

        for row_idx, item in enumerate(self.phrase_mistakes):
            self._set_phrase_table_row(row_idx=row_idx, item=item, table=self.phrase_mistake_table)

        phrase_mistake_header = self.phrase_mistake_table.horizontalHeader()
        for column in range(4):
            phrase_mistake_header.setSectionResizeMode(column, QtWidgets.QHeaderView.Fixed)
        phrase_mistake_header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self._apply_phrase_column_widths(self.phrase_mistake_table)
        self.phrase_mistake_table.resizeRowsToContents()

        phrase_mistake_layout.addWidget(self.phrase_mistake_table)
        self.table_stack.addWidget(phrase_mistake_page)

        # Irregular verbs table page
        irregular_page = QtWidgets.QWidget()
        irregular_layout = QtWidgets.QVBoxLayout(irregular_page)
        irregular_layout.setContentsMargins(0, 0, 0, 0)
        irregular_layout.setSpacing(0)

        self.irregular_table = QtWidgets.QTableWidget(len(self.irregulars), 5)
        self.irregular_table.setHorizontalHeaderLabels(["序号", "原型", "过去式", "过去分词", "翻译"])
        self.irregular_table.verticalHeader().setVisible(False)
        self.irregular_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.irregular_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.irregular_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.irregular_table.setWordWrap(True)
        self.irregular_table.setFocusPolicy(QtCore.Qt.NoFocus)
        self.irregular_table.setStyleSheet(
            "QTableWidget { background: white; border: none; }"
            "QHeaderView::section { background: #F8F9FA; border: 1px solid #DEE2E6; padding: 4px; font-weight: bold; }"
        )

        for row_idx, item in enumerate(self.irregulars):
            self._set_irregular_table_row(row_idx, item, self.irregular_table)

        self.irregular_table.setColumnWidth(0, 35)
        self.irregular_table.setColumnWidth(1, self.irregular_col_widths["infinitive"])
        self.irregular_table.setColumnWidth(2, self.irregular_col_widths["past_tense"])
        self.irregular_table.setColumnWidth(3, self.irregular_col_widths["past_participle"])
        self.irregular_table.horizontalHeader().setStretchLastSection(True)
        self.irregular_table.resizeRowsToContents()

        irregular_layout.addWidget(self.irregular_table)
        self.table_stack.addWidget(irregular_page)

        # Irregular verb mistake table page
        irregular_mistake_page = QtWidgets.QWidget()
        irregular_mistake_layout = QtWidgets.QVBoxLayout(irregular_mistake_page)
        irregular_mistake_layout.setContentsMargins(0, 0, 0, 0)
        irregular_mistake_layout.setSpacing(0)

        self.irregular_mistake_table = QtWidgets.QTableWidget(len(self.irregular_mistakes), 5)
        self.irregular_mistake_table.setHorizontalHeaderLabels(["序号", "原形", "过去式", "过去分词", "翻译"])
        self.irregular_mistake_table.verticalHeader().setVisible(False)
        self.irregular_mistake_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.irregular_mistake_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.irregular_mistake_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.irregular_mistake_table.setWordWrap(True)
        self.irregular_mistake_table.setFocusPolicy(QtCore.Qt.NoFocus)
        self.irregular_mistake_table.setStyleSheet(
            "QTableWidget { background: white; border: none; }"
            "QHeaderView::section { background: #F8F9FA; border: 1px solid #DEE2E6; padding: 4px; font-weight: bold; }"
        )

        for row_idx, item in enumerate(self.irregular_mistakes):
            self._set_irregular_table_row(row_idx, item, self.irregular_mistake_table)

        self.irregular_mistake_table.setColumnWidth(0, 35)
        self.irregular_mistake_table.setColumnWidth(1, self.irregular_col_widths["infinitive"])
        self.irregular_mistake_table.setColumnWidth(2, self.irregular_col_widths["past_tense"])
        self.irregular_mistake_table.setColumnWidth(3, self.irregular_col_widths["past_participle"])
        self.irregular_mistake_table.horizontalHeader().setStretchLastSection(True)
        self.irregular_mistake_table.resizeRowsToContents()

        irregular_mistake_layout.addWidget(self.irregular_mistake_table)
        self.table_stack.addWidget(irregular_mistake_page)

    def _apply_phrase_column_widths(self, table=None):
        if table is None:
            if not hasattr(self, "phrase_table"):
                return
            table = self.phrase_table

        table_width = table.viewport().width()
        fixed_width = (
            35
            + self.phrase_col_widths["p"]
            + self.phrase_col_widths["m"]
        )
        min_translation_width = 180
        available_for_example = max(180, table_width - fixed_width - min_translation_width)
        readable_example_width = max(220, int(table_width * 0.24))
        example_width = min(
            self.phrase_col_widths["en"],
            available_for_example,
            readable_example_width
        )

        table.setColumnWidth(0, 35)
        table.setColumnWidth(1, self.phrase_col_widths["p"])
        table.setColumnWidth(2, self.phrase_col_widths["m"])
        table.setColumnWidth(3, example_width)
        table.resizeRowsToContents()

    def _set_phrase_table_row(self, row_idx: int, item: dict, table=None):
        if table is None:
            table = self.phrase_table
        index_item = QtWidgets.QTableWidgetItem(str(row_idx + 1))
        index_item.setTextAlignment(QtCore.Qt.AlignCenter)
        table.setItem(row_idx, 0, index_item)

        phrase_item = QtWidgets.QTableWidgetItem(item.get("p", ""))
        phrase_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setItem(row_idx, 1, phrase_item)

        meaning_item = QtWidgets.QTableWidgetItem(item.get("m", ""))
        meaning_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setItem(row_idx, 2, meaning_item)

        example_item = QtWidgets.QTableWidgetItem(item.get("en", ""))
        example_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setItem(row_idx, 3, example_item)

        translation_item = QtWidgets.QTableWidgetItem(item.get("cn", ""))
        translation_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setItem(row_idx, 4, translation_item)

    def _set_irregular_table_row(self, row_idx: int, item: dict, table=None):
        if table is None:
            table = self.irregular_table
        index_item = QtWidgets.QTableWidgetItem(str(row_idx + 1))
        index_item.setTextAlignment(QtCore.Qt.AlignCenter)
        table.setItem(row_idx, 0, index_item)

        infinitive_item = QtWidgets.QTableWidgetItem(_clean_verb_field(item.get("infinitive", "")))
        infinitive_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setItem(row_idx, 1, infinitive_item)

        past_item = QtWidgets.QTableWidgetItem(_clean_verb_field(item.get("past_tense", "")))
        past_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setItem(row_idx, 2, past_item)

        participle_item = QtWidgets.QTableWidgetItem(_clean_verb_field(item.get("past_participle", "")))
        participle_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setItem(row_idx, 3, participle_item)

        meaning_item = QtWidgets.QTableWidgetItem(item.get("meaning", ""))
        meaning_item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setItem(row_idx, 4, meaning_item)

    def _populate_phrase_table(self, table, items):
        table.setRowCount(len(items))
        for row_idx, item in enumerate(items):
            self._set_phrase_table_row(row_idx=row_idx, item=item, table=table)
        self._apply_phrase_column_widths(table)
        table.resizeRowsToContents()

    def _populate_irregular_table(self, table, items):
        table.setRowCount(len(items))
        for row_idx, item in enumerate(items):
            self._set_irregular_table_row(row_idx, item, table)
        table.setColumnWidth(0, 35)
        table.setColumnWidth(1, self.irregular_col_widths["infinitive"])
        table.setColumnWidth(2, self.irregular_col_widths["past_tense"])
        table.setColumnWidth(3, self.irregular_col_widths["past_participle"])
        table.resizeRowsToContents()

    def refresh_mistake_tables(self):
        self.phrase_mistakes = self._load_mistake_json(self.phrase_mistake_file_path)
        self.irregular_mistakes = self._load_mistake_json(self.irregular_mistake_file_path)
        if hasattr(self, "phrase_mistake_table"):
            self._populate_phrase_table(self.phrase_mistake_table, self.phrase_mistakes)
        if hasattr(self, "irregular_mistake_table"):
            self._populate_irregular_table(self.irregular_mistake_table, self.irregular_mistakes)

    def _show_table(self, table_type: str):
        if table_type in {"phrase_mistake", "irregular_mistake"}:
            self.refresh_mistake_tables()

        self.btn_phrases_table.setChecked(table_type == "phrase")
        self.btn_irregulars_table.setChecked(table_type == "irregular")
        self.btn_phrase_mistake_table.setChecked(table_type == "phrase_mistake")
        self.btn_irregular_mistake_table.setChecked(table_type == "irregular_mistake")

        self.btn_phrases_table.setStyleSheet(self._tab_button_style(table_type == "phrase"))
        self.btn_irregulars_table.setStyleSheet(self._tab_button_style(table_type == "irregular"))
        self.btn_phrase_mistake_table.setStyleSheet(self._tab_button_style(table_type == "phrase_mistake"))
        self.btn_irregular_mistake_table.setStyleSheet(self._tab_button_style(table_type == "irregular_mistake"))

        table_indices = {
            "phrase": 0,
            "phrase_mistake": 1,
            "irregular": 2,
            "irregular_mistake": 3,
        }
        self.table_stack.setCurrentIndex(table_indices.get(table_type, 0))

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

    def _load_mistake_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            for item in data:
                if isinstance(item, dict):
                    item.setdefault("correct_count", 0)
            return [item for item in data if isinstance(item, dict)]
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"DEBUG: 加载错题表失败 {path}: {e}")
            return []

    def _load_json(self, path):
        try:
            with open(get_resource_path(path), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _return_to_word_list(self):
        if hasattr(self.main_window, '_safe_nav_to_word_list'):
            self.main_window._safe_nav_to_word_list()
