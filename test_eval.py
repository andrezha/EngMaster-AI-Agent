import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
app = QApplication(sys.argv)
w = QWidget()
l = QVBoxLayout(w)
# 获取 QWidget 的布局对象
# 如果 QWidget 已经设置了布局，w.layout() 会返回该布局对象
# 否则，w.layout() 会返回 None
l2 = w.layout()
print("w.layout():", l2)
print("bool(l2):", bool(l2))
if not l2:
    print("Evaluated to False!")
else:
    print("Evaluated to True!")
