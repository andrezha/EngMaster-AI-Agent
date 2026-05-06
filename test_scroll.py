import sys
from PySide6 import QtWidgets, uic
app = QtWidgets.QApplication(sys.argv)
class MockMain(QtWidgets.QMainWindow):
    """
    模拟主窗口类，用于加载UI文件并测试布局。
    """
    def __init__(self):
        super().__init__()
        uic.loadUi('resources/main_window.ui', self)

# 创建 MockMain 实例并查找 'gk_answer_content' 控件的布局
win = MockMain()
target = win.findChild(QtWidgets.QWidget, "gk_answer_content")
print("Target layout:", target.layout())
