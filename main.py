import sys
import os
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication, QMainWindow
from vocab_module import VocabManager     
from analyzer_module import AnalyzerManager 
from exam_module import ExamManager       

class HighSchoolEnglishAI(QMainWindow):
    def __init__(self):
        # 🚀 必须有这一行！地基
        super().__init__() 
    
        # 1. 定位路径
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        res_dir = os.path.join(self.base_path, "resources")
        
        # 2. 加载主框架 UI (这里面包含那个空的 stackedWidget)
        main_ui_path = os.path.join(res_dir, "main_window.ui")
        uic.loadUi(main_ui_path, self)

        # 3. 【重点】加载并强行嵌入“高考真题”
        gk_ui_path = os.path.join(res_dir, "page_gaokao.ui")
        
        # 🌟 关键改动：加载时就明确告诉它：你的“亲爹”是 stackedWidget
        self.page_gaokao_widget = uic.loadUi(gk_ui_path) 
        
        # 🌟 关键改动：先塞进去，再处理显示
        self.stackedWidget.addWidget(self.page_gaokao_widget)
        
        # 🌟 关键改动：确保父级容器(StackedWidget)有布局来撑开它
        if not self.stackedWidget.layout():
            v_layout = QtWidgets.QVBoxLayout(self.stackedWidget)
            v_layout.setContentsMargins(0, 0, 0, 0)
            self.stackedWidget.setLayout(v_layout)

        # 🌟 关键：不要在这里直接调 show()，那是让它变成独立窗口
        # 而是在切换函数里去唤醒它
        self.gk_index = self.stackedWidget.indexOf(self.page_gaokao_widget)
        

        # 4. 抓取 UI 控件引用 (确保这些名字和 XML 里的 ObjectName 一致)
        # 注意：这里我们直接用 self.stackedWidget 也可以，因为 uic.loadUi 已经把名字赋给 self 了
        self.stack = self.stackedWidget 
        self.btn_nav_vocab = self.findChild(QtWidgets.QPushButton, "btn_nav_vocab")
        self.btn_nav_scan = self.findChild(QtWidgets.QPushButton, "btn_nav_scan")
        self.btn_nav_gaokao = self.findChild(QtWidgets.QPushButton, "btn_nav_gaokao")

        # 5. 启动子模块 (传入 self 以便子模块能操作 UI)
        self.vocab_ctrl = VocabManager(self)
        self.analyzer_ctrl = AnalyzerManager(self)
        self.exam_ctrl = ExamManager(self) 

        # 6. 绑定导航按钮点击事件
        if self.btn_nav_vocab:
            self.btn_nav_vocab.clicked.connect(self.switch_to_vocab)
        if self.btn_nav_scan:
            self.btn_nav_scan.clicked.connect(self.switch_to_scan)
        if self.btn_nav_gaokao:
            self.btn_nav_gaokao.clicked.connect(self.switch_to_gaokao)
        

    # --- 导航切换函数 ---
    def switch_to_vocab(self):
        """切回词汇页"""
        self.stack.setCurrentIndex(0)
        # 逻辑：如果单词模块有计时器，切回来就开启
        if hasattr(self, 'vocab_ctrl') and hasattr(self.vocab_ctrl, 'timer'):
            self.vocab_ctrl.timer.start(1000)

    def switch_to_scan(self):
        """切到解析页"""
        self.stack.setCurrentIndex(1)
        if hasattr(self, 'vocab_ctrl') and hasattr(self.vocab_ctrl, 'timer'):
            self.vocab_ctrl.timer.stop()

    def switch_to_gaokao(self):
        """切到高考真题页"""
      
        # 1. 停止其他页面的干扰（比如计时器）
        if hasattr(self, 'vocab_ctrl'):
            self.vocab_ctrl.timer.stop()

        # 2. 强行把 Stack 切到这一页
        self.stackedWidget.setCurrentWidget(self.page_gaokao_widget)
        
        # 3. 终极唤醒：确保这一页是可见的
        self.page_gaokao_widget.setVisible(True)
        self.page_gaokao_widget.raise_() # 把它提到最顶层，防止被旧页面盖住
        
        # 4. 打印调试：如果还是看不见，看这里的输出
        print(f"当前 Stack 页数: {self.stackedWidget.count()}")
        print(f"当前显示的 Widget: {self.stackedWidget.currentWidget().objectName()}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HighSchoolEnglishAI()
    window.show()
    sys.exit(app.exec_())

