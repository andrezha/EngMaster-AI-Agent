import sys
from PySide6 import QtWidgets, uic
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
ui = uic.loadUi("resources/page_gaokao.ui")

def print_tree(widget, indent=0):
    """
    递归打印 PySide6 UI 控件的层级结构，包括类名和对象名。
    """
    print(" " * indent + f"{widget.metaObject().className()} - {widget.objectName()}")
    layout = widget.layout()
    if layout:
        print(" " * (indent + 2) + f"Layout: {layout.metaObject().className()} - {layout.objectName()}")
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                print_tree(item.widget(), indent + 4)
            elif item.layout():
                print(" " * (indent + 4) + f"Sub-Layout: {item.layout().metaObject().className()} - {item.layout().objectName()}")

print_tree(ui)
