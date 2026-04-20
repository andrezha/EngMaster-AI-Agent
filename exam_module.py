import json
import os
import random
import re
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QRadioButton, QButtonGroup, QSizePolicy, QLineEdit, QMessageBox
from PySide6.QtCore import Qt
from parsers.reading_parser import parse_reading_txt


class ExamManager:
    """
    专项练习模块的核心管理器，负责加载、渲染和管理各类题型的练习。
    """
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
        """
        初始化 ExamManager。
        """
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
        self.currentGrammarData = None  # 语法填空数据
        self.currentClozeFillData = None  # 完形填空数据

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
        # 🎯 初始不默认加载任何题型，只确保按钮样式正确
        print("💡 [ExamManager] 初始不默认加载任何题型。")

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
        彻底清理所有状态，确保新页面是干净的。
        """
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
        """
        递归清理布局中的所有子组件（widget 和 layout）。
        """
        """递归清理布局中的所有项"""
        if not layout:
            return
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                # 物理销毁 widget
                child.widget().setParent(None)
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
        懒加载核心函数：获取或加载题型数据。
        """
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
            elif topic_name == "语法填空" and self.currentGrammarData is not None:
                print("📝 [懒加载] 语法填空数据已存在，直接返回缓存数据")
                self.current_q = self.currentGrammarData
                self.current_type = topic_name
                self.currentView = 'grammar'
                return True
            elif topic_name == "完形填空" and self.currentClozeFillData is not None:
                print("📝 [懒加载] 完形填空数据已存在，直接返回缓存数据")
                self.current_q = self.currentClozeFillData
                self.current_type = topic_name
                self.currentView = 'cloze_fill'
                return True
        
        # 2. 需要加载新数据（数据为 null 或点击了"下一题"）
        print(f"📥 [懒加载] 需要加载新数据: 下一题={is_next_button}")
        return self.fetchNewRandomFile(topic_name)
    
    def fetchNewRandomFile(self, topic_name):
        """
        从指定题型文件夹中随机加载一个新的 TXT 文件。
        """
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
            parsed_data = {} # Initialize parsed_data to an empty dict to prevent NameError if parse_reading_txt fails
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
            elif topic_name == "语法填空":
                self.currentGrammarData = question_data
                self.currentView = 'grammar'
            elif topic_name == "完形填空":
                self.currentClozeFillData = question_data
                self.currentView = 'cloze_fill'
            
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
        切换题型 - 懒加载逻辑。
        """
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
            print(f"DEBUG: Data for UI rendering: {json.dumps(self.current_q, ensure_ascii=False, indent=2)}")
            self.update_nav_highlight()
            # 渲染界面
            self.render_passage()
            self.render_question_ui()
            print("🏁 [Switch] 题型切换完成")
        else:
            print("❌ [Switch] 数据加载失败")

    def get_data_path(self):
        """
        根据当前题型获取严格的数据路径。
        """
        """根据当前题型获取严格的数据路径"""
        if self.current_type not in self.PATH_MAPPING:
            return None

        base_path = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(base_path, self.PATH_MAPPING[self.current_type])
        # 确保路径存在，否则返回 None
        if not os.path.exists(data_path):
            return None
        return data_path

    def load_and_render(self):
        """
        加载数据并渲染界面 - 支持懒加载。
        """
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
            print(f"DEBUG: Data for UI rendering: {json.dumps(self.current_q, ensure_ascii=False, indent=2)}")
            self.render_passage()
            self.render_question_ui()
            print("🏁 [load_and_render] 渲染流程全部执行完毕")
            print("=" * 30 + "\n")
        else:
            print("❌ [load_and_render] 数据加载失败")
            # 如果加载失败，尝试使用已有的缓存数据
            if self.current_type == "语法填空" and self.currentGrammarData is not None:
                print("🔄 [load_and_render] 尝试使用缓存的语法填空数据...")
                self.current_q = self.currentGrammarData
                self.render_passage()
                self.render_question_ui()
            elif self.current_type == "完形填空" and self.currentClozeFillData is not None:
                print("🔄 [load_and_render] 尝试使用缓存的完形填空数据...")
                self.current_q = self.currentClozeFillData
                self.render_passage()
                self.render_question_ui()
            elif self.current_type == "阅读理解" and self.currentReadingData is not None:
                print("🔄 [load_and_render] 尝试使用缓存的阅读理解数据...")
                self.current_q = self.currentReadingData
                self.render_passage()
                self.render_question_ui()
            elif self.current_type == "七选五" and self.currentClozeData is not None:
                print("🔄 [load_and_render] 尝试使用缓存的七选五数据...")
                self.current_q = self.currentClozeData
                self.render_passage()
                self.render_question_ui()

    def render_passage(self):
        """
        渲染文章区域，包括标题、文章内容和格式化。
        """
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

        # 🎯 根据CAT字段判断显示"真题"或"模拟"
        category_raw = self.current_q.get('category', '').strip()
        if "模拟" in category_raw:
            exam_type = "模拟"
        else:
            exam_type = "真题"

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

            top_tag = f"[{year}] {normalized_cat} {exam_type}"
            letter_str = f"【阅读理解 {passage_letter} 篇】" if passage_letter else "【阅读理解】"
            main_title_html = f"<h3 style='text-align: center; color: #34495e;'>{main_title}</h3>" if main_title else ""
        else:
            # 七选五等其他题型
            for line in p_lines:
                if line.strip():
                    p_text_lines.append(line)
            top_tag = f"[{year}] {normalized_cat} {exam_type}"
            letter_str = f"【{self.current_type}】"
            main_title_html = ""

        p_text = '\n'.join(p_text_lines).strip()
        
        # 🎯 如果是七选五且文章内容为空，显示提示
        if self.current_type == "七选五" and not p_text:
            # 对于七选五题型，'passage' 字段应包含带有空白的主体文章。
            # 如果此处为空，则表明解析器或输入文件格式存在问题。
            p_text = "<div style='color:#e74c3c; text-align:center; padding:20px; border:1px dashed #e74c3c; border-radius:8px; margin:20px 0;'>" \
                     "⚠️ **七选五文章主体内容缺失**<br>" \
                     "请检查 `parsers/reading_parser.py` 是否正确提取了 `[PASSAGE]` 部分，<br>" \
                     "或确保 `七选五` 题型的 TXT 文件中包含文章主体内容。" \
                     "</div>"
        
        # 🎯 清理HTML标签残留，保持原始格式
        import re
        p_text_clean = re.sub(r'<[^>]+>', '', p_text)
        
        # 🎯 完形填空、七选五、语法填空：将题号转换为 ___XX___ 格式，方便识别
        question_type = self.current_q.get('question_type', 'reading')
        if question_type in ['cloze', 'seven_five', 'grammar']:
            items = self.current_q.get('items', [])
            q_ids = [item.get('q_id', '') for item in items]
            
            # 将空格+题号+空格的格式转换为 ___XX___
            for q_id in q_ids:
                # 匹配空格+题号+空格的模式
                pattern = rf'(\s+){q_id}(\s+)'
                replacement = r'\1___' + q_id + r'___\2'
                p_text_clean = re.sub(pattern, replacement, p_text_clean)
        
        # 将换行转换为HTML的<br>
        p_text_html = p_text_clean.replace('\n', '<br>')

        # 最终标题拼接
        html_output = (
            f"<div style='text-align: center; color: #7f8c8d; font-size:14px; margin-bottom: 5px;'>{top_tag}</div>"
            f"<h2 style='text-align: center; color: #2c3e50; margin-top: 0;'>{letter_str}</h2>"
            f"{main_title_html}" # 移除 <hr> 标签
            f"<div style='font-size:16px; line-height:1.7; color:#2c3e50;'>{p_text_html}</div>"
        )
        self.ui.gk_question_body.setHtml(html_output)

    def render_question_ui(self):
        """
        动态生成答题按钮 - 使用条件渲染确保不同题型组件不会同时存在。
        """
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
        
        print(f"DEBUG: render_question_ui - self.current_q: {self.current_q}")
        print(f"🎨 [Render] 当前题型: {question_type}")
        print(f"📊 [Render] 题目数量: {len(items)}")
        if items:
            print(f"📋 [Render] 第一题数据: q_id={items[0].get('q_id')}, options_count={len(items[0].get('options', []))}")
        
        # 条件渲染：根据题型只创建对应的 UI 组件
        if question_type == "seven_five":
            # 只显示七选五 UI，不创建阅读理解的组件
            print("  → 渲染七选五 UI (ClozeOptionList)")
            self._render_seven_five_ui(layout, items)
        elif question_type == "grammar":
            # 显示语法填空 UI - 输入框形式
            print("  → 渲染语法填空 UI (GrammarFillWidget)")
            self._render_grammar_fill_ui(layout, items)
        elif question_type == "cloze":
            # 显示完形填空 UI - 选择题形式（与阅读理解类似但题号不同）
            print("  → 渲染完形填空 UI (ClozeQuestionWidget)")
            self._render_cloze_ui(layout, items)
        else:
            # 只显示阅读理解 UI，不创建七选五的组件
            print("  → 渲染阅读理解 UI (ReadingQuestionWidget)")
            self._render_reading_ui(layout, items)
        
        # 添加弹性空间，确保布局美观
        layout.addStretch()
        
        print("✅ [Render] UI 渲染完成")

    def _render_reading_ui(self, layout, items):
        """
        渲染阅读理解题目UI（单选题）。
        """
        """
        渲染阅读理解题目UI（单选题）
        
        🚨 关键修复：
        - 正则纠偏：确保解析器能准确识别 TXT 里的 [Q_1], [Q_2] 标签
        - 单选锁定：每一个 [Q_n] 块必须是一个独立的单选组（Radio Group）
        - 显示逻辑：如果读取的是阅读理解文件夹，必须强制触发 showQuestionCard = true
        """
        print(f"📝 [Reading UI] 开始渲染 {len(items)} 道阅读理解题目...")
        
        for idx, item in enumerate(items):
            print(f"DEBUG: _render_reading_ui processing item {idx}: {item}")
            qid = item.get('q_id', '')
            content = item.get('content', '')

            # 显示选项按钮行（优先使用 options 字段，否则从 content 提取）
            options = item.get('options', [])
            if options:
                # 使用已有的 options 字段
                qtext = content
            else:
                print(f"DEBUG: _render_reading_ui options empty for Q{qid}, extracting from content: {content[:100]}...")
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
                print(f"DEBUG: _render_reading_ui rendering options for Q{qid}: {options}")
                # 处理 options 为字典的情况（如完形填空解析器返回的格式）
                if isinstance(options, dict):
                    options_list = [f"{k}. {v}" for k, v in sorted(options.items())]
                else:
                    options_list = options
                for i, opt_content in enumerate(options_list):
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
        """
        从题目内容中提取题干和选项。
        """
        """从题目内容中提取题干和选项"""
        print(f"DEBUG: _extract_options_from_content received content (len {len(content)}): {content[:200]}...")
        # 容错处理：将全角 ． 替换为半角 .
        clean_content = content.replace('．', '.')
        
        # 🎯 关键修复：处理选项前缀格式不标准的情况
        # 统一将 "A", "A.", "A)" 等格式标准化为 "A. "
        # This regex looks for A, B, C, or D, optionally followed by a dot or parenthesis,
        # then optionally followed by spaces, and replaces it with "X. "
        clean_content = re.sub(r'([A-D])\s*[\.\)]?\s*', r'\1. ', clean_content)

        # Find positions using regex for more flexibility
        # Use a non-greedy match for the content of the option
        option_matches = list(re.finditer(r'([A-D])\.\s*(.*?)(?=\s*[A-D]\.|\Z)', clean_content, re.DOTALL))
        
        options_dict = {}
        q_text = clean_content

        if option_matches:
            # The question stem is everything before the first option
            first_option_start_pos = option_matches[0].start()
            q_text = clean_content[:first_option_start_pos].strip()

            # Extract options
            for i, match in enumerate(option_matches):
                label = match.group(1).upper()
                content = match.group(2).strip()
                options_dict[label] = content
            
            # Ensure all A, B, C, D are present and in order
            if all(label in options_dict for label in ['A', 'B', 'C', 'D']) and \
               list(options_dict.keys()) == ['A', 'B', 'C', 'D']:
                options = [options_dict['A'], options_dict['B'], options_dict['C'], options_dict['D']]
                print(f"DEBUG: _extract_options_from_content returning q_text (len {len(q_text)}): {q_text[:100]}..., options: {options}")
                return q_text, options
            else:
                print(f"DEBUG: _extract_options_from_content found options but not A,B,C,D in order: {options_dict}")
                return content, [] # Fallback if not all options or not in order
        else:
            # 兜底：没找齐四个选项或顺序错乱
            print(f"DEBUG: _extract_options_from_content failed to extract options, returning content and empty list.")
            return content, []

    def _render_seven_five_ui(self, layout, items):
        """
        渲染七选五题目UI（A-G选项列表）。
        """
        """渲染七选五题目UI（A-G选项列表）- 样式与阅读理解一致"""
        print(f"🔍 [七选五UI] 开始渲染，items数量: {len(items)}")
        
        if not items:
            print("⚠️ [七选五UI] items为空，直接返回")
            return

        # 获取选项列表（所有题目共享同一组选项）
        options_list = items[0].get('options', [])
        print(f"🔍 [七选五UI] options_list数量: {len(options_list)}")

        if not options_list:
            print("⚠️ [七选五UI] options_list为空，显示错误提示")
            no_opt_label = QLabel("<i style='color:#e74c3c;'>⚠️ 选项数据缺失，请检查TXT文件格式</i>")
            no_opt_label.setWordWrap(True)
            layout.addWidget(no_opt_label)
            return

        # 🎯 选项区域标题
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
        print("✅ [七选五UI] 已添加选项标题")

        # 🎯 选项显示区域
        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)
        options_layout.setSpacing(6)
        options_layout.setContentsMargins(5, 5, 5, 5)
        
        options_widget.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.MinimumExpanding
        )
        options_widget.setMinimumHeight(0)
        options_widget.setMaximumHeight(16777215)

        for opt in options_list:
            label = opt.get('label', '')
            content = opt.get('content', '')
            opt_text = f"{label}. {content}"

            opt_label = QLabel(opt_text)
            opt_label.setStyleSheet("""
                QLabel {
                    color: #374151;
                    font-size: 14px;
                    padding: 8px 12px;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    background-color: #f9fafb;
                }
                QLabel:hover {
                    background-color: #e5e7eb;
                }
            """)
            opt_label.setWordWrap(True)
            opt_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
            opt_label.setMinimumHeight(0)
            options_layout.addWidget(opt_label)

        layout.addWidget(options_widget)
        print("✅ [七选五UI] 已添加选项列表")

        # 分隔线
        separator = QLabel("<hr style='border: none; border-top: 1px solid #e5e7eb; margin: 8px 0;'>")
        layout.addWidget(separator)
        print("✅ [七选五UI] 已添加分隔线")

        # 为每个空白处创建选择器
        for idx, item in enumerate(items):
            qid = item.get('q_id', '')
            print(f"🔍 [七选五UI] 渲染第{idx+1}题，qid={qid}")
            
            # 显示题干
            q_label = QLabel(f"<b>{qid}.</b> 请选择答案")
            q_label.setWordWrap(True)
            q_label.setObjectName(f"label_q{qid}")
            q_label.setStyleSheet("QLabel { color: #2c3e50; font-size: 14px; padding: 4px 0; background: transparent; }")
            layout.addWidget(q_label)

            # 为每道题目创建独立的 QButtonGroup（单选组）
            blank_group = QButtonGroup(self.mw)
            blank_group.setExclusive(True)
            
            # 保存按钮组引用
            if not hasattr(self, 'seven_five_button_groups'):
                self.seven_five_button_groups = {}
            self.seven_five_button_groups[f"blank_{qid}"] = blank_group

            # 显示选项按钮
            for i, opt in enumerate(options_list):
                opt_label_text = opt.get('label', '')
                opt_content = opt.get('content', '')
                
                btn = QPushButton(f"{opt_label_text}. {opt_content}")
                btn.setCheckable(True)
                btn.setObjectName(f"btn_seven_q{qid}_opt{opt_label_text}")
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
                
                # 绑定点击事件
                btn.clicked.connect(
                    lambda checked, blank_id=qid, opt_label=opt_label_text:
                    self.on_seven_five_blank_choice(blank_id, opt_label, checked)
                )
                
                blank_group.addButton(btn)
                layout.addWidget(btn)

            # 添加分隔线
            sep = QLabel("<hr style='border: none; border-top: 1px solid #e5e7eb; margin: 8px 0;'>")
            layout.addWidget(sep)

        layout.addStretch()
        print("✅ [七选五UI] 渲染完成")

    def on_choice_click(self, qid, choice, btn):
        """
        记录用户选择（阅读理解）并取消同题其他按钮 - 旧版兼容。
        """
        """记录用户选择（阅读理解）并取消同题其他按钮 - 旧版兼容"""
        parent = btn.parentWidget()
        for child in parent.findChildren(QPushButton):
            if child != btn and child.isCheckable():
                child.setChecked(False)
        self.user_selections[qid] = choice
        # 确保 QButtonGroup 也能感知到这个选择，尽管这里是手动处理
        if hasattr(self, 'reading_button_groups') and qid in self.reading_button_groups:
            self.reading_button_groups[qid].buttonClicked.emit(btn)
        print(f"📝 题目 {qid}: 选择 {choice}")

    def on_reading_choice_click(self, qid, choice, btn):
        """
        记录用户选择（阅读理解）- 新版单选逻辑。
        """
        """
        记录用户选择（阅读理解）- 新版单选逻辑
        
        🚨 关键修复：使用 QButtonGroup 的互斥功能，确保每道题目的选项只能选一个
        不需要手动取消其他按钮，QButtonGroup.setExclusive(True) 会自动处理
        """
        self.user_selections[qid] = choice
        print(f"📝 [单选锁定] 题目 {qid}: 选择 {choice}")
        # QButtonGroup 会自动处理互斥，无需手动取消

    def on_seven_five_choice(self, opt_label, btn):
        """
        七选五选项点击（显示已选状态）。
        """
        """七选五选项点击（显示已选状态）"""
        # 这里只是视觉反馈，实际选择在 blank_choice 中处理
        pass

    def on_seven_five_blank_choice(self, blank_id, opt_label, checked):
        """
        记录七选五每个空白处的选择。
        """
        """记录七选五每个空白处的选择"""
        if checked:
            self.user_selections[blank_id] = opt_label
            print(f"📝 空白 {blank_id}: 选择 {opt_label}")
        elif blank_id in self.user_selections:
            del self.user_selections[blank_id]

    def _render_grammar_fill_ui(self, layout, items):
        """
        渲染语法填空题目UI（输入框形式）。
        """
        """
        渲染语法填空题目UI（输入框形式）

        
        🎯 语法填空特点：
        - 每题需要输入答案（而不是选择）
        - 题号通常是61-70
        - 答案可能是单词的不同形式
        """
        print(f"📝 [Grammar Fill UI] 开始渲染 {len(items)} 道语法填空题目...")
        
        # 创建输入框字典，方便后续获取用户答案
        self.grammar_input_fields = {}
        
        for item in items:
            qid = item.get('q_id', '')
            
            # 创建水平布局容器
            h_layout = QHBoxLayout()
            h_layout.setSpacing(12)
            h_layout.setContentsMargins(5, 8, 5, 8)
            
            # 题号标签（固定宽度，右对齐，普通颜色）
            q_label = QLabel(f"{qid}.")
            q_label.setFixedWidth(45)
            q_label.setStyleSheet("""
                QLabel {
                    font-size: 15px;
                    font-weight: bold;
                    color: #555555;
                    padding: 5px 8px;
                }
            """)
            q_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            h_layout.addWidget(q_label)
            
            # 答案输入框
            answer_input = QLineEdit()
            answer_input.setObjectName(f"grammar_input_{qid}")
            answer_input.setPlaceholderText("请输入答案...")
            answer_input.setFixedHeight(40)
            answer_input.setStyleSheet("""
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
            h_layout.addWidget(answer_input, stretch=1)
            
            # 保存输入框引用
            self.grammar_input_fields[qid] = answer_input
            
            # 答案显示标签（初始隐藏，查看答案时显示）
            answer_label = QLabel("")
            answer_label.setObjectName(f"grammar_answer_{qid}")
            answer_label.setWordWrap(True)
            answer_label.setStyleSheet("""
                QLabel {
                    font-size: 15px;
                    color: #27ae60;
                    font-weight: bold;
                    padding: 8px;
                    background-color: #f0f9ff;
                    border-radius: 6px;
                    border-left: 4px solid #27ae60;
                }
            """)
            answer_label.hide()
            h_layout.addWidget(answer_label, stretch=1)
            
            layout.addLayout(h_layout)
        
        print(f"✅ [Grammar Fill UI] {len(items)} 道题目渲染完成")

    def _render_cloze_ui(self, layout, items):
        """
        渲染完形填空题目UI（选择题形式，双列布局）。
        """
        """
        渲染完形填空题目UI（选择题形式，双列布局）
        
        🎯 完形填空特点：
        - 与阅读理解类似的选择题形式
        - 题号通常是36-55（两篇文章）
        - 每题4个选项
        - 🎯 双列布局：左右相邻数字（46左, 47右），方便选题，减少滚动
        - 🎯 无背景框：简洁显示，题号无背景框
        """
        print(f"📝 [Cloze UI] 开始渲染 {len(items)} 道完形填空题目...")
        
        # 🎯 双列布局：将题目分成两列
        cols_layout = QHBoxLayout()
        col1_layout = QVBoxLayout()
        col2_layout = QVBoxLayout()
        
        col1_layout.setSpacing(8)
        col2_layout.setSpacing(8)
        col1_layout.setContentsMargins(0, 0, 10, 0)
        col2_layout.setContentsMargins(10, 0, 0, 0)
        
        # 🎯 左右交替排序：奇数索引在左列，偶数索引在右列
        for idx, item in enumerate(items):
            qid = item.get('q_id', '')
            content = item.get('content', '')
            
            # 获取选项（完形填空的options是字典格式）
            options = item.get('options', [])
            
            # 🎯 无背景框容器
            q_widget = QWidget()
            q_layout = QVBoxLayout(q_widget)
            q_layout.setSpacing(4)
            q_layout.setContentsMargins(0, 4, 0, 4)
            # 移除背景框样式
            
            # 🎯 显示题干：如果有 content 就显示，否则只显示题号（无背景框）
            if content and content.strip():
                q_label = QLabel(f"<b>{qid}.</b> {content}")
            else:
                q_label = QLabel(f"<b>{qid}.</b>")
            q_label.setWordWrap(True)
            q_label.setObjectName(f"label_cloze_q{qid}")
            q_label.setStyleSheet("""
                QLabel {
                    color: #2c3e50;
                    font-size: 14px;
                    padding: 0;
                    background: transparent;
                    border: none;
                }
                QLabel b {
                    color: #e67e22;
                    font-weight: bold;
                }
            """)
            q_layout.addWidget(q_label)
            
            # 为每道题目创建独立的 QButtonGroup（单选组）
            question_button_group = QButtonGroup(self.mw)
            question_button_group.setExclusive(True)
            
            # 保存按钮组引用
            if not hasattr(self, 'cloze_button_groups'):
                self.cloze_button_groups = {}
            self.cloze_button_groups[qid] = question_button_group
            
            # 显示选项按钮（双列显示选项）
            if options:
                # 处理 options 为字典的情况
                if isinstance(options, dict):
                    options_list = [f"{k}. {v}" for k, v in sorted(options.items())]
                else:
                    options_list = options
                
                # 🎯 选项双列布局：A B 一行，C D 一行
                opts_grid = QHBoxLayout()
                opts_col1 = QVBoxLayout()
                opts_col2 = QVBoxLayout()
                
                for i, opt_content in enumerate(options_list):
                    btn = QPushButton(opt_content)
                    btn.setCheckable(True)
                    btn.setObjectName(f"btn_cloze_q{qid}_opt{chr(65+i)}")
                    btn.setStyleSheet("""
                        QPushButton {
                            text-align: left;
                            padding: 4px 8px;
                            border: 1px solid #d1d5db;
                            border-radius: 4px;
                            background-color: #ffffff;
                            font-size: 13px;
                            color: #374151;
                            min-height: 28px;
                        }
                        QPushButton:hover {
                            background-color: #f3f4f6;
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
                    
                    # 绑定点击事件
                    btn.clicked.connect(
                        lambda checked, q=qid, c=choice, b=btn: self.on_cloze_choice_click(q, c, b)
                    )
                    
                    # 🎯 双列分配：A C 在左列，B D 在右列
                    if i % 2 == 0:
                        opts_col1.addWidget(btn)
                    else:
                        opts_col2.addWidget(btn)
                
                opts_col1.setSpacing(2)
                opts_col2.setSpacing(2)
                opts_grid.addLayout(opts_col1)
                opts_grid.addLayout(opts_col2)
                q_layout.addLayout(opts_grid)
            
            # 🎯 左右交替排序：索引0,2,4...在左列，索引1,3,5...在右列
            if idx % 2 == 0:
                col1_layout.addWidget(q_widget)
            else:
                col2_layout.addWidget(q_widget)
        
        cols_layout.addLayout(col1_layout)
        cols_layout.addLayout(col2_layout)
        layout.addLayout(cols_layout)
        
        print(f"✅ [Cloze UI] {len(items)} 道题目渲染完成（双列布局，无背景框）")

    def on_cloze_choice_click(self, qid, choice, btn):
        """
        记录完形填空用户选择。
        """
        """记录完形填空用户选择"""
        self.user_selections[qid] = choice
        print(f"📝 [完形填空] 题目 {qid}: 选择 {choice}")

    def _check_grammar_answer(self, user_ans, correct_answer):
        """
        检查语法填空答案是否正确，支持多种答案格式。
        """
        """
        检查语法填空答案是否正确
        
        🎯 支持多种答案格式：
        - 单一答案: "being"
        - 多个可选答案: "a/the" 或 "which/that"
        - 带斜杠的格式: "have made/have gotten"
        """
        if not user_ans or not correct_answer:
            return False
        
        # 去除空格
        user_ans = user_ans.strip().lower()
        correct_answer = correct_answer.strip().lower()
        
        # 如果答案完全匹配
        if user_ans == correct_answer:
            return True
        
        # 处理 "a/the" 或 "which/that" 格式（支持多种正确答案）
        if '/' in correct_answer or '／' in correct_answer:
            # 替换全角斜杠
            correct_answer = correct_answer.replace('／', '/')
            # 分割多个可选答案
            valid_answers = [ans.strip() for ans in correct_answer.split('/')]
            if user_ans in valid_answers:
                return True
        
        # 处理 "【答案】61. being" 这种格式（提取实际答案）
        if '【答案】' in correct_answer:
            # 提取 "【答案】" 后面的内容
            actual_answer = correct_answer.split('【答案】')[-1].strip()
            # 去除题号前缀如 "61. "
            actual_answer = re.sub(r'^\d+\.\s*', '', actual_answer)
            if user_ans == actual_answer.lower().strip():
                return True
        
        return False

    def check_score(self):
        """
        判分与展示解析，使用 PyQt5 原生方式实现分析按钮。
        """
        """判分与展示解析 - 使用 PyQt5 原生方式实现分析按钮"""
        if not self.current_q:
            return

        correct_count = 0
        items = self.current_q.get('items', [])
        total = len(items)

        if total == 0:
            self.ui.gk_result_panel.setHtml( # This is a QTextBrowser, so it's fine.
                "<div style='padding:10px; color:#e74c3c;'>❌ 没有可判分的题目</div>"
            )
            return

        # 🎯 解析分割（提前准备）
        analysis = self.current_q.get('original_analysis', '').strip()
        analysis_by_q = {}
        if analysis:
            parts = re.split(r'(?:^|\n)\s*(【\d+题详解】|\d+[．.])', analysis)
            current_q_num = ""
            for i, part in enumerate(parts):
                part = part.strip()
                if not part:
                    continue
                if re.match(r'【\d+题详解】', part) or re.match(r'\d+[．.]', part):
                    q_match = re.search(r'(\d+)', part)
                    if q_match:
                        current_q_num = q_match.group(1)
                elif current_q_num and part:
                    clean_content = re.sub(r'<[^>]+>', '', part)
                    analysis_by_q[current_q_num] = clean_content
            
            # 如果没有找到分割的题号，尝试另一种格式
            if not analysis_by_q:
                pattern = re.findall(r'(\d+)[．.]\s*(.*?)(?=\d+[．.]|$)', analysis, re.DOTALL)
                for q_num, content in pattern:
                    if content.strip():
                        clean_content = re.sub(r'<[^>]+>', '', content.strip())
                        analysis_by_q[q_num] = clean_content

        # 🎯 保存解析数据，供按钮点击时使用
        self._analysis_by_q = analysis_by_q
        self._shown_analysis_qids = set()

        # 🎯 使用 QWidget 布局代替 HTML，实现可点击的分析按钮
        result_widget = QWidget()
        result_main_layout = QVBoxLayout(result_widget)
        result_main_layout.setSpacing(0)
        result_main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 得分标题区域（固定高度，不会被压缩）
        score_widget = QWidget()
        score_layout = QVBoxLayout(score_widget)
        score_layout.setContentsMargins(10, 10, 10, 10)
        score_layout.setSpacing(5)
        
        score_label = QLabel(f"<h3 style='color:#2c3e50; margin:0;'>得分：{correct_count}/{total} ({correct_count/total*100:.1f}%)</h3>")
        score_layout.addWidget(score_label)
        
        # 分隔线
        line = QLabel("<hr style='border: none; border-top: 2px solid #e5e7eb; margin: 0;'>")
        score_layout.addWidget(line)
        
        result_main_layout.addWidget(score_widget)
        
        # 题目结果区域（可滚动，使用独立容器）
        result_scroll = QWidget()
        result_layout = QVBoxLayout(result_scroll)
        result_layout.setSpacing(8)
        result_layout.setContentsMargins(10, 5, 10, 10)

        question_type = self.current_q.get('question_type', 'reading')
        
        # 🎯 语法填空特殊处理
        if question_type == "grammar":
            for item in items:
                qid = item.get('q_id', '')
                correct_answer = item.get('answer', '').strip().lower()
                
                user_ans = "未做"
                if hasattr(self, 'grammar_input_fields') and qid in self.grammar_input_fields:
                    input_widget = self.grammar_input_fields[qid]
                    if input_widget:
                        user_ans = input_widget.text().strip().lower()
                
                # 创建题目结果容器
                item_widget = QWidget()
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(8, 8, 8, 8)
                item_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                
                # 题目信息标签
                if not correct_answer:
                    info_text = f"第{qid}题：你的答案 <b>{user_ans}</b> | 正确答案 <b style='color:#e67e22;'>未知 (题库未录入)</b>"
                else:
                    is_correct = self._check_grammar_answer(user_ans, correct_answer)
                    color = "#27ae60" if is_correct else "#e74c3c"
                    if is_correct:
                        correct_count += 1
                    info_text = f"第{qid}题：你的答案 <b>{user_ans}</b> | 正确答案 <b style='color:{color};'>{correct_answer}</b>"
                
                info_label = QLabel(info_text)
                info_label.setWordWrap(True)
                info_label.setTextFormat(Qt.RichText)
                item_layout.addWidget(info_label, 1)
                
                # 🎯 添加分析按钮（PyQt5 原生按钮）
                has_analysis = qid in analysis_by_q
                if has_analysis:
                    analysis_btn = QPushButton("📖 查看解析")
                    analysis_btn.setFixedHeight(32)
                    analysis_btn.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                stop:0 #3498db, stop:1 #2980b9);
                            color: white;
                            border: none;
                            border-radius: 6px;
                            padding: 4px 14px;
                            font-size: 13px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                stop:0 #2980b9, stop:1 #2471a3);
                        }
                        QPushButton:pressed {
                            background: #2471a3;
                        }
                    """)
                    # 🎯 绑定点击事件
                    analysis_btn.clicked.connect(lambda checked, q=qid: self._on_analysis_button_click(q))
                    item_layout.addWidget(analysis_btn)
                
                result_layout.addWidget(item_widget)
        else:
            # 其他题型
            if question_type == "cloze":
                # 🎯 完形填空：两列布局
                cols_layout = QHBoxLayout()
                col1_layout = QVBoxLayout()
                col2_layout = QVBoxLayout()
                
                col1_layout.setSpacing(8)
                col2_layout.setSpacing(8)
                col1_layout.setContentsMargins(0, 0, 10, 0)
                col2_layout.setContentsMargins(10, 0, 0, 0)
                
                for idx, item in enumerate(items):
                    qid = item.get('q_id', '')
                    ans = item.get('answer', '').strip().upper()
                    user_ans = self.user_selections.get(qid, "未做")

                    # 创建题目结果容器
                    item_widget = QWidget()
                    item_layout = QHBoxLayout(item_widget)
                    item_layout.setContentsMargins(8, 8, 8, 8)
                    item_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                    
                    if not ans:
                        info_text = f"第{qid}题：你的选择 <b>{user_ans}</b> | 正确答案 <b style='color:#e67e22;'>未知 (题库未录入)</b>"
                    else:
                        color = "#27ae60" if user_ans == ans else "#e74c3c"
                        if user_ans == ans:
                            correct_count += 1
                        info_text = f"第{qid}题：你的选择 <b>{user_ans}</b> | 正确答案 <b style='color:{color};'>{ans}</b>"
                    
                    info_label = QLabel(info_text)
                    info_label.setWordWrap(True)
                    info_label.setTextFormat(Qt.RichText)
                    item_layout.addWidget(info_label, 1)
                    
                    # 🎯 添加分析按钮（PyQt5 原生按钮）
                    has_analysis = qid in analysis_by_q
                    if has_analysis:
                        analysis_btn = QPushButton("📖 查看解析")
                        analysis_btn.setFixedHeight(32)
                        analysis_btn.setStyleSheet("""
                            QPushButton {
                                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                    stop:0 #3498db, stop:1 #2980b9);
                                color: white;
                                border: none;
                                border-radius: 6px;
                                padding: 4px 14px;
                                font-size: 13px;
                                font-weight: bold;
                            }
                            QPushButton:hover {
                                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                    stop:0 #2980b9, stop:1 #2471a3);
                            }
                            QPushButton:pressed {
                                background: #2471a3;
                            }
                        """)
                        # 🎯 绑定点击事件
                        analysis_btn.clicked.connect(lambda checked, q=qid: self._on_analysis_button_click(q))
                        item_layout.addWidget(analysis_btn)
                    
                    # 🎯 左右交替排序：索引0,2,4...在左列，索引1,3,5...在右列
                    if idx % 2 == 0:
                        col1_layout.addWidget(item_widget)
                    else:
                        col2_layout.addWidget(item_widget)
                
                cols_layout.addLayout(col1_layout)
                cols_layout.addLayout(col2_layout)
                result_layout.addLayout(cols_layout)
            else:
                # 其他题型保持原有一列布局
                for item in items:
                    qid = item.get('q_id', '')
                    ans = item.get('answer', '').strip().upper()
                    user_ans = self.user_selections.get(qid, "未做")

                    # 创建题目结果容器
                    item_widget = QWidget()
                    item_layout = QHBoxLayout(item_widget)
                    item_layout.setContentsMargins(8, 8, 8, 8)
                    item_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                    
                    if not ans:
                        info_text = f"第{qid}题：你的选择 <b>{user_ans}</b> | 正确答案 <b style='color:#e67e22;'>未知 (题库未录入)</b>"
                    else:
                        color = "#27ae60" if user_ans == ans else "#e74c3c"
                        if user_ans == ans:
                            correct_count += 1
                        info_text = f"第{qid}题：你的选择 <b>{user_ans}</b> | 正确答案 <b style='color:{color};'>{ans}</b>"
                    
                    info_label = QLabel(info_text)
                    info_label.setWordWrap(True)
                    info_label.setTextFormat(Qt.RichText)
                    item_layout.addWidget(info_label, 1)
                    
                    # 🎯 添加分析按钮（PyQt5 原生按钮）
                    has_analysis = qid in analysis_by_q
                    if has_analysis:
                        analysis_btn = QPushButton("📖 查看解析")
                        analysis_btn.setFixedHeight(32)
                        analysis_btn.setStyleSheet("""
                            QPushButton {
                                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                    stop:0 #3498db, stop:1 #2980b9);
                                color: white;
                                border: none;
                                border-radius: 6px;
                                padding: 4px 14px;
                                font-size: 13px;
                                font-weight: bold;
                            }
                            QPushButton:hover {
                                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                    stop:0 #2980b9, stop:1 #2471a3);
                            }
                            QPushButton:pressed {
                                background: #2471a3;
                            }
                        """)
                        # 🎯 绑定点击事件
                        analysis_btn.clicked.connect(lambda checked, q=qid: self._on_analysis_button_click(q))
                        item_layout.addWidget(analysis_btn)
                    
                    result_layout.addWidget(item_widget)

        result_layout.addStretch()
        
        # 🎯 将 result_widget 的内容复制到 gk_result_panel
        # 确保 gk_result_panel 有布局
        panel_layout = self.ui.gk_result_panel.layout()
        if not panel_layout:
            # 创建新布局
            panel_layout = QVBoxLayout(self.ui.gk_result_panel)
            self.ui.gk_result_panel.setLayout(panel_layout)
        
        panel_layout.setSpacing(8)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        
        # 🚨 强制清空现有内容（包括 widget 和 layout）
        while panel_layout.count():
            child = panel_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                # 递归清空嵌套布局
                self._clear_layout(child.layout())
        
        # 将 result_widget 的子控件移动到 panel_layout
        while result_layout.count():
            item = result_layout.takeAt(0)
            if item.widget():
                panel_layout.addWidget(item.widget())
            elif item.layout():
                panel_layout.addLayout(item.layout())
        
        # 2. 渲染右侧 AI 解析（初始显示提示文字）
        self.ui.gk_ai_display.setHtml(
            """
            <div id="aiAnalysisPanel" style='background:#fdf6ec; padding:15px; border-radius:8px; border-left: 4px solid #e67e22; min-height:100px;'>
                <div style="color:#7f8c8d; text-align:center; padding:20px;">点击左侧题目后的"📖 查看解析"按钮，解析将在此处显示</div>
            </div>
            """
        )

        print(f"✅ 判分完成：{correct_count}/{total}")

    def _on_analysis_link_clicked(self, url):
        """
        处理分析链接点击事件。
        """
        """分析链接点击事件处理"""
        # 从 URL 中提取题号
        url_str = url.toString()
        if url_str.startswith("analysis_"):
            qid = url_str.replace("analysis_", "")
            self._on_analysis_button_click(qid)

    def _on_analysis_button_click(self, qid):
        """
        处理分析按钮点击事件，切换解析的显示/隐藏状态。
        """
    def _on_analysis_button_click(self, qid):
        """分析按钮点击事件处理"""
        if not hasattr(self, '_analysis_by_q'):
            return
        
        analysis_text = self._analysis_by_q.get(qid, "")
        if not analysis_text:
            return
        
        # 🎯 切换显示状态
        if not hasattr(self, '_shown_analysis_qids'):
            self._shown_analysis_qids = set()
        
        if qid in self._shown_analysis_qids:
            self._shown_analysis_qids.remove(qid)
        else:
            self._shown_analysis_qids.add(qid)
        
        # 🎯 更新右侧解析框
        self._update_analysis_panel()

    def _update_analysis_panel(self):
        """
        更新右侧解析框显示，根据已显示的题目ID生成HTML。
        """
        """更新右侧解析框显示"""
        if not hasattr(self, '_shown_analysis_qids') or not hasattr(self, '_analysis_by_q'):
            return
        
        if not self._shown_analysis_qids:
            # 没有显示任何解析，显示提示文字
            self.ui.gk_ai_display.setHtml(
                """
                <div id="aiAnalysisPanel" style='background:#fdf6ec; padding:15px; border-radius:8px; border-left: 4px solid #e67e22; min-height:100px;'>
                    <div style="color:#7f8c8d; text-align:center; padding:20px;">👆 点击左侧题目后的"📖 查看解析"按钮，解析将在此处显示</div>
                </div>
                """
            )
            return
        
        # 生成解析HTML
        html_parts = ['<h4 style="color:#e67e22; margin-top:0;">📖 题目深度解析</h4>']
        for qid in sorted(self._shown_analysis_qids, key=int): # 确保按数字顺序显示
            formatted_analysis = self._format_analysis_by_question(qid)
            if formatted_analysis:
                html_parts.append(formatted_analysis)
        
        analysis_html = "\n".join(html_parts)
        self.ui.gk_ai_display.setHtml(
            f"""
            <div style='background:#fdf6ec; padding:15px; border-radius:8px; border-left: 4px solid #e67e22; min-height:100px;'>
                {analysis_html}
            </div>
            """
        )

    def _format_analysis_by_question(self, analysis):
        """
        根据已解析的 `self._analysis_by_q`，为指定题号生成格式化的 HTML 解析内容。
        """
        qid = analysis # In this context, 'analysis' is actually the qid
        if not hasattr(self, '_analysis_by_q') or qid not in self._analysis_by_q:
            return ""
        
        content = self._analysis_by_q.get(qid, "")
        if not content:
            return ""

        # 清理内容中的HTML标签（如果_parse_analysis_for_display没有完全清理）
        clean_content = re.sub(r'<[^>]+>', '', content)

        return (
            f"<div style='margin-bottom: 12px; padding: 8px; background: #fff; border-radius: 6px; border-left: 3px solid #3498db;'>"
            f"<strong style='color: #3498db;'>第{qid}题</strong> "
            f"<span style='color: #555;'>{clean_content}</span>"
            f"</div>"
        )

    def update_nav_highlight(self):
        """
        更新顶部菜单按钮的高亮状态。
        """
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
                        "background-color: #f0f0f0; color: #333; border-radius: 5px; padding: 5px 10px;"
                    )