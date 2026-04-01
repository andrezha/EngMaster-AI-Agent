from PyQt5 import QtCore, QtWidgets

class AnalyzerManager:
    def __init__(self, main_win):
        self.win = main_win
        self.current_type = "完形填空" 
        
        # 1. 核心组件绑定 (必须和 UI XML 里的 name="xxx" 一致)
        self.raw_area = self.win.findChild(QtWidgets.QTextEdit, "raw_text_area")
        self.ai_area = self.win.findChild(QtWidgets.QTextEdit, "ai_answer_area")
        
        # UI 里的清空按钮名字叫 btn_scan
        self.btn_clear = self.win.findChild(QtWidgets.QPushButton, "btn_scan")
        # UI 里的开始按钮名字叫 btn_start_ai
        self.btn_start_ai = self.win.findChild(QtWidgets.QPushButton, "btn_start_ai")

        # 2. 🚀 题型按钮绑定 (对应你 XML 里的英文 objectName)
        self.type_config = {
            "btn_cloze": "完形填空",
            "btn_reading": "阅读理解",
            "btn_grammar": "语法填空",
            "btn_seven_five": "七选五",
            "btn_correction": "短文改错",
            "btn_writing": "写作续写"
        }

        for obj_name, q_type in self.type_config.items():
            btn = self.win.findChild(QtWidgets.QPushButton, obj_name)
            if btn:
                btn.clicked.connect(lambda checked, t=q_type: self.set_type(t))
                print(f"✅ 成功激活按钮: {obj_name} -> {q_type}")
            else:
                print(f"⚠️ 找不到按钮: {obj_name}")

        # 3. 逻辑连接 (加个判断防止 NoneType 报错)
        if self.btn_clear and self.raw_area:
            self.btn_clear.clicked.connect(self.raw_area.clear)
        
        if self.btn_start_ai:
            self.btn_start_ai.clicked.connect(self.action_ai_explain)

    def set_type(self, q_type):
        self.current_type = q_type
        
        # 统一的按钮皮肤（防止焦点蓝框，统一圆角和边框）
        normal_style = """
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                outline: none;  /* 👈 关键：去掉那个讨厌的蓝框 */
            }
            QPushButton:hover { background-color: #e2e6ea; }
        """
        
        active_style = """
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: 1px solid #27ae60;
                border-radius: 4px;
                padding: 5px;
                outline: none;
                font-weight: bold;
            }
        """

        for obj_name, name_text in self.type_config.items():
            btn = self.win.findChild(QtWidgets.QPushButton, obj_name)
            if btn:
                # 给所有按钮统一“去光标蓝框”
                if name_text == q_type:
                    btn.setStyleSheet(active_style)
                else:
                    btn.setStyleSheet(normal_style)
        
        if self.ai_area:
            self.ai_area.setPlainText(f"🎯 模式已切至：{q_type}")

    # ... 前面的 __init__ 和 set_type 保持不变 ...

    def action_ai_explain(self):
        """🚀 AI 解析的主入口"""
        # 1. 检查输入
        content = self.raw_area.toPlainText().strip()
        if not content:
            self.ai_area.setPlainText("⚠️ 请先在左侧粘贴题目文字！")
            return

        # 2. 🔒 物理锁：禁用按钮防止重复点击
        self.btn_start_ai.setEnabled(False) 
        self.btn_start_ai.setText("⏳ AI 老师正在思考中...")
        self.ai_area.setPlainText(f"⏳ 正在以【{self.current_type}】模式深度解析，请稍候...")

        # 3. 启动线程
        from ai_service import AIWorker
        self.worker = AIWorker(self.current_type, content)
        
        # 🎯 绑定信号
        self.worker.result_ready.connect(self.on_ai_finished)
        self.worker.error_occurred.connect(self.on_ai_error)
        self.worker.start()

    def on_ai_finished(self, msg):
        """✅ 成功时的处理"""
        self.btn_start_ai.setEnabled(True)
        self.btn_start_ai.setText("🚀 开始解析")
        
        # 使用 Markdown 让结果更漂亮
        self.ai_area.setMarkdown(f"### 【{self.current_type}解析结果】\n\n{msg}")

    def on_ai_error(self, err):
        """❌ 出错时的处理（不要在这里重新启动 Worker！）"""
        self.btn_start_ai.setEnabled(True)
        self.btn_start_ai.setText("🚀 开始解析")
        self.ai_area.setPlainText(f"❌ 解析引擎打了个盹: {err}")
        self.btn_start_ai.setEnabled(True)
        self.btn_start_ai.setText("🚀 开始解析")
        self.ai_area.setPlainText(f"❌ 解析出错：{err}")
        self.ai_area.setPlainText(f"❌ 出错啦：{err}")
        self.btn_start_ai.setEnabled(True)
        self.ai_area.setPlainText(f"❌ 解析引擎打了个盹: {err}")
        # 1. 检查输入区域是否存在，并获取文字
        if not self.raw_area:
            print("❌ 错误：找不到输入框 raw_text_area")
            return
            
        content = self.raw_area.toPlainText().strip()
        
        if not content:
            if self.ai_area:
                self.ai_area.setPlainText("⚠️ 请先在左侧粘贴题目文字！")
            return

        # 2. 修改界面提示，让用户知道 AI 正在按什么题型干活
        if self.ai_area:
            self.ai_area.setPlainText(f"⏳ AI 老师正在以【{self.current_type}】模式深度解析，请稍候...")

        # 3. 🚀 启动 AI 工人 (导入 AIWorker)
        try:
            from ai_service import AIWorker 
            
            # 这里的 self.current_type 就是你刚才点大按钮切好的题型
            self.worker = AIWorker(self.current_type, content)

            # 4. 绑定信号（结果回来后显示在右边）
            self.worker.result_ready.connect(lambda msg: self.ai_area.setPlainText(f"【{self.current_type}解析结果】\n\n{msg}"))
            self.worker.error_occurred.connect(lambda err: self.ai_area.setPlainText(f"❌ 引擎报错: {err}"))

            # 5. 🔥 启动！
            self.worker.start()
            
        except Exception as e:
            if self.ai_area:
                self.ai_area.setPlainText(f"❌ 启动失败: {str(e)}")