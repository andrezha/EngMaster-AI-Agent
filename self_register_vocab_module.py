import json
import os
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QTableWidgetItem, QPushButton, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame, QHeaderView
from PySide6.QtCore import Qt
from utils import _normalize_legacy as _normalize_full_width_to_half_width, get_writable_data_path
from edition_config import is_trial_edition
from ui_styles import (
    CHECKABLE_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)

class EditWordDialog(QDialog):
    """
    用于编辑单词的独立对话框。
    """
    def __init__(self, parent=None, english_word="", chinese_explanation=""):
        super().__init__(parent)
        self.setWindowTitle("编辑单词")
        self.setMinimumWidth(300)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        english_layout = QHBoxLayout()
        english_layout.addWidget(QLabel("英语单词:"))
        self.english_input = QLineEdit(english_word)
        self.english_input.setMinimumHeight(30)
        english_layout.addWidget(self.english_input)
        layout.addLayout(english_layout)

        chinese_layout = QHBoxLayout()
        chinese_layout.addWidget(QLabel("中文解释:"))
        self.chinese_input = QLineEdit(chinese_explanation)
        self.chinese_input.setMinimumHeight(30)
        chinese_layout.addWidget(self.chinese_input)
        layout.addLayout(chinese_layout)

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
        """)
        self.cancel_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.save_button.setStyleSheet(PRIMARY_BUTTON_STYLE)

    def get_edited_data(self):
        return self.english_input.text().strip(), self.chinese_input.text().strip()

class SelfRegisterVocabManager(QtWidgets.QWidget):
    """
    自主登记单词功能模块管理器。
    """
    def __init__(self, main_window_instance, initial_user_vocab_data=None):
        super().__init__()
        self.main_window = main_window_instance
        self.user_vocab_data = initial_user_vocab_data if initial_user_vocab_data is not None else []
        self.is_trial = is_trial_edition(getattr(main_window_instance, "edition", None))
        self.word_limit = 30 if self.is_trial else None
        self.data_file_path = get_writable_data_path("user_registered_vocab.json")

        self.current_page = 0
        self.display_mode = "both"
        self.words_per_physical_row = 3
        self.physical_rows_per_page = 15
        self.words_per_page = self.words_per_physical_row * self.physical_rows_per_page

        print(f"DEBUG: SelfRegisterVocabManager initialized. Version with {self.physical_rows_per_page} physical rows per page.")

        self._build_ui()
        
        if self.add_word_button:
            self.add_word_button.clicked.connect(self._add_word)
        if self.english_word_input and self.chinese_explanation_input:
            self.english_word_input.returnPressed.connect(lambda: self.chinese_explanation_input.setFocus())
            self.chinese_explanation_input.returnPressed.connect(self._add_word)

        if self.prev_page_button:
            self.prev_page_button.clicked.connect(self._prev_page)
        if self.next_page_button:
            self.next_page_button.clicked.connect(self._next_page)
        self.btn_show_both.clicked.connect(lambda: self._set_display_mode("both"))
        self.btn_only_english.clicked.connect(lambda: self._set_display_mode("english"))
        self.btn_only_chinese.clicked.connect(lambda: self._set_display_mode("chinese"))

        if self.vocab_table:
            self.vocab_table.setColumnCount(self.words_per_physical_row * 5)
            
            header_labels = []
            for _ in range(self.words_per_physical_row):
                header_labels.extend(["序号", "英语", "中文", "修改", "删除"])
            self.vocab_table.setHorizontalHeaderLabels(header_labels)
            
            for i in range(self.words_per_physical_row):
                base_col = i * 5
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col, QtWidgets.QHeaderView.ResizeToContents)
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col + 1, QtWidgets.QHeaderView.Stretch)
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col + 2, QtWidgets.QHeaderView.Stretch)
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col + 3, QtWidgets.QHeaderView.Fixed)
                self.vocab_table.setColumnWidth(base_col + 3, 85)
                self.vocab_table.horizontalHeader().setSectionResizeMode(base_col + 4, QtWidgets.QHeaderView.Fixed)
                self.vocab_table.setColumnWidth(base_col + 4, 90)
            
            self.vocab_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.vocab_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.vocab_table.setWordWrap(True)
            self.vocab_table.setTextElideMode(Qt.ElideNone)
            self.vocab_table.verticalHeader().setVisible(False)
            self.vocab_table.setRowCount(self.physical_rows_per_page)
            self.vocab_table.verticalHeader().setDefaultSectionSize(50)
            self.vocab_table.verticalHeader().setMinimumSectionSize(50)
            self.vocab_table.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        self._load_user_vocab()
        self._refresh_table()
        self._apply_styles()

    def _build_ui(self):
        main_v_layout = QVBoxLayout(self)
        main_v_layout.setSpacing(15)
        main_v_layout.setContentsMargins(20, 20, 20, 20)

        self.title_label = QLabel("自主登记单词")
        self.title_label.setAlignment(Qt.AlignLeft)
        self.title_label.setStyleSheet(
            "QLabel { font-size:24px; font-weight:700; color:#2c3e50; }")
        main_v_layout.addWidget(self.title_label)

        self.limit_label = QLabel("")
        self.limit_label.setObjectName("self_register_limit_label")
        self.limit_label.setWordWrap(True)
        self.limit_label.setStyleSheet(
            "color:#92400e; background:#fef3c7; border:1px solid #f59e0b; "
            "border-radius:8px; padding:8px 12px; font-size:14px; font-weight:700;")
        self.limit_label.setVisible(self.is_trial)
        main_v_layout.addWidget(self.limit_label)

        input_frame = QFrame()
        input_frame.setObjectName("word_entry_frame")
        input_frame.setFrameShape(QFrame.StyledPanel)
        input_frame.setFrameShadow(QFrame.Raised)
        input_frame.setStyleSheet(
            "QFrame#word_entry_frame { background:#ffffff; border:1px solid #dbe3ee; "
            "border-radius:8px; }")
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
        self.chinese_explanation_input.setMaximumWidth(350)
        input_h_layout.addWidget(self.chinese_explanation_input)

        self.add_word_button = QPushButton("录入")
        self.add_word_button.setMinimumHeight(50)
        input_h_layout.addWidget(self.add_word_button)
        input_h_layout.addStretch()

        main_v_layout.addWidget(input_frame)

        display_frame = QFrame()
        display_frame.setObjectName("display_mode_frame")
        display_layout = QHBoxLayout(display_frame)
        display_layout.setContentsMargins(16, 10, 16, 10)
        display_layout.setSpacing(10)

        self.btn_show_both = QPushButton("📚 中英对照")
        self.btn_only_english = QPushButton("📖 只看英语")
        self.btn_only_chinese = QPushButton("📝 只看中文")
        self.language_display_group = QtWidgets.QButtonGroup(self)
        self.language_display_group.setExclusive(True)
        for button in (
            self.btn_show_both,
            self.btn_only_english,
            self.btn_only_chinese,
        ):
            button.setCheckable(True)
            button.setFixedHeight(36)
            button.setMinimumWidth(112)
            self.language_display_group.addButton(button)
            display_layout.addWidget(button)
        self.btn_show_both.setChecked(True)
        display_layout.addStretch()
        main_v_layout.addWidget(display_frame)

        self.vocab_table = QtWidgets.QTableWidget()
        self.vocab_table.setMinimumHeight(self.physical_rows_per_page * 50)
        self.vocab_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        main_v_layout.addWidget(self.vocab_table)

        pagination_layout = QHBoxLayout()
        self.prev_page_button = QPushButton("上一页")
        self.next_page_button = QPushButton("下一页")
        self.page_label = QLabel("第 1 / 1 页")
        self.page_label.setAlignment(Qt.AlignLeft)
        
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_button)
        pagination_layout.addStretch()
        main_v_layout.addLayout(pagination_layout)

        self.setObjectName("SelfRegisterVocabPage")
        self.title_label.setObjectName("title_label")
        self.english_word_input.setObjectName("english_word_input")
        self.chinese_explanation_input.setObjectName("chinese_explanation_input")
        self.add_word_button.setObjectName("add_word_button")
        self.btn_show_both.setObjectName("btn_show_both")
        self.btn_only_english.setObjectName("btn_only_english")
        self.btn_only_chinese.setObjectName("btn_only_chinese")
        self.vocab_table.setObjectName("vocab_table")
        self.prev_page_button.setObjectName("prev_page_button")
        self.next_page_button.setObjectName("next_page_button")
        self.page_label.setObjectName("page_label")

    def _load_user_vocab(self):
        """
        从本地 JSON 文件加载用户登记的单词数据。
        """
        if self.user_vocab_data:
            print(f"✅ 自主登记单词已从后台数据加载完成，共 {len(self.user_vocab_data)} 词。")
            return

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
            sync_counts = getattr(
                self.main_window, '_sync_challenge_user_vocab_counts', None)
            if callable(sync_counts):
                sync_counts()
        except Exception as e:
            QMessageBox.critical(self.main_window, "错误", f"保存自主登记单词失败: {e}")

    def _refresh_table(self):
        """
        刷新表格显示。
        """
        if not self.vocab_table:
            return

        total_words = len(self.user_vocab_data)
        self._update_limit_status()
        total_pages = (total_words + self.words_per_page - 1) // self.words_per_page
        if total_pages == 0:
            total_pages = 1
        
        self.current_page = max(0, min(self.current_page, total_pages - 1))

        self.page_label.setText(f"第 {self.current_page + 1} / {total_pages} 页")
        self.prev_page_button.setEnabled(self.current_page > 0)
        self.next_page_button.setEnabled(self.current_page < total_pages - 1)

        for row in range(self.physical_rows_per_page):
            for col in range(self.vocab_table.columnCount()):
                self.vocab_table.setItem(row, col, QTableWidgetItem(""))
                self.vocab_table.setCellWidget(row, col, None)

        for physical_row_idx in range(self.physical_rows_per_page):
            for word_in_physical_row_idx in range(self.words_per_physical_row):
                data_idx = self.current_page * self.words_per_page + \
                           physical_row_idx * self.words_per_physical_row + \
                           word_in_physical_row_idx
                
                base_col_idx = word_in_physical_row_idx * 5

                if data_idx < total_words:
                    item_data = self.user_vocab_data[data_idx]
                    
                    item_index = QTableWidgetItem(str(data_idx + 1))
                    item_index.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.vocab_table.setItem(physical_row_idx, base_col_idx, item_index)
                    
                    word_text = item_data.get("word", "")
                    visible_word = "" if self.display_mode == "chinese" else word_text
                    item_word = QTableWidgetItem(visible_word)
                    item_word.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                    item_word.setToolTip(visible_word)
                    self.vocab_table.setItem(physical_row_idx, base_col_idx + 1, item_word)
                    
                    content_text = item_data.get("content", "")
                    visible_content = "" if self.display_mode == "english" else content_text
                    item_content = QTableWidgetItem(visible_content)
                    item_content.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                    item_content.setToolTip(visible_content)
                    self.vocab_table.setItem(physical_row_idx, base_col_idx + 2, item_content)

                    edit_widget = QtWidgets.QWidget()
                    edit_layout = QtWidgets.QHBoxLayout(edit_widget)
                    edit_layout.setContentsMargins(0, 0, 0, 0)
                    edit_layout.setSpacing(0)
                    edit_layout.setAlignment(Qt.AlignCenter)
                    edit_button = QPushButton("修改")
                    edit_button.setFixedSize(60, 30)
                    edit_button.clicked.connect(lambda checked, r=data_idx: self._edit_word(r))
                    edit_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
                    edit_layout.addWidget(edit_button)
                    self.vocab_table.setCellWidget(physical_row_idx, base_col_idx + 3, edit_widget)

                    delete_widget = QtWidgets.QWidget()
                    delete_layout = QtWidgets.QHBoxLayout(delete_widget)
                    delete_layout.setContentsMargins(0, 0, 0, 0)
                    delete_layout.setSpacing(0)
                    delete_layout.setAlignment(Qt.AlignCenter)
                    delete_button = QPushButton("删除")
                    delete_button.setFixedSize(60, 30)
                    delete_button.clicked.connect(lambda checked, r=data_idx: self._delete_word(r))
                    delete_button.setStyleSheet(DANGER_BUTTON_STYLE)
                    delete_layout.addWidget(delete_button)
                    self.vocab_table.setCellWidget(physical_row_idx, base_col_idx + 4, delete_widget)

                else:
                    item_index = QTableWidgetItem(str(data_idx + 1))
                    item_index.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.vocab_table.setItem(physical_row_idx, base_col_idx, item_index)

                    for col_offset in range(1, 5):
                        empty_item = QTableWidgetItem("")
                        empty_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        self.vocab_table.setItem(physical_row_idx, base_col_idx + col_offset, empty_item)
        
        self.vocab_table.resizeRowsToContents()
        for row in range(self.physical_rows_per_page):
            if self.vocab_table.rowHeight(row) < 50:
                self.vocab_table.setRowHeight(row, 50)

    def _set_display_mode(self, mode):
        if mode not in {"both", "english", "chinese"}:
            return
        self.display_mode = mode
        self.btn_show_both.setChecked(mode == "both")
        self.btn_only_english.setChecked(mode == "english")
        self.btn_only_chinese.setChecked(mode == "chinese")
        self._refresh_table()

    def _add_word(self):
        """
        将输入框中的单词和解释录入到列表中。
        """
        english_word = self.english_word_input.text().strip()
        chinese_explanation = self.chinese_explanation_input.text().strip()

        if self.word_limit is not None and len(self.user_vocab_data) >= self.word_limit:
            QMessageBox.information(
                self.main_window,
                "体验版录入已满",
                "体验版自主登记最多保存30词。你可以修改或删除已有单词；购买正式版后不受此限制。",
            )
            self._update_limit_status()
            return

        if not english_word or not chinese_explanation:
            QMessageBox.warning(self.main_window, "输入错误", "英语单词和中文解释都不能为空。")
            return

        new_word = {
            "word": english_word,
            "content": chinese_explanation
        }
        self.user_vocab_data.append(new_word)
        self._save_user_vocab()
        
        total_words = len(self.user_vocab_data)
        total_pages = (total_words + self.words_per_page - 1) // self.words_per_page
        self.current_page = total_pages - 1
        self._refresh_table()

        self.english_word_input.clear()
        self.chinese_explanation_input.clear()
        self.english_word_input.setFocus()

    def _update_limit_status(self):
        if not hasattr(self, "limit_label") or self.word_limit is None:
            return
        used = len(self.user_vocab_data)
        remaining = max(0, self.word_limit - used)
        self.limit_label.setText(
            f"免费体验版：自主登记最多30词 · 已登记 {used} 词 · 还可登记 {remaining} 词")
        is_full = used >= self.word_limit
        self.add_word_button.setEnabled(not is_full)
        self.english_word_input.setEnabled(not is_full)
        self.chinese_explanation_input.setEnabled(not is_full)
        if is_full:
            self.add_word_button.setToolTip("体验版自主登记已达到30词上限")
        else:
            self.add_word_button.setToolTip("")

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
            
            total_words = len(self.user_vocab_data)
            total_pages = (total_words + self.words_per_page - 1) // self.words_per_page if total_words > 0 else 1
            if self.current_page >= total_pages and total_pages > 0:
                self.current_page = max(0, total_pages - 1)
            elif total_pages == 0:
                self.current_page = 0
            self._refresh_table()

    def _apply_styles(self):
        """
        应用统一的样式。
        """
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
                        font-family: "Microsoft YaHei UI", "Microsoft YaHei";
                    }
                    QLineEdit:focus {
                        border: 1px solid #0284c7;
                        background-color: #ffffff;
                        outline: none;
                    }
                """)
        
        if self.add_word_button:
            self.add_word_button.setStyleSheet(PRIMARY_BUTTON_STYLE)

        display_button_style = CHECKABLE_BUTTON_STYLE
        for button in (
            self.btn_show_both,
            self.btn_only_english,
            self.btn_only_chinese,
        ):
            button.setStyleSheet(display_button_style)
        
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
                    border-bottom: 2px solid #0284c7;
                    font-weight: bold;
                    text-align: left;
                }
                QTableWidget::item {
                    padding: 6px;
                    border-bottom: 1px solid #f0f0f0;
                    text-align: left;
                    min-height: 50px;
                }
                QTableWidget::item:selected {
                    background-color: #e0f2f7;
                    color: #333333;
                }
            """)
        
        if self.prev_page_button:
            self.prev_page_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        if self.next_page_button:
            self.next_page_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        if self.page_label:
            self.page_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #555;
                    padding: 8px 10px;
                    text-align: left;
                }
            """)
        self.setStyleSheet("""
                QWidget#SelfRegisterVocabPage { background-color: #f0f2f5; }
            """)
