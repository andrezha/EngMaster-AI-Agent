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
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_path not in sys.path:
        sys.path.insert(0, root_path)
    from utils import _normalize_full_width_to_half_width
except ImportError:
    def _normalize_full_width_to_half_width(t):
        if not t: return ""
        return re.sub(r'[\uE000-\uF8FF]', '', str(t)).strip()

class WordListView(QtWidgets.QWidget):
    # --- 布局常量：PO 定义的紧凑标准 ---
    ROW_HEIGHT = 54           
    WORDS_PER_PAGE = 60       
    ROWS_PER_PAGE = 20        
    COLS = 3                  
    INDEX_COL_WIDTH = 35      
    WORD_COL_WIDTH = 125      
    
    # --- 字体规范：极致信息密度 ---
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
        
        # 绿色打印按钮
        self.print_tool_btn = QtWidgets.QToolButton()
        self.print_tool_btn.setFixedHeight(34)
        self.print_tool_btn.setText("输出Word打印单词表")
        self.print_tool_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.print_tool_btn.setStyleSheet("""
            QToolButton { background: #28a745; color: white; border-radius: 2px; font-weight: bold; font-size: 11px; padding: 0 12px; }
            QToolButton:hover { background: #218838; }
        """)
        self._setup_print_menu() # 核心复位：一级扁平化 9 选项
        
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
        """
        全量复位方案：严格保持一级扁平化菜单，绝对禁止二级嵌套。
        通过 QSS 强制高度，确保 9 个选项在屏幕内全显。
        """
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: white; border: 1px solid #DCDFE6; }
            QMenu::item { padding: 6px 25px; font-size: 11px; height: 26px; }
            QMenu::item:selected { background: #2c3e50; color: white; }
            QMenu::separator { height: 1px; background: #E4E7ED; margin: 2px 0; }
        """)

        # 第一组：常规
        menu.addAction("常规英语词汇中文+ 英语表").triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "normal", "常规_全表"))
        menu.addAction("常规英语词汇看英语填写中文默写表").triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "en_dictate_cn", "常规_英默中"))
        menu.addAction("常规英语词汇英语默写表").triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "cn_dictate_en", "常规_中默英"))
        
        menu.addSeparator()
        
        # 第二组：错词
        menu.addAction("错词英语词汇中文+ 英语表").triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "normal", "错词_全表"))
        menu.addAction("错词英语词汇看英语填写中文默写表").triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "en_dictate_cn", "错词_英默中"))
        menu.addAction("错词英语词汇英语默写表").triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "cn_dictate_en", "错词_中默英"))
        
        menu.addSeparator()
        
        # 第三组：自主
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
        
        w_txt = _normalize_full_width_to_half_width(data.get("word", ""))
        w_lbl = QtWidgets.QLabel("" if self.hide_english else w_txt)
        w_lbl.setFixedWidth(self.WORD_COL_WIDTH); w_lbl.setFont(QtGui.QFont("Arial", self.WORD_FONT_SIZE, QtGui.QFont.Medium))
        w_lbl.setStyleSheet("color: #1A1A1A; border-right: 1px solid #E0E0E0; padding-left: 8px;")
        
        c_txt = _normalize_full_width_to_half_width(data.get("content", ""))
        c_lbl = QtWidgets.QLabel("" if self.hide_chinese else c_txt)
        c_lbl.setFont(QtGui.QFont("Microsoft YaHei", self.CONTENT_FONT_SIZE)); c_lbl.setWordWrap(True)
        c_lbl.setStyleSheet("color: #444; padding-left: 8px;")
        
        l.addWidget(idx); l.addWidget(w_lbl); l.addWidget(c_lbl, 1)
        return row

    def _render_page(self):
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
            for i, w in enumerate(words):
                col.addWidget(self._create_row(w, start + c*20 + i))
            for _ in range(20 - len(words)):
                s = QtWidgets.QFrame(); s.setFixedHeight(self.ROW_HEIGHT); col.addWidget(s)
            grid.addLayout(col)
        self.list_layout.addWidget(inner)

    def _load_vocabulary_async(self): QtCore.QTimer.singleShot(50, self._do_load)
    def _do_load(self):
        try:
            base = getattr(self.main_window, 'base_path', os.path.dirname(__file__))
            path = os.path.normpath(os.path.join(base, "assets", "vocabulary.json"))
            with open(path, 'r', encoding='utf-8') as f:
                self.all_regular_words = json.load(f)
                self.all_regular_words.sort(key=lambda x: x.get("word", "").lower())
            self.display_words = self.all_regular_words.copy()
            self.total_pages = max(1, (len(self.display_words) + 59) // 60)
            self._render_page(); self.btn_reg.setChecked(True)
        except: pass

    def _switch_list_type(self, ltype):
        self.current_list_type = ltype
        self.display_words = self.all_regular_words.copy() if ltype == "regular" else self.all_mistake_words.copy()
        self.current_page = 0; self.total_pages = max(1, (len(self.display_words) + 59) // 60); self._render_page()

    def _toggle_en_logic(self): self.hide_english = self.toggle_en.isChecked(); self._render_page()
    def _toggle_cn_logic(self): self.hide_chinese = self.toggle_cn.isChecked(); self._render_page()
    def _handle_search(self):
        q = self.search_input.text().strip().lower()
        src = self.all_regular_words if self.current_list_type == "regular" else self.all_mistake_words
        self.display_words = [w for w in src if q in w.get("word", "").lower() or q in w.get("content", "")] if q else src.copy()
        self.current_page = 0; self.total_pages = max(1, (len(self.display_words) + 59) // 60); self._render_page()

    def _generate_word_doc(self, data, mode, desc):
        from word_document_generator import generate_word_table
        if not data: return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存单词表", f"{desc}_{datetime.now().strftime('%Y%m%d')}.docx", "Word Files (*.docx)")
        if path: generate_word_table(data, path, mode=mode)

    def _prev_page(self): self.current_page -= 1; self._render_page()
    def _next_page(self): self.current_page += 1; self._render_page()
    def _get_self_reg(self): return self.main_window.self_register_vocab_ctrl.user_vocab_data if hasattr(self.main_window, 'self_register_vocab_ctrl') else []