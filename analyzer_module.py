from PyQt5 import QtCore, QtWidgets

class AnalyzerManager:
    def __init__(self, main_win):
        self.win = main_win
        
        # 绑定 UI
        self.raw_area = self.win.findChild(QtWidgets.QTextEdit, "raw_text_area")
        self.ai_area = self.win.findChild(QtWidgets.QTextEdit, "ai_answer_area")
        self.btn_clear = self.win.findChild(QtWidgets.QPushButton, "btn_scan")
        self.btn_go = self.win.findChild(QtWidgets.QPushButton, "btn_start_ai")

        # 初始 UI 设置
        if self.btn_clear: self.btn_clear.setText("🧹 清空内容")
        if self.btn_go: self.btn_go.setText("🚀 开始解析")
        if self.raw_area: self.raw_area.setPlaceholderText("在此粘贴题目文字...")

        # 逻辑连接
        if self.btn_clear: self.btn_clear.clicked.connect(self.raw_area.clear)
        if self.btn_go: self.btn_go.clicked.connect(self.action_ai_explain)

    def action_ai_explain(self):
        content = self.raw_area.toPlainText().strip()
        if not content:
            self.ai_area.setPlainText("⚠️ 请先粘贴题目文字！")
            return
        self.ai_area.setPlainText("⏳ AI 老师正在解析，请稍候...")
        # 模拟 AI 延时
        QtCore.QTimer.singleShot(1000, lambda: self.ai_area.setPlainText(f"【解析结果】\n\n{content}\n\n[AI逻辑已就绪]"))