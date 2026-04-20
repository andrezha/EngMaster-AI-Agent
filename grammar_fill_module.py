#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语法填空模块
实现"专项练习"中的"语法填空"功能
"""

import os # Already imported
import re
from PySide6 import QtCore, QtWidgets, QtGui
from parsers.reading_parser import parse_reading_txt


class GrammarFillModule(QtWidgets.QWidget):
    """语法填空模块 - 独立页面"""
    
    """
    语法填空模块，用于专项练习中的语法填空题型。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_win = parent
        self.current_file_idx = 0
        self.time_left = 15 * 60  # 15分钟倒计时（秒）
        self.answers_revealed = False
        self.files = []
        self.current_data = None
        
        # 初始化UI
        self._init_ui()
        self._load_files()
        self._load_passage(0)
        self._start_timer()
        
    def _init_ui(self):
        """
        初始化界面布局，包括左右分栏、文章显示区、倒计时和答题区。
        """
        """初始化界面布局"""
        # 主布局 - 水平布局，左右分栏
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # ============ 左侧：文章显示区 ============
        left_panel = QtWidgets.QVBoxLayout()
        left_panel.setSpacing(10)
        
        # 文章标题
        self.title_label = QtWidgets.QLabel("")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 8px;
            }
        """)
        self.title_label.setWordWrap(True)
        left_panel.addWidget(self.title_label)
        
        # 文章正文显示区
        self.passage_display = QtWidgets.QTextBrowser()
        self.passage_display.setStyleSheet("""
            QTextBrowser {
                font-size: 18px;
                line-height: 1.8;
                color: #2c3e50;
                background-color: #ffffff;
                border: 1px solid #e4e7ed;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        self.passage_display.setOpenExternalLinks(True)
        left_panel.addWidget(self.passage_display, stretch=1)
        
        # 上一题/下一题按钮
        nav_btn_layout = QtWidgets.QHBoxLayout()
        nav_btn_layout.setSpacing(15)
        
        self.btn_prev = QtWidgets.QPushButton("◀ 上一题")
        self.btn_prev.setFixedHeight(45)
        self.btn_prev.setStyleSheet(self._btn_stylesheet("#3498db"))
        self.btn_prev.clicked.connect(self._prev_passage)
        nav_btn_layout.addWidget(self.btn_prev)
        
        self.btn_next = QtWidgets.QPushButton("下一题 ▶")
        self.btn_next.setFixedHeight(45)
        self.btn_next.setStyleSheet(self._btn_stylesheet("#3498db"))
        self.btn_next.clicked.connect(self._next_passage)
        nav_btn_layout.addWidget(self.btn_next)
        
        left_panel.addLayout(nav_btn_layout)
        
        # ============ 右侧：交互区 ============
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(15)
        
        # 倒计时 - 右上角红色显示
        timer_layout = QtWidgets.QHBoxLayout()
        timer_layout.addStretch()
        self.timer_label = QtWidgets.QLabel("15:00")
        self.timer_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                font-size: 24px;
                font-weight: bold;
                padding: 8px 16px;
                background-color: #fef0f0;
                border-radius: 8px;
                border: 2px solid #e74c3c;
            }
        """)
        timer_layout.addWidget(self.timer_label)
        right_panel.addLayout(timer_layout)
        
        # 题号列表区域
        self.questions_label = QtWidgets.QLabel("答题区域（61-70）")
        self.questions_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 8px;
            }
        """)
        right_panel.addWidget(self.questions_label)
        
        # 题号和答案显示区域
        self.questions_scroll = QtWidgets.QScrollArea()
        self.questions_scroll.setWidgetResizable(True)
        self.questions_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e4e7ed;
                border-radius: 12px;
                background-color: #fafafa;
            }
        """)
        
        self.questions_container = QtWidgets.QWidget()
        self.questions_layout = QtWidgets.QVBoxLayout(self.questions_container)
        self.questions_layout.setSpacing(10)
        self.questions_layout.setAlignment(QtCore.Qt.AlignTop)
        self.questions_layout.setContentsMargins(5, 5, 5, 5)
        
        # 设置容器大小策略，确保内容能正确显示
        self.questions_container.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )
        self.questions_container.setMinimumWidth(280)
        
        self.questions_scroll.setWidget(self.questions_container)
        right_panel.addWidget(self.questions_scroll, stretch=1)
        
        # 查看答案按钮
        self.btn_reveal = QtWidgets.QPushButton("👁 查看答案与解析")
        self.btn_reveal.setFixedHeight(50)
        self.btn_reveal.setStyleSheet(self._btn_stylesheet("#2ecc71"))
        self.btn_reveal.clicked.connect(self._toggle_answers)
        right_panel.addWidget(self.btn_reveal)
        
        # 返回按钮
        self.btn_back = QtWidgets.QPushButton("← 返回专项练习")
        self.btn_back.setFixedHeight(45)
        self.btn_back.setStyleSheet(self._btn_stylesheet("#95a5a6"))
        self.btn_back.clicked.connect(self._go_back)
        right_panel.addWidget(self.btn_back)
        
        # 添加左右面板到主布局
        main_layout.addLayout(left_panel, stretch=3)
        main_layout.addLayout(right_panel, stretch=2)
        
    def _btn_stylesheet(self, color):
        """
        生成统一的按钮样式表。
        """
        """统一的按钮样式"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 40)};
            }}
        """
    
    def _darken_color(self, hex_color, amount=20):
        """
        将十六进制颜色值变暗。
        """
        """将颜色变暗"""
        hex_color = hex_color.lstrip('#')
        r = min(255, max(0, int(hex_color[0:2], 16) - amount))
        g = min(255, max(0, int(hex_color[2:4], 16) - amount))
        b = min(255, max(0, int(hex_color[4:6], 16) - amount))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _load_files(self):
        """
        加载 data/语法填空/ 目录下的所有 TXT 文件。
        """
        """加载 data/语法填空/ 目录下的所有 TXT 文件"""
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "语法填空")
        if not os.path.exists(data_dir):
            # 尝试相对路径
            data_dir = "data/语法填空"
        
        if os.path.exists(data_dir):
            self.files = sorted([
                f for f in os.listdir(data_dir) 
                if f.endswith('.txt')
            ])
            print(f"语法填空：加载了 {len(self.files)} 个文件")
        else:
            print(f"语法填空数据目录不存在: {data_dir}")
            self.files = []
    
    def _load_passage(self, idx):
        """
        加载指定索引的文章，并更新UI显示。
        """
        """加载指定索引的文章"""
        if not self.files or idx < 0 or idx >= len(self.files):
            return
        
        self.current_file_idx = idx
        file_path = os.path.join("data", "语法填空", self.files[idx])
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用解析器解析内容
            self.current_data = parse_reading_txt(content)
            
            # 更新标题
            year = self.current_data.get('year', '')
            category = self.current_data.get('category', '')
            self.title_label.setText(f"📝 语法填空 - {year}年 {category}")
            
            # 更新文章显示 - 高亮空白处
            passage = self.current_data.get('passage', '')
            passage_html = self._highlight_blanks(passage)
            self.passage_display.setHtml(f"""
                <html>
                <head>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                            font-size: 18px;
                            line-height: 1.8;
                            color: #2c3e50;
                        }}
                        .blank {{
                            display: inline-block;
                            border-bottom: 2px solid #3498db;
                            background-color: #ebf5fb;
                            padding: 0 4px;
                            margin: 0 2px;
                            border-radius: 3px;
                            font-weight: bold;
                            color: #2980b9;
                            min-width: 30px;
                            text-align: center;
                        }}
                    </style>
                </head>
                <body>
                    {passage_html}
                </body>
                </html>
            """)
            
            # 更新题号区域
            self._build_questions_area()
            
            # 重置答案显示状态
            self.answers_revealed = False
            self.btn_reveal.setText("👁 查看答案与解析")
            
        except Exception as e:
            print(f"加载语法填空文件失败: {file_path}, 错误: {e}")
    
    def _highlight_blanks(self, passage):
        """
        高亮文章中的空白题号，将其转换为 HTML 样式。
        """
        """高亮文章中的空白题号"""
        # 获取所有题号
        items = self.current_data.get('items', []) if self.current_data else []
        q_ids = [item.get('q_id', '') for item in items]
        
        # 将换行转换为HTML的<br>
        text = passage.replace('\n', '<br>')
        
        # 为每个题号添加高亮样式
        for q_id in q_ids:
            # 使用单词边界匹配，避免匹配到其他数字的一部分（如1969中的69）
            # 匹配前后有空白、全角空格、标点或行首行尾的题号
            import re
            pattern = rf'(?<!\d)(\s*{q_id}\s*)(?!\d)'
            replacement = r'<span class="blank">\1</span>'
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _build_questions_area(self):
        """
        构建题号和答案输入/显示区域。
        """
        """构建题号和答案显示区域"""
        # 清空现有内容
        while self.questions_layout.count():
            item = self.questions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        items = self.current_data.get('items', []) if self.current_data else []
        
        if not items:
            # 如果没有解析出题目，尝试从原始内容提取
            label = QtWidgets.QLabel("暂无题目数据")
            label.setStyleSheet("QLabel { color: #999; padding: 20px; font-size: 14px; }")
            self.questions_layout.addWidget(label)
            return
        
        # 更新题号标签，显示实际题号范围
        q_ids = [item.get('q_id', '') for item in items]
        self.questions_label.setText(f"答题区域（{q_ids[0]}-{q_ids[-1]}）")
        
        for item in items:
            q_id = item.get('q_id', '')
            answer = item.get('answer', '')
            analysis = item.get('analysis', '')
            
            # 创建题号容器
            q_container = QtWidgets.QFrame()
            q_container.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border: 1px solid #e4e7ed;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            q_layout = QtWidgets.QHBoxLayout(q_container)
            q_layout.setSpacing(10)
            q_layout.setContentsMargins(10, 10, 10, 10)
            
            # 题号标签（固定宽度，右对齐）
            q_label = QtWidgets.QLabel(f"{q_id}.")
            q_label.setFixedWidth(35)
            q_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #2c3e50;
                    padding: 5px;
                }
            """)
            q_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            q_layout.addWidget(q_label)
            
            # 答案输入框
            answer_input = QtWidgets.QLineEdit()
            answer_input.setObjectName(f"input_{q_id}")
            answer_input.setPlaceholderText("请输入答案...")
            answer_input.setStyleSheet("""
                QLineEdit {
                    font-size: 15px;
                    padding: 8px 12px;
                    border: 2px solid #dce4ec;
                    border-radius: 6px;
                    background-color: #fafafa;
                }
                QLineEdit:focus {
                    border-color: #3498db;
                    background-color: #ffffff;
                }
            """)
            q_layout.addWidget(answer_input, stretch=1)
            
            # 答案显示区域（初始隐藏，查看答案时显示）
            answer_label = QtWidgets.QLabel("")
            answer_label.setObjectName(f"answer_{q_id}")
            answer_label.setWordWrap(True)
            answer_label.setStyleSheet("""
                QLabel {
                    font-size: 15px;
                    color: #2c3e50;
                    padding: 8px;
                    background-color: #f0f9ff;
                    border-radius: 6px;
                    border-left: 4px solid #3498db;
                }
            """)
            answer_label.hide()
            q_layout.addWidget(answer_label, stretch=1)
            
            # 解析显示区域（初始隐藏，查看答案时显示）
            analysis_label = QtWidgets.QLabel("")
            analysis_label.setObjectName(f"analysis_{q_id}")
            analysis_label.setWordWrap(True)
            analysis_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #e74c3c;
                    padding: 8px;
                    background-color: #fef0f0;
                    border-radius: 6px;
                    border-left: 4px solid #e74c3c;
                    line-height: 1.6;
                }
            """)
            analysis_label.hide()
            q_layout.addWidget(analysis_label, stretch=2)
            
            # 存储答案和解析数据
            q_container.setProperty("answer", answer)
            q_container.setProperty("analysis", analysis)
            
            self.questions_layout.addWidget(q_container)
        
        # 添加弹性空间到底部
        self.questions_layout.addStretch()
    
    def _toggle_answers(self):
        """
        切换答案和解析的显示/隐藏状态。
        """
        """切换答案显示/隐藏"""
        self.answers_revealed = not self.answers_revealed
        
        if self.answers_revealed:
            self.btn_reveal.setText("🙈 隐藏答案与解析")
            self.btn_reveal.setStyleSheet(self._btn_stylesheet("#e67e22"))
        else:
            self.btn_reveal.setText("👁 查看答案与解析")
            self.btn_reveal.setStyleSheet(self._btn_stylesheet("#2ecc71"))
        
        # 显示/隐藏所有答案和解析
        items = self.current_data.get('items', []) if self.current_data else []
        
        for i, item in enumerate(items):
            q_id = item.get('q_id', '')
            answer = item.get('answer', '')
            analysis = item.get('analysis', '')
            
            # 获取容器（使用 findChild 通过输入框的 objectName 来查找容器）
            input_field = self.questions_container.findChild(QtWidgets.QLineEdit, f"input_{q_id}")
            if not input_field:
                continue
            
            container = input_field.parentWidget()
            
            # 获取答案标签和解析标签
            answer_label = container.findChild(QtWidgets.QLabel, f"answer_{q_id}")
            analysis_label = container.findChild(QtWidgets.QLabel, f"analysis_{q_id}")
            
            # 切换输入框和答案标签的显示
            input_field.setVisible(not self.answers_revealed)
            
            if answer_label:
                answer_label.setText(f"✅ 参考答案：<b>{answer}</b>")
                answer_label.setVisible(self.answers_revealed)
            
            if analysis_label:
                # 清理解析文本，提取对应题号的解析
                analysis_text = self._extract_analysis_for_question(analysis, q_id)
                analysis_label.setText(f"📖 解析：<br>{analysis_text}")
                analysis_label.setVisible(self.answers_revealed)
    
    def _extract_analysis_for_question(self, full_analysis, q_id):
        """
        从完整的解析文本中提取指定题号的解析内容。
        """
        """从完整解析中提取指定题号的解析"""
        if not full_analysis:
            return "暂无解析"
        
        # 尝试匹配题号开头的解析段落
        # 匹配 "61．" 或 "61." 开头的内容
        pattern = rf'{q_id}[．.]\s*(.*?)(?=\d+[．.]|$)'
        match = re.search(pattern, full_analysis, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # 如果没有匹配到，返回完整解析
        return full_analysis[:200] + "..." if len(full_analysis) > 200 else full_analysis
    
    def _prev_passage(self):
        """
        切换到上一篇文章。
        """
        """切换到上一篇文章"""
        if self.current_file_idx > 0:
            self._load_passage(self.current_file_idx - 1)
    
    def _next_passage(self):
        """
        切换到下一篇文章。
        """
        """切换到下一篇文章"""
        if self.current_file_idx < len(self.files) - 1:
            self._load_passage(self.current_file_idx + 1)
    
    def _go_back(self):
        """
        返回专项练习主菜单。
        """
        """返回专项练习主菜单"""
        if self.main_win:
            # 停止计时器
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
            # 返回到高考页面（作为专项练习的入口）
            self.main_win.switch_to_gaokao()
    
    def _start_timer(self):
        """
        启动倒计时计时器。
        """
        """启动倒计时"""
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
    
    def _tick(self):
        """
        计时器滴答事件处理函数，更新倒计时显示，并在时间到时自动显示答案。
        """
        """计时器滴答"""
        if self.time_left > 0:
            self.time_left -= 1
            minutes = self.time_left // 60
            seconds = self.time_left % 60
            self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
            
            # 最后5分钟变红闪烁
            if self.time_left <= 300:
                self.timer_label.setStyleSheet("""
                    QLabel {
                        color: #e74c3c;
                        font-size: 24px;
                        font-weight: bold;
                        padding: 8px 16px;
                        background-color: #fef0f0;
                        border-radius: 8px;
                        border: 2px solid #e74c3c;
                    }
                """)
        else:
            self.timer.stop()
            # 时间到，自动显示答案
            if not self.answers_revealed:
                QtWidgets.QMessageBox.information( # Needs to be imported from PySide6.QtWidgets
                    self, "时间到", "⏰ 答题时间已到！系统将自动显示答案与解析。"
                )
                self._toggle_answers()