# -*- coding: utf-8 -*-
import json
import os
import re
import sys
import traceback
import unicodedata
from PySide6 import QtCore, QtWidgets, QtGui
from datetime import datetime

# 🟢 挪到根目录后，直接导入邻居模块，最简单最稳健
from utils import get_resource_path, get_writable_data_path, _normalize_full_width_to_half_width
from ui_styles import CHECKABLE_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, SUCCESS_TOOLBUTTON_STYLE
from edition_config import is_trial_edition


# 完整资料打印暂时封闭；生成代码继续保留，后续需要时可恢复。
FULL_LIST_PRINTING_ENABLED = False


def _normalize_search_text(value):
    """Normalize lookup text without changing the fixed vocabulary data."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return text.strip().casefold()

class WordListView(QtWidgets.QWidget):
    # --- 样式常量 (严格保持原始尺寸) ---
    ROW_HEIGHT = 54
    WORDS_PER_PAGE = 60
    ROWS_PER_PAGE = 20
    COLS = 3
    INDEX_COL_WIDTH = 35
    WORD_COL_WIDTH = 130

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.edition = getattr(main_window, "edition", None)
        self.is_trial = is_trial_edition(self.edition)
        self.word_list_title = (
            self.edition.word_list_title if self.edition is not None
            else "高考3800词汇表"
        )
        self.include_phrase_resources = bool(
            self.edition is None
            or self.edition.page_enabled("phrase_challenge")
            or self.edition.page_enabled("phrase_list")
        )
        self.all_regular_words = []
        self.all_mistake_words = []
        self.display_words = []
        self.all_phrases = []  # New: Store phrase data
        self.all_irregulars = []  # New: Store irregular verb data
        self.all_mistake_phrases = []
        self.all_mistake_irregulars = []

        self.current_list_type = "regular"
        self.current_page = 0
        self.total_pages = 0
        self.hide_english = False
        self.hide_chinese = False
        self.initial_filter = ""

        self._init_ui()
        # 延迟加载
        QtCore.QTimer.singleShot(100, self._load_json_data)

    def _init_ui(self):
        self.setObjectName("word_list_view")
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QtWidgets.QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet("background: #F8F9FA; border-bottom: 1px solid #DEE2E6;")
        header_layout = QtWidgets.QVBoxLayout(header)
        header_layout.setContentsMargins(15, 8, 15, 8)
        header_layout.setSpacing(8)
        self.header_primary_row = QtWidgets.QHBoxLayout()
        self.header_primary_row.setSpacing(9)
        self.header_display_row = QtWidgets.QHBoxLayout()
        self.header_display_row.setSpacing(10)

        self.btn_reg = QtWidgets.QPushButton(self.word_list_title)
        self.btn_mis = QtWidgets.QPushButton("查看单词错词表（0） →")

        self.btn_export = QtWidgets.QToolButton()
        self.btn_export.setText("生成错词打印表  ▼")
        self.btn_export.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_export.setFixedHeight(34)
        self.btn_export.setMinimumWidth(158)
        export_font = QtGui.QFont("Microsoft YaHei UI", 10)
        export_font.setWeight(QtGui.QFont.Weight.DemiBold)
        self.btn_export.setFont(export_font)
        if self.is_trial:
            self.btn_export.setText("体验版打印说明  ▼")
            self.btn_export.setToolTip("打开查看正式版支持的错词打印类型")
            self.btn_export.setStyleSheet("""
                QToolButton {
                    background: #f59e0b; color: white; border: 1px solid #d97706;
                    border-radius: 8px; padding: 0 12px; font-size: 14px;
                }
                QToolButton:hover { background: #d97706; border-color: #b45309; }
                QToolButton:pressed { background: #b45309; }
                QToolButton::menu-indicator { image: none; width: 0; }
            """)
        else:
            self.btn_export.setStyleSheet(SUCCESS_TOOLBUTTON_STYLE)

        self._setup_export_menu()

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("检索单词或释义...")
        self.search_input.setFixedWidth(145)
        self.search_input.setFixedHeight(34)

        self.initial_filter_combo = QtWidgets.QComboBox()
        self.initial_filter_combo.setObjectName("initial_filter_combo")
        self.initial_filter_combo.setFixedSize(205, 36)
        self.initial_filter_combo.setPlaceholderText("选择首字母筛选")
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            self.initial_filter_combo.addItem(
                f"显示 {letter} 字母开头单词", letter.lower())
        self.initial_filter_combo.setCurrentIndex(-1)
        self.initial_filter_combo.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.initial_filter_combo.setStyleSheet("""
            QComboBox { background:white; color:#334155; border:1px solid #cbd5e1;
                border-radius:8px; padding:0 28px 0 10px; font-size:13px; }
            QComboBox:hover { border-color:#3b82f6; }
            QComboBox::drop-down { width:26px; border:none; }
            QComboBox::down-arrow { width:10px; height:10px; }
            QComboBox QAbstractItemView { min-width:205px; }
        """)

        self.btn_show_all_letters = QtWidgets.QPushButton("显示全部")
        self.btn_show_all_letters.setObjectName("btn_show_all_letters")
        self.btn_show_all_letters.setFixedSize(88, 36)
        self.btn_show_all_letters.setCursor(
            QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_show_all_letters.setToolTip("清除字母筛选和检索内容，恢复完整词表")
        self.btn_show_all_letters.setStyleSheet(SECONDARY_BUTTON_STYLE)

        self.btn_show_both = QtWidgets.QPushButton("📚 中英对照")
        self.btn_only_english = QtWidgets.QPushButton("📖 只看英语")
        self.btn_only_chinese = QtWidgets.QPushButton("📝 只看中文")
        self.lbl_filter_status = QtWidgets.QLabel("当前：全部词汇")
        self.lbl_filter_status.setStyleSheet(
            "color:#64748b; font-size:13px; padding-left:8px;")
        self.language_display_group = QtWidgets.QButtonGroup(self)
        self.language_display_group.setExclusive(True)
        for button in [self.btn_show_both, self.btn_only_english, self.btn_only_chinese]:
            button.setCheckable(True)
            self.language_display_group.addButton(button)
        self.btn_show_both.setChecked(True)

        button_style = CHECKABLE_BUTTON_STYLE

        for button in (self.btn_reg, self.btn_mis):
            button.setCheckable(True)
            button.setFixedHeight(34)
            button.setStyleSheet(button_style)
            self.header_primary_row.addWidget(button)
        self.header_primary_row.addWidget(self.search_input)
        self.header_primary_row.addWidget(self.btn_export)
        self.header_primary_row.addStretch()

        for button in (self.btn_show_both, self.btn_only_english, self.btn_only_chinese):
            button.setFixedHeight(36)
            button.setMinimumWidth(112)
            button.setStyleSheet(button_style)
            self.header_display_row.addWidget(button)
        self.header_display_row.addWidget(self.initial_filter_combo)
        self.header_display_row.addWidget(self.btn_show_all_letters)
        self.header_display_row.addWidget(self.lbl_filter_status)
        self.header_display_row.addStretch()
        header_layout.addLayout(self.header_primary_row)
        header_layout.addLayout(self.header_display_row)
        main_layout.addWidget(header)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border:none; background:white;")
        self.container = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

        footer = QtWidgets.QFrame()
        footer.setFixedHeight(40)
        footer.setStyleSheet("background: #F8F9FA; border-top: 1px solid #DEE2E6;")
        f_layout = QtWidgets.QHBoxLayout(footer)
        self.lbl_page = QtWidgets.QLabel("第 1 / 1 页")
        self.btn_prev = QtWidgets.QPushButton("← 上一页")
        self.btn_next = QtWidgets.QPushButton("下一页 →")
        self.btn_prev.setFixedHeight(34)
        self.btn_next.setFixedHeight(34)
        self.btn_prev.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.btn_next.setStyleSheet(SECONDARY_BUTTON_STYLE)
        f_layout.addWidget(self.lbl_page); f_layout.addStretch(); f_layout.addWidget(self.btn_prev); f_layout.addWidget(self.btn_next)
        main_layout.addWidget(footer)

        self.btn_reg.clicked.connect(lambda: self._switch_list("regular"))
        self.btn_mis.clicked.connect(lambda: self._switch_list("mistake"))
        self.btn_show_both.clicked.connect(lambda: self._set_display_mode("both"))
        self.btn_only_english.clicked.connect(lambda: self._set_display_mode("english"))
        self.btn_only_chinese.clicked.connect(lambda: self._set_display_mode("chinese"))
        self.search_input.textChanged.connect(self._handle_search)
        self.initial_filter_combo.currentIndexChanged.connect(
            self._apply_initial_filter)
        self.btn_show_all_letters.clicked.connect(self._show_all_letters)
        self.btn_prev.clicked.connect(lambda: self._change_page(-1))
        self.btn_next.clicked.connect(lambda: self._change_page(1))

    def _update_mistake_button_text(self):
        self.btn_mis.setText(f"查看单词错词表（{len(self.all_mistake_words)}） →")

    def _apply_initial_filter(self, _index=None):
        self.initial_filter = str(self.initial_filter_combo.currentData() or "")
        self._handle_search(self.search_input.text())

    def _show_all_letters(self):
        """Clear every lookup condition so the complete current list is visible."""
        self.initial_filter_combo.setCurrentIndex(-1)
        if self.search_input.text():
            self.search_input.clear()
        else:
            self._handle_search("")

    def _setup_export_menu(self):
        menu = QtWidgets.QMenu(self)
        menu_font = QtGui.QFont("Microsoft YaHei UI", 10)
        menu.setFont(menu_font)
        menu.setStyleSheet(
            'QMenu { font-family: "Microsoft YaHei UI", "Microsoft YaHei"; font-size: 14px; }'
            'QMenu::item { padding: 8px 25px; }'
        )

        export_title = self.word_list_title
        menu.addAction(f"{export_title}打印表").triggered.connect(lambda: self._do_export(self.all_regular_words, "normal", f"{export_title}打印表"))
        menu.addAction(f"{export_title}默写打印表-看英默中").triggered.connect(lambda: self._do_export(self.all_regular_words, "en_dictate_cn", f"{export_title}默写打印表_看英默中"))
        menu.addAction(f"{export_title}默写打印表-看中默英").triggered.connect(lambda: self._do_export(self.all_regular_words, "cn_dictate_en", f"{export_title}默写打印表_看中默英"))
        menu.addSeparator()
        menu.addAction("错词英语词汇打印表").triggered.connect(lambda: self._do_export(self.all_mistake_words, "normal", "错词英语词汇打印表"))
        menu.addAction("错词英语词汇默写打印表-看英默中").triggered.connect(lambda: self._do_export(self.all_mistake_words, "en_dictate_cn", "错词英语词汇默写打印表_看英默中"))
        menu.addAction("错词英语词汇默写打印表-看中默英").triggered.connect(lambda: self._do_export(self.all_mistake_words, "cn_dictate_en", "错词英语词汇默写打印表_看中默英"))
        menu.addSeparator()
        menu.addAction("自主录入单词打印表").triggered.connect(lambda: self._do_export(self._get_self_reg(), "normal", "自主录入单词打印表"))
        menu.addAction("自主录入单词默写打印表-看英默中").triggered.connect(lambda: self._do_export(self._get_self_reg(), "en_dictate_cn", "自主录入单词默写打印表_看英默中"))
        menu.addAction("自主录入单词默写打印表-看中默英").triggered.connect(lambda: self._do_export(self._get_self_reg(), "cn_dictate_en", "自主录入单词默写打印表_看中默英"))
        if self.include_phrase_resources:
            menu.addSeparator()
            menu.addAction("短语打印表").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self.all_phrases), "normal", "短语打印表", data_type="phrases"))
            menu.addAction("短语默写打印表-看英默中").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self.all_phrases), "en_dictate_cn", "短语默写打印表_看英默中", data_type="phrases"))
            menu.addAction("短语默写打印表-看中默英").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self.all_phrases), "cn_dictate_en", "短语默写打印表_看中默英", data_type="phrases"))
            menu.addSeparator()
            menu.addAction("短语错词打印表").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self._get_mistake_phrases()), "normal", "短语错词打印表", data_type="phrases"))
            menu.addAction("短语错词默写打印表-看英默中").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self._get_mistake_phrases()), "en_dictate_cn", "短语错词默写打印表_看英默中", data_type="phrases"))
            menu.addAction("短语错词默写打印表-看中默英").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self._get_mistake_phrases()), "cn_dictate_en", "短语错词默写打印表_看中默英", data_type="phrases"))
            menu.addSeparator()
            menu.addAction("不规则动词打印表").triggered.connect(lambda: self._do_export(self._prepare_irregular_data(self.all_irregulars), "normal", "不规则动词打印表", data_type="irregular_verbs"))
            menu.addAction("不规则动词默写打印表-看原形默过去式/过去分词").triggered.connect(lambda: self._do_export(self._prepare_irregular_data(self.all_irregulars), "en_dictate_cn", "不规则动词默写打印表_看原形默过去式_过去分词", data_type="irregular_verbs"))
            menu.addSeparator()
            menu.addAction("不规则动词错词打印表").triggered.connect(lambda: self._do_export(self._prepare_irregular_data(self._get_mistake_irregulars()), "normal", "不规则动词错词打印表", data_type="irregular_verbs"))
            menu.addAction("不规则动词错词默写打印表-看原形默过去式/过去分词").triggered.connect(lambda: self._do_export(self._prepare_irregular_data(self._get_mistake_irregulars()), "en_dictate_cn", "不规则动词错词默写打印表_看原形默过去式_过去分词", data_type="irregular_verbs"))

        if not FULL_LIST_PRINTING_ENABLED:
            # 仅封住完整资料入口，不删除原有生成实现。
            for action in list(menu.actions()):
                if action.isSeparator():
                    continue
                text = action.text()
                if "错词" not in text and "错题" not in text:
                    menu.removeAction(action)

            # 清除隐藏菜单项后遗留的连续或首尾分隔线。
            previous_was_separator = True
            for action in list(menu.actions()):
                if action.isSeparator():
                    if previous_was_separator:
                        menu.removeAction(action)
                    else:
                        previous_was_separator = True
                else:
                    previous_was_separator = False
            remaining_actions = menu.actions()
            if remaining_actions and remaining_actions[-1].isSeparator():
                menu.removeAction(remaining_actions[-1])

        if self.is_trial:
            # 体验版保留入口用于说明打印范围，但不允许触发任何文件生成。
            printable_actions = [
                action for action in menu.actions() if not action.isSeparator()
            ]
            for action in printable_actions:
                action.setText(f"正式版可打印：{action.text()}")
                action.setEnabled(False)

            self.trial_print_header_label = QtWidgets.QLabel("体验版暂不支持打印")
            self.trial_print_header_label.setContentsMargins(12, 8, 12, 8)
            self.trial_print_header_label.setStyleSheet(
                "color:#b45309; background:#fffbeb; font-size:14px; "
                "font-weight:600; border:1px solid #fde68a; border-radius:6px;"
            )
            self.trial_print_header_action = QtWidgets.QWidgetAction(menu)
            self.trial_print_header_action.setDefaultWidget(
                self.trial_print_header_label)
            first_action = menu.actions()[0] if menu.actions() else None
            if first_action is None:
                menu.addAction(self.trial_print_header_action)
            else:
                menu.insertAction(first_action, self.trial_print_header_action)
                menu.insertSeparator(first_action)

        self.btn_export.setMenu(menu)

    def _load_json_data(self):
        # 🟢 挪到根目录后，直接用 utils 提供的 resource_path 找 assets
        # 加载常规词汇
        vocabulary_path = (
            self.edition.vocabulary_path if self.edition is not None
            else "assets/vocabulary.json"
        )
        json_path = get_resource_path(vocabulary_path)
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.all_regular_words = json.load(f)
                    self.all_regular_words.sort(key=lambda x: (str(x.get('word',''))).lower())
            except Exception as e:
                print(f"DEBUG: 加载常规词汇失败 {e}")
        
        # Phrase resources are only loaded for editions that expose them.
        phrase_path = (
            self.edition.phrase_path if self.edition is not None
            else "assets/short_phrase.json"
        )
        phrase_json_path = get_resource_path(phrase_path)
        if self.include_phrase_resources and os.path.exists(phrase_json_path):
            try:
                with open(phrase_json_path, 'r', encoding='utf-8') as f:
                    self.all_phrases = [
                        item for item in json.load(f)
                        if isinstance(item, dict)
                        and item.get("tier", "core") != "candidate"
                    ]
                    self.all_phrases.sort(key=lambda x: (str(x.get('p',''))).lower()) # Sort by phrase 'p' key
                print(f"✅ 短语表加载成功，共 {len(self.all_phrases)} 词")
            except Exception as e:
                print(f"DEBUG: 加载短语表失败 {e}")
                self.all_phrases = []

        # New: Load irregular verb data
        irregular_path = (
            self.edition.irregular_verbs_path if self.edition is not None
            else "assets/irregular_verbs.json"
        )
        irregular_json_path = get_resource_path(irregular_path)
        if self.include_phrase_resources and os.path.exists(irregular_json_path):
            try:
                with open(irregular_json_path, 'r', encoding='utf-8') as f:
                    self.all_irregulars = json.load(f)
                    self.all_irregulars.sort(key=lambda x: (str(x.get('infinitive',''))).lower()) # Sort by infinitive key
                print(f"✅ 不规则动词表加载成功，共 {len(self.all_irregulars)} 词")
            except Exception as e:
                print(f"DEBUG: 加载不规则动词表失败 {e}")
                self.all_irregulars = []

        # 加载错词表
        mistake_words_path = get_writable_data_path("mistake_words.json")
        if os.path.exists(mistake_words_path):
            try:
                with open(mistake_words_path, 'r', encoding='utf-8') as f:
                    self.all_mistake_words = json.load(f)
                    if self.all_mistake_words:
                        self.all_mistake_words.sort(key=lambda x: (str(x.get('word',''))).lower())
                        print(f"✅ 错词表加载成功，共 {len(self.all_mistake_words)} 词")
            except Exception as e:
                print(f"DEBUG: 加载错词表失败 {e}")
                self.all_mistake_words = []

        # 保留外部跳转已经指定的目标页，不能在延迟初始化完成后强制切回常规词表。
        self._update_mistake_button_text()
        self._switch_list(self.current_list_type)

    def _load_writable_json_list(self, filename, sort_key, label):
        path = get_writable_data_path(filename)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            data = [item for item in data if isinstance(item, dict)]
            data.sort(key=lambda x: str(x.get(sort_key, "")).lower())
            print(f"✅ {label}加载成功，共 {len(data)} 条")
            return data
        except Exception as e:
            print(f"DEBUG: 加载{label}失败 {e}")
            return []

    def _get_mistake_phrases(self):
        self.all_mistake_phrases = self._load_writable_json_list(
            "mistake_phrases.json", "p", "短语错词表"
        )
        return self.all_mistake_phrases

    def _get_mistake_irregulars(self):
        self.all_mistake_irregulars = self._load_writable_json_list(
            "mistake_irregular_verbs.json", "infinitive", "不规则动词错词表"
        )
        return self.all_mistake_irregulars

    def _prepare_phrase_data(self, original_data):
        """
        将短语数据转换为 {"word": "...", "content": "..."} 格式，以便与通用导出函数兼容。
        """
        transformed = []
        for item in original_data:
            transformed.append({
                "word": item.get("p", ""),  # Phrase as 'word'
                "content": item.get("m", "") # Meaning as 'content'
            })
        return transformed

    def _prepare_irregular_data(self, original_data):
        """
        将不规则动词数据转换为 {"word": "...", "content": "..."} 格式。
        'word' 为原型，'content' 为过去式/过去分词/翻译的组合。
        """
        transformed = []
        for item in original_data:
            content_parts = [item.get("past_tense", ""), item.get("past_participle", ""), item.get("meaning", "")]
            transformed.append({"word": item.get("infinitive", ""), "content": " / ".join(filter(None, content_parts))})
        return transformed

    def refresh_mistake_list(self, data):
        self.all_mistake_words = data if isinstance(data, list) else [data] if data else []
        self._update_mistake_button_text()
        if self.current_list_type == "mistake":
            self._handle_search(self.search_input.text())

    def open_mistake_list(self, data=None):
        if data is not None:
            self.refresh_mistake_list(data)
        self.search_input.clear()
        self._switch_list("mistake")

    def _switch_list(self, t):
        self.current_list_type = t
        self.current_page = 0
        self.btn_reg.setChecked(t == "regular")
        self.btn_mis.setChecked(t == "mistake")
        self._handle_search(self.search_input.text())

    def _render_page(self):
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        self.total_pages = max(1, (len(self.display_words) + 59) // 60)
        self.lbl_page.setText(f"第 {self.current_page + 1} / {self.total_pages} 页")
        start_idx = self.current_page * self.WORDS_PER_PAGE
        page_data = self.display_words[start_idx : start_idx + self.WORDS_PER_PAGE]

        container = QtWidgets.QWidget()
        h_layout = QtWidgets.QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        for col in range(self.COLS):
            v_layout = QtWidgets.QVBoxLayout()
            v_layout.setContentsMargins(0, 0, 0, 0); v_layout.setSpacing(0)
            col_data = page_data[col*20 : (col + 1) * 20]
            for i in range(self.ROWS_PER_PAGE):
                if i < len(col_data):
                    v_layout.addWidget(self._create_row(col_data[i], start_idx + col*20 + i))
                else:
                    v_layout.addWidget(self._create_row(None, -1))
            h_layout.addLayout(v_layout)
            if col < 2:
                line = QtWidgets.QFrame(); line.setFrameShape(QtWidgets.QFrame.VLine)
                line.setStyleSheet("color: #DEE2E6;"); h_layout.addWidget(line)
        self.list_layout.addWidget(container)

    def _create_row(self, item, num):
        row = QtWidgets.QFrame(); row.setFixedHeight(self.ROW_HEIGHT)
        row.setStyleSheet("border-bottom: 1px solid #F1F3F5; background: white;")
        layout = QtWidgets.QHBoxLayout(row); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        idx = QtWidgets.QLabel(); idx.setFixedWidth(35); idx.setAlignment(QtCore.Qt.AlignCenter)
        idx.setStyleSheet("background: #F8F9FA; color: #ADB5BD; font-size: 10px; font-weight: bold;")
        w_lbl = QtWidgets.QLabel(); w_lbl.setFixedWidth(130);
        w_lbl.setFont(QtGui.QFont(
            "Microsoft YaHei UI", 11, QtGui.QFont.DemiBold))
        w_lbl.setStyleSheet("padding-left: 8px; color: #212529; border-right: 1px solid #F1F3F5;")
        c_lbl = QtWidgets.QLabel(); c_lbl.setWordWrap(True);
        c_lbl.setFont(QtGui.QFont("Microsoft YaHei UI", 10))
        c_lbl.setStyleSheet("padding-left: 8px; color: #495057;")

        if item is not None:
            idx.setText(f"{num + 1}")
            word = item.get('word') or item.get('english', '')
            trans = item.get('content') or item.get('translation', '')
            w_lbl.setText("" if self.hide_english else str(word))
            c_lbl.setText("" if self.hide_chinese else str(trans))

        layout.addWidget(idx); layout.addWidget(w_lbl); layout.addWidget(c_lbl, 1)
        return row

    def _handle_search(self, text):
        t = _normalize_search_text(text)
        src = self.all_regular_words if self.current_list_type == "regular" else self.all_mistake_words
        if self.initial_filter:
            src = [
                word for word in src
                if _normalize_search_text(word.get('word', '')).startswith(
                    self.initial_filter)
            ]
        self.display_words = [
            word for word in src
            if t in _normalize_search_text(word.get('word', ''))
            or t in _normalize_search_text(word.get('content', ''))
        ] if t else src.copy()
        label = (
            f"{self.initial_filter.upper()} 字母开头单词"
            if self.initial_filter else "全部词汇")
        self.lbl_filter_status.setText(
            f"当前：{label}，共 {len(self.display_words)} 词")
        self.current_page = 0; self._render_page()

    def _do_export(self, data, mode, name, data_type="words"):
        if not data:
            QtWidgets.QMessageBox.warning(self, "提示", f"【{name}】目前没有单词数据，无法导出。")
            return
        try:
            # 🟢 现在的位置在根目录，直接导入邻居，打包绝对不会报错
            from pdf_document_generator import generate_pdf_table
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出PDF", f"{name}.pdf", "PDF (*.pdf)") 
            if path:
                watermark_mode = getattr(self.main_window, "watermark_mode", "licensed")
                document_title = name.replace("_", "-")
                generate_pdf_table(
                    data,
                    path,
                    mode=mode,
                    data_type=data_type,
                    watermark_mode=watermark_mode,
                    document_title=document_title,
                )
                QtWidgets.QMessageBox.information(self, "成功", f"文件已成功保存至：\n{path}")
        except Exception as e:
            error_detail = traceback.format_exc()
            QtWidgets.QMessageBox.critical(self, "导出失败", f"原因：{str(e)}\n\n{error_detail}")

    def _get_self_reg(self):
        ctrl = getattr(self.main_window, 'self_register_vocab_ctrl', None)
        if ctrl:
            data = getattr(ctrl, 'user_vocab_data', [])
            print(f"DEBUG: 获取自主录入数据，共 {len(data)} 词")
            return data
        else:
            print("DEBUG: 自主录入模块未初始化")
            return []

    def _change_page(self, delta):
        new_p = self.current_page + delta
        if 0 <= new_p < self.total_pages:
            self.current_page = new_p
            self._render_page()

    def _set_display_mode(self, mode):
        self.hide_english = mode == "chinese"
        self.hide_chinese = mode == "english"
        self.btn_show_both.setChecked(mode == "both")
        self.btn_only_english.setChecked(mode == "english")
        self.btn_only_chinese.setChecked(mode == "chinese")
        self._render_page()
