# -*- coding: utf-8 -*-
import json
import os
import re
import sys
import traceback
from PySide6 import QtCore, QtWidgets, QtGui
from datetime import datetime

# 🟢 挪到根目录后，直接导入邻居模块，最简单最稳健
from utils import get_resource_path, get_writable_data_path, _normalize_full_width_to_half_width

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

        self._init_ui()
        # 延迟加载
        QtCore.QTimer.singleShot(100, self._load_json_data)

    def _init_ui(self):
        self.setObjectName("word_list_view")
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QtWidgets.QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet("background: #F8F9FA; border-bottom: 1px solid #DEE2E6;")
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(15, 0, 15, 0)

        self.btn_reg = QtWidgets.QPushButton("📚 常规词汇")
        self.btn_mis = QtWidgets.QPushButton("❌ 错词表")

        self.btn_export = QtWidgets.QToolButton()
        self.btn_export.setText("输出 Word 打印单词表")
        self.btn_export.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_export.setFixedHeight(34)
        self.btn_export.setStyleSheet("QToolButton{background:#28A745; color:white; border-radius:4px; font-weight:bold; padding: 0 10px;}")

        self._setup_export_menu()

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("检索词汇...")
        self.search_input.setFixedWidth(150)
        self.search_input.setFixedHeight(34)

        self.btn_toggle_en = QtWidgets.QPushButton("📖 隐藏英语")
        self.btn_toggle_cn = QtWidgets.QPushButton("📝 隐藏中文")

        button_style = """
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 14px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #f3f4f6;
            }
            QPushButton:pressed {
                background-color: #e2e6ea;
            }
            QPushButton:checked {
                background-color: #2196F3;
                color: white;
            }
        """

        for w in [self.btn_reg, self.btn_mis, self.btn_export, self.search_input, self.btn_toggle_en, self.btn_toggle_cn]:
            h_layout.addWidget(w)
            if isinstance(w, QtWidgets.QPushButton):
                w.setCheckable(True)
                w.setFixedHeight(34)
                if w is not self.btn_export:
                    w.setStyleSheet(button_style)

        h_layout.addStretch()
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
        self.btn_prev.setStyleSheet(button_style)
        self.btn_next.setStyleSheet(button_style)
        f_layout.addWidget(self.lbl_page); f_layout.addStretch(); f_layout.addWidget(self.btn_prev); f_layout.addWidget(self.btn_next)
        main_layout.addWidget(footer)

        self.btn_reg.clicked.connect(lambda: self._switch_list("regular"))
        self.btn_mis.clicked.connect(lambda: self._switch_list("mistake"))
        self.btn_toggle_en.clicked.connect(self._toggle_en)
        self.btn_toggle_cn.clicked.connect(self._toggle_cn)
        self.search_input.textChanged.connect(self._handle_search)
        self.btn_prev.clicked.connect(lambda: self._change_page(-1))
        self.btn_next.clicked.connect(lambda: self._change_page(1))

    def _setup_export_menu(self):
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("QMenu::item { padding: 8px 25px; }")

        menu.addAction("常规英语词汇中文+ 英语表").triggered.connect(lambda: self._do_export(self.all_regular_words, "normal", "常规英语词汇_全表"))
        menu.addAction("常规英语词汇看英语填写中文默写表").triggered.connect(lambda: self._do_export(self.all_regular_words, "en_dictate_cn", "常规英语词汇_英默中"))
        menu.addAction("常规英语词汇英语默写表").triggered.connect(lambda: self._do_export(self.all_regular_words, "cn_dictate_en", "常规英语词汇_中默英"))
        menu.addSeparator()
        menu.addAction("错词英语词汇中文+ 英语表").triggered.connect(lambda: self._do_export(self.all_mistake_words, "normal", "错词英语词汇_全表"))
        menu.addAction("错词英语词汇看英语填写中文默写表").triggered.connect(lambda: self._do_export(self.all_mistake_words, "en_dictate_cn", "错词英语词汇_英默中"))
        menu.addAction("错词英语词汇英语默写表").triggered.connect(lambda: self._do_export(self.all_mistake_words, "cn_dictate_en", "错词英语词汇_中默英"))
        menu.addSeparator()
        menu.addAction("自主录入单词全表").triggered.connect(lambda: self._do_export(self._get_self_reg(), "normal", "自主全表"))
        menu.addAction("自主录入-看英默中").triggered.connect(lambda: self._do_export(self._get_self_reg(), "en_dictate_cn", "自主英默中"))
        menu.addAction("自主录入-看中默英").triggered.connect(lambda: self._do_export(self._get_self_reg(), "cn_dictate_en", "自主中默英"))
        menu.addSeparator()
        # New: Phrase List export options
        menu.addAction("短语表 - 中英对照").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self.all_phrases), "normal", "短语表_中英对照", data_type="phrases"))
        menu.addAction("短语表 - 看英默中").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self.all_phrases), "en_dictate_cn", "短语表_看英默中", data_type="phrases"))
        menu.addAction("短语表 - 看中默英").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self.all_phrases), "cn_dictate_en", "短语表_看中默英", data_type="phrases"))
        menu.addSeparator()
        menu.addAction("短语错题表 - 中英对照").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self._get_mistake_phrases()), "normal", "短语错题表_中英对照", data_type="phrases"))
        menu.addAction("短语错题表 - 看英默中").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self._get_mistake_phrases()), "en_dictate_cn", "短语错题表_看英默中", data_type="phrases"))
        menu.addAction("短语错题表 - 看中默英").triggered.connect(lambda: self._do_export(self._prepare_phrase_data(self._get_mistake_phrases()), "cn_dictate_en", "短语错题表_看中默英", data_type="phrases"))
        menu.addSeparator()
        # New: Irregular Verbs List export options
        menu.addAction("不规则动词表 - 过去式过去分词表").triggered.connect(lambda: self._do_export(self._prepare_irregular_data(self.all_irregulars), "normal", "不规则动词表_过去式过去分词表", data_type="irregular_verbs"))
        menu.addAction("不规则动词表 - 看原形默过去式/过去分词").triggered.connect(lambda: self._do_export(self._prepare_irregular_data(self.all_irregulars), "en_dictate_cn", "不规则动词表_看原形默过去式_过去分词", data_type="irregular_verbs"))
        menu.addSeparator()
        menu.addAction("不规则动词错题表 - 过去式过去分词表").triggered.connect(lambda: self._do_export(self._prepare_irregular_data(self._get_mistake_irregulars()), "normal", "不规则动词错题表_过去式过去分词表", data_type="irregular_verbs"))
        menu.addAction("不规则动词错题表 - 看原形默过去式/过去分词").triggered.connect(lambda: self._do_export(self._prepare_irregular_data(self._get_mistake_irregulars()), "en_dictate_cn", "不规则动词错题表_看原形默过去式_过去分词", data_type="irregular_verbs"))

        self.btn_export.setMenu(menu)

    def _load_json_data(self):
        # 🟢 挪到根目录后，直接用 utils 提供的 resource_path 找 assets
        # 加载常规词汇
        json_path = get_resource_path("assets/vocabulary.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.all_regular_words = json.load(f)
                    self.all_regular_words.sort(key=lambda x: (str(x.get('word',''))).lower())
                self._switch_list("regular")
            except Exception as e:
                print(f"DEBUG: 加载常规词汇失败 {e}")
        
        # New: Load phrase data
        phrase_json_path = get_resource_path("assets/short_phrase.json")
        if os.path.exists(phrase_json_path):
            try:
                with open(phrase_json_path, 'r', encoding='utf-8') as f:
                    self.all_phrases = json.load(f)
                    self.all_phrases.sort(key=lambda x: (str(x.get('p',''))).lower()) # Sort by phrase 'p' key
                print(f"✅ 短语表加载成功，共 {len(self.all_phrases)} 词")
            except Exception as e:
                print(f"DEBUG: 加载短语表失败 {e}")
                self.all_phrases = []

        # New: Load irregular verb data
        irregular_json_path = get_resource_path("assets/irregular_verbs.json")
        if os.path.exists(irregular_json_path):
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
            "mistake_phrases.json", "p", "短语错题表"
        )
        return self.all_mistake_phrases

    def _get_mistake_irregulars(self):
        self.all_mistake_irregulars = self._load_writable_json_list(
            "mistake_irregular_verbs.json", "infinitive", "不规则动词错题表"
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
        if self.current_list_type == "mistake":
            self.display_words = self.all_mistake_words.copy()
            self._render_page()

    def _switch_list(self, t):
        self.current_list_type = t
        self.display_words = self.all_regular_words.copy() if t == "regular" else self.all_mistake_words.copy()
        self.current_page = 0
        self.btn_reg.setChecked(t == "regular")
        self.btn_mis.setChecked(t == "mistake")
        self._render_page()

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
        w_lbl.setFont(QtGui.QFont("Arial", 11, QtGui.QFont.Bold))
        w_lbl.setStyleSheet("padding-left: 8px; color: #212529; border-right: 1px solid #F1F3F5;")
        c_lbl = QtWidgets.QLabel(); c_lbl.setWordWrap(True);
        c_lbl.setFont(QtGui.QFont("Microsoft YaHei", 10))
        c_lbl.setStyleSheet("padding-left: 8px; color: #495057;")

        if item is not None:
            idx.setText(f"{num + 1}")
            word = item.get('word') or item.get('english', '')
            trans = item.get('content') or item.get('translation', '')
            w_lbl.setText("" if self.hide_english else str(word))
            c_lbl.setText("" if self.hide_chinese else str(trans))

        layout.addWidget(idx); layout.addWidget(w_lbl); layout.addWidget(c_lbl, 1)
        return row

    def _handle_search(self, text): # No change here, but including for context
        t = text.lower()
        src = self.all_regular_words if self.current_list_type == "regular" else self.all_mistake_words
        self.display_words = [w for w in src if t in (str(w.get('word',''))).lower() or t in (str(w.get('content','')))] if t else src.copy()
        self.current_page = 0; self._render_page()

    def _do_export(self, data, mode, name, data_type="words"):
        if not data:
            QtWidgets.QMessageBox.warning(self, "提示", f"【{name}】目前没有单词数据，无法导出。")
            return
        try:
            # 🟢 现在的位置在根目录，直接导入邻居，打包绝对不会报错
            from word_document_generator import generate_word_table
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出Word", f"{name}.docx", "Word (*.docx)") # No change here
            if path:
                generate_word_table(data, path, mode=mode, data_type=data_type) # Pass data_type
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

    def _toggle_en(self): self.hide_english = not self.hide_english; self._render_page()
    def _toggle_cn(self): self.hide_chinese = not self.hide_chinese; self._render_page()
