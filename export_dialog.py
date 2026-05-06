# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/export_dialog.py
import os
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QRadioButton, QButtonGroup,
                               QLineEdit, QPushButton, QFileDialog, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt

class ExportDialog(QDialog):
    def __init__(self, parent=None, regular_vocab_data=None, mistake_vocab_data=None):
        super().__init__(parent)
        self.setWindowTitle("保存单词表")
        self.setMinimumWidth(400)
        
        self.regular_vocab_data = regular_vocab_data if regular_vocab_data is not None else []
        self.mistake_vocab_data = mistake_vocab_data if mistake_vocab_data is not None else []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # Vocabulary Type Selection (Radio Buttons)
        vocab_type_group_box = QGroupBox("词汇类型")
        vocab_type_layout = QVBoxLayout(vocab_type_group_box)
        
        self.radio_regular_vocab = QRadioButton(f"常规词汇 ({len(self.regular_vocab_data)} 词)")
        self.radio_mistake_vocab = QRadioButton(f"错词词汇 ({len(self.mistake_vocab_data)} 词)")
        
        self.vocab_type_button_group = QButtonGroup(self)
        self.vocab_type_button_group.addButton(self.radio_regular_vocab)
        self.vocab_type_button_group.addButton(self.radio_mistake_vocab)
        
        self.radio_regular_vocab.setChecked(True) # Default selection
        self.vocab_type_button_group.buttonClicked.connect(self._set_default_path)
        vocab_type_layout.addWidget(self.radio_regular_vocab)
        vocab_type_layout.addWidget(self.radio_mistake_vocab)
        
        self.main_layout.addWidget(vocab_type_group_box)

        # Content Type Selection
        content_type_layout = QHBoxLayout()
        self.content_type_label = QLabel("内容类型:")
        self.content_type_combo = QComboBox()
        self.content_type_combo.addItems(["英文+中文", "英语默写中文", "中文默写英文"])
        self.content_type_combo.currentIndexChanged.connect(self._set_default_path)
        content_type_layout.addWidget(self.content_type_label)
        content_type_layout.addWidget(self.content_type_combo)
        self.main_layout.addLayout(content_type_layout)

        # Output Format Selection (Fixed to docx as per requirement)
        self.output_format = "docx" 

        # File path selection
        path_layout = QHBoxLayout()
        self.path_label = QLabel("保存到:")
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True) # Make it read-only, user uses browse button
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self._browse_file)

        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        self.main_layout.addLayout(path_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        self.main_layout.addLayout(button_layout)

        self._set_default_path()
        self._apply_styles()

    def _set_default_path(self):
        """
        设置默认保存路径为桌面，并生成默认文件名。
        """
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        current_date = datetime.now().strftime("%Y%m%d")

        # Determine vocabulary type for filename
        if self.radio_regular_vocab.isChecked():
            vocab_type_name = "常规词汇"
        else:
            vocab_type_name = "错词词汇"

        # Generate default filename based on type and content
        file_name_parts = ["HSE_Vocabulary"]
        
        file_name_parts.append(vocab_type_name)

        # Map content_type to a more descriptive string for the filename
        content_type_text = self.content_type_combo.currentText()
        if content_type_text == "英文+中文":
            file_name_parts.append("英文+中文")
        elif content_type_text == "英语默写中文":
            file_name_parts.append("英文默写中文")
        elif content_type_text == "中文默写英文":
            file_name_parts.append("中文默写英文")
        
        file_name_parts.append(current_date)
        default_file_name = "_".join(file_name_parts) + f".{self.output_format}"
        
        self.default_file_path = os.path.join(desktop_path, default_file_name)
        self.path_input.setText(self.default_file_path)

    def _browse_file(self):
        """
        打开文件保存对话框，让用户选择保存位置和文件名。
        """
        file_filter = "Word Documents (*.docx)"
        file_path, _ = QFileDialog.getSaveFileName(self, "保存单词表", self.default_file_path, file_filter)
        if file_path:
            self.path_input.setText(file_path)
            # Update default_file_path to reflect user's last choice for next time
            self.default_file_path = file_path
            
    def get_save_path(self):
        return self.path_input.text()
    
    def get_selected_vocabulary_data(self):
        if self.radio_regular_vocab.isChecked():
            return self.regular_vocab_data
        else:
            return self.mistake_vocab_data

    def get_selected_mode(self):
        content_type_text = self.content_type_combo.currentText()
        if content_type_text == "英文+中文":
            return "normal"
        elif content_type_text == "英语默写中文":
            return "en_dictate_cn"
        elif content_type_text == "中文默写英文":
            return "cn_dictate_en"
        return "normal" # Default

    def get_output_format(self):
        return self.output_format # Always docx

    def get_content_type(self):
        return self.content_type_combo.currentText()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f2f5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            QGroupBox {
                font-weight: bold;
                margin-top: 10px;
            }
            QRadioButton {
                font-size: 14px;
                color: #555;
                padding: 4px 0;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
