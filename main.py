import sys
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication, QMainWindow
from vocab_module import VocabManager     # 导入单词模块
from analyzer_module import AnalyzerManager # 导入解析模块


class HighSchoolEnglishAI(QMainWindow):
    def __init__(self):
        # 🚀 必须有这一行！它是地基，没有它必崩
        super().__init__() 
        
        # 1. 定位路径并加载 UI
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(self.base_path, "resources", "main_window.ui")
        uic.loadUi(ui_path, self)

        self.vocab_ctrl = VocabManager(self)
        self.analyzer_ctrl = AnalyzerManager(self)

        # 2. 抓取 UI 控件
        self.stack = self.findChild(QtWidgets.QStackedWidget, "stackedWidget")
        self.btn_nav_vocab = self.findChild(QtWidgets.QPushButton, "btn_nav_vocab")
        self.btn_nav_scan = self.findChild(QtWidgets.QPushButton, "btn_nav_scan")

        # 3. 启动子模块 (把 VocabManager 实例化)
        self.vocab_ctrl = VocabManager(self)
        self.analyzer_ctrl = AnalyzerManager(self)

        # 4. 绑定导航按钮
        if self.btn_nav_vocab:
            self.btn_nav_vocab.clicked.connect(self.switch_to_vocab)
        if self.btn_nav_scan:
            self.btn_nav_scan.clicked.connect(self.switch_to_scan)

    def switch_to_vocab(self):
        """切回词汇页：恢复计时"""
        self.stack.setCurrentIndex(0)
        if hasattr(self, 'vocab_ctrl'):
            self.vocab_ctrl.timer.start(1000)
            self.vocab_ctrl.v_input.setFocus()

    def switch_to_scan(self):
        """切到解析页：暂停计时"""
        self.stack.setCurrentIndex(1)
        if hasattr(self, 'vocab_ctrl'):
            self.vocab_ctrl.timer.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HighSchoolEnglishAI()
    window.show()
    sys.exit(app.exec_())