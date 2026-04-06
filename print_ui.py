import sys
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)
ui = uic.loadUi("resources/page_gaokao.ui")

def print_tree(widget, indent=0):
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
