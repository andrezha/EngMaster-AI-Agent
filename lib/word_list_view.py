# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/lib/word_list_view.py
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
import re # Import re for filename cleaning
from PySide6 import QtCore, QtWidgets, QtGui
from datetime import datetime # Import datetime for filename generation
from PySide6.QtPrintSupport import QPrintDialog, QPrinter # Corrected: QPrinter is in QtPrintSupport


class WordListView(QtWidgets.QWidget):
    """词汇表视图 - 扁平化表格展示高考3800词"""
    
    # 布局常量
    ROW_HEIGHT = 64           # 每行高度
    WORDS_PER_PAGE = 60       # 每页60个词
    ROWS_PER_PAGE = 20        # 20行
    COLS = 3                  # 3列
    
    # 列宽常量
    INDEX_COL_WIDTH = 50      # 序号列宽
    WORD_COL_WIDTH = 160      # 英文列宽
    WORD_COL_WIDTH = 200      # 英文列宽
    
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
        self.all_regular_words = []  # 常规词汇数据
        self.all_mistake_words = []  # 错词表数据
        self.display_words = []      # 当前显示顺序 (指向 all_regular_words 或 all_mistake_words)
        self.current_list_type = "regular" # 当前显示的列表类型: "regular" 或 "mistake"
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
        print("DEBUG: WordListView initialized. _trigger_print method should be available.")
    
    def refresh_mistake_list(self):
        """
        刷新错词表数据并重新渲染显示。
        """
        print("DEBUG: WordListView received signal to refresh mistake list.")
        self.all_mistake_words = self._load_mistake_vocabulary_from_file()
        if self.current_list_type == "mistake":
            self._switch_list_type("mistake") # This will re-render the page

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
        
        # 常规词汇按钮
        self.btn_regular_words = QtWidgets.QPushButton("📚 常规词汇")
        self.btn_regular_words.setFixedHeight(40)
        self.btn_regular_words.setCheckable(True)
        self.btn_regular_words.clicked.connect(lambda: self._switch_list_type("regular"))
        header_layout.addWidget(self.btn_regular_words)

        # 错词表按钮
        self.btn_mistake_words = QtWidgets.QPushButton("❌ 错词表")
        self.btn_mistake_words.setFixedHeight(40)
        self.btn_mistake_words.setCheckable(True)
        self.btn_mistake_words.clicked.connect(lambda: self._switch_list_type("mistake"))
        header_layout.addWidget(self.btn_mistake_words)

        # 随机乱序按钮
        self.shuffle_btn = QtWidgets.QPushButton("🔀 随机乱序")
        self.shuffle_btn.setFixedHeight(40)
        self.shuffle_btn.clicked.connect(self._shuffle_words)
        header_layout.addWidget(self.shuffle_btn)
        
        # 字母排序按钮
        self.sort_btn = QtWidgets.QPushButton("🔠 字母排序")
        self.sort_btn.setFixedHeight(40)
        self.sort_btn.clicked.connect(self._sort_words)
        header_layout.addWidget(self.sort_btn)

        # 打印工具按钮 (带下拉菜单)
        self.print_tool_button = QtWidgets.QToolButton() # Corrected: Instantiate QToolButton without text argument
        self.print_tool_button.setFixedHeight(40)
        self.print_tool_button.setPopupMode(QtWidgets.QToolButton.InstantPopup) # 点击立即显示菜单
        self.print_tool_button.setStyleSheet("""
            QToolButton {
                background-color: #28a745 !important; /* Green color, matching vocab_module's print button */
                color: white !important;
                border: none;
                border-radius: 2px;
                font-size: 12px;
                font-weight: bold;
                padding: 0 12px;
            }
            QToolButton:hover { background-color: #218838 !important; } /* Darker green on hover */
            QToolButton:pressed { background-color: #1e7e34 !important; } /* Even darker green on press */
            QToolButton::menu-indicator { image: none; } /* 隐藏菜单指示器 */
        """)
        # Set the actual text for the button after instantiation
        self.print_tool_button.setText("输出Word打印单词表")
        header_layout.addWidget(self.print_tool_button)

        # 创建打印菜单
        print_menu = QtWidgets.QMenu(self)
        
        # 常规英语词汇选项
        action_regular_normal = print_menu.addAction("常规英语词汇中文+ 英语表")
        action_regular_normal.triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "normal", "常规英语词汇中文+英语表"))
        
        action_regular_en_dictate_cn = print_menu.addAction("常规英语词汇看英语填写中文默写表")
        action_regular_en_dictate_cn.triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "en_dictate_cn", "常规英语词汇看英语填写中文默写表"))
        
        action_regular_cn_dictate_en = print_menu.addAction("常规英语词汇英语默写表")
        action_regular_cn_dictate_en.triggered.connect(lambda: self._generate_word_doc(self.all_regular_words, "cn_dictate_en", "常规英语词汇英语默写表"))
        
        print_menu.addSeparator() # 分隔线

        # 错词英语词汇选项
        action_mistake_normal = print_menu.addAction("错词英语词汇中文+ 英语表")
        action_mistake_normal.triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "normal", "错词英语词汇中文+英语表"))
        
        action_mistake_en_dictate_cn = print_menu.addAction("错词英语词汇看英语填写中文默写表")
        action_mistake_en_dictate_cn.triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "en_dictate_cn", "错词英语词汇看英语填写中文默写表"))
        
        action_mistake_cn_dictate_en = print_menu.addAction("错词英语词汇英语默写表")
        action_mistake_cn_dictate_en.triggered.connect(lambda: self._generate_word_doc(self.all_mistake_words, "cn_dictate_en", "错词英语词汇英语默写表"))
        self.print_tool_button.setMenu(print_menu)

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
        header_layout.addWidget(self.search_input)
        
        # 隐藏英语按钮
        self.toggle_english_btn = QtWidgets.QPushButton("📖 隐藏英语")
        self.toggle_english_btn.setFixedHeight(40)
        self.toggle_english_btn.setCheckable(True)
        self.toggle_english_btn.setChecked(False)
        self.toggle_english_btn.clicked.connect(self._toggle_english)
        self._style_toggle_btn(self.toggle_english_btn, False) # Initial style
        header_layout.addWidget(self.toggle_english_btn)
        
        # 隐藏中文按钮
        self.toggle_chinese_btn = QtWidgets.QPushButton("📝 隐藏中文")
        self.toggle_chinese_btn.setFixedHeight(40)
        self.toggle_chinese_btn.setCheckable(True)
        self.toggle_chinese_btn.setChecked(False)
        self.toggle_chinese_btn.clicked.connect(self._toggle_chinese)
        self._style_toggle_btn(self.toggle_chinese_btn, False) # Initial style
        header_layout.addWidget(self.toggle_chinese_btn)
        
        header_layout.addStretch(1) # Push everything to the left
        
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
    
    def _load_regular_vocabulary_from_file(self):
        """从文件加载常规词汇表"""
        try:
            if hasattr(self.main_window, 'base_path'):
                vocab_path = os.path.join(self.main_window.base_path, "assets", "vocabulary.json")
            else:
                vocab_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "vocabulary.json")
                vocab_path = os.path.normpath(vocab_path)

            if not os.path.exists(vocab_path):
                print(f"ERROR: Regular vocabulary file not found: {vocab_path}")
                return []

            with open(vocab_path, "r", encoding="utf-8") as f:
                words = json.load(f)
            words.sort(key=lambda x: x.get("word", "").lower())
            print(f"✅ 常规词汇表加载成功，共 {len(words)} 词。")
            return words
        except Exception as e:
            print(f"❌ 加载常规词汇表失败: {e}")
            QtWidgets.QMessageBox.warning(self.main_window, "错误", f"加载常规词汇表失败: {e}\n请检查 assets/vocabulary.json 文件。")
            return []

    def _load_mistake_vocabulary_from_file(self):
        """从文件加载错词表"""
        try:
            if hasattr(self.main_window, 'base_path'):
                mistake_vocab_path = os.path.join(self.main_window.base_path, "assets", "mistake_words.json")
            else:
                mistake_vocab_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "mistake_words.json")
                mistake_vocab_path = os.path.normpath(mistake_vocab_path)

            if os.path.exists(mistake_vocab_path):
                with open(mistake_vocab_path, "r", encoding="utf-8") as f:
                    mistake_words = json.load(f)
                print(f"✅ 错词表加载成功，共 {len(mistake_words)} 词。")
                if not mistake_words:
                    print("💡 WordListView: 错词表文件存在但为空，已添加测试词汇。")
                    self._add_test_mistake_words_if_empty(mistake_vocab_path)
                    # 重新加载文件以获取新添加的测试词汇
                    with open(mistake_vocab_path, "r", encoding="utf-8") as f:
                        mistake_words = json.load(f)
                return mistake_words
            else:
                print("💡 错词表文件不存在，返回空列表。")
                print("💡 WordListView: 错词表文件不存在，已创建并添加测试词汇。")
                self._add_test_mistake_words_if_empty(mistake_vocab_path)
                # 重新加载文件以获取新添加的测试词汇
                with open(mistake_vocab_path, "r", encoding="utf-8") as f: # Re-open to read the newly added test words
                    mistake_words = json.load(f)
                return mistake_words
        except json.JSONDecodeError:
            print(f"❌ WordListView: 错词表文件 {mistake_vocab_path} 格式错误，已重置并添加测试词汇。")
            QtWidgets.QMessageBox.warning(self.main_window, "错误", f"错词表文件 {mistake_vocab_path} 格式错误，已重置。")
            self._add_test_mistake_words_if_empty(mistake_vocab_path)
            # 重新加载文件以获取新添加的测试词汇
            with open(mistake_vocab_path, "r", encoding="utf-8") as f:
                mistake_words = json.load(f)
            return mistake_words
        except Exception as e:
            print(f"❌ 加载错词表失败: {e}")
            QtWidgets.QMessageBox.warning(self.main_window, "错误", f"加载错词表失败: {e}\n请检查 assets/mistake_words.json 文件。")
            print("💡 WordListView: 加载错词表失败，已尝试添加测试词汇。")
            self._add_test_mistake_words_if_empty(mistake_vocab_path)
            # 重新加载文件以获取新添加的测试词汇
            with open(mistake_vocab_path, "r", encoding="utf-8") as f:
                mistake_words = json.load(f)
            return mistake_words

    def _add_test_mistake_words_if_empty(self, file_path):
        """
        如果错词表为空，添加几个测试用的错词到错词表文件。
        """
        test_words = [
            {"word": "test1", "content": "测试词汇1", "correct_count": 0},
            {"word": "example", "content": "例子", "correct_count": 0},
            {"word": "debug", "content": "调试", "correct_count": 0}
        ]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(test_words, f, ensure_ascii=False, indent=4)
        print(f"✅ WordListView: 测试错词已保存到 {file_path}。")

    def _do_load_vocabulary(self):
        """执行词汇加载，同时加载常规词汇和错词表"""
        self.all_regular_words = self._load_regular_vocabulary_from_file()
        self.all_mistake_words = self._load_mistake_vocabulary_from_file()
        
        # 初始显示常规词汇
        self._switch_list_type(self.current_list_type)

    def _switch_list_type(self, list_type):
        """切换显示的词汇列表类型"""
        self.current_list_type = list_type
        if list_type == "regular":
            self.display_words = self.all_regular_words.copy()
        elif list_type == "mistake":
            self.display_words = self.all_mistake_words.copy()
        
        self.current_page = 0
        self.total_pages = (len(self.display_words) + self.WORDS_PER_PAGE - 1) // self.WORDS_PER_PAGE if self.display_words else 1
        
        self._render_page()
        self._update_list_type_buttons_style()
    
    def _show_loading(self):
        self._clear_list()
        label = QtWidgets.QLabel("正在加载词汇列表...")
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
        self.list_layout.addStretch(1) # 添加弹性空间，将错误信息推到顶部
    
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
        col1 = self._create_column(page_words[0:col_size], start_idx) # First column
        col2 = self._create_column(page_words[col_size:col_size*2], start_idx + col_size) # Second column
        col3 = self._create_column(page_words[col_size*2:col_size*3], start_idx + col_size * 2) # Third column
        
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
        index_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
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
        word_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
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
        content_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
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
        """处理搜索功能"""
        query = self.search_input.text().strip().upper()
        
        if not query:
            # 如果搜索框为空，则恢复当前列表类型的完整词汇
            if self.current_list_type == "regular":
                self.display_words = self.all_regular_words.copy()
            else: # mistake
                self.display_words = self.all_mistake_words.copy()

            self.current_page = 0
            self.total_pages = (len(self.display_words) + self.WORDS_PER_PAGE - 1) // self.WORDS_PER_PAGE
            self._render_page()
            return
        
        # 搜索始终在当前活动的完整词汇列表（all_regular_words 或 all_mistake_words）中进行
        source_list = self.all_regular_words if self.current_list_type == "regular" else self.all_mistake_words
        
        if len(query) == 1 and query.isalpha():
            self._jump_to_letter(query, source_list)
        else:
            self._search_words(query.lower(), source_list)

    def _jump_to_letter(self, letter, source_list):
        """跳转到以指定字母开头的单词"""
        for i, word in enumerate(source_list):
            if word.get("word", "").upper().startswith(letter):
                self.display_words = source_list.copy() # 确保显示的是完整列表，只是跳转页码
                self.current_page = i // self.WORDS_PER_PAGE
                self.total_pages = (len(self.display_words) + self.WORDS_PER_PAGE - 1) // self.WORDS_PER_PAGE
                self._render_page()
                return
        # 如果没有找到以指定字母开头的单词，则清空显示列表，并重新渲染页面以显示错误信息
        self.display_words = []
        self._render_page()
    
    def _search_words(self, query, source_list):
        filtered = [
            word for word in source_list
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
        self._update_list_type_buttons_style() # 乱序后更新按钮样式
    
    def _sort_words(self):
        if not self.display_words:
            return
        self.display_words.sort(key=lambda x: x.get("word", "").lower())
        self.is_shuffled = False
        self.current_page = 0
        self._render_page() # 排序后更新按钮样式
        self._update_list_type_buttons_style()

    def _update_list_type_buttons_style(self):
        """更新常规词汇和错词表按钮的样式"""
        active_style = "background-color: #007bff; color: white; border: none; border-radius: 2px; font-size: 12px; font-weight: bold; padding: 0 12px;"
        inactive_style = "background-color: #e0e0e0; color: #555555; border: 1px solid #BDBDBD; border-radius: 2px; font-size: 12px; font-weight: bold; padding: 0 12px;"

        if self.btn_regular_words:
            self.btn_regular_words.setStyleSheet(active_style if self.current_list_type == "regular" else inactive_style) # Apply style
            self.btn_regular_words.setChecked(self.current_list_type == "regular") # Set checked state
        if self.btn_mistake_words:
            self.btn_mistake_words.setStyleSheet(active_style if self.current_list_type == "mistake" else inactive_style) # Apply style
            self.btn_mistake_words.setChecked(self.current_list_type == "mistake") # Set checked state
    
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

    def _print_current_page(self):
        """打印当前页的词汇。"""
        if not self.display_words: # If no words to display at all
            QtWidgets.QMessageBox.information(self, "提示", "没有词汇可供打印。")
            return
        
        start_idx = self.current_page * self.WORDS_PER_PAGE
        end_idx = min(start_idx + self.WORDS_PER_PAGE, len(self.display_words))
        page_words = self.display_words[start_idx:end_idx]
        
        if not page_words: # If current page is empty
            QtWidgets.QMessageBox.information(self, "提示", "当前页没有词汇可供打印。")
            return
        
        self._perform_print(page_words, "当前页词汇列表")

    def _print_all_words(self):
        """打印所有词汇。"""
        if not self.display_words:
            QtWidgets.QMessageBox.information(self, "提示", "没有词汇可供打印。")
            return
        self._perform_print(self.display_words, "所有词汇列表")

    def _perform_print(self, words_to_print, title="词汇列表"):
        """执行实际的打印操作。"""
        if not words_to_print:
            QtWidgets.QMessageBox.information(self, "提示", "没有词汇可供打印。")
            return

        printer = QPrinter(QPrinter.HighResolution) # Corrected: QPrinter is from QtPrintSupport
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec() == QtWidgets.QDialog.Accepted:
            print("DEBUG: _trigger_print executed - print dialog accepted.")
            document = QtGui.QTextDocument() # Create a new document for each print job
            html_content = self._generate_print_html(words_to_print, title)
            document.setHtml(html_content) # Set the HTML content
            document.print(printer)
            QtWidgets.QMessageBox.information(self, "打印", "词汇列表已发送到打印机。")

    def _generate_word_doc(self, data, mode, description):
        """
        根据选择的模式生成Word文档，并弹出保存对话框让用户选择保存路径。
        """
        # 局部导入，避免循环依赖
        from word_document_generator import generate_word_table
        
        if not data:
            QtWidgets.QMessageBox.warning(self.main_window, "导出失败", f"没有 {description} 的数据可供导出。")
            return
        
        # 构造默认文件名
        current_date = datetime.now().strftime("%Y%m%d")
        # 清理描述，使其适合作为文件名（移除特殊字符，替换空格为下划线）
        cleaned_description = re.sub(r'[^\w\s]', '', description).replace(' ', '_')
        file_name = f"HSE_Vocabulary_{cleaned_description}_{current_date}.docx"
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        default_save_path = os.path.join(desktop_path, file_name)

        # 弹出文件保存对话框
        file_filter = "Word Documents (*.docx)"
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "保存单词表", default_save_path, file_filter)

        if save_path: # 如果用户选择了路径并点击了保存
            try:
                generate_word_table(data, save_path, mode=mode)
                QtWidgets.QMessageBox.information(self.main_window, "导出成功", f"'{description}' 已成功导出到：{save_path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self.main_window, "导出错误", f"导出 '{description}' 时发生错误: {e}")
        else:
            print("导出操作已取消。")


    def _generate_print_html(self, words_to_print, title):
        """
        生成用于打印的HTML内容。
        """
        html = """
        <html>
        <head>
            <style>
                body { font-family: "Microsoft YaHei", "Arial", sans-serif; margin: 20mm; font-size: 10pt; }
                h1 { text-align: center; color: #333; font-size: 16pt; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .word { font-weight: bold; color: #1a1a1a; }
                .content { color: #444444; }
                .index { color: #666666; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <h1>核心词汇列表</h1>
            <h2 style="text-align: center; color: #555; font-size: 12pt;">%s</h2>
            <table>
                <thead>
                    <tr>
                        <th style="width: 10%;">序号</th>
                        <th style="width: 35%;">英文</th>
                        <th style="width: 55%;">中文释义</th>
                    </tr>
                </thead>
                <tbody>
        """ % title
        
        for i, word_data in enumerate(words_to_print):
            word_text = word_data.get("word", "")
            content_text = word_data.get("content", "")
            
            html += f"""
                    <tr>
                        <td class="index">{i + 1}</td>
                        <td class="word">{word_text}</td>
                        <td class="content">{content_text}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </body>
        </html>
        """
        return html
