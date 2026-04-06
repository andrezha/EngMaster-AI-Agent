import sys
import os
from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QFrame
from vocab_module import VocabManager     
from analyzer_module import AnalyzerManager 
from exam_module import ExamManager       

class HighSchoolEnglishAI(QMainWindow):
    def __init__(self):
        # 🚀 必须有这一行！地基
        super().__init__() 
        
        # 0. 初始尺寸与居中
        self.resize(1280, 800)
        self.setMinimumSize(1280, 800)
        self.center_window()
    
        # 1. 定位路径
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        res_dir = os.path.join(self.base_path, "resources")
        
        # 2. 加载主框架 UI (这里面包含那个空的 stackedWidget)
        main_ui_path = os.path.join(res_dir, "main_window.ui")
        uic.loadUi(main_ui_path, self)

        # 🎯 立即设置显示单词闯关页面（防止其他页面被自动激活）
        self.stackedWidget.setCurrentIndex(0)

        # 3. 【重点】加载并强行嵌入"高考真题"
        gk_ui_path = os.path.join(res_dir, "page_gaokao.ui")
        
        # 🌟 关键改动：加载时就明确告诉它：你的"亲爹"是 stackedWidget
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
        self.btn_nav_core_vocab = self.findChild(QtWidgets.QPushButton, "btn_nav_core_vocab")
        self.btn_nav_scan = self.findChild(QtWidgets.QPushButton, "btn_nav_scan")
        self.btn_nav_gaokao = self.findChild(QtWidgets.QPushButton, "btn_nav_gaokao")
        self.btn_nav_full_exam = self.findChild(QtWidgets.QPushButton, "btn_nav_full_exam")

        self.nav_v_layout = self.findChild(QtWidgets.QVBoxLayout, "nav_v_layout")
        if self.nav_v_layout:
            self.nav_v_layout.setSpacing(18)
            self.nav_v_layout.setContentsMargins(10, 10, 10, 10)

        # --- 1. 侧边栏品牌区域 ---
        self.brand_label = QLabel("高考英语·智胜工作站")
        self.brand_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 30px;
                padding: 10px;
            }
        """)
        self.brand_label.setAlignment(QtCore.Qt.AlignCenter)
        self.brand_label.setFixedHeight(50)
        
        # 将品牌标签插入到布局最上方
        if self.nav_v_layout:
            self.nav_v_layout.insertWidget(0, self.brand_label)

        # 调整分割线
        self.nav_divider = self.findChild(QtWidgets.QFrame, "nav_divider")
        if self.nav_divider:
            self.nav_divider.setMinimumHeight(1)
            self.nav_divider.setMaximumHeight(1)
            self.nav_divider.setStyleSheet("QFrame { background-color: #e4e7ed; border: none; margin-top: 15px; margin-bottom: 10px; }")

        # 将所有导航按钮放入一个列表方便管理互斥高亮
        self.nav_buttons = [self.btn_nav_vocab, self.btn_nav_core_vocab, self.btn_nav_gaokao, self.btn_nav_full_exam]

        # 2. 实现按钮互斥（单选效果）
        self.sidebar_group = QtWidgets.QButtonGroup(self)
        self.sidebar_group.setExclusive(True)

        sidebar_qss = """
            QPushButton {
                height: 55px;
                border-radius: 12px;
                border: 1px solid #e4e7ed;
                background: transparent;
                color: #606266;
                font-size: 15px;
                text-align: left;
                padding-left: 15px;
                outline: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f5f7fa;
                border: 1px solid #c0c4cc;
            }
            QPushButton:checked {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #2c3e50;
            }
        """

        for btn in self.nav_buttons:
            if btn:
                btn.setCheckable(True)
                btn.setMinimumHeight(55)
                self.sidebar_group.addButton(btn)
                btn.setStyleSheet(sidebar_qss)

        # --- 3. 增值服务: AI 老师视觉锁定 ---
        self.is_pro = False
        
        # 为 btn_nav_scan 设置灰色虚线边框样式（非 Pro 用户）
        if self.btn_nav_scan and not self.is_pro:
            self.btn_nav_scan.setCheckable(False)  # 非 Pro 用户不可选中
            self.btn_nav_scan.setMinimumHeight(55)
            self.btn_nav_scan.setStyleSheet("""
                QPushButton {
                    height: 55px;
                    border-radius: 12px;
                    border: 1px dashed #dcdfe6;
                    background-color: #f5f5f5;
                    color: #a8abb2;
                    font-size: 15px;
                    text-align: left;
                    padding-left: 15px;
                    outline: none;
                    font-weight: bold;
                }
                QPushButton:hover { 
                    background-color: #f5f5f5; 
                    border: 1px dashed #c0c4cc;
                }
            """)
            # 点击时显示购买引导页
            self.btn_nav_scan.clicked.connect(self.show_ai_pro_guide)

        # 🎯 启动时默认显示单词闯关页面（必须在初始化子模块之前设置！）
        self.stack.setCurrentIndex(0)
        
        # 5. 启动子模块 (传入 self 以便子模块能操作 UI)
        self.vocab_ctrl = VocabManager(self)
        self.analyzer_ctrl = AnalyzerManager(self)
        self.exam_ctrl = ExamManager(self) 

        # 6. 绑定导航按钮点击事件
        if self.btn_nav_vocab:
            self.btn_nav_vocab.clicked.connect(self.switch_to_vocab)
        if self.btn_nav_gaokao:
            self.btn_nav_gaokao.clicked.connect(self.switch_to_gaokao)
        if self.btn_nav_full_exam:
            self.btn_nav_full_exam.clicked.connect(self.switch_to_full_exam)
            
        # 默认选中第一个（单词闯关）
        if self.btn_nav_vocab:
            self.btn_nav_vocab.setChecked(True)
        
        # 7. 绑定高考页面 AI 聊天功能
        self.bind_gaokao_ai_chat()
        
    def center_window(self):
        """让主窗口在屏幕居中显示"""
        qr = self.frameGeometry()
        # 获取屏幕中心点
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        # 将矩形的中心移动到屏幕中心
        qr.moveCenter(cp)
        # 将窗口移动到矩形的左上角
        self.move(qr.topLeft())

    def show_pro_tip(self):
        """显示未解锁提示"""
        # 如果是未解锁状态被点击，它会被选中。我们需要恢复它之前的状态，或者如果单选限制了，我们只能重置
        QtWidgets.QMessageBox.information(self, "解锁增值服务", "此功能为 PRO 专属增值服务，请升级后使用。")
        # 将焦点切回上一个合法页面，或简单处理
        if self.stackedWidget.currentIndex() == 0 and self.btn_nav_vocab:
            self.btn_nav_vocab.setChecked(True)
        elif self.stackedWidget.currentIndex() == 1 and self.btn_nav_gaokao:
            # 高考真题页面其实原本是index 2,但在现在代码里不知道怎么映射的，这里只做粗略恢复
            self.btn_nav_gaokao.setChecked(True)

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

    def switch_to_full_exam(self):
        """切到高考整卷页"""
        if hasattr(self, 'vocab_ctrl'):
            self.vocab_ctrl.timer.stop()
        # 暂时切换到高考真题页（整卷功能待扩展）
        self.switch_to_gaokao()

    def show_ai_pro_guide(self):
        """显示 AI 老师 Pro 购买引导页"""
        # 切换到高考页面并在 gk_ai_display 渲染购买引导
        self.switch_to_gaokao()
        
        gk_ai_display = self.page_gaokao_widget.findChild(QtWidgets.QTextEdit, "gk_ai_display")
        if gk_ai_display:
            gk_ai_display.setHtml("""
                <div style="text-align: center; padding: 40px 20px;">
                    <h2 style="color: #e67e22; font-size: 24px; margin-bottom: 20px;">🔒 AI 老师·题目精讲</h2>
                    <p style="font-size: 16px; color: #7f8c8d; line-height: 1.8; margin-bottom: 30px;">
                        该功能仅限 <b style="color: #2c3e50;">Pro 版本</b> 用户使用
                    </p>
                    <div style="background: #fdf6ec; border-radius: 12px; padding: 25px; margin: 20px 0;">
                        <p style="font-size: 15px; color: #2c3e50; line-height: 1.8;">
                            ✅ AI 实时解析每一道题目<br>
                            ✅ 深度讲解考点与解题思路<br>
                            ✅ 24/7 智能答疑辅导<br>
                            ✅ 个性化错题本与弱项分析
                        </p>
                    </div>
                    <p style="font-size: 14px; color: #95a5a6; margin-top: 20px;">
                        ⚠️ 升级解锁 AI 实时解析，让每一道题都物超所值
                    </p>
                </div>
            """)

    def bind_gaokao_ai_chat(self):
        """绑定高考页面 AI 聊天功能"""
        # 获取高考页面的聊天输入框和发送按钮
        gk_chat_input = self.page_gaokao_widget.findChild(QtWidgets.QLineEdit, "gk_chat_input")
        btn_gk_chat_send = self.page_gaokao_widget.findChild(QtWidgets.QPushButton, "btn_gk_chat_send")
        
        # 🎯 统一输入框样式（56px 高度，大圆角，与按钮对齐）
        if gk_chat_input:
            gk_chat_input.setFixedHeight(56)
            gk_chat_input.setStyleSheet("""
                QLineEdit {
                    background-color: #f8f9fa;
                    border: 2px solid #dee2e6;
                    border-radius: 16px;
                    font-size: 16px;
                    padding: 0px 20px;
                    color: #2c3e50;
                }
                QLineEdit:focus {
                    border: 2px solid #3498db;
                    background-color: #ffffff;
                }
                QLineEdit::placeholder {
                    color: #95a5a6;
                }
            """)
            gk_chat_input.returnPressed.connect(lambda: self.ask_ai(gk_chat_input))
        
        if btn_gk_chat_send:
            btn_gk_chat_send.clicked.connect(lambda: self.ask_ai(gk_chat_input))
            # 🎯 统一发送按钮样式（56px 高度，大圆角，醒目颜色）
            btn_gk_chat_send.setFixedHeight(56)
            btn_gk_chat_send.setStyleSheet("""
                QPushButton {
                    background-color: #2ecc71;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 12px 24px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #27ae60;
                }
                QPushButton:pressed {
                    background-color: #229954;
                }
            """)

    def ask_ai(self, chat_input):
        """AI 老师聊天功能（含 Pro 权限校验）"""
        # 获取 AI 显示区域
        gk_ai_display = self.page_gaokao_widget.findChild(QtWidgets.QTextEdit, "gk_ai_display")
        
        if not gk_ai_display:
            return
        
        # 🔒 Pro 权限校验
        if not self.is_pro:
            # 清空输入框
            if chat_input:
                chat_input.clear()
            
            # 追加红色警告
            current_html = gk_ai_display.toHtml()
            warning_html = """
                <div style="background: #fef0f0; border-left: 4px solid #e74c3c; padding: 15px; margin: 10px 0; border-radius: 4px;">
                    <p style="color: #e74c3c; font-size: 15px; font-weight: bold; margin: 0;">
                        ⚠️ 该功能仅限 Pro 版本。升级解锁 AI 实时解析。
                    </p>
                </div>
            """
            gk_ai_display.setHtml(current_html + warning_html)
            return
        
        # Pro 用户的正常逻辑（待实现 AI 调用）
        question = chat_input.text().strip() if chat_input else ""
        if not question:
            return
        
        if chat_input:
            chat_input.clear()
        
        # TODO: 这里将来接入真实的 AI 问答逻辑
        gk_ai_display.append(f"<p><b>🤖 AI老师：</b> 收到问题：{question}</p>")
        gk_ai_display.append("<p><i>（AI 实时解析功能即将上线...）</i></p>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HighSchoolEnglishAI()
    window.showMaximized()
    sys.exit(app.exec_())

