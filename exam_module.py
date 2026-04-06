import json
import os
import random
import re
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QRadioButton, QButtonGroup, QSizePolicy
from PyQt5.QtCore import Qt
from parsers.reading_parser import parse_reading_txt


class ExamManager:
    # 严格的路径映射配置
    PATH_MAPPING = {
        "阅读理解": "data/阅读理解",
        "七选五": "data/七选五",
        "完形填空": "data/完形填空",
        "语法填空": "data/语法填空",
        "短文改错": "data/短文改错",
        "写作续写": "data/写作续写",
    }

    def __init__(self, main_window):
        self.mw = main_window
        self.ui = main_window.page_gaokao_widget

        # 1. 初始化变量
        self.current_type = None  # 初始无题型
        self.user_selections = {}  # {q_id: selected_option}
        self.current_q = None
        self.current_file_index = -1
        self.current_files = []
        self.seven_five_button_groups = {}  # 七选五的按钮组

        # 🎯 懒加载核心：独立存储每种题型的数据
        self.currentReadingData = None  # 阅读理解数据
        self.currentClozeData = None    # 七选五数据

        # 🎯 双变量存储：记录每种题型最后显示的标题
        self.lastReadingTitle = None
        self.lastClozeTitle = None

        # 🎯 当前视图类型：'reading', 'cloze', 或 None
        self.currentView = None

        # 2. 比例调整
        main_layout = self.ui.layout()
        if main_layout and hasattr(main_layout, 'setStretch'):
            main_layout.setStretch(0, 6)
            main_layout.setStretch(1, 4)
            print("🚀 [OK] 界面 6:4 比例调整完成")

        # 右侧垂直布局比例调整 (上方题目/选项 6 : 下方解析 4)
        right_parent = self.ui.gk_result_panel.parentWidget()
        if hasattr(right_parent, 'setStretchFactor'):
            right_parent.setStretchFactor(0, 6)
            right_parent.setStretchFactor(1, 4)
            print("🚀 [OK] 右侧垂直 QSplitter 6:4 比例调整完成")
        else:
            right_v_layout = right_parent.layout()
            if right_v_layout and hasattr(right_v_layout, 'setStretch'):
                right_v_layout.setStretch(0, 6)
                right_v_layout.setStretch(1, 4)
                print("🚀 [OK] 右侧垂直 Layout 6:4 比例调整完成")

        # 3. 绑定信号
        self.ui.btn_gk_next.clicked.connect(self.load_and_render)
        self.ui.btn_gk_submit.clicked.connect(self.check_score)

        # 4. 初始导航高亮
        self.update_nav_highlight()

        # 5. 绑定题型选择按钮
        # 🚫 禁用自动默认按钮，防止进入页面时自动触发点击
        for btn in [self.ui.gk_btn_reading, self.ui.gk_btn_cloze, self.ui.gk_btn_seven_five, self.ui.gk_btn_grammar]:
            if btn:
                btn.setAutoDefault(False)
                btn.setDefault(False)
        
        self.ui.gk_btn_reading.clicked.connect(lambda: self.switch_topic("阅读理解"))
        self.ui.gk_btn_cloze.clicked.connect(lambda: self.switch_topic("完形填空"))
        self.ui.gk_btn_seven_five.clicked.connect(lambda: self.switch_topic("七选五"))
        self.ui.gk_btn_grammar.clicked.connect(lambda: self.switch_topic("语法填空"))

        # 清空初始界面显示
        self.ui.gk_question_body.clear()
        self.ui.gk_result_panel.clear()
        self.ui.gk_ai_display.clear()

        # 🎯 6. 底部操作栏样式统一规范
        self._style_bottom_action_bar()

    def _style_bottom_action_bar(self):
        """
        底部操作栏统一规范：
        - 按钮高度固定为 56px
        - 大圆角（16px）和实色背景
        - 增加阴影效果
        - 提交按钮使用醒目的品牌色
        """
        # 提交按钮 - 醒目蓝色，核心操作
        if hasattr(self.ui, 'btn_gk_submit'):
            self.ui.btn_gk_submit.setFixedHeight(56)
            self.ui.btn_gk_submit.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #2471a3;
                }
            """)
        
        # 下一题按钮 - 浅灰色边框模式
        if hasattr(self.ui, 'btn_gk_next'):
            self.ui.btn_gk_next.setFixedHeight(56)
            self.ui.btn_gk_next.setStyleSheet("""
                QPushButton {
                    background-color: #ecf0f1;
                    color: #2c3e50;
                    border: 2px solid #bdc3c7;
                    border-radius: 16px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background-color: #d5dbdb;
                }
                QPushButton:pressed {
                    background-color: #ccd1d1;
                }
            """)

    def clear_all_state(self):
        """
        彻底清理所有状态，确保新页面是干净的
        包括：用户选择、按钮状态、解析显示、滚动位置
        
        🚨 强效清空逻辑：在每次加载新TXT之前，强制重置所有UI变量
        """
        print("🧹 [State Reset] 开始强制重置所有UI状态...")
        
        # 清空用户选择
        self.user_selections = {}
        print("  ✓ user_selections 已清空")

        # 清空当前题目
        self.current_q = None
        print("  ✓ current_q 已重置为 None")

        # 清空七选五按钮组
        self.seven_five_button_groups = {}
        print("  ✓ seven_five_button_groups 已清空")
        
        # 清空阅读理解按钮组
        if hasattr(self, 'reading_button_groups'):
            self.reading_button_groups = {}
        print("  ✓ reading_button_groups 已清空")

        # 清空答题区域（包括所有嵌套布局和widget）
        self.clear_answer_area()
        print("  ✓ 答题区域已清空")

        # 清空结果显示区域
        self.ui.gk_result_panel.clear()
        self.ui.gk_ai_display.clear()
        print("  ✓ 结果和AI解析区域已清空")

        # 重置滚动条位置
        if hasattr(self.ui, 'gk_answer_scroll'):
            self.ui.gk_answer_scroll.verticalScrollBar().setValue(0)
        if hasattr(self.ui, 'gk_question_body'):
            self.ui.gk_question_body.verticalScrollBar().setValue(0)
        print("  ✓ 滚动条已重置到顶部")
        
        # 🚨 强制刷新UI，确保切换瞬间屏幕是全空的
        self.ui.gk_question_body.setHtml("")
        self.ui.gk_result_panel.setHtml("")
        self.ui.gk_ai_display.setHtml("")
        
        # 确保答题内容区域完全清空
        target_area = self.mw.findChild(QWidget, "gk_answer_content")
        if target_area:
            layout = target_area.layout()
            if layout:
                self._clear_layout(layout)
                # 重新创建一个干净的布局
                self._clear_layout(layout)
        
        print("🧹 [State Reset] 所有状态已强制重置完成！")

    def _clear_layout(self, layout):
        """递归清理布局中的所有项"""
        if not layout:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def clear_answer_area(self):
        """清空答题区域的旧组件（包括嵌套布局）"""
        target_area = self.mw.findChild(QWidget, "gk_answer_content")
        if target_area:
            layout = target_area.layout()
            if layout:
                self._clear_layout(layout)

    def getOrFetchData(self, topic_name, is_next_button=False):
        """
        懒加载核心函数：获取或加载题型数据
        
        🎯 逻辑：
        1. 如果内存中已存在该题型的数据（不为 null），直接返回旧数据，禁止重新读取文件
        2. 只有当内存数据为 null，或者用户点击了"下一题"按钮时，才执行 fetchNewRandomFile()
        
        Args:
            topic_name: 题型名称（"阅读理解" 或 "七选五"）
            is_next_button: 是否由"下一题"按钮触发（True 时强制刷新）
        
        Returns:
            bool: 是否成功获取数据
        """
        print(f"\n🔍 [getOrFetchData] 请求题型: {topic_name}, 下一题: {is_next_button}")
        
        # 检查路径是否存在
        if topic_name not in self.PATH_MAPPING:
            print(f"❌ 未配置题型 [{topic_name}] 的路径映射")
            return False
        
        # 🎯 懒加载逻辑：
        # 1. 如果不是"下一题"按钮，且内存中已有数据 → 直接返回旧数据
        if not is_next_button:
            if topic_name == "阅读理解" and self.currentReadingData is not None:
                print("📝 [懒加载] 阅读理解数据已存在，直接返回缓存数据")
                self.current_q = self.currentReadingData
                self.current_type = topic_name
                self.currentView = 'reading'
                self.lastReadingTitle = self.currentReadingData.get('filename', '')
                return True
            elif topic_name == "七选五" and self.currentClozeData is not None:
                print("📝 [懒加载] 七选五数据已存在，直接返回缓存数据")
                self.current_q = self.currentClozeData
                self.current_type = topic_name
                self.currentView = 'cloze'
                self.lastClozeTitle = self.currentClozeData.get('filename', '')
                return True
        
        # 2. 需要加载新数据（数据为 null 或点击了"下一题"）
        print(f"📥 [懒加载] 需要加载新数据: 数据为空={topic_name == '阅读理解' and self.currentReadingData is None}, 下一题={is_next_button}")
        return self.fetchNewRandomFile(topic_name)
    
    def fetchNewRandomFile(self, topic_name):
        """
        从指定题型文件夹中随机加载一个新的 TXT 文件
        
        Args:
            topic_name: 题型名称
        
        Returns:
            bool: 是否成功加载
        """
        print(f"\n📂 [fetchNewRandomFile] 开始加载新文件: {topic_name}")
        
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.PATH_MAPPING[topic_name])
        
        if not os.path.exists(data_path):
            print(f"❌ 路径不存在: {data_path}")
            return False
        
        # 扫描文件列表
        files = sorted([f for f in os.listdir(data_path) if f.endswith(".txt")])
        
        if not files:
            print(f"❌ 文件夹内无 TXT 文件: {data_path}")
            return False
        
        # 随机选择文件（避免连续重复）
        if len(files) > 1 and self.current_files == files:
            # 在同一题型内避免重复
            available = [f for f in files if f != getattr(self, f'last_{topic_name}_file', None)]
            if available:
                target = random.choice(available)
            else:
                target = random.choice(files)
        else:
            target = random.choice(files)
            self.current_files = files
        
        setattr(self, f'last_{topic_name}_file', target)
        target_path = os.path.join(data_path, target)
        
        print(f"📖 [fetchNewRandomFile] 选中文件: {target}")
        
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed_data = parse_reading_txt(content)
            print(f"✅ [fetchNewRandomFile] 解析成功: {parsed_data.get('question_type', 'unknown')}")
            
            # 构建题目数据结构
            question_data = {
                'year': parsed_data.get('year', ''),
                'category': parsed_data.get('category', ''),
                'passage': parsed_data.get('passage', ''),
                'items': parsed_data.get('items', []),
                'original_analysis': parsed_data.get('original_analysis', ''),
                'question_type': parsed_data.get('question_type', 'reading'),
                'filename': target
            }
            
            # 🎯 缓存到对应的变量
            if topic_name == "阅读理解":
                self.currentReadingData = question_data
                self.currentView = 'reading'
                self.lastReadingTitle = target
            elif topic_name == "七选五":
                self.currentClozeData = question_data
                self.currentView = 'cloze'
                self.lastClozeTitle = target
            
            # 设置当前题目
            self.current_q = question_data
            self.current_type = topic_name
            
            print(f"✅ [fetchNewRandomFile] 加载完成: {target}")
            return True
            
        except Exception as e:
            print(f"❌ [fetchNewRandomFile] 读取失败: {e}")
            return False

    def switch_topic(self, topic_name):
        """
        切换题型 - 懒加载逻辑
        
        🎯 关键逻辑：
        1. 如果题型相同且有题目 → 保持不变
        2. 如果题型不同或无题目 → 使用 getOrFetchData 懒加载
        3. 切换时不清空另一个题型的数据变量
        """
        # 检查路径是否存在
        if topic_name not in self.PATH_MAPPING:
            print(f"❌ 未配置题型 [{topic_name}] 的路径映射")
            return

        print(f"🔄 [Switch] 切换题型: {self.current_type} -> {topic_name}")
        
        # 🎯 关键逻辑：题型相同且有题目时，保持不变
        if self.current_type == topic_name and self.current_q is not None:
            print("📝 [Switch] 题型相同且有题目，保持不变")
            return
        
        # 🎯 使用懒加载获取数据（不是"下一题"按钮，不强制刷新）
        success = self.getOrFetchData(topic_name, is_next_button=False)
        
        if success:
            # 更新导航高亮
            self.update_nav_highlight()
            # 渲染界面
            self.render_passage()
            self.render_question_ui()
            print("🏁 [Switch] 题型切换完成")
        else:
            print("❌ [Switch] 数据加载失败")

    def get_data_path(self):
        """根据当前题型获取严格的数据路径"""
        if self.current_type not in self.PATH_MAPPING:
            return None

        base_path = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(base_path, self.PATH_MAPPING[self.current_type])
        return data_path

    def load_and_render(self):
        """
        加载数据并渲染界面 - 支持懒加载
        
        🎯 逻辑：
        1. 当"下一题"按钮被点击时，使用懒加载强制刷新
        2. 更新对应的缓存数据
        """
        print("\n" + "=" * 30)
        print(f"🚀 [load_and_render] 开始加载 [{self.current_type}] 题目...")
        
        if not self.current_type:
            print("❌ 错误：未选择题型，请先点击题型按钮")
            self.ui.gk_question_body.setHtml(
                "<div style='font-size:16px; color:#e74c3c; text-align:center; padding:40px;'>"
                "👈 请先点击上方的题型按钮（如《阅读理解》、《七选五》）开始练习</div>"
            )
            return
        
        # 🎯 使用懒加载，强制刷新新题目
        success = self.getOrFetchData(self.current_type, is_next_button=True)
        
        if success:
            # 渲染界面
            self.render_passage()
            self.render_question_ui()
            print("🏁 [load_and_render] 渲染流程全部执行完毕")
            print("=" * 30 + "\n")
        else:
            print("❌ [load_and_render] 数据加载失败")

    def render_passage(self):
        """渲染文章区域"""
        if not self.current_q:
            return

        year = self.current_q.get('year', '未知')
        normalized_cat = self.current_q.get('category', '').strip()

        # 规范化卷区名称
        if not normalized_cat:
            file_name_no_ext = self.current_q.get('filename', '').replace(".txt", "")
            parts = file_name_no_ext.split("_")
            category = parts[1] if len(parts) > 1 else ""
            normalized_cat = category.strip("()（）")
        else:
            normalized_cat = normalized_cat.strip("()（）")

        if "新课标" in normalized_cat:
            normalized_cat = "全国新课标Ⅰ卷"

        # 处理正文
        raw_passage = self.current_q.get('passage', '文章加载失败')
        raw_passage = raw_passage.replace('[PASSAGE]', '').replace('[QUESTIONS]', '')

        p_lines = raw_passage.splitlines()
        p_text_lines = []
        passage_letter = ""
        main_title = ""

        found_letter = False
        found_title = False

        if self.current_type == "阅读理解":
            for line in p_lines:
                stripped = line.strip()
                if not stripped:
                    continue
                # 检测篇目字母
                if not found_letter and len(stripped) == 1 and stripped.upper() in ['A', 'B', 'C', 'D', 'E']:
                    passage_letter = stripped.upper()
                    found_letter = True
                    continue
                # 检测紧接着的主标题
                if found_letter and not found_title:
                    if len(stripped) < 60 and not stripped.endswith('.') and not stripped.endswith('"') and not stripped.endswith('"'):
                        main_title = stripped
                        found_title = True
                        continue
                    else:
                        found_title = True

                p_text_lines.append(line)

            top_tag = f"[{year}] {normalized_cat} 真题"
            letter_str = f"【阅读理解 {passage_letter} 篇】" if passage_letter else "【阅读理解】"
            main_title_html = f"<h3 style='text-align: center; color: #34495e;'>{main_title}</h3>" if main_title else ""
        else:
            # 七选五等其他题型
            for line in p_lines:
                if line.strip():
                    p_text_lines.append(line)
            top_tag = f"[{year}] {normalized_cat} 真题"
            letter_str = f"【{self.current_type}】"
            main_title_html = ""

        p_text = '\n'.join(p_text_lines).strip()
        p_text_html = p_text.replace('\n', '<br>')

        # 最终标题拼接
        html_output = (
            f"<div style='text-align: center; color: #7f8c8d; font-size:14px; margin-bottom: 5px;'>{top_tag}</div>"
            f"<h2 style='text-align: center; color: #2c3e50; margin-top: 0;'>{letter_str}</h2>"
            f"{main_title_html}"
            f"<hr>"
            f"<div style='font-size:16px; line-height:1.7; color:#2c3e50;'>{p_text_html}</div>"
        )
        self.ui.gk_question_body.setHtml(html_output)

    def render_question_ui(self):
        """
        动态生成答题按钮 - 使用条件渲染确保不同题型组件不会同时存在
        
        🚨 关键逻辑：
        - 使用条件渲染，确保不属于当前题型的组件在 DOM/Widget Tree 中被物理移除
        - 严禁让两个组件同时存在于一个页面 Stack 中！
        """
        target_area = self.mw.findChild(QWidget, "gk_answer_content")

        if not target_area:
            print("❌ 严重错误：在整个界面中都找不到 'gk_answer_content'！")
            return

        layout = target_area.layout()
        if layout is None:
            layout = QVBoxLayout(target_area)
            target_area.setLayout(layout)

        # 增加间距与边距
        layout.setSpacing(15)
        layout.setContentsMargins(10, 20, 10, 20)

        # 固定高度限制
        target_area.setMinimumHeight(300)

        # 🔄 彻底清空布局中的所有项（包括 widget、layout 和 spacer）
        # 这一步确保旧题型的组件被完全销毁（物理移除）
        print("🗑️ [Render] 开始清空答题区域的所有旧组件...")
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                widget_name = child.widget().objectName()
                print(f"  - 销毁 widget: {widget_name or type(child.widget()).__name__}")
                child.widget().deleteLater()  # 物理销毁
                child.widget().setParent(None)  # 移除父级引用
            elif child.layout():
                print("  - 销毁嵌套布局")
                # 递归删除嵌套布局
                self._clear_layout(child.layout())
        print("✅ [Render] 答题区域已清空")

        # 清空所有按钮组引用（确保旧题型的按钮组被彻底清理）
        self.seven_five_button_groups = {}
        if hasattr(self, 'reading_button_groups'):
            self.reading_button_groups = {}

        items = self.current_q.get('items', []) if self.current_q else []

        if not items:
            no_question_label = QLabel("<i style='color:#7f8c8d;'>暂无题目数据</i>")
            layout.addWidget(no_question_label)
            layout.addStretch()
            return

        # 🎯 根据题型渲染不同的UI - 条件渲染
        # 确保只渲染当前题型需要的组件，其他题型的组件不会被创建
        question_type = self.current_q.get('question_type', 'reading') if self.current_q else 'reading'
        
        print(f"🎨 [Render] 当前题型: {question_type}")
        
        # 条件渲染：根据题型只创建对应的 UI 组件
        if question_type == "seven_five":
            # 只显示七选五 UI，不创建阅读理解的组件
            print("  → 渲染七选五 UI (ClozeOptionList)")
            self._render_seven_five_ui(layout, items)
        else:
            # 只显示阅读理解 UI，不创建七选五的组件
            print("  → 渲染阅读理解 UI (ReadingQuestionWidget)")
            self._render_reading_ui(layout, items)
        
        # 添加弹性空间，确保布局美观
        layout.addStretch()
        
        print("✅ [Render] UI 渲染完成")

    def _render_reading_ui(self, layout, items):
        """
        渲染阅读理解题目UI（单选题）
        
        🚨 关键修复：
        - 正则纠偏：确保解析器能准确识别 TXT 里的 [Q_1], [Q_2] 标签
        - 单选锁定：每一个 [Q_n] 块必须是一个独立的单选组（Radio Group）
        - 显示逻辑：如果读取的是阅读理解文件夹，必须强制触发 showQuestionCard = true
        """
        print(f"📝 [Reading UI] 开始渲染 {len(items)} 道阅读理解题目...")
        
        for idx, item in enumerate(items):
            qid = item.get('q_id', '')
            content = item.get('content', '')

            # 显示选项按钮行（优先使用 options 字段，否则从 content 提取）
            options = item.get('options', [])
            if options:
                # 使用已有的 options 字段
                qtext = content
            else:
                # 从 content 中提取题干和选项
                qtext, options = self._extract_options_from_content(content)

            # 显示题干
            q_label = QLabel(f"<b>{qid}. {qtext}</b>")
            q_label.setWordWrap(True)
            q_label.setObjectName(f"label_q{qid}")
            layout.addWidget(q_label)

            # 🎯 关键修复：为每道题目创建独立的 QButtonGroup（单选组）
            # 这样每道题目内部的选项是互斥的，但不同题目之间互不影响
            question_button_group = QButtonGroup(self.mw)
            question_button_group.setExclusive(True)  # 设置为互斥（单选）
            
            # 保存按钮组引用，方便后续管理
            if not hasattr(self, 'reading_button_groups'):
                self.reading_button_groups = {}
            self.reading_button_groups[qid] = question_button_group

            # 显示选项按钮行
            if options:
                for i, opt_content in enumerate(options):
                    btn = QPushButton(opt_content)
                    btn.setCheckable(True)
                    btn.setObjectName(f"btn_q{qid}_opt{chr(65+i)}")
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
                    choice = chr(65 + i)  # A, B, C, D
                    
                    # 将按钮添加到该题目的专属按钮组
                    question_button_group.addButton(btn)
                    
                    # 绑定点击事件 - 使用新的单选逻辑
                    btn.clicked.connect(
                        lambda checked, q=qid, c=choice, b=btn: self.on_reading_choice_click(q, c, b)
                    )
                    layout.addWidget(btn)
            else:
                no_opt_label = QLabel("<i style='color:#95a5a6;'>⚠️ 选项数据缺失，请检查TXT文件格式</i>")
                no_opt_label.setWordWrap(True)
                layout.addWidget(no_opt_label)

            # 添加分隔线
            separator = QLabel("<hr style='border: none; border-top: 1px solid #e5e7eb; margin: 8px 0;'>")
            layout.addWidget(separator)
        
        print(f"✅ [Reading UI] {len(items)} 道题目渲染完成，每题已设置独立单选组")

    def _extract_options_from_content(self, content):
        """从题目内容中提取题干和选项"""
        # 容错处理：将全角 ． 替换为半角 .
        clean_content = content.replace('．', '.')

        # 查找选项位置
        posA = clean_content.find("A.")
        posB = clean_content.find("B.")
        posC = clean_content.find("C.")
        posD = clean_content.find("D.")

        if posA != -1 and posB != -1 and posC != -1 and posD != -1 and posA < posB < posC < posD:
            # 切分题干：位置 A 之前的所有内容
            q_text = clean_content[:posA].strip()

            # 选项切分（去除选项前缀 "A.", "B." 等）
            optA = clean_content[posA+2:posB].strip()  # +2 跳过 "A."
            optB = clean_content[posB+2:posC].strip()  # +2 跳过 "B."
            optC = clean_content[posC+2:posD].strip()  # +2 跳过 "C."
            optD = clean_content[posD+2:].strip()      # +2 跳过 "D."

            options = [optA, optB, optC, optD]
            return q_text, options
        else:
            # 兜底：没找齐四个选项或顺序错乱
            return content, []

    def _render_seven_five_ui(self, layout, items):
        """渲染七选五题目UI（A-G选项列表）"""
        if not items:
            return

        # 获取选项列表（所有题目共享同一组选项）
        options_list = items[0].get('options', [])

        if not options_list:
            no_opt_label = QLabel("<i style='color:#e74c3c;'>⚠️ 选项数据缺失，请检查TXT文件格式</i>")
            no_opt_label.setWordWrap(True)
            layout.addWidget(no_opt_label)
            return

        # 🚨 修复1：选项区域标题 - 纯文本展示，无按钮样式
        options_title = QLabel("📋 选项列表 (A-G)")
        options_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 0;
                border: none;
                background: transparent;
            }
        """)
        options_title.setWordWrap(True)
        layout.addWidget(options_title)

        # 🚨 修复2：选项显示区域 - 纯文本标签，自适应高度，无交互
        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)
        options_layout.setSpacing(6)
        options_layout.setContentsMargins(5, 5, 5, 5)
        
        # 关键修复：让内容自动撑开，不设置任何高度限制
        options_widget.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.MinimumExpanding  # 垂直方向根据内容自动扩展
        )
        # 移除所有高度限制
        options_widget.setMinimumHeight(0)
        options_widget.setMaximumHeight(16777215)  # Qt 的最大值

        for opt in options_list:
            label = opt.get('label', '')
            content = opt.get('content', '')
            opt_text = f"{label}. {content}"

            # 🚨 修复3：纯文本展示，去掉背景框，只留文字，自适应高度
            opt_label = QLabel(opt_text)
            opt_label.setStyleSheet("""
                QLabel {
                    color: #374151;
                    font-size: 15px;
                    padding: 4px 0;
                    background: transparent;
                    border: none;
                }
            """)
            opt_label.setWordWrap(True)
            # 关键：不设置固定高度，让文字自动撑开
            opt_label.setSizePolicy(
                QSizePolicy.Preferred,
                QSizePolicy.MinimumExpanding  # 根据内容自动调整高度
            )
            opt_label.setMinimumHeight(0)  # 移除最小高度限制
            options_layout.addWidget(opt_label)

        layout.addWidget(options_widget)

        # 🚨 修复4：分隔线
        separator = QLabel("<hr style='border: none; border-top: 2px solid #e5e7eb; margin: 10px 0;'>")
        layout.addWidget(separator)

        # 显示题目编号和答题区域标题
        questions_title = QLabel("✏️ 请选择每个空白处的答案")
        questions_title.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 15px;
                font-weight: bold;
                padding: 8px 0;
                border: none;
                background: transparent;
            }
        """)
        layout.addWidget(questions_title)

        # 🚨 修复5：为每个空白处创建选择器（单选锁定）
        for item in items:
            qid = item.get('q_id', '')
            
            # 创建水平布局容器
            h_layout = QHBoxLayout()
            h_layout.setSpacing(8)
            
            # 空白编号标签
            q_label = QLabel(f"空白 {qid}:")
            q_label.setStyleSheet("""
                QLabel {
                    color: #2c3e50;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 70px;
                }
            """)
            h_layout.addWidget(q_label)

            # 🚨 修复6：为每个空白处创建独立的单选组（关键：单选锁定）
            blank_group = QButtonGroup(self.mw)
            blank_group.setExclusive(True)  # 确保每行只能选一个
            
            # 保存按钮组引用
            self.seven_five_button_groups[f"blank_{qid}"] = blank_group

            # 为每个选项创建单选按钮
            for opt in options_list:
                opt_label_text = opt.get('label', '')
                
                radio = QRadioButton(opt_label_text)
                radio.setStyleSheet("""
                    QRadioButton {
                        padding: 6px 12px;
                        font-size: 14px;
                        spacing: 6px;
                        color: #374151;
                    }
                    QRadioButton::indicator {
                        width: 18px;
                        height: 18px;
                    }
                    QRadioButton:checked {
                        font-weight: bold;
                        color: #2563eb;
                    }
                    QRadioButton:hover {
                        background-color: #f3f4f6;
                        border-radius: 4px;
                    }
                """)
                
                # 🚨 修复7：绑定点击事件，确保正确对应到 [ANSWERS] 块
                radio.toggled.connect(
                    lambda checked, blank_id=qid, opt_label=opt_label_text:
                    self.on_seven_five_blank_choice(blank_id, opt_label, checked)
                )
                
                h_layout.addWidget(radio)
                blank_group.addButton(radio)

            h_layout.addStretch()
            layout.addLayout(h_layout)

        layout.addStretch()

    def on_choice_click(self, qid, choice, btn):
        """记录用户选择（阅读理解）并取消同题其他按钮 - 旧版兼容"""
        parent = btn.parentWidget()
        for child in parent.findChildren(QPushButton):
            if child != btn and child.isCheckable():
                child.setChecked(False)
        self.user_selections[qid] = choice
        print(f"📝 题目 {qid}: 选择 {choice}")

    def on_reading_choice_click(self, qid, choice, btn):
        """
        记录用户选择（阅读理解）- 新版单选逻辑
        
        🚨 关键修复：使用 QButtonGroup 的互斥功能，确保每道题目的选项只能选一个
        不需要手动取消其他按钮，QButtonGroup.setExclusive(True) 会自动处理
        """
        self.user_selections[qid] = choice
        print(f"📝 [单选锁定] 题目 {qid}: 选择 {choice}")
        # QButtonGroup 会自动处理互斥，无需手动取消

    def on_seven_five_choice(self, opt_label, btn):
        """七选五选项点击（显示已选状态）"""
        # 这里只是视觉反馈，实际选择在 blank_choice 中处理
        pass

    def on_seven_five_blank_choice(self, blank_id, opt_label, checked):
        """记录七选五每个空白处的选择"""
        if checked:
            self.user_selections[blank_id] = opt_label
            print(f"📝 空白 {blank_id}: 选择 {opt_label}")
        elif blank_id in self.user_selections:
            del self.user_selections[blank_id]

    def check_score(self):
        """判分与展示解析"""
        if not self.current_q:
            return

        correct_count = 0
        items = self.current_q.get('items', [])
        total = len(items)

        if total == 0:
            self.ui.gk_result_panel.setHtml(
                "<div style='padding:10px; color:#e74c3c;'>❌ 没有可判分的题目</div>"
            )
            return

        res_details = ""

        for item in items:
            qid = item.get('q_id', '')
            ans = item.get('answer', '').strip().upper()
            user_ans = self.user_selections.get(qid, "未做")

            if not ans:
                res_details += (
                    f"<p>第{qid}题：你的选择 <b>{user_ans}</b> | "
                    f"正确答案 <b style='color:#e67e22;'>未知 (题库未录入)</b></p>"
                )
            else:
                color = "#27ae60" if user_ans == ans else "#e74c3c"
                if user_ans == ans:
                    correct_count += 1
                res_details += (
                    f"<p>第{qid}题：你的选择 <b>{user_ans}</b> | "
                    f"正确答案 <b style='color:{color};'>{ans}</b></p>"
                )

        # 1. 渲染左侧结果
        score_html = (
            f"<h3 style='color:#2c3e50;'>得分：{correct_count}/{total} "
            f"({correct_count/total*100:.1f}%)</h3>"
            f"<hr>"
            f"{res_details}"
        )
        self.ui.gk_result_panel.setHtml(
            f"<div style='padding:10px; font-size:14px; line-height:1.6;'>{score_html}</div>"
        )

        # 2. 渲染右侧 AI 解析（只有提交后才显示）
        analysis = self.current_q.get('original_analysis', '').strip()
        if not analysis:
            analysis = (
                "<span style='color:#7f8c8d;'>"
                "暂无本地解析。您可以到【解析】页面呼叫 AI 老师为您详细讲解！"
                "</span>"
            )

        self.ui.gk_ai_display.setHtml(
            f"""
            <div style='background:#fdf6ec; padding:15px; border-radius:8px; border-left: 4px solid #e67e22;'>
                <h4 style='color:#e67e22; margin-top:0;'>📖 题目深度解析</h4>
                <div style='line-height:1.6; font-size:14px;'>{analysis}</div>
            </div>
            """
        )

        print(f"✅ 判分完成：{correct_count}/{total}")

    def update_nav_highlight(self):
        """顶部菜单按钮高亮控制"""
        btn_map = {
            "阅读理解": "gk_btn_reading",
            "完形填空": "gk_btn_cloze",
            "语法填空": "gk_btn_grammar",
            "七选五": "gk_btn_seven_five",
            "短文改错": "gk_btn_correction",
            "写作续写": "gk_btn_writing"
        }

        for type_name, obj_name in btn_map.items():
            btn = getattr(self.ui, obj_name, None)
            if btn:
                if type_name == self.current_type:
                    btn.setStyleSheet(
                        "background-color: #3498db; color: white; "
                        "border-radius: 5px; padding: 5px 10px; font-weight: bold;"
                    )
                else:
                    btn.setStyleSheet(
                        "background-color: transparent; color: #333; padding: 5px 10px;"
                    )