# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/export_dialog.py
import os
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                               QLineEdit, QPushButton, QFileDialog, QMessageBox)
import sys # Import sys for debugging
from PySide6.QtCore import Qt

class ExportDialog(QDialog):
    def __init__(self, parent=None, regular_vocab_data=None, mistake_vocab_data=None):
        super().__init__(parent)
        self.setWindowTitle("保存单词表")
        self.setMinimumWidth(400)
        
        print(f"DEBUG: ExportDialog __init__ called from: {__file__}") # Add this debug print
        self.regular_vocab_data = regular_vocab_data if regular_vocab_data is not None else []
        self.mistake_vocab_data = mistake_vocab_data if mistake_vocab_data is not None else []

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 合并后的导出模式选择 (QComboBox)
        export_mode_layout = QHBoxLayout()
        self.export_mode_label = QLabel("选择导出模式:")
        self.export_mode_combo = QComboBox()
        
        # 根据用户需求填充所有组合选项
        new_items = [
            f"常规英语词汇中文+ 英语表 ({len(self.regular_vocab_data)} 词)",
            f"常规英语词汇英语默写表 ({len(self.regular_vocab_data)} 词)",
            f"常规英语词汇看英语填写中文默写表 ({len(self.regular_vocab_data)} 词)",
            f"错词英语词汇中文+ 英语表 ({len(self.mistake_vocab_data)} 词)",
            f"错词英语词汇英语默写表 ({len(self.mistake_vocab_data)} 词)",
            f"错词英语词汇看英语填写中文默写表 ({len(self.mistake_vocab_data)} 词)"
        ]
        self.export_mode_combo.addItems(new_items)
        self.export_mode_combo.currentIndexChanged.connect(self._set_default_path)
        export_mode_layout.addWidget(self.export_mode_label)
        export_mode_layout.addWidget(self.export_mode_combo)
        self.main_layout.addLayout(export_mode_layout)

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
        selected_text = self.export_mode_combo.currentText()
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        current_date = datetime.now().strftime("%Y%m%d")

        # 从选中的文本中解析词汇类型和内容类型
        vocab_type_name = ""
        content_type_desc = ""

        if "常规英语词汇" in selected_text:
            vocab_type_name = "常规词汇"
        elif "错词英语词汇" in selected_text:
            vocab_type_name = "错词词汇"

        file_name_parts = ["HSE_Vocabulary"]
        file_name_parts.append(vocab_type_name)

        if "中文+ 英语表" in selected_text:
            file_name_parts.append("中英对照")
        elif "英语默写表" in selected_text:
            file_name_parts.append("英文默写")
        elif "看英语填写中文默写表" in selected_text:
            file_name_parts.append("英文默写中文")
        elif "看中文填写英语默写表" in selected_text:
            file_name_parts.append("中文默写英文")
        
        file_name_parts.append(current_date)
        default_file_name = "_".join(file_name_parts) + f".{self.output_format}"
        
        self.default_file_path = os.path.join(desktop_path, default_file_name)
        self.path_input.setText(self.default_file_path)

    def get_selected_vocabulary_data(self):
        selected_text = self.export_mode_combo.currentText()
        if "常规英语词汇" in selected_text:
            return self.regular_vocab_data
        return self.mistake_vocab_data # 默认为错词词汇

    def get_selected_mode(self):
        selected_text = self.export_mode_combo.currentText()
        if "中文+ 英语表" in selected_text:
            return "normal"
        elif "看英语填写中文默写表" in selected_text:
            return "en_dictate_cn"
        elif "看中文填写英语默写表" in selected_text:
            return "cn_dictate_en"
        return "normal" # 默认模式

    def get_output_format(self):
        return self.output_format # 始终为 docx

    def get_content_type(self):
        # 此方法可能不再需要，因为我们直接使用 get_selected_mode
        return self.export_mode_combo.currentText()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f2f5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            /* QGroupBox 和 QRadioButton 样式已不再需要，因为它们已被 QComboBox 替换 */
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
