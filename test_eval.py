import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
app = QApplication(sys.argv)
w = QWidget()
l = QVBoxLayout(w)
l2 = w.layout()
print("w.layout():", l2)
print("bool(l2):", bool(l2))
if not l2:
    print("Evaluated to False!")
else:
    print("Evaluated to True!")
