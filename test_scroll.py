import sys
from PyQt5 import QtWidgets, uic
app = QtWidgets.QApplication(sys.argv)
class MockMain(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('resources/main_window.ui', self)

win = MockMain()
target = win.findChild(QtWidgets.QWidget, "gk_answer_content")
print("Target layout:", target.layout())
