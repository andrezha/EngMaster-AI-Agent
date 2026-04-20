import sys
import re
from PySide6 import QtWidgets # 导入 QtWidgets 模块
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextBrowser, QScrollArea, QStackedWidget,
                             QPushButton, QLabel, QComboBox, QLineEdit, QFrame, QButtonGroup)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# ==========================================================
# 1. 题目卡片：强行在UI上画出红色分值标签
# ==========================================================
class QuestionCard(QWidget):
    """
    用于显示单个题目及其选项或输入框的 UI 组件。
    """
    def __init__(self, data, q_type, current_ans="", sync_func=None):
        super().__init__()
        self.data = data # Store data for options
        self.q_type = q_type # Store q_type for options
        self.current_ans = current_ans # Store current answer for pre-selection
        self.main_layout = QVBoxLayout(self)
        
        # 提取题号数字
        raw_qid = str(data.get('q_id', ''))
        self.qid = re.sub(r'\D', '', raw_qid)
        self.sync_func = sync_func
        
        # --- 计算高考分值 ---
        num = int(self.qid) if self.qid.isdigit() else 0
        if 21 <= num <= 40: weight = "2.5"
        elif 41 <= num <= 55: weight = "1.0"
        elif 56 <= num <= 65: weight = "1.5"
        else: weight = "2.5"

        # --- 顶部行：题号 + 显眼的红色分数标签 ---
        top_row_layout = QHBoxLayout()
        
        # 题号
        qid_label = QLabel(f"第 {self.qid} 题")
        qid_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_row_layout.addWidget(qid_label)
        
        # 分数显示：深蓝色背景，白色文字
        score_tag = QLabel(f" {weight} 分 ")
        score_tag.setStyleSheet("""
            background-color: #2E5B88; 
            color: white; 
            font-weight: bold; 
            border-radius: 4px; 
            padding: 2px 8px;
            font-size: 13px;
        """)
        top_row_layout.addWidget(score_tag)
        top_row_layout.addStretch() # Push qid and score to the left
        self.main_layout.addLayout(top_row_layout)

        # Question content (if any)
        q_content = data.get('content', '') # 七选五的 q_content 是空白处的提示文本
        if q_content and q_type != "grammar": # 语法填空没有单独的题干，七选五和阅读理解有
            q_content_label = QLabel(f"{q_content}")
            q_content_label.setWordWrap(True)
            q_content_label.setStyleSheet("font-size: 15px; color: #2c3e50; padding: 5px 0 5px 0;")
            self.main_layout.addWidget(q_content_label)

        # 答题交互区
        self.input_widget = None # Renamed from input_node to avoid confusion with layout
        
        if q_type == "grammar":
            self.input_widget = QLineEdit()
            self.input_widget.setText(current_ans)
            self.input_widget.setPlaceholderText("请输入答案...")
            self.input_widget.textChanged.connect(self._notify_grammar)
            self.input_widget.setStyleSheet("""
                QLineEdit {
                    font-size: 15px;
                    padding: 8px 12px;
                    border: 2px solid #dce4ec;
                    border-radius: 8px;
                    background-color: #fafafa;
                }
                QLineEdit:focus {
                    border-color: #3498db;
                    background-color: #ffffff;
                }
            """)
            self.main_layout.addWidget(self.input_widget)
        else: # Reading, Cloze, Seven-five (multiple choice)
            self.button_group = QButtonGroup(self)
            self.button_group.setExclusive(True) # Ensure only one option can be selected
            
            options_layout = QVBoxLayout()
            options_layout.setContentsMargins(0, 5, 0, 0) # Small top margin for options
            options_layout.setSpacing(2) # Compact spacing between buttons

            opts = data.get('options', {})
            # Handle list form (seven-five) or dict form (reading/cloze)
            if isinstance(opts, list): # Seven-five
                for opt in opts:
                    self._add_option_button(opt['label'], opt['content'], options_layout)
            else: # Reading/Cloze
                for label, content in sorted(opts.items()): # Sort options A, B, C, D
                    self._add_option_button(label, content, options_layout)
            
            self.main_layout.addLayout(options_layout)
            
            # Pre-select answer if current_ans is provided
            if current_ans:
                for button in self.button_group.buttons():
                    # Extract label from button text (e.g., "A. Option text" -> "A")
                    button_label = button.text().split('.')[0].strip()
                    if button_label == current_ans:
                        button.setChecked(True)
                        break

    def _add_option_button(self, label, content, layout):
        """
        为选择题添加一个选项按钮。
        """
        btn = QPushButton(f"{label}. {content}")
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #f9fafb;
                font-size: 14px;
                color: #374151;
                margin: 2px 0;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                border-color: #9ca3af;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                color: white;
                border: 1px solid #2563eb;
                font-weight: bold;
            }
        """)
        btn.clicked.connect(lambda checked, l=label: self._notify_choice(l, checked))
        self.button_group.addButton(btn)
        layout.addWidget(btn)

    def _notify_choice(self, choice, checked):
        """
        当选择题选项被点击时，通知外部同步函数。
        """
        if checked:
            self.sync_func(self.qid, choice)

    def _notify_grammar(self, text):
        """
        当语法填空输入框内容改变时，通知外部同步函数。
        """
        self.sync_func(self.qid, text)

# ==========================================================
# 2. 结果结算页
# ==========================================================
class ResultPage(QWidget):
    """
    显示考试成绩结算单的页面，包括总分、耗时、错题列表和解析。
    """
    def __init__(self, exit_cb):
        super().__init__()
        self._full_res = None # Store the full result for analysis lookup
        self.current_displayed_analysis_qid = None # Track currently displayed analysis
        self.l = QVBoxLayout(self) # Main layout for ResultPage
        
        # Ensure the main layout can expand vertically
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.l.setContentsMargins(20, 20, 20, 20) # Add some padding around the content
        self.l.setSpacing(15) # Add spacing between elements

        self.exit_cb = exit_cb

        # 用于显示题目解析的 QTextBrowser
        self.analysis_detail_box = QTextBrowser()
        self.analysis_detail_box.setReadOnly(True)
        self.analysis_detail_box.setStyleSheet("""
            QTextBrowser {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
                color: #34495e;
                min-height: 100px; /* Ensure a minimum height even when empty */
            }
        """.replace("min-height: 100px;", "min-height: 250px;")) # 增大解析框的最小高度
        self.analysis_detail_box.hide() # 初始隐藏
        # 初始不将 analysis_detail_box 添加到布局中，而是在 update_res 中动态添加

    def update_res(self, res, elapsed_time_seconds, all_questions_data): # 修正了参数传递，添加 all_questions_data
        """
        更新并显示考试结果。
        """
        while self.l.count(): self.l.takeAt(0).widget().deleteLater()
        
        t = QLabel("🎉 考试成绩结算单"); t.setAlignment(Qt.AlignCenter); t.setStyleSheet("font-size: 26px; font-weight: bold; color: #2ecc71;")
        self.l.addWidget(t)
        
        # 计算理想时间 (假设80分卷的理想时间是60分钟)
        ideal_time_minutes = 60
        used_minutes = elapsed_time_seconds // 60
        used_seconds = elapsed_time_seconds % 60
        
        time_info_html = f"""
            <div style='text-align:center; font-size:16px; color:#555;'>
                <p>理想时间：<b style='color:#27ae60;'>{ideal_time_minutes} 分钟</b></p>
                <p>本次耗时：<b style='color:#e67e22;'>{used_minutes} 分 {used_seconds} 秒</b></p>
            </div>
        """

        score_val = QLabel(f"总得分：{res['total']:.1f} / 80.0 {time_info_html}")
        score_val.setAlignment(Qt.AlignCenter)
        score_val.setStyleSheet("background: #f1f2f6; border: 2px solid #2f3542; padding: 25px; font-size: 24px; border-radius: 15px; font-weight: bold; color: #2E5B88;")
        score_val.setTextFormat(Qt.RichText) # 确保 QLabel 能够正确渲染 HTML
        self.l.addWidget(score_val)

        # 将结果分成左右两列
        main_results_layout = QHBoxLayout()
        left_column_layout = QVBoxLayout()
        right_column_layout = QVBoxLayout()
        
        # 题型映射
        mapping = {"reading":"阅读理解", "seven_five":"七选五", "cloze":"完形填空", "grammar":"语法填空"}
        
        for k, v in res['details'].items():
            f = QFrame(); f.setStyleSheet("background: white; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px; padding: 10px;")
            fl = QVBoxLayout(f)
            
            # 题型标题和得分
            fl.addWidget(QLabel(f"<h4 style='color:#2c3e50; margin:0;'>【{mapping.get(k, k)}】得分：<b style='color:#2E5B88;'>{v['score']:.1f}</b> / {v['total_possible_score']:.1f}</h4>"))
            
            # 错题分析
            if v['wrongs']:
                wrongs_label = QLabel(f"<b style='color:#e74c3c;'>错题 ({len(v['wrongs'])}):</b>") # 错题只数
                wrongs_label.setStyleSheet("padding-top: 10px; padding-bottom: 5px;") # 增加上下边距，避免过高
                fl.addWidget(wrongs_label)
                
                # 直接显示所有错题，不使用内部滚动区域
                for wrong_item in v['wrongs_details']:
                    # 为每个错题创建一个 QWidget 容器，包含文本和按钮
                    wrong_item_widget = QWidget()
                    wrong_item_h_layout = QHBoxLayout(wrong_item_widget)
                    wrong_item_h_layout.setContentsMargins(0,0,0,0) # 调整边距

                    wrong_text = f"❌ Q{wrong_item['id']} | 你的答案: <b style='color:#e74c3c;'>{wrong_item['user']}</b> | 正确答案: <b style='color:#27ae60;'>{wrong_item['correct']}</b>"
                    wrong_text_label = QLabel(wrong_text) # 错题文本标签
                    wrong_item_h_layout.setAlignment(Qt.AlignTop) # 确保按钮和文本从顶部对齐
                    wrong_text_label.setWordWrap(True) # 确保文本自动换行
                    wrong_item_h_layout.addWidget(wrong_text_label, 1) # 伸展因子 1

                    # 添加分析按钮
                    analysis_btn = QPushButton("查看解析")
                    analysis_btn.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.MinimumExpanding) # 允许按钮根据文本高度拉伸
                    analysis_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #3498db;
                            color: white;
                            border: none;
                            border-radius: 5px;
                            font-size: 12px;
                            padding: 3px 6px;
                        }
                        QPushButton:hover { background-color: #2980b9; }
                    """)
                    # 绑定点击事件，传递 q_id 和 all_questions_data
                    analysis_btn.clicked.connect(lambda checked, q_id=wrong_item['id']: self._display_question_analysis(q_id, all_questions_data))
                    wrong_item_h_layout.addWidget(analysis_btn)

                    fl.addWidget(wrong_item_widget) # 将新的 widget 添加到部分布局中
            else:
                fl.addWidget(QLabel("<p style='color:#27ae60;'>✅ 本部分全对！</p>"))
            
            # 根据题型分配到左右列
            if k in ["reading", "seven_five"]:
                left_column_layout.addWidget(f)
            elif k in ["cloze", "grammar"]:
                right_column_layout.addWidget(f)
        
        # 每次刷新结果时，隐藏解析框并重置当前显示的题号
        self.analysis_detail_box.hide()
        self.current_displayed_analysis_qid = None
        
        main_results_layout.addLayout(left_column_layout)
        main_results_layout.addLayout(right_column_layout)
        
        # 将主结果布局添加到 ResultPage 的主布局中
        self.l.addLayout(main_results_layout)
        
        # 退出按钮
        b = QPushButton("退出系统"); b.setFixedHeight(50); b.setStyleSheet("background: #2f3542; color: white; font-weight: bold;"); b.clicked.connect(self.exit_cb)
        self.l.addWidget(b)

    def _display_question_analysis(self, q_id, all_questions_data):
        """
        显示或隐藏指定题目的解析。
        """
        """
        显示或隐藏指定题目的解析。
        如果点击的按钮是当前正在显示的解析，则隐藏它；否则显示新的解析。
        """
        if self.current_displayed_analysis_qid == q_id and self.analysis_detail_box.isVisible():
            print(f"DEBUG: Hiding analysis for Q{q_id}")
            self.analysis_detail_box.hide()
            self.current_displayed_analysis_qid = None
            return

        q_data = all_questions_data.get(q_id)
        if not q_data:
            self.analysis_detail_box.setHtml(f"<p style='color:red;'>未找到题号 {q_id} 的详细信息。</p>")
            print(f"DEBUG: Showing 'not found' analysis for Q{q_id}")
            self.analysis_detail_box.show()
            self.current_displayed_analysis_qid = q_id
            return

        user_ans = ""
        # 从 _full_res 中查找用户的答案
        if self._full_res and 'details' in self._full_res:
            for detail_type, details in self._full_res['details'].items():
                for wrong_detail in details['wrongs_details']:
                    if wrong_detail['id'] == q_id:
                        user_ans = wrong_detail['user']
                        break
                if user_ans: break

        question_html = f"<h4 style='color:#2c3e50;'>Q{q_id}. {q_data['content']}</h4>"

        # 添加选项（如果存在）
        if q_data['options']:
            question_html += "<p><b>选项:</b></p><ul>"
            if isinstance(q_data['options'], list): # 七选五
                for opt in q_data['options']:
                    question_html += f"<li>{opt['label']}. {opt['content']}</li>"
            else: # 阅读/完形
                for label, content in sorted(q_data['options'].items()):
                    question_html += f"<li>{label}. {content}</li>"
            question_html += "</ul>"

        question_html += f"<p><b>你的答案:</b> <span style='color:#e74c3c;'>{user_ans}</span></p>"
        question_html += f"<p><b>正确答案:</b> <span style='color:#27ae60;'>{q_data['answer']}</span></p>"
        question_html += f"<p><b>解析:</b></p><div style='background:#f0f9ff; padding:10px; border-radius:5px; border-left:3px solid #3498db;'>{q_data['analysis']}</div>"

        self.analysis_detail_box.setHtml(question_html)
        print(f"DEBUG: Showing analysis for Q{q_id}")
        self.analysis_detail_box.show()
        self.analysis_detail_box.verticalScrollBar().setValue(0) # 滚动到顶部
        self.current_displayed_analysis_qid = q_id

