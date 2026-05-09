# word_list_view.py 完整内容
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QHeaderView, QMessageBox
from PySide6.QtCore import Qt

class WordListView(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.mistake_list = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["序号", "英语单词", "中文释义"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    # 🎯 必须有这个函数，否则 main.py 会报错
    def refresh_mistake_list(self, mistake_data):
        self.mistake_list = mistake_data
        self.table.setRowCount(len(mistake_data))
        for i, item in enumerate(mistake_data):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(item.get('word', '')))
            self.table.setItem(i, 2, QTableWidgetItem(item.get('translation', '')))

    def export_to_word(self):
        pass # 这里是你之前的导出逻辑