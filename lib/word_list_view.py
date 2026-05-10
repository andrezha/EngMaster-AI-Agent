# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/lib/word_list_view.py
import json
import os
import random
import re
import sys
from PySide6 import QtCore, QtWidgets, QtGui
from datetime import datetime
from PySide6.QtPrintSupport import QPrintDialog, QPrinter

# 严格匹配根目录 utils.py 导入 (下划线函数名)
try:
    if hasattr(sys, '_MEIPASS'):
        root_path = sys._MEIPASS
    else:
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    from utils import _normalize_full_width_to_half_width
except ImportError:
    def _normalize_full_width_to_half_width(t):
        if not t: return ""
        return re.sub(r'[\uE000-\uF8FF]', '', str(t)).strip()

class WordListView(QtWidgets.QWidget):
    # --- 布局常量 (坚决不动) ---
    ROW_HEIGHT = 54
    WORDS_PER_PAGE = 60
    ROWS_PER_PAGE = 20
    COLS = 3
    INDEX_COL_WIDTH = 35
    WORD_COL_WIDTH = 125

    # --- 字体规范 (坚决不动) ---
    WORD_FONT_SIZE = 14
    CONTENT_FONT_SIZE = 12
    INDEX_COLOR = "#000000"

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.all_regular_words = []
        self.all_mistake_words = []
        self.display_words = []
        self.current_list_type = "regular"
        self.current_page = 0
        self.total_pages = 0
        self.hide_english = False
        self.hide_chinese = False

        self._init_ui()
        self._load_vocabulary_async()

    def _init_ui(self):
        self.setObjectName("word_list_view")
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 顶部栏 (50px)
        header = QtWidgets.QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet("background: #EEEEEE; border-bottom: 1px solid #E0E0E0;")
        h_layout = QtWidgets.QHBoxLayout(header)
        h_layout.setContentsMargins(15, 5, 15, 5)

        self.btn_reg = QtWidgets.QPushButton("📚 常规词汇")
        self.btn_mis = QtWidgets.QPushButton("❌ 错词表")

        self.print_tool_btn = QtWidgets.QToolButton()
        self.print_tool_btn.setFixedHeight(34)
        self.print_tool_btn.setText("输出Word打印单词表")
        self.print_tool_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.print_tool_btn.setStyleSheet("""
            QToolButton { background: #28a745; color: white; border-radius: 2px; font-weight: bold; font-size: 11px; padding: 0 12px; }
            QToolButton:hover { background: #218838; }
        """)
        self._setup_print_menu()

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("检索...")
        self.search_input.setFixedHeight(34)
        self.search_input.setFixedWidth(150)

        self.toggle_en = QtWidgets.QPushButton("📖 隐藏英语")
        self.toggle_cn = QtWidgets.QPushButton("📝 隐藏中文")

        for w in [self.btn_reg, self.btn_mis, self.print_tool_btn, self.search_input, self.toggle_en, self.toggle_cn]:
            h_layout.addWidget(w)
            if isinstance(w, QtWidgets.QPushButton):
                w.setFixedHeight(34)
                w.setCheckable(True)

        # 信号连接
        self.btn_reg.clicked.connect(lambda: self._switch_list_type("regular"))
        self.btn_mis.clicked.connect(lambda: self._switch_list_type("mistake"))
        self.toggle_en.clicked.connect(self._toggle_en_logic)
        self.toggle_cn.clicked.connect(self._toggle_cn_logic)
        self.search_input.returnPressed.connect(self._handle_search)

        h_layout.addStretch(1)
        main_layout.addWidget(header)

        # 2. 内容区
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: white;")
        self.container = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout(self.container)
        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

        # 3. 底部栏 (40px)
        footer = QtWidgets.QFrame()
        footer.setFixedHeight(40)
        footer.setStyleSheet("background: #EEEEEE; border-top: 1px solid #E0E0E0;")
        f_layout = QtWidgets.QHBoxLayout(footer)
        self.page_lbl = QtWidgets.QLabel("第 1 / 1 页")
        self.page_lbl.setFont(QtGui.QFont("Microsoft YaHei", 11, QtGui.QFont.Bold))
        self.btn_prev = QtWidgets.QPushButton("← 上一页")
        self.btn_next = QtWidgets.QPushButton("下一页 →")
        for b in [self.btn_prev, self.btn_next]: b.setFixedSize(100, 30)
        self.btn_prev.clicked.connect(self._prev_page)
        self.btn_next.clicked.connect(self._next_page)
        f_layout.addWidget(self.page_lbl); f_layout.addStretch(); f_layout.addWidget(self.btn_prev); f_layout.addWidget(self.btn_next)
        main_layout.addWidget(footer)

    def _setup_print_menu(self):
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #DCDFE6; }
            QMenu::item { padding: 6px 25px; font-size: 11px; height: 26px; }
            QMenu::item:selected { background: #2c3e50; color: white; }
            QMenu::separator { height: 1px; background: #E4E7ED; margin: 2px 0; }
        """)

        menu.addAction("常规英语词汇中文+ 英语表").triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "normal", "常规_全表"))
        menu.addAction("常规英语词汇看英语填写中文默写表").triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "en_dictate_cn", "常规_英默中"))
        menu.addAction("常规英语词汇英语默写表").triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "cn_dictate_en", "常规_中默英"))
        menu.addSeparator()
        menu.addAction("错词英语词汇中文+ 英语表").triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "normal", "错词_全表"))
        menu.addAction("错词英语词汇看英语填写中文默写表").triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "en_dictate_cn", "错词_英默中"))
        menu.addAction("错词英语词汇英语默写表").triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "cn_dictate_en", "错词_中默英"))
        menu.addSeparator()
        menu.addAction("自主录入单词表").triggered.connect(lambda: self._generate_word_doc(self._get_self_reg(), "normal", "自主_全表"))
        menu.addAction("自主录入-看英默中").triggered.connect(lambda: self._generate_word_doc(self._get_self_reg(), "en_dictate_cn", "自主_英默中"))
        menu.addAction("自主录入-看中默英").triggered.connect(lambda: self._generate_word_doc(self._get_self_reg(), "cn_dictate_en", "自主_中默英"))
        self.print_tool_btn.setMenu(menu)

    def _create_row(self, data, num):
        row = QtWidgets.QFrame()
        row.setFixedHeight(self.ROW_HEIGHT)
        row.setStyleSheet("border-bottom: 1px solid #E0E0E0; background: white;")
        l = QtWidgets.QHBoxLayout(row)
        l.setContentsMargins(0, 0, 0, 0); l.setSpacing(0)

        idx = QtWidgets.QLabel(f"{num + 1:02d}")
        idx.setFixedWidth(self.INDEX_COL_WIDTH); idx.setAlignment(QtCore.Qt.AlignCenter)
        idx.setStyleSheet(f"background: #E9ECEF; color: {self.INDEX_COLOR}; font-weight: bold; font-size: 11px; border-right: 1px solid #E0E0E0;")

        # 兼容性修复：处理多种可能的 Key 名
        eng = data.get("word") or data.get("english", "")
        w_txt = _normalize_full_width_to_half_width(eng)
        w_lbl = QtWidgets.QLabel("" if self.hide_english else w_txt)
        w_lbl.setFixedWidth(self.WORD_COL_WIDTH); w_lbl.setFont(QtGui.QFont("Arial", self.WORD_FONT_SIZE, QtGui.QFont.Medium))
        w_lbl.setStyleSheet("color: #1A1A1A; border-right: 1px solid #E0E0E0; padding-left: 8px;")

        chn = data.get("content") or data.get("translation", "")
        c_txt = _normalize_full_width_to_half_width(chn)
        c_lbl = QtWidgets.QLabel("" if self.hide_chinese else c_txt)
        c_lbl.setFont(QtGui.QFont("Microsoft YaHei", self.CONTENT_FONT_SIZE)); c_lbl.setWordWrap(True)
        c_lbl.setStyleSheet("color: #444; padding-left: 8px;")

        l.addWidget(idx); l.addWidget(w_lbl); l.addWidget(c_lbl, 1)
        return row

    def _render_page(self):
        # 强制更新总页数逻辑
        self.total_pages = max(1, (len(self.display_words) + 59) // 60)

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        start = self.current_page * 60
        page_words = self.display_words[start:start+60]
        self.page_lbl.setText(f"第 {self.current_page + 1} / {self.total_pages} 页")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < self.total_pages - 1)

        inner = QtWidgets.QWidget()
        grid = QtWidgets.QHBoxLayout(inner)
        grid.setContentsMargins(0,0,0,0); grid.setSpacing(0)
        for c in range(3):
            col = QtWidgets.QVBoxLayout()
            col.setContentsMargins(0,0,0,0); col.setSpacing(0)
            words = page_words[c*20 : (c+1)*20]
            for i in range(20): # 始终迭代 20 次，确保每列都有 20 行
                # 如果有单词数据，则使用单词数据；否则传入空字典，_create_row 会处理为显示空白但带样式的行
                word_data = words[i] if i < len(words) else {} 
                col.addWidget(self._create_row(word_data, start + c*20 + i))
            grid.addLayout(col)
        self.list_layout.addWidget(inner)

    def _load_vocabulary_async(self): QtCore.QTimer.singleShot(50, self._do_load)

    def _do_load(self):
        """[ARCHITECT AUDIT] 增加深度路径审计日志"""
        print("\n" + "="*50)
        print("DEBUG: 开始加载词汇表数据...")
        try:
            if hasattr(sys, '_MEIPASS'):
                base = sys._MEIPASS
                real_dir = os.path.dirname(sys.executable)
            else:
                base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                real_dir = base

            print(f"DEBUG: 根目录检测 -> {real_dir}")

            # 1. 加载内置词库
            path = os.path.normpath(os.path.join(base, "assets", "vocabulary.json"))
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.all_regular_words = json.load(f)
                    self.all_regular_words.sort(key=lambda x: (x.get("word") or "").lower())
                print(f"DEBUG: 常规词库加载成功，共 {len(self.all_regular_words)} 个单词")
            else:
                print(f"ERROR: 常规词库不存在 -> {path}")

            # 2. 加载错词库 (文件名与写入点对齐：mistake_words.json)
            m_path = os.path.normpath(os.path.join(real_dir, "data", "mistake_words.json"))
            print(f"DEBUG: 尝试访问错词路径 -> {m_path}")
            if os.path.exists(m_path):
                with open(m_path, 'r', encoding='utf-8') as f:
                    self.all_mistake_words = json.load(f)
                print(f"DEBUG: 错词库加载成功，共 {len(self.all_mistake_words)} 条记录")
                if self.all_mistake_words:
                    print(f"DEBUG: 错词数据样例 -> {self.all_mistake_words[0]}")
            else:
                print(f"WARNING: 错词文件未找到 -> {m_path}")

            self.display_words = self.all_regular_words.copy()
            self._render_page()
            self.btn_reg.setChecked(True)
            print("="*50 + "\n")
        except Exception as e:
            print(f"CRITICAL: 加载过程中发生崩溃: {str(e)}")

    def refresh_mistake_list(self, data=None):
        """[ARCHITECT AUDIT] 接收外部信号监控，支持 data=None 自动重载"""
        print(f"DEBUG: 外部触发 refresh_mistake_list，携带数据: {data is not None}")

        if data is not None:
            self.all_mistake_words = data
        else:
            # 如果没传 data，主动从磁盘重载一次
            if hasattr(sys, '_MEIPASS'):
                real_dir = os.path.dirname(sys.executable)
            else:
                real_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            m_path = os.path.normpath(os.path.join(real_dir, "data", "mistake_words.json"))
            if os.path.exists(m_path):
                with open(m_path, 'r', encoding='utf-8') as f:
                    self.all_mistake_words = json.load(f)

        if self.current_list_type == "mistake":
            self.display_words = self.all_mistake_words.copy()
            self.current_page = 0
            self._render_page()

    def _switch_list_type(self, ltype):
        """[ARCHITECT AUDIT] 切换逻辑监控"""
        print(f"DEBUG: 用户点击切换 -> {ltype}")
        self.current_list_type = ltype

        if ltype == "regular":
            self.display_words = self.all_regular_words.copy()
        else:
            # 切换到错词表时，主动触发一次刷新逻辑（会重载文件）
            self.refresh_mistake_list()
            self.display_words = self.all_mistake_words.copy()

        print(f"DEBUG: 切换后待显示单词数: {len(self.display_words)}")

        self.current_page = 0
        self._render_page()

    def _toggle_en_logic(self): self.hide_english = self.toggle_en.isChecked(); self._render_page()
    def _toggle_cn_logic(self): self.hide_chinese = self.toggle_cn.isChecked(); self._render_page()

    def _handle_search(self):
        q = self.search_input.text().strip().lower()
        src = self.all_regular_words if self.current_list_type == "regular" else self.all_mistake_words
        self.display_words = [w for w in src if q in (w.get("word") or "").lower() or q in (w.get("content") or "")] if q else src.copy()
        self.current_page = 0; self._render_page()

    def _generate_word_doc(self, data, mode, desc):
        if not data:
            QtWidgets.QMessageBox.warning(self, "提示", "当前列表没有数据，无法导出。")
            return
        from word_document_generator import generate_word_table
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存单词表", f"{desc}_{datetime.now().strftime('%Y%m%d')}.docx", "Word Files (*.docx)")
        if path: generate_word_table(data, path, mode=mode)

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1; self._render_page()
    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1; self._render_page()

    def _get_self_reg(self):
        return getattr(self.main_window.self_register_vocab_ctrl, 'user_vocab_data', [])