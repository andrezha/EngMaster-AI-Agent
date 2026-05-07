import json
import os
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QTableWidgetItem, QPushButton, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame, QHeaderView
from PySide6.QtCore import Qt
from utils import _normalize_full_width_to_half_width

class EditWordDialog(QDialog):
    """
    用于编辑单词的独立对话框。
    """
    def __init__(self, parent=None, english_word="", chinese_explanation=""):
        super().__init__(parent)
        self.setWindowTitle("编辑单词")
        self.setMinimumWidth(300)
        self.setModal(True) # Make it a modal dialog

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # English Word Input
        english_layout = QHBoxLayout()
        english_layout.addWidget(QLabel("英语单词:"))
        self.english_input = QLineEdit(english_word)
        self.english_input.setMinimumHeight(30)
        english_layout.addWidget(self.english_input)
        layout.addLayout(english_layout)

        # Chinese Explanation Input
        chinese_layout = QHBoxLayout()
        chinese_layout.addWidget(QLabel("中文解释:"))
        self.chinese_input = QLineEdit(chinese_explanation)
        self.chinese_input.setMinimumHeight(30)
        chinese_layout.addWidget(self.chinese_input)
        layout.addLayout(chinese_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f2f5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #0284c7; /* Blue */
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0369a1; /* Darker blue */
            }
        """)

    def get_edited_data(self):
        return self.english_input.text().strip(), self.chinese_input.text().strip()

class SelfRegisterVocabManager(QtWidgets.QWidget): # Inherit from QWidget directly
    """
    自主登记单词功能模块管理器。
    """
    def __init__(self, main_window_instance): # Removed page_widget parameter
        super().__init__() # Call QWidget's init
        self.main_window = main_window_instance
        self.user_vocab_data = []
        self.data_file_path = os.path.join(self.main_window.base_path, "assets", "user_registered_vocab.json") # 数据文件路径，确保在 assets 文件夹下

        self.current_page = 0  # 0-indexed
        self.words_per_physical_row = 3  # 每物理行显示多少组单词 (例如：3组)
        self.physical_rows_per_page = 15 # 每页显示多少物理行 (增加表格高度)
        self.words_per_page = self.words_per_physical_row * self.physical_rows_per_page # 每页总共显示多少个单词 (例如：3 * 15 = 45个单词)

        print(f"DEBUG: SelfRegisterVocabManager initialized. Version with {self.physical_rows_per_page} physical rows per page.") # Debug print to confirm version

        # Build UI elements programmatically
        self._build_ui() # New method to build UI
        
        # Connect signals
        if self.add_word_button:
            self.add_word_button.clicked.connect(self._add_word)
        # 确保输入框回车也能触发录入
        if self.english_word_input and self.chinese_explanation_input:
            self.english_word_input.returnPressed.connect(lambda: self.chinese_explanation_input.setFocus())
            self.chinese_explanation_input.returnPressed.connect(self._add_word)

        # Connect pagination signals
        if self.prev_page_button:
            self.prev_page_button.clicked.connect(self._prev_page)
        if self.next_page_button:
            self.next_page_button.clicked.connect(self._next_page)

        # Initialize table
        if self.vocab_table:
            self.vocab_table.setColumnCount(self.words_per_physical_row * 5) # 3组 * 5列 = 15列
            
            header_labels = []
            for _ in range(self.words_per_physical_row):
                header_labels.extend(["序号", "英语", "中文", "修改", "删除"])
            self.vocab_table.setHorizontalHeaderLabels(header_labels)
            
            for i in range(self.words_per_physical_row):
                base_col = i * 5
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col, QtWidgets.QHeaderView.ResizeToContents) # 序号
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col + 1, QtWidgets.QHeaderView.Stretch) # 英语
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col + 2, QtWidgets.QHeaderView.Stretch) # 中文
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col + 3, QtWidgets.QHeaderView.Fixed) # 修改
                self.vocab_table.setColumnWidth(base_col + 3, 85) # Set fixed width for "修改" button column
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col + 4, QtWidgets.QHeaderView.Fixed) # 删除
                self.vocab_table.setColumnWidth(base_col + 4, 90) # Set fixed width for "删除" button column, increased to 90
            
            self.vocab_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers) # Make table read-only
            self.vocab_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows) # Select entire rows
            self.vocab_table.verticalHeader().setVisible(False) # Hide vertical header
            self.vocab_table.setRowCount(self.physical_rows_per_page) # Always set row count to physical_rows_per_page
            self.vocab_table.verticalHeader().setDefaultSectionSize(50) # Set default row height
            self.vocab_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # Force fixed height for rows

        self._load_user_vocab()
        self._refresh_table()
        self._apply_styles()

    def _build_ui(self):
        # Main layout for this widget
        main_v_layout = QVBoxLayout(self)
        main_v_layout.setSpacing(15)
        main_v_layout.setContentsMargins(20, 20, 20, 20)

        # Title Label
        self.title_label = QLabel("自主登记单词")
        self.title_label.setAlignment(Qt.AlignLeft) # Left align title
        self.title_label.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; color: #2c3e50; }")
        main_v_layout.addWidget(self.title_label)

        # Input Frame
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.StyledPanel)
        input_frame.setFrameShadow(QFrame.Raised)
        input_h_layout = QHBoxLayout(input_frame)
        input_h_layout.setSpacing(10)
        input_h_layout.setContentsMargins(10, 10, 10, 10)

        self.english_word_input = QLineEdit()
        self.english_word_input.setPlaceholderText("英语单词")
        self.english_word_input.setMinimumHeight(35)
        self.english_word_input.setMaximumWidth(350)
        input_h_layout.addWidget(self.english_word_input)

        self.chinese_explanation_input = QLineEdit()
        self.chinese_explanation_input.setPlaceholderText("中文解释")
        self.chinese_explanation_input.setMinimumHeight(35)
        self.chinese_explanation_input.setMaximumWidth(350) # 增加输入框宽度
        input_h_layout.addWidget(self.chinese_explanation_input)

        self.add_word_button = QPushButton("录入")
        self.add_word_button.setMinimumHeight(50)
        # self.add_word_button.setMaximumWidth(150) # Removed to allow min-width and padding to control width
        input_h_layout.addWidget(self.add_word_button)
        input_h_layout.addStretch() # Push inputs and button to the left

        main_v_layout.addWidget(input_frame)

        # Vocab Table
        self.vocab_table = QtWidgets.QTableWidget()
        self.vocab_table.setMinimumHeight(self.physical_rows_per_page * 50) # Adjusted to match item min-height
        self.vocab_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding) # Ensure table expands
        main_v_layout.addWidget(self.vocab_table)

        # Pagination controls
        pagination_layout = QHBoxLayout()
        self.prev_page_button = QPushButton("上一页")
        self.next_page_button = QPushButton("下一页")
        self.page_label = QLabel("第 1 / 1 页")
        self.page_label.setAlignment(Qt.AlignLeft) # Left align page label
        
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_button)
        pagination_layout.addStretch() # Push pagination controls to the left
        main_v_layout.addLayout(pagination_layout)


        # Set object names for styling and debugging
        self.setObjectName("SelfRegisterVocabPage") # This widget itself is the page
        self.title_label.setObjectName("title_label")
        self.english_word_input.setObjectName("english_word_input")
        self.chinese_explanation_input.setObjectName("chinese_explanation_input")
        self.add_word_button.setObjectName("add_word_button")
        self.vocab_table.setObjectName("vocab_table")
        self.prev_page_button.setObjectName("prev_page_button")
        self.next_page_button.setObjectName("next_page_button")
        self.page_label.setObjectName("page_label")

    def _load_user_vocab(self):
        """
        从本地 JSON 文件加载用户登记的单词数据。
        """
        # 确保 assets 目录存在
        assets_dir = os.path.dirname(self.data_file_path)
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)

        try:
            if os.path.exists(self.data_file_path):
                with open(self.data_file_path, "r", encoding="utf-8") as f:
                    self.user_vocab_data = json.load(f)
                print(f"✅ 自主登记单词加载成功，共 {len(self.user_vocab_data)} 词。")
            else:
                self.user_vocab_data = []
                print("💡 自主登记单词文件不存在，已创建空列表。")
        except json.JSONDecodeError:
            self.user_vocab_data = []
            QMessageBox.warning(self.main_window, "错误", f"自主登记单词文件 {self.data_file_path} 格式错误，已重置。")
        except Exception as e:
            self.user_vocab_data = []
            QMessageBox.critical(self.main_window, "错误", f"加载自主登记单词失败: {e}")

    def _save_user_vocab(self):
        """
        将用户登记的单词数据保存到本地 JSON 文件。
        """
        try:
            with open(self.data_file_path, "w", encoding="utf-8") as f:
                json.dump(self.user_vocab_data, f, ensure_ascii=False, indent=4)
            print(f"✅ 自主登记单词已保存，当前 {len(self.user_vocab_data)} 词。")
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"保存自主登记单词失败: {e}")

    def _refresh_table(self):
        """
        刷新表格显示。
        """
        if not self.vocab_table:
            return

        total_words = len(self.user_vocab_data)
        total_pages = (total_words + self.words_per_page - 1) // self.words_per_page
        if total_pages == 0: # Handle case with no words
            total_pages = 1
        
        # Ensure current_page is within valid bounds
        self.current_page = max(0, min(self.current_page, total_pages - 1))

        self.page_label.setText(f"第 {self.current_page + 1} / {total_pages} 页")
        self.prev_page_button.setEnabled(self.current_page > 0)
        self.next_page_button.setEnabled(self.current_page < total_pages - 1)

        # Clear existing content in the table
        for row in range(self.physical_rows_per_page):
            for col in range(self.vocab_table.columnCount()):
                self.vocab_table.setItem(row, col, QTableWidgetItem(""))
                self.vocab_table.setCellWidget(row, col, None) # Clear any cell widgets

        # Populate table with words for the current page, arranged in words_per_physical_row groups per physical row
        for physical_row_idx in range(self.physical_rows_per_page):
            for word_in_physical_row_idx in range(self.words_per_physical_row):
                # Calculate the global index of the word in user_vocab_data
                data_idx = self.current_page * self.words_per_page + \
                           physical_row_idx * self.words_per_physical_row + \
                           word_in_physical_row_idx
                
                # Calculate the starting column for this word group (5 columns per group)
                base_col_idx = word_in_physical_row_idx * 5

                if data_idx < total_words:
                    item_data = self.user_vocab_data[data_idx]
                    
                    # 序号
                    item_index = QTableWidgetItem(str(data_idx + 1))
                    item_index.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.vocab_table.setItem(physical_row_idx, base_col_idx, item_index)
                    
                    # 英语单词
                    item_word = QTableWidgetItem(item_data.get("word", ""))
                    item_word.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.vocab_table.setItem(physical_row_idx, base_col_idx + 1, item_word)
                    
                    # 中文解释
                    item_content = QTableWidgetItem(item_data.get("content", ""))
                    item_content.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.vocab_table.setItem(physical_row_idx, base_col_idx + 2, item_content)

                    # 修改按钮
                    edit_widget = QtWidgets.QWidget()
                    edit_layout = QtWidgets.QHBoxLayout(edit_widget)
                    edit_layout.setContentsMargins(0, 0, 0, 0)
                    edit_layout.setSpacing(0)
                    edit_layout.setAlignment(Qt.AlignCenter)
                    edit_button = QPushButton("修改")
                    edit_button.setFixedSize(60, 30) # Increased size for the button
                    edit_button.clicked.connect(lambda checked, r=data_idx: self._edit_word(r))
                    edit_button.setStyleSheet("""
                        QPushButton {
                            background-color: #0284c7; /* Blue */
                            color: white;
                            border: none;
                            border-radius: 4px;
                            padding: 6px 10px; /* Increased padding */
                            font-size: 12px;
                        }
                        QPushButton:hover { background-color: #0369a1; }
                    """)
                    edit_layout.addWidget(edit_button)
                    self.vocab_table.setCellWidget(physical_row_idx, base_col_idx + 3, edit_widget)

                    # 删除按钮
                    delete_widget = QtWidgets.QWidget()
                    delete_layout = QtWidgets.QHBoxLayout(delete_widget)
                    delete_layout.setContentsMargins(0, 0, 0, 0)
                    delete_layout.setSpacing(0)
                    delete_layout.setAlignment(Qt.AlignCenter)
                    delete_button = QPushButton("删除")
                    delete_button.setFixedSize(60, 30) # Increased size for the button
                    delete_button.clicked.connect(lambda checked, r=data_idx: self._delete_word(r))
                    delete_button.setStyleSheet("""
                        QPushButton {
                            background-color: #0284c7; /* Blue */
                            color: white;
                            border: none;
                            border-radius: 4px;
                            padding: 6px 10px; /* Increased padding */
                            font-size: 12px;
                        }
                        QPushButton:hover { background-color: #0369a1; }
                    """)
                    delete_layout.addWidget(delete_button)
                    self.vocab_table.setCellWidget(physical_row_idx, base_col_idx + 4, delete_widget)

                else: # Fill empty cells with pre-filled serial numbers and blank items
                    # Pre-fill serial number
                    item_index = QTableWidgetItem(str(data_idx + 1))
                    item_index.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.vocab_table.setItem(physical_row_idx, base_col_idx, item_index)

                    # Fill other cells with empty items
                    for col_offset in range(1, 5):
                        empty_item = QTableWidgetItem("")
                        empty_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        self.vocab_table.setItem(physical_row_idx, base_col_idx + col_offset, empty_item)
        
        # Removed resizeRowsToContents() as row height is now fixed by setSectionResizeMode(Fixed)

    def _add_word(self):
        """
        将输入框中的单词和解释录入到列表中。
        """
        english_word = self.english_word_input.text().strip()
        chinese_explanation = self.chinese_explanation_input.text().strip()

        if not english_word or not chinese_explanation:
            QMessageBox.warning(self.main_window, "输入错误", "英语单词和中文解释都不能为空。")
            return

        new_word = {
            "word": english_word,
            "content": chinese_explanation
        }
        self.user_vocab_data.append(new_word) # Add new word
        self._save_user_vocab()
        
        # After adding, ensure we go to the last page to see the new word
        total_words = len(self.user_vocab_data)
        total_pages = (total_words + self.words_per_page - 1) // self.words_per_page
        self.current_page = total_pages - 1 # Go to the last page
        self._refresh_table()

        self.english_word_input.clear()
        self.chinese_explanation_input.clear()
        self.english_word_input.setFocus()

    def _next_page(self):
        total_words = len(self.user_vocab_data)
        total_pages = (total_words + self.words_per_page - 1) // self.words_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._refresh_table()

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_table()

    def _edit_word(self, row_idx):
        """
        编辑指定行的单词数据。
        """
        if not (0 <= row_idx < len(self.user_vocab_data)):
            return

        current_word_data = self.user_vocab_data[row_idx]
        dialog = EditWordDialog(self.main_window, current_word_data.get("word", ""), current_word_data.get("content", ""))
        
        if dialog.exec() == QDialog.Accepted:
            edited_word, edited_explanation = dialog.get_edited_data()
            if not edited_word or not edited_explanation:
                QMessageBox.warning(self.main_window, "输入错误", "编辑后的英语单词和中文解释都不能为空。")
                return
            
            self.user_vocab_data[row_idx]["word"] = edited_word
            self.user_vocab_data[row_idx]["content"] = edited_explanation
            self._save_user_vocab()
            self._refresh_table()

    def _delete_word(self, row_idx):
        """
        删除指定行的单词数据。
        """
        if not (0 <= row_idx < len(self.user_vocab_data)):
            return

        reply = QMessageBox.question(self.main_window, "确认删除", 
                                     f"确定要删除单词 '{self.user_vocab_data[row_idx].get('word', '')}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.user_vocab_data[row_idx]
            self._save_user_vocab()
            
            # After deleting, refresh table, current_page might need adjustment if last word on page was deleted
            total_words = len(self.user_vocab_data)
            total_pages = (total_words + self.words_per_page - 1) // self.words_per_page if total_words > 0 else 1
            if self.current_page >= total_pages and total_pages > 0:
                self.current_page = max(0, total_pages - 1) # Ensure it's not negative
            elif total_pages == 0:
                self.current_page = 0 # If no words left, stay on page 0 (first page)
            self._refresh_table()

    def _apply_styles(self):
        """
        应用统一的样式。
        """
        # Apply styles to inputs
        for widget in [self.english_word_input, self.chinese_explanation_input]:
            if widget:
                widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #fafafa;
                        border: 1px solid #ddd;
                        border-radius: 6px;
                        font-size: 16px;
                        padding: 0px 10px;
                        color: #333333;
                        font-family: "Arial", "Microsoft YaHei";
                    }
                    QLineEdit:focus {
                        border: 1px solid #0284c7; /* Blue focus border */
                        background-color: #ffffff;
                        outline: none;
                    }
                """)
        
        # Apply styles to add button
        if self.add_word_button:
            self.add_word_button.setStyleSheet("""
                QPushButton { /* Blue */
                    background-color: #0284c7;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px; /* Adjusted padding */
                    font-size: 16px;
                    font-weight: bold;
                    min-width: 120px; /* Added min-width */
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); /* Added shadow */
                }
                QPushButton:hover { /* Darker blue */
                    background-color: #0369a1;
                    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15); /* Darker shadow on hover */
                }
                QPushButton:pressed {
                    background-color: #075985; /* Even darker blue for pressed state */
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Smaller shadow on press */
                }
            """)
        
        # Apply styles to table
        if self.vocab_table:
            self.vocab_table.setStyleSheet("""
                QTableWidget {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    font-size: 14px;
                    selection-background-color: #e0f2f7;
                    selection-color: #333333;
                }
                QHeaderView::section {
                    background-color: #f5f7fa;
                    color: #555555;
                    padding: 8px;
                    border: 1px solid #e0e0e0;
                    border-bottom: 2px solid #0284c7; /* Blue bottom border */
                    font-weight: bold;
                    text-align: left; /* Left align header text */
                }
                QTableWidget::item {
                    padding: 6px;
                    border-bottom: 1px solid #f0f0f0;
                    text-align: left; /* Left align item text */
                    min-height: 50px; /* Added min-height for rows */
                }
                QTableWidget::item:selected {
                    background-color: #e0f2f7;
                    color: #333333;
                }
            """)
        
        # Apply styles for pagination buttons
        if self.prev_page_button:
            self.prev_page_button.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 15px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #0369a1;
                }
                QPushButton:disabled {
                    background-color: #a7a7a7; /* Grey for disabled */
                    color: #e0e0e0;
                    border-color: #ccc;
                }
            """)
        if self.next_page_button:
            self.next_page_button.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 15px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #0369a1;
                }
                QPushButton:disabled {
                    background-color: #a7a7a7; /* Grey for disabled */
                    color: #e0e0e0;
                    border-color: #ccc;
                }
            """)
        if self.page_label:
            self.page_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #555;
                    padding: 8px 10px;
                    text-align: left;
                }
            """)
        # Apply default background to the page widget
        # Since SelfRegisterVocabManager is now the QWidget itself, apply style to self
        self.setStyleSheet("""
                QWidget#SelfRegisterVocabPage { background-color: #f0f2f5; }
            """)