# ==========================================================
# 3. 考试系统主逻辑 (HSEExamSystem)
# ==========================================================
class HSEExamSystem(QWidget): # 修改基类为 QWidget
    """
    全真战场模块的主逻辑，负责管理考试流程、UI切换和最终成绩计算。
    """
    # 静态方法：解析原始解析文本，按题号分割
    @staticmethod
    def _parse_analysis_text(analysis_text):
        analysis_by_q = {}
        if not analysis_text:
            return analysis_by_q

        # Split by common patterns like 【N题详解】 or N.
        # This regex splits, keeping the delimiters.
        parts = re.split(r'(【\d+题详解】|\d+[．.])', analysis_text)
        
        current_q_num = ""
        
        # Find the first actual delimiter
        first_delimiter_idx = -1
        for i, part in enumerate(parts):
            if re.match(r'【\d+题详解】|\d+[．.]', part.strip()):
                first_delimiter_idx = i
                break
                
        if first_delimiter_idx == -1: # No delimiters found, return empty
            return analysis_by_q
            
        # Process from the first delimiter onwards
        for i in range(first_delimiter_idx, len(parts)):
            part = parts[i].strip()
            if not part:
                continue
            
            q_match = re.search(r'(\d+)', part)
            if q_match and (re.match(r'【\d+题详解】', part) or re.match(r'\d+[．.]', part)):
                current_q_num = q_match.group(1)
                analysis_by_q[current_q_num] = "" # Initialize analysis for this q_id
            elif current_q_num:
                analysis_by_q[current_q_num] += part + "\n"
        return {q: text.strip() for q, text in analysis_by_q.items()}
    def __init__(self, data_list):
        """
        初始化 HSEExamSystem。
        """
        super().__init__()
        self.all_data = data_list
        self.ans_cache = {}
        self.cur_idx = 0
        self.exam_start_time = None # 新增：记录考试开始时间
        # self.setWindowTitle("高考英语整卷模拟 (不含听力和作文)") # QWidget 没有 setWindowTitle，已移除
        # self.resize(1200, 900) # QWidget 没有 resize，已移除
        
        self.main_layout = QVBoxLayout(self) # HSEExamSystem 的主布局
        
        self.screen_manager_stack = QStackedWidget() # 负责管理开始界面、考试内容和结果页
        self.screen_manager_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.main_layout.addWidget(self.screen_manager_stack)
        
        # exam_view 现在包含一个 QStackedLayout 来切换开始界面和考试内容界面
        self.exam_view = QWidget()
        self.exam_view.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._setup_exam_screens() # 设置考试屏幕，包括开始界面和实际考试界面，其内部会使用 exam_screens_stack
        # self.stack.addWidget(self.exam_view) # 移除此行，因为 self.stack 不存在，应使用 self.screen_manager_stack
        self.screen_manager_stack.addWidget(self.exam_view) # 确保使用正确的堆栈
        
        self.res_view = ResultPage(self.close)
        # Wrap ResultPage in a QScrollArea to enable scrolling for the entire result page
        self.res_scroll_area = QScrollArea()
        self.res_scroll_area.setWidgetResizable(True) # Allow the ResultPage to take its natural size
        self.res_scroll_area.setWidget(self.res_view)
        self.screen_manager_stack.addWidget(self.res_scroll_area)
        
        # 初始显示 exam_view (其中包含 start_screen_widget)
        self.screen_manager_stack.setCurrentWidget(self.exam_view)

    def build_exam_ui(self):
        """
        构建考试界面的主UI布局（已废弃，功能已移至 _build_exam_content_ui）。
        """
        main_l = QVBoxLayout(self.exam_view)
        self.header_l = QLabel(""); self.header_l.setAlignment(Qt.AlignCenter); self.header_l.setStyleSheet("font-size: 20px; font-weight: bold; color: #2980b9; background: #f8f9fa; padding: 10px;")
        main_l.addWidget(self.header_l)
        
        body = QHBoxLayout() # This layout holds the passage and the questions panel
        self.passage_box = QTextBrowser(); self.passage_box.setStyleSheet("font-size: 17px; line-height: 1.6; padding: 20px; background: white;")
        body.addWidget(self.passage_box, 1)

        # 右侧答题区
        right_panel = QVBoxLayout()
        self.q_scroll = QScrollArea() # Removed setWidgetResizable(True) to allow content to overflow and trigger scrollbar
        self.q_widget = QWidget(); self.q_layout = QVBoxLayout(self.q_widget); self.q_layout.setAlignment(Qt.AlignTop)
        self.q_scroll.setWidget(self.q_widget)
        right_panel.addWidget(self.q_scroll, 1) # Make the scroll area expand vertically
        
        # 【提交按钮】强行出现在右侧下方，最后一页才显示
        self.submit_btn = QPushButton("🏁 确认交卷并计算总分")
        self.submit_btn.setFixedHeight(60)
        self.submit_btn.setStyleSheet("background-color: #ff4757; color: white; font-weight: bold; font-size: 18px; border-radius: 8px;")
        self.submit_btn.clicked.connect(self.final_calc)
        self.submit_btn.hide()
        right_panel.addWidget(self.submit_btn)

        body.addLayout(right_panel, 1)
        main_l.addLayout(body)
        
        nav = QHBoxLayout()
        self.p_btn = QPushButton("⬅️ 上一部分"); self.n_btn = QPushButton("下一部分 ➡️")
        self.p_btn.clicked.connect(lambda: self.step(-1)); self.n_btn.clicked.connect(lambda: self.step(1))
        nav.addWidget(self.p_btn); nav.addStretch(); nav.addWidget(self.n_btn)
        main_l.addLayout(nav)

    def _setup_exam_screens(self):
        """
        设置考试界面的堆叠布局，包括开始界面和实际考试内容界面。
        """
        """设置考试界面的堆叠布局，包括开始界面和实际考试内容界面"""
        self.exam_view_layout = QVBoxLayout(self.exam_view)
        self.exam_screens_stack = QStackedWidget()
        self.exam_view_layout.addWidget(self.exam_screens_stack)
        self.exam_screens_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # --- 1. 开始界面 ---
        self.start_screen_widget = QWidget()
        start_layout = QVBoxLayout(self.start_screen_widget)
        start_layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel("高考整卷模拟")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 50px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        start_layout.addWidget(title_label)

        start_button = QPushButton("开始考试")
        start_button.setFixedSize(250, 80)
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 28px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2471a3;
            }
        """)
        start_button.clicked.connect(self._start_exam)
        start_layout.addWidget(start_button, alignment=Qt.AlignCenter)
        
        self.start_screen_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.exam_screens_stack.addWidget(self.start_screen_widget)

        # --- 2. 考试内容界面 ---
        self.exam_content_widget = QWidget()
        self._build_exam_content_ui(self.exam_content_widget) # 将原有 build_exam_ui 逻辑移到这里
        self.exam_screens_stack.addWidget(self.exam_content_widget)
        self.exam_content_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # 初始显示开始界面
        self.exam_screens_stack.setCurrentWidget(self.start_screen_widget)

    def _build_exam_content_ui(self, parent_widget):
        """
        构建实际的考试内容UI，包括文章、题目和导航。
        """
        """构建实际的考试内容UI，包括文章、题目和导航"""
        # 将 build_exam_ui 的内容移动到这里，并修改父布局
        main_l = QVBoxLayout(parent_widget)
        # ... (以下内容与原 build_exam_ui 相同，只是父布局变为 parent_widget)

        self.header_l = QLabel(""); self.header_l.setAlignment(Qt.AlignCenter); self.header_l.setStyleSheet("font-size: 20px; font-weight: bold; color: #2980b9; background: #f8f9fa; padding: 10px;")
        main_l.addWidget(self.header_l) # Header takes its natural height
        
        body = QHBoxLayout()
        self.passage_box = QTextBrowser(); self.passage_box.setStyleSheet("font-size: 17px; line-height: 1.6; padding: 20px; background: white;")
        body.addWidget(self.passage_box, 1)
        
        # 右侧答题区
        right_panel = QVBoxLayout()
        self.q_scroll = QScrollArea() # Removed setWidgetResizable(True) to allow content to overflow and trigger scrollbar
        self.q_widget = QWidget(); self.q_layout = QVBoxLayout(self.q_widget); self.q_layout.setAlignment(Qt.AlignTop)
        self.q_scroll.setWidget(self.q_widget)
        right_panel.addWidget(self.q_scroll, 1) # Make the scroll area expand vertically
        
        # 【提交按钮】强行出现在右侧下方，最后一页才显示
        self.submit_btn = QPushButton("🏁 确认交卷并计算总分")
        self.submit_btn.setFixedHeight(60)
        self.submit_btn.setStyleSheet("background-color: #ff4757; color: white; font-weight: bold; font-size: 18px; border-radius: 8px;")
        self.submit_btn.clicked.connect(self.final_calc)
        self.submit_btn.hide()
        right_panel.addWidget(self.submit_btn)

        body.addLayout(right_panel, 1)
        main_l.addLayout(body, 1) # Body takes most of the vertical space
        
        nav = QHBoxLayout()
        self.p_btn = QPushButton("⬅️ 上一部分"); self.n_btn = QPushButton("下一部分 ➡️")
        self.p_btn.clicked.connect(lambda: self.step(-1)); self.n_btn.clicked.connect(lambda: self.step(1))
        nav.addWidget(self.p_btn); nav.addStretch(); nav.addWidget(self.n_btn)
        main_l.addLayout(nav)

    def _start_exam(self):
        """
        点击开始按钮后，切换到考试内容界面并加载第一页。
        """
        """点击开始按钮后，切换到考试内容界面并加载第一页"""
        self.exam_screens_stack.setCurrentWidget(self.exam_content_widget) # 切换到考试内容界面
        self.exam_start_time = time.time() # 记录考试开始时间
        self.refresh() # 加载第一页试卷内容

    def step(self, s):
        """
        根据步长 s 切换到上一页或下一页试卷。
        """
        self.cur_idx += s
        self.refresh()

    def refresh(self):
        """
        刷新当前页面的试卷内容和答题区。
        """
        d = self.all_data[self.cur_idx]
        print(f"DEBUG: Refreshing section {self.cur_idx}. Data: {d.get('category')}, Items count: {len(d.get('items', []))}")
        self.header_l.setText(f"{d['category']} ({self.cur_idx+1}/{len(self.all_data)})")
        
        # 正文题号增强：加粗且带下划线
        passage_content = d['passage'].replace('\n', '<br>')
        question_type = d.get('question_type', 'reading')
        if question_type in ['seven_five', 'cloze', 'grammar']:
            # 匹配36-65之间的两位数字，并用<u><b></b></u>标签包裹
            passage_content = re.sub(r'\b(3[6-9]|4[0-9]|5[0-9]|6[0-5])\b', r'<u><b>\1</b></u>', passage_content)
        self.passage_box.setHtml(passage_content)
        
        
        while self.q_layout.count():
            w = self.q_layout.takeAt(0).widget()
            if w: w.deleteLater()
            
        if not d.get('items', []): # 如果没有题目，则显示提示信息
            no_questions_label = QtWidgets.QLabel("⚠️ 本部分暂无题目数据，请检查试卷文件。")
            no_questions_label.setStyleSheet("color: #e74c3c; font-size: 16px; padding: 20px; text-align: center;")
            self.q_layout.addWidget(no_questions_label)
        
        for it in d.get('items', []):
            qid = re.sub(r'\D', '', str(it['q_id']))
            card = QuestionCard(it, d.get('question_type', 'reading'), self.ans_cache.get(qid, ""), lambda q, v: self.ans_cache.update({q: v}))
            self.q_layout.addWidget(card)

        # 控制：只有最后一页才显示提交按钮
        is_last = (self.cur_idx == len(self.all_data) - 1)
        self.submit_btn.setVisible(is_last)
        self.n_btn.setVisible(not is_last)
        self.p_btn.setEnabled(self.cur_idx > 0)
        self.q_scroll.verticalScrollBar().setValue(0)

    def final_calc(self):
        """
        计算最终得分，生成结算报告，并切换到结果页面。
        """
        all_questions_data = {} # 用于存储所有题目的详细信息和解析
        res = {'total': 0, 'details': {}} # total_possible_score 字段用于存储每个部分的满分
        for sec in self.all_data:
            tp = sec.get('question_type', 'reading')
            if tp not in res['details']: res['details'][tp] = {'score':0, 'total':0, 'correct':0, 'wrongs':[], 'wrongs_details':[], 'total_possible_score':0}
            for it in sec.get('items', []):
                qid = re.sub(r'\D', '', str(it['q_id']))
                n = int(qid) if qid.isdigit() else 0

                # 解析当前部分的原始解析文本
                analysis_by_q_id = self._parse_analysis_text(sec.get('original_analysis', ''))

                # 存储当前题目的详细信息
                all_questions_data[qid] = {
                    'content': it.get('content', ''),
                    'options': it.get('options', {}),
                    'answer': it.get('answer', ''),
                    'analysis': analysis_by_q_id.get(qid, '暂无解析')
                }

                # 计算分数权重
                w = 1.0 if 41<=n<=55 else (1.5 if 56<=n<=65 else 2.5)
                
                res['details'][tp]['total'] += 1
                res['details'][tp]['total_possible_score'] += w # 累加每个部分的满分

                user = self.ans_cache.get(qid, "").strip().upper()
                real = it.get('answer', '').strip().upper()
                
                if user == real and real != "":
                    res['total'] += w
                    res['details'][tp]['score'] += w
                    res['details'][tp]['correct'] += 1
                else:
                    res['details'][tp]['wrongs'].append(qid)
                    res['details'][tp]['wrongs_details'].append({'id': qid, 'user': user, 'correct': real})
        
        for k in res['details']:
            d = res['details'][k]
            d['acc'] = (d['correct']/d['total']*100) if d['total']>0 else 0
            
        elapsed = int(time.time() - self.exam_start_time) if self.exam_start_time else 0
        self.res_view.update_res(res, elapsed, all_questions_data) # 传递 elapsed_time_seconds 和所有题目数据
        self.screen_manager_stack.setCurrentWidget(self.res_scroll_area) # 切换到结果页所在的 QScrollArea