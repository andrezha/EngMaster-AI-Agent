"""
词汇表视图模块 - Word List View (扁平化终极版)
=============================================
- 三列布局，每页60词（20行×3列）
- 固定行高48px，纯Label无阴影
- 互斥隐藏功能（透明色隐藏，坐标不变）
- 全库乱序和字母排序
- 异步加载
- 扁平化设计
"""

import json
import os
import random
from PySide6 import QtCore, QtWidgets, QtGui


class WordListView(QtWidgets.QWidget):
    """词汇表视图 - 扁平化表格展示高考3800词"""
    
    # 布局常量
    ROW_HEIGHT = 48           # 每行高度
    WORDS_PER_PAGE = 60       # 每页60个词
    ROWS_PER_PAGE = 20        # 20行
    COLS = 3                  # 3列
    
    # 列宽常量
    INDEX_COL_WIDTH = 50      # 序号列宽
    WORD_COL_WIDTH = 160      # 英文列宽
    
    # 字体常量
    WORD_FONT_SIZE = 20       # 英文单词字体
    CONTENT_FONT_SIZE = 16    # 中文释义字体
    
    # 颜色常量
    BG_COLOR = "#FAFAFA"      # 极浅灰色背景
    CELL_BG = "#FFFFFF"       # 单元格白色背景
    INDEX_BG = "#F0F0F0"      # 序号列背景
    BORDER_COLOR = "#E0E0E0"  # 边框颜色
    WORD_COLOR = "#1A1A1A"    # 近黑色英文
    CONTENT_COLOR = "#444444" # 深灰色中文
    INDEX_COLOR = "#666666"   # 序号颜色
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        # 核心数据
        self.all_words = []          # 全部词汇数据
        self.display_words = []      # 当前显示顺序
        self.current_page = 0        # 当前页码
        self.total_pages = 0         # 总页数
        
        # 显示控制状态（互斥）
        self.hide_english = False    # 隐藏英语
        self.hide_chinese = False    # 隐藏中文
        
        # 排序状态
        self.is_shuffled = False
        
        # 初始化UI
        self._init_ui()
        
        # 异步加载数据
        self._load_vocabulary_async()
    
    def _init_ui(self):
        """初始化界面"""
        self.setObjectName("word_list_view")
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. 顶端控制栏（56px）
        self._create_header(main_layout)
        
        # 2. 词汇列表区域
        self._create_word_list(main_layout)
        
        # 3. 底部分页栏（56px）
        self._create_footer(main_layout)
        
        self.setStyleSheet(f"""
            QWidget#word_list_view {{
                background-color: {self.BG_COLOR};
            }}
        """)
    
    def _create_header(self, parent_layout):
        """创建顶端控制栏（56px）"""
        header_frame = QtWidgets.QFrame()
        header_frame.setFixedHeight(56)
        header_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #EEEEEE;
                border-bottom: 1px solid {self.BORDER_COLOR};
            }}
        """)
        
        header_layout = QtWidgets.QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 8, 15, 8)
        header_layout.setSpacing(12)
        
        # 搜索框
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("输入 A-Z 跳转 或 输入单词搜索...")
        self.search_input.setFixedHeight(40)
        self.search_input.setFont(QtGui.QFont("Microsoft YaHei", 12))
        self.search_input.returnPressed.connect(self._handle_search)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #CCCCCC;
                border-radius: 2px;
                padding: 0 10px;
                font-size: 12px;
                color: #1A1A1A;
            }
            QLineEdit:focus {
                border: 1px solid #888888;
            }
        """)
        header_layout.addWidget(self.search_input, 1)
        
        # 隐藏英语按钮
        self.toggle_english_btn = QtWidgets.QPushButton("📖 隐藏英语")
        self.toggle_english_btn.setFixedHeight(40)
        self.toggle_english_btn.setCheckable(True)
        self.toggle_english_btn.setChecked(False)
        self.toggle_english_btn.clicked.connect(self._toggle_english)
        self._style_toggle_btn(self.toggle_english_btn, False)
        header_layout.addWidget(self.toggle_english_btn)
        
        # 隐藏中文按钮
        self.toggle_chinese_btn = QtWidgets.QPushButton("📝 隐藏中文")
        self.toggle_chinese_btn.setFixedHeight(40)
        self.toggle_chinese_btn.setCheckable(True)
        self.toggle_chinese_btn.setChecked(False)
        self.toggle_chinese_btn.clicked.connect(self._toggle_chinese)
        self._style_toggle_btn(self.toggle_chinese_btn, False)
        header_layout.addWidget(self.toggle_chinese_btn)
        
        # 随机乱序按钮
        self.shuffle_btn = QtWidgets.QPushButton("🔀 随机乱序")
        self.shuffle_btn.setFixedHeight(40)
        self.shuffle_btn.clicked.connect(self._shuffle_words)
        self.shuffle_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 12px;
            }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #333333; }
        """)
        header_layout.addWidget(self.shuffle_btn)
        
        # 字母排序按钮
        self.sort_btn = QtWidgets.QPushButton("🔠 字母排序")
        self.sort_btn.setFixedHeight(40)
        self.sort_btn.clicked.connect(self._sort_words)
        self.sort_btn.setStyleSheet("""
            QPushButton {
                background-color: #777777;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 12px;
            }
            QPushButton:hover { background-color: #666666; }
            QPushButton:pressed { background-color: #555555; }
        """)
        header_layout.addWidget(self.sort_btn)
        
        parent_layout.addWidget(header_frame)
    
    def _style_toggle_btn(self, btn, is_active):
        """设置切换按钮样式"""
        if is_active:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #D32F2F;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 0 12px;
                }
                QPushButton:hover { background-color: #C62828; }
                QPushButton:pressed { background-color: #B71C1C; }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #E0E0E0;
                    color: #555555;
                    border: 1px solid #BDBDBD;
                    border-radius: 2px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 0 12px;
                }
                QPushButton:hover { background-color: #D5D5D5; }
            """)
    
    def _create_word_list(self, parent_layout):
        """创建词汇列表区域"""
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #FAFAFA;
                border: none;
            }
            QScrollBar:vertical {
                background: #E0E0E0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #9E9E9E; }
        """)
        
        self.list_container = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        self.list_layout.setAlignment(QtCore.Qt.AlignTop)
        
        self.scroll_area.setWidget(self.list_container)
        parent_layout.addWidget(self.scroll_area)
    
    def _create_footer(self, parent_layout):
        """创建底部分页栏（56px）"""
        footer_frame = QtWidgets.QFrame()
        footer_frame.setFixedHeight(56)
        footer_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #EEEEEE;
                border-top: 1px solid {self.BORDER_COLOR};
            }}
        """)
        
        footer_layout = QtWidgets.QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(15, 8, 15, 8)
        
        self.page_label = QtWidgets.QLabel("第 1 / 1 页")
        self.page_label.setFont(QtGui.QFont("Microsoft YaHei", 13, QtGui.QFont.Bold))
        self.page_label.setAlignment(QtCore.Qt.AlignCenter)
        self.page_label.setStyleSheet("color: #555555;")
        footer_layout.addWidget(self.page_label)
        
        footer_layout.addStretch()
        
        self.prev_btn = QtWidgets.QPushButton("← 上一页")
        self.prev_btn.setFixedHeight(40)
        self.prev_btn.setFixedWidth(120)
        self.prev_btn.clicked.connect(self._prev_page)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #333333; }
            QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; }
        """)
        footer_layout.addWidget(self.prev_btn)
        
        self.next_btn = QtWidgets.QPushButton("下一页 →")
        self.next_btn.setFixedHeight(40)
        self.next_btn.setFixedWidth(120)
        self.next_btn.clicked.connect(self._next_page)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #333333; }
            QPushButton:disabled { background-color: #BDBDBD; color: #9E9E9E; }
        """)
        footer_layout.addWidget(self.next_btn)
        
        parent_layout.addWidget(footer_frame)
    
    def _load_vocabulary_async(self):
        """异步加载词汇数据"""
        self._show_loading()
        QtCore.QTimer.singleShot(100, self._do_load_vocabulary)
    
    def _do_load_vocabulary(self):
        """执行词汇加载"""
        try:
            if hasattr(self.main_window, 'base_path'):
                vocab_path = os.path.join(self.main_window.base_path, "assets", "vocabulary.json")
            else:
                vocab_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "vocabulary.json")
                vocab_path = os.path.normpath(vocab_path)
            
            if not os.path.exists(vocab_path):
                self._show_error("词汇文件加载失败")
                return
            
            with open(vocab_path, "r", encoding="utf-8") as f:
                self.all_words = json.load(f)
            
            self.all_words.sort(key=lambda x: x.get("word", "").lower())
            self.display_words = self.all_words.copy()
            self.total_pages = (len(self.display_words) + self.WORDS_PER_PAGE - 1) // self.WORDS_PER_PAGE
            self.current_page = 0
            
            self._render_page()
            
        except Exception as e:
            self._show_error(f"加载失败: {str(e)}")
    
    def _show_loading(self):
        self._clear_list()
        label = QtWidgets.QLabel("正在加载词汇表...")
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setFont(QtGui.QFont("Microsoft YaHei", 16))
        label.setStyleSheet("color: #999999; padding: 60px;")
        self.list_layout.addWidget(label)
    
    def _show_error(self, message):
        self._clear_list()
        label = QtWidgets.QLabel(message)
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setFont(QtGui.QFont("Microsoft YaHei", 14))
        label.setStyleSheet("color: #D32F2F; padding: 60px;")
        self.list_layout.addWidget(label)
    
    def _clear_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _render_page(self):
        self._clear_list()
        
        if not self.display_words:
            self._show_error("没有找到匹配的词汇")
            return
        
        start_idx = self.current_page * self.WORDS_PER_PAGE
        end_idx = min(start_idx + self.WORDS_PER_PAGE, len(self.display_words))
        page_words = self.display_words[start_idx:end_idx]
        
        self.page_label.setText(f"第 {self.current_page + 1} / {self.total_pages} 页")
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < self.total_pages - 1)
        
        # 表格容器
        table_widget = QtWidgets.QWidget()
        table_layout = QtWidgets.QHBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)
        
        col_size = self.ROWS_PER_PAGE
        col1 = self._create_column(page_words[0:col_size], start_idx)
        col2 = self._create_column(page_words[col_size:col_size*2], start_idx + col_size)
        col3 = self._create_column(page_words[col_size*2:col_size*3], start_idx + col_size * 2)
        
        table_layout.addWidget(col1, 1)
        table_layout.addWidget(col2, 1)
        table_layout.addWidget(col3, 1)
        
        self.list_layout.addWidget(table_widget)
    
    def _create_column(self, words, start_index):
        column_widget = QtWidgets.QWidget()
        column_layout = QtWidgets.QVBoxLayout(column_widget)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(0)
        
        for i in range(self.ROWS_PER_PAGE):
            if i < len(words):
                row = self._create_row(words[i], start_index + i)
                column_layout.addWidget(row)
            else:
                placeholder = self._create_placeholder_row()
                column_layout.addWidget(placeholder)
        
        return column_widget
    
    def _create_row(self, word_data, index):
        """创建一行（三个Label：序号、英文、中文）"""
        row_frame = QtWidgets.QFrame()
        row_frame.setFixedHeight(self.ROW_HEIGHT)
        row_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.CELL_BG};
                border-bottom: 1px solid {self.BORDER_COLOR};
            }}
            QFrame:hover {{
                background-color: #F5F5F5;
            }}
        """)
        
        row_layout = QtWidgets.QHBoxLayout(row_frame)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        
        # 序号 Label
        index_label = QtWidgets.QLabel(f"{index + 1:02d}")
        index_label.setFixedWidth(self.INDEX_COL_WIDTH)
        index_label.setFont(QtGui.QFont("Arial", 11, QtGui.QFont.Bold))
        index_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.INDEX_BG};
                color: {self.INDEX_COLOR};
                padding-left: 10px;
                border-right: 1px solid {self.BORDER_COLOR};
            }}
        """)
        index_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        row_layout.addWidget(index_label)
        
        # 英文 Label
        word_text = "" if self.hide_english else word_data.get("word", "")
        word_label = QtWidgets.QLabel(word_text)
        word_label.setFixedWidth(self.WORD_COL_WIDTH)
        word_label.setFont(QtGui.QFont("Arial", self.WORD_FONT_SIZE, QtGui.QFont.Bold))
        word_label.setStyleSheet(f"""
            QLabel {{
                color: {self.WORD_COLOR};
                padding-left: 10px;
                border-right: 1px solid {self.BORDER_COLOR};
            }}
        """)
        word_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        row_layout.addWidget(word_label)
        
        # 中文 Label
        content_text = "" if self.hide_chinese else word_data.get("content", "")
        content_label = QtWidgets.QLabel(content_text)
        content_label.setFont(QtGui.QFont("Microsoft YaHei", self.CONTENT_FONT_SIZE))
        content_label.setStyleSheet(f"""
            QLabel {{
                color: {self.CONTENT_COLOR};
                padding-left: 10px;
            }}
        """)
        content_label.setWordWrap(True)
        content_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        row_layout.addWidget(content_label, 1)
        
        return row_frame
    
    def _create_placeholder_row(self):
        row_frame = QtWidgets.QFrame()
        row_frame.setFixedHeight(self.ROW_HEIGHT)
        row_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.CELL_BG};
                border-bottom: 1px solid {self.BORDER_COLOR};
            }}
        """)
        
        row_layout = QtWidgets.QHBoxLayout(row_frame)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        
        index_label = QtWidgets.QLabel("")
        index_label.setFixedWidth(self.INDEX_COL_WIDTH)
        index_label.setStyleSheet(f"""
            QLabel {{
                background-color: {self.INDEX_BG};
                border-right: 1px solid {self.BORDER_COLOR};
            }}
        """)
        row_layout.addWidget(index_label)
        
        word_label = QtWidgets.QLabel("")
        word_label.setFixedWidth(self.WORD_COL_WIDTH)
        word_label.setStyleSheet(f"""
            QLabel {{
                border-right: 1px solid {self.BORDER_COLOR};
            }}
        """)
        row_layout.addWidget(word_label)
        
        content_label = QtWidgets.QLabel("")
        row_layout.addWidget(content_label, 1)
        
        return row_frame
    
    def _handle_search(self):
        query = self.search_input.text().strip().upper()
        
        if not query:
            self.display_words = self.all_words.copy()
            self.current_page = 0
            self.total_pages = (len(self.display_words) + self.WORDS_PER_PAGE - 1) // self.WORDS_PER_PAGE
            self._render_page()
            return
        
        if len(query) == 1 and query.isalpha():
            self._jump_to_letter(query)
        else:
            self._search_words(query.lower())
    
    def _jump_to_letter(self, letter):
        for i, word in enumerate(self.all_words):
            if word.get("word", "").upper().startswith(letter):
                self.display_words = self.all_words.copy()
                self.current_page = i // self.WORDS_PER_PAGE
                self.total_pages = (len(self.display_words) + self.WORDS_PER_PAGE - 1) // self.WORDS_PER_PAGE
                self._render_page()
                return
        QtWidgets.QMessageBox.information(self, "提示", f"没有找到以 '{letter}' 开头的单词")
    
    def _search_words(self, query):
        filtered = [
            word for word in self.all_words
            if query in word.get("word", "").lower() or query in word.get("content", "").lower()
        ]
        self.display_words = filtered
        self.current_page = 0
        self.total_pages = (len(filtered) + self.WORDS_PER_PAGE - 1) // self.WORDS_PER_PAGE if filtered else 1
        self._render_page()
    
    def _toggle_english(self):
        self.hide_english = self.toggle_english_btn.isChecked()
        self._style_toggle_btn(self.toggle_english_btn, self.hide_english)
        
        if self.hide_english and self.hide_chinese:
            self.hide_chinese = False
            self.toggle_chinese_btn.setChecked(False)
            self._style_toggle_btn(self.toggle_chinese_btn, False)
        
        self._render_page()
    
    def _toggle_chinese(self):
        self.hide_chinese = self.toggle_chinese_btn.isChecked()
        self._style_toggle_btn(self.toggle_chinese_btn, self.hide_chinese)
        
        if self.hide_chinese and self.hide_english:
            self.hide_english = False
            self.toggle_english_btn.setChecked(False)
            self._style_toggle_btn(self.toggle_english_btn, False)
        
        self._render_page()
    
    def _shuffle_words(self):
        if not self.display_words:
            return
        random.shuffle(self.display_words)
        self.is_shuffled = True
        self.current_page = 0
        self._render_page()
    
    def _sort_words(self):
        if not self.display_words:
            return
        self.display_words.sort(key=lambda x: x.get("word", "").lower())
        self.is_shuffled = False
        self.current_page = 0
        self._render_page()
    
    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_page()
    
    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._render_page()
    
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Left:
            self._prev_page()
        elif event.key() == QtCore.Qt.Key_Right:
            self._next_page()
        elif event.key() == QtCore.Qt.Key_PageUp:
            self.current_page = max(0, self.current_page - 5)
            self._render_page()
        elif event.key() == QtCore.Qt.Key_PageDown:
            self.current_page = min(self.total_pages - 1, self.current_page + 5)
            self._render_page()
        else:
            super().keyPressEvent(event)