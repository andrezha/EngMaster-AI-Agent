import sys
from PyQt5.QtWidgets import QApplication
from main import HighSchoolEnglishAI
app = QApplication(sys.argv)
window = HighSchoolEnglishAI()
window.exam_ctrl.switch_topic("七选五")
