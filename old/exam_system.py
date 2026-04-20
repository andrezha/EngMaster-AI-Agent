# -*- coding: utf-8 -*-
from PySide6 import QtWidgets, QtCore, QtGui
import re

class HSEExamSystem(QtWidgets.QWidget):
    def __init__(self, data_list=None):
        super().__init__()
        
        # 状态初始化
        self.current_index = 0
        self.all_data = []

        # 主布局：垂直布局，上方是内容区，下方是导航区
        self.main_v_layout = QtWidgets.QVBoxLayout(self)
        self.main_v_layout.setContentsMargins(0, 0, 0, 0)
        self.main_v_layout.setSpacing(0)

        # 内容区：左右 1:1 分割
        self.content_h_layout = QtWidgets.QHBoxLayout()
        self.content_h_layout.setSpacing(15)
        self.content_h_layout.setContentsMargins(15, 15, 15, 15) # 添加边距

        # 左侧：纯白文章背景
        self.text_browser = QtWidgets.QTextBrowser()
        self.text_browser.setStyleSheet("""
            QTextBrowser { background-color: #ffffff; border: 1px solid #dcdfe6; 
                           border-radius: 8px; padding: 20px; font-size: 16px; line-height: 1.6; }
        """)
        self.content_h_layout.addWidget(self.text_browser, 1)

        # 右侧：题目滚动交互区
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.q_container = QtWidgets.QWidget()
        self.q_layout = QtWidgets.QVBoxLayout(self.q_container)
        self.q_layout.setSpacing(15)
        self.q_layout.setAlignment(QtCore.Qt.AlignTop)
        self.scroll.setWidget(self.q_container)
        
        self.content_h_layout.addWidget(self.scroll, 1)
        
        self.main_v_layout.addLayout(self.content_h_layout, 1) # 内容区占据大部分空间

        # 底部导航区
        self.nav_h_layout = QtWidgets.QHBoxLayout()
        self.nav_h_layout.setContentsMargins(15, 10, 15, 10) # 导航区边距
        self.nav_h_layout.setSpacing(10)
        self.nav_h_layout.setAlignment(QtCore.Qt.AlignCenter)

        self.btn_prev = QtWidgets.QPushButton("◀ 上一页")
        self.btn_prev.setFixedSize(100, 40)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0; border: 1px solid #dcdfe6; border-radius: 8px;
                font-size: 14px; font-weight: bold; color: #606266;
            }
            QPushButton:hover { background-color: #e6e6e6; }
            QPushButton:pressed { background-color: #d9d9d9; }
            QPushButton:disabled { background-color: #f5f5f5; color: #c0c4cc; border-color: #ebeef5; }
        """)
        self.btn_prev.clicked.connect(lambda: self.switch_page(self.current_index - 1))
        self.nav_h_layout.addWidget(self.btn_prev)

        self.current_section_label = QtWidgets.QLabel("当前板块")
        self.current_section_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        self.nav_h_layout.addWidget(self.current_section_label)

        self.btn_next = QtWidgets.QPushButton("下一页 ▶")
        self.btn_next.setFixedSize(100, 40)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #409eff; border: 1px solid #409eff; border-radius: 8px;
                font-size: 14px; font-weight: bold; color: white;
            }
            QPushButton:hover { background-color: #66b1ff; }
            QPushButton:pressed { background-color: #3a8ee6; }
            QPushButton:disabled { background-color: #a0cfff; color: #ffffff; border-color: #a0cfff; }
        """)
        self.btn_next.clicked.connect(lambda: self.switch_page(self.current_index + 1))
        self.nav_h_layout.addWidget(self.btn_next)
        
        self.main_v_layout.addLayout(self.nav_h_layout) # 导航区在底部

        if data_list:
            self.update_data(data_list)

    def update_data(self, parsed_exam_data):
        """【真·执行核心】接收来自 main.py 的整卷数据"""
        self.all_data = parsed_exam_data
        self.switch_page(0) # 默认显示第一页

    def switch_page(self, index):
        """
        清空当前显示，加载并显示指定索引的试卷板块内容。
        严格按照高考 A->B->C->D->七选五->完形->语法的顺序切换。
        """
        if not self.all_data:
            self.text_browser.setHtml("<div style='text-align:center; color:#e74c3c; font-size:18px; padding:50px;'>暂无试卷数据加载。</div>")
            self.current_section_label.setText("无数据")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            return

        # 边界检查
        if index < 0:
            index = 0
        elif index >= len(self.all_data):
            index = len(self.all_data) - 1

        self.current_index = index
        part_data = self.all_data[self.current_index]

        # 清空旧内容
        self.text_browser.clear()
        # 清理旧按钮，防止重叠
        while self.q_layout.count():
            item = self.q_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        # Reset scroll position to top for new data
        self.scroll.verticalScrollBar().setValue(0)
        
        # 加载当前页内容
        sec_category = part_data.get('category', 'Unknown')
        passage_content = part_data.get('passage', '')
        items = part_data.get('items', [])
        question_type = part_data.get('question_type', 'reading')

        self.text_browser.append(f"<div style='color:#409EFF; font-weight:bold; font-size:18px; margin-bottom: 10px;'>【{sec_category}】</div>")
        self.text_browser.append(f"<div style='margin-bottom:20px;'>{passage_content.replace(chr(10), '<br>')}</div>")
        
        self._create_interactive_items(items, question_type)

        # 更新导航标签和按钮状态
        self.current_section_label.setText(f"{sec_category} ({self.current_index + 1}/{len(self.all_data)})")
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < len(self.all_data) - 1)

    def _create_interactive_items(self, items, question_type):
        """根据解析好的题目数据生成交互式UI"""
        
        if not items:
            return # 如果没有题目，则不渲染

        # 添加一个题目范围的标题
        first_q_id = items[0].get('q_id', '')
        last_q_id = items[-1].get('q_id', '')
        header_label = QtWidgets.QLabel(f"<b>{first_q_id} - {last_q_id} 题</b>")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; margin-bottom: 10px;")
        header_label.setContentsMargins(0, 0, 0, 5) # Add a small bottom margin
        self.q_layout.addWidget(header_label)

        for item in items:
            q_id = item.get('q_id', '')
            q_content = item.get('content', '')
            options = item.get('options', {}) # 字典形式的选项，语法填空为空

            if question_type == "grammar":
                # 语法填空：只显示题号和输入框
                q_label = QtWidgets.QLabel(f"<b>{q_id}.</b>")
                q_label.setWordWrap(True)
                q_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50; padding: 5px;")
                q_label.setContentsMargins(0, 10, 0, 0) # Add top margin for separation
                self.q_layout.addWidget(q_label)
                
                input_field = QtWidgets.QLineEdit()
                input_field.setPlaceholderText("请输入答案...")
                input_field.setMinimumHeight(35)
                input_field.setStyleSheet("""
                    QLineEdit {
                        font-size: 14px;
                        padding: 5px 10px;
                        border: 1px solid #dcdfe6;
                        border-radius: 6px;
                    }
                """)
                self.q_layout.addWidget(input_field)
                self.q_layout.addSpacing(10) # Spacing after each grammar question
            else:
                # 选择题 (阅读、完形、七选五)：显示题号、题干和选项按钮
                q_label = QtWidgets.QLabel(f"<b>{q_id}. {q_content}</b>")
                q_label.setWordWrap(True)
                q_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #2c3e50; padding: 5px;")
                q_label.setContentsMargins(0, 10, 0, 0) # Add top margin for separation
                self.q_layout.addWidget(q_label)

                # 选项按钮 (按字母顺序排序)
                sorted_options = sorted(options.items())
                for label, opt_text in sorted_options:
                    btn = QtWidgets.QPushButton(f"{label}. {opt_text}")
                    btn.setCheckable(True)
                    btn.setMinimumHeight(40)
                    # 🚀 强制样式：拒绝黑色按钮，选中变蓝
                    btn.setStyleSheet("""
                        QPushButton { 
                            background-color: #ffffff; border: 1px solid #dcdfe6;
                            border-radius: 6px; text-align: left; padding-left: 15px; font-size: 14px;
                        }
                        QPushButton:hover { background-color: #f5f7fa; border-color: #409eff; }
                        QPushButton:checked { background-color: #409eff; color: white; border: none; }
                    """)
                    self.q_layout.addWidget(btn)

                self.q_layout.addSpacing(10) # Spacing after each multiple choice question
