import json
import random
import os
from PySide6 import QtCore, QtWidgets, QtGui  # Import QtGui for QMenu
from datetime import datetime  # Import datetime for filename generation
from PySide6.QtCore import Signal, QObject  # Import Signal and QObject
from PySide6.QtWidgets import QMessageBox  # Explicitly import QMessageBox
from PySide6.QtGui import QDesktopServices  # For opening file
from PySide6.QtCore import QUrl
from utils import get_writable_data_path, _normalize_full_width_to_half_width, get_resource_path


class VocabManager(QObject):  # 继承自 QObject
    """
    词汇学习模块管理器，负责加载词汇、显示单词、检查用户输入和计时。
    """
    mistake_vocabulary_changed = Signal(list)  # Define the signal

    def __init__(self, main_window_instance, initial_vocabulary=None, initial_mistake_vocabulary=None):
        self.main_window = main_window_instance  # Store the main window instance
        super().__init__(main_window_instance)  # 调用父类 QObject 的构造函数，并设置父对

        self.initial_vocabulary = initial_vocabulary
        self.initial_mistake_vocabulary = initial_mistake_vocabulary

        self.current_idx = 0
        self.time_left = 15

        self.mistake_word_file_path = get_writable_data_path(
            "mistake_words.json")
        # Find the vocabulary page widget from the main window's stacked widget.
        # Assuming the vocabulary page is the first widget in the stackedWidget.
        # 🟢 [架构师单点植入] 仅处理路径，不触动任何 UI 绑定
        self.mistake_word_file_path = get_writable_data_path(
            "mistake_words.json")
        print(f"🔍 [Path Audit] {self.mistake_word_file_path}")
        self.vocab_page_widget = self.main_window.stack.findChild(
            QtWidgets.QWidget, "page_vocab")
        if not self.vocab_page_widget and self.main_window.stack:
            # If the page has been shifted by the loading screen, fallback to index 1.
            self.vocab_page_widget = self.main_window.stack.widget(1)

        if not self.vocab_page_widget:
            raise AttributeError(
                "Vocabulary page widget not found in stackedWidget. Ensure page_vocab exists.")

        # 查找控件
        self.v_input = self.vocab_page_widget.findChild(
            QtWidgets.QLineEdit, "vocab_input")
        self.v_disp = self.vocab_page_widget.findChild(
            QtWidgets.QTextEdit, "vocab_display")
        self.t_label = self.vocab_page_widget.findChild(
            QtWidgets.QLabel, "timer_label")
        self.btn_confirm = self.vocab_page_widget.findChild(
            QtWidgets.QPushButton, "btn_confirm")

        # 新增：闯关模式选择按钮和打印控件
        self.btn_challenge_regular = self.vocab_page_widget.findChild(
            QtWidgets.QPushButton, "btn_challenge_regular")  # 查找现有按钮
        if not self.btn_challenge_regular:  # 如果没找到，则创建
            self.btn_challenge_regular = QtWidgets.QPushButton("常规闯关")
            self.btn_challenge_regular.setObjectName("btn_challenge_regular")
            self.btn_challenge_regular.setCheckable(True)  # 使按钮可选中
            print("DEBUG: btn_challenge_regular created dynamically.")

        self.btn_challenge_mistake = self.vocab_page_widget.findChild(
            QtWidgets.QPushButton, "btn_challenge_mistake")  # 查找现有按钮
        if not self.btn_challenge_mistake:  # 如果没找到，则创建
            self.btn_challenge_mistake = QtWidgets.QPushButton("错词闯关")
            self.btn_challenge_mistake.setObjectName("btn_challenge_mistake")
            self.btn_challenge_mistake.setCheckable(True)  # 使按钮可选中
            # This line was moved up.
            print("DEBUG: btn_challenge_mistake created dynamically.")

        # NEW: 自主录入闯关按钮
        self.btn_challenge_self_register = self.vocab_page_widget.findChild(
            QtWidgets.QPushButton, "btn_challenge_self_register")
        if not self.btn_challenge_self_register:
            self.btn_challenge_self_register = QtWidgets.QPushButton("自主录入闯关")
            self.btn_challenge_self_register.setObjectName(
                "btn_challenge_self_register")
            self.btn_challenge_self_register.setCheckable(True)
            print("DEBUG: btn_challenge_self_register created dynamically.")

        self.lbl_mistake_count = self.vocab_page_widget.findChild(
            QtWidgets.QLabel, "lbl_mistake_count")  # 查找现有标签
        if not self.lbl_mistake_count:  # 如果没找到，则创建
            self.lbl_mistake_count = QtWidgets.QLabel("错词表 (0 词)")
            self.lbl_mistake_count.setObjectName("lbl_mistake_count")
            print("DEBUG: lbl_mistake_count created dynamically.")

        # NEW: 自主录入单词数标签
        self.lbl_self_register_count = self.vocab_page_widget.findChild(
            QtWidgets.QLabel, "lbl_self_register_count")
        if not self.lbl_self_register_count:
            self.lbl_self_register_count = QtWidgets.QLabel("自主录入 (0 词)")
            self.lbl_self_register_count.setObjectName(
                "lbl_self_register_count")
            print("DEBUG: lbl_self_register_count created dynamically.")

        # 初始化词汇表相关属性
        self.vocabulary = []  # 常规词汇
        self.mistake_vocabulary = []  # 错词表 (包含 correct_count)
        self.self_registered_vocabulary = []  # NEW: 自主录入词汇表
        self.current_challenge_mode = "regular"  # 默认常规闯关模式
        self._notification_message_for_next_display = ""  # 用于在显示下一个单词时传递通知消息

        # 初始化计时器
        # Keep timer initialized to prevent AttributeError on .stop()
        self.timer = QtCore.QTimer()
        # self.timer.timeout.connect(self.tick) # Comment out connection to tick as tick method is removed

        # 绑定逻辑
        if self.btn_confirm:
            self.btn_confirm.clicked.connect(self.check_answer)
        if self.v_input:
            self.v_input.returnPressed.connect(self.check_answer)

        # 绑定闯关模式选择按钮
        if self.btn_challenge_regular:
            self.btn_challenge_regular.clicked.connect(
                lambda: self.switch_challenge_mode("regular"))
        if self.btn_challenge_mistake:
            self.btn_challenge_mistake.clicked.connect(
                lambda: self.switch_challenge_mode("mistake_list"))
        # NEW: 绑定自主录入闯关按钮
        if self.btn_challenge_self_register:
            self.btn_challenge_self_register.clicked.connect(
                lambda: self.switch_challenge_mode("self_register"))

        # 重构布局
        self._rebuild_layout()

        # 统一样式 (在 _rebuild_layout 之后调用，确保所有组件都已就位)
        self._style_components()

        # 初始加载常规闯关模式
        self.switch_challenge_mode("regular")

    def _rebuild_layout(self):
        """
        重构词汇学习页面的布局，实现倒计时置顶、单词居中等效果。
        """
        # Get the layout of the vocab_page_widget
        self.main_layout = self.vocab_page_widget.layout()
        if not self.main_layout:
            # If the vocab_page_widget doesn't have a layout, create one.
            self.main_layout = QtWidgets.QVBoxLayout(self.vocab_page_widget)
            self.vocab_page_widget.setLayout(self.main_layout)

        if not self.v_disp or not self.v_input or not self.btn_confirm:
            return

        # Clear existing layout completely, but DO NOT delete the widgets we want to reuse. Instead, just remove them from the layout.
        widgets_to_keep = {self.t_label, self.v_disp, self.v_input, self.btn_confirm,
                           self.btn_challenge_regular, self.btn_challenge_mistake, self.btn_challenge_self_register,  # NEW
                           self.lbl_mistake_count, self.lbl_self_register_count}  # NEW
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                if item.widget() in widgets_to_keep:
                    # If it's a widget we want to reuse, just remove it from the layout
                    item.widget().setParent(None)  # Detach from parent layout
                else:
                    item.widget().deleteLater()  # Delete other widgets
            elif item.layout():
                # Recursively clear nested layouts, passing widgets_to_keep
                self._clear_layout(item.layout(), widgets_to_keep)

        # 1. 倒计时 - 红色置顶，右上角
        # timer_row_layout = QtWidgets.QHBoxLayout() # 注释掉：不再显示倒计时
        # timer_row_layout.addStretch(1) # 注释掉：不再显示倒计时
        # timer_row_layout.addWidget(self.t_label) # 注释掉：不再显示倒计时
        # self.main_layout.addLayout(timer_row_layout) # 注释掉：不再显示倒计时
        self.main_layout.addSpacing(15)  # 与窗口顶部保持约15px边距

        # 新增：闯关模式选择按钮和错词数量显示
        challenge_mode_layout = QtWidgets.QHBoxLayout()
        challenge_mode_layout.addStretch(1)  # 将按钮推到中间
        challenge_mode_layout.addWidget(self.btn_challenge_regular)
        challenge_mode_layout.addSpacing(10)  # 按钮之间间距
        challenge_mode_layout.addWidget(self.btn_challenge_mistake)
        challenge_mode_layout.addSpacing(10)  # NEW: 按钮之间间距
        challenge_mode_layout.addWidget(
            self.btn_challenge_self_register)  # NEW: 自主录入闯关按钮
        challenge_mode_layout.addSpacing(20)  # 按钮与标签之间间距
        challenge_mode_layout.addWidget(
            self.lbl_mistake_count)  # Add mistake count label
        challenge_mode_layout.addSpacing(10)  # NEW: 标签之间间距
        challenge_mode_layout.addWidget(
            self.lbl_self_register_count)  # NEW: 自主录入单词数标签
        challenge_mode_layout.addStretch(1)  # 将按钮推到中间
        self.main_layout.addLayout(challenge_mode_layout)
        self.main_layout.addSpacing(20)  # 模式选择与单词显示区之间间距

        # 2. 顶部弹簧 - 黄金重心（上移）
        self.main_layout.addStretch(1)

        # 3. 单词显示区 - 居中
        self.main_layout.addWidget(
            self.v_disp, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # 错词数量标签 - 放在单词显示区下方
        # self.main_layout.addWidget(self.lbl_mistake_count, alignment=QtCore.Qt.AlignmentFlag.AlignCenter) # Moved to challenge_mode_layout

        # 4. 巨大间距 - 拒绝拥挤
        self.main_layout.addSpacing(80)  # 单词和输入框之间

        # 5. 输入框 - 限宽 300px，居中
        self.v_input.setFixedWidth(300)
        self.main_layout.addWidget(
            self.v_input, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # 6. 间距
        self.main_layout.addSpacing(40)  # 输入框和按钮之间

        # 7. 确认按钮 - 限宽 300px，居中
        self.btn_confirm.setFixedWidth(300)
        self.main_layout.addWidget(
            self.btn_confirm, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # 8. 底部弹簧 - 黄金重心（2倍，使内容上移）
        self.main_layout.addStretch(2)

    # Accept widgets_to_keep_set as an argument
    def _clear_layout(self, layout, widgets_to_keep_set):
        """
        Helper to recursively clear a layout.
        """
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                if item.widget() not in widgets_to_keep_set:
                    item.widget().deleteLater()
                else:
                    item.widget().setParent(None)  # Detach from parent layout if it's one we keep
            elif item.layout():
                # Recursive call with the argument
                self._clear_layout(item.layout(), widgets_to_keep_set)

    def _style_components(self):
        """
        为词汇学习模块的UI组件应用统一的样式。
        """
        """统一样式规范：现代、简洁、专业"""

        # 倒计时标签 - 红色置顶，醒目
        # if self.t_label: # 注释掉：不再显示倒计时
        #     self.t_label.setStyleSheet("""
        #         QLabel {
        #             color: #E74C3C;
        #             font-size: 18px;
        #             font-weight: bold;
        #             background: transparent;
        #             padding: 4px 12px;
        #         }
        #     """)

        # 输入框 - 38px 高度，现代边框
        if self.v_input:  # 确保输入框宽度和居中由 UI 文件控制
            self.v_input.setFixedHeight(38)
            self.v_input.setStyleSheet("""
				QLineEdit {
					background-color: #fafafa;
					border: 1px solid #ddd;
					border-radius: 6px;
					font-size: 18px;
					padding: 0px 16px;
					color: #333333;
					font-family: "Arial", "Microsoft YaHei"; /* Add font family for consistency */
				}
				QLineEdit:focus {
					border: 1px solid #2196F3;
					background-color: #ffffff;
					outline: none;
				}
			""")

        # 确认按钮 - 42px 高度
        if self.btn_confirm:  # 确保按钮宽度和居中由 UI 文件控制
            self.btn_confirm.setFixedHeight(42)
            self.btn_confirm.setStyleSheet("""
				QPushButton {
					background-color: #2196F3;
					color: white;
					border: none;
					border-radius: 6px;
					font-size: 16px;
					font-weight: bold;
				}
				QPushButton:hover {
					background-color: #1976D2;
				}
				QPushButton:pressed {
					background-color: #1565C0;
				}
			""")

        # 显示区域 - 透明背景，无边框，固定宽度防止滚动条
        if self.v_disp:  # 确保显示区域宽度和居中由 UI 文件控制
            self.v_disp.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignCenter)  # 保持文本居中
            self.v_disp.setFixedWidth(600)  # 固定宽度，防止出现滚动条
            self.v_disp.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOff)  # 禁用水平滚动条
            self.v_disp.setStyleSheet("""
				QTextEdit {
					background-color: transparent;
					border: none;
					font-family: "Arial", "Microsoft YaHei"; /* Add font family for consistency */
				}
			""")

        # Apply a default background to the vocab_page_widget itself for consistency
        if self.vocab_page_widget:
            # Assuming the objectName of the vocabulary page widget is 'vocab_page_widget' in the UI file
            self.vocab_page_widget.setStyleSheet("""
				QWidget#vocab_page_widget { background-color: #f0f2f5; } /* Light grey background */
			""")

        # 错词数量标签样式
        if self.lbl_mistake_count:
            self.lbl_mistake_count.setStyleSheet("""
				QLabel {
					color: #777777;
					font-size: 13px;
					padding: 4px 8px;
					border: 1px solid #cccccc;
					border-radius: 4px;
					background-color: #f5f5f5;
				}
			""")

        # NEW: 自主录入单词数标签样式
        if self.lbl_self_register_count:
            self.lbl_self_register_count.setStyleSheet("""
				QLabel {
					color: #777777;
					font-size: 13px;
					padding: 4px 8px;
					border: 1px solid #cccccc;
					border-radius: 4px;
					background-color: #f5f5f5;
				}
			""")

    def _load_regular_vocabulary(self):
        """
        从 assets/vocabulary.json 文件加载词汇表并随机打乱。
        """
        if self.initial_vocabulary is not None:
            self.vocabulary = list(self.initial_vocabulary)
            random.shuffle(self.vocabulary)
            print(f"✅ 常规词汇表已从后台数据加载完成，共 {len(self.vocabulary)} 词。")
            return
        try:
            vocab_path = get_resource_path("assets/vocabulary.json")
            print(
                f"DEBUG: Attempting to load regular vocabulary from: {vocab_path}")
            if not os.path.exists(vocab_path):
                print(
                    f"ERROR: Regular vocabulary file not found: {vocab_path}")
                raise FileNotFoundError(f"常规词汇表文件不存在: {vocab_path}")

            with open(vocab_path, "r", encoding="utf-8") as f:
                self.vocabulary = json.load(f)
                random.shuffle(self.vocabulary)
            print(f"✅ 常规词汇表加载成功，共 {len(self.vocabulary)} 词。")
            print(f"DEBUG: First 3 words loaded: {self.vocabulary[:3]}")
        except Exception as e:  # Use self.main_window for QMessageBox
            print(f"❌ 加载常规词汇表失败: {e}")
            self.vocabulary = [{"word": "apple", "content": "苹果", "pronunciation": "/ˈæpl/",
                                "example": "An apple a day keeps the doctor away."}]  # Fallback with more details
            QMessageBox.warning(
                self.main_window, "错误", f"加载常规词汇表失败: {e}\n请检查 assets/vocabulary.json 文件。已加载默认词汇。")
            print(f"DEBUG: Fallback vocabulary loaded: {self.vocabulary}")

    def _load_mistake_vocabulary(self):
        """
        从 mistake_words.json 文件加载错词表。
        """
        if self.initial_mistake_vocabulary is not None:
            self.mistake_vocabulary = list(self.initial_mistake_vocabulary)
            for word_obj in self.mistake_vocabulary:
                word_obj.setdefault('pronunciation', '')
                word_obj.setdefault('example', '')
            random.shuffle(self.mistake_vocabulary)
            print(f"✅ 错词表已从后台数据加载完成，共 {len(self.mistake_vocabulary)} 词。")
            return

        try:
            if os.path.exists(self.mistake_word_file_path):
                with open(self.mistake_word_file_path, "r", encoding="utf-8") as f:
                    self.mistake_vocabulary = json.load(f)
                random.shuffle(self.mistake_vocabulary)  # 错词表也需要打乱
                # Ensure all mistake words have 'pronunciation' and 'example' fields for consistent display
                for word_obj in self.mistake_vocabulary:
                    word_obj.setdefault('pronunciation', '')
                    word_obj.setdefault('example', '')

                print(f"✅ 错词表加载成功，共 {len(self.mistake_vocabulary)} 词。")
            else:
                self.mistake_vocabulary = []
                print("💡 错词表文件不存在，初始化为空列表。")
        except json.JSONDecodeError:
            print(f"❌ 错词表文件 {self.mistake_word_file_path} 格式错误，重置为空列表。")
            self.mistake_vocabulary = []
            QMessageBox.warning(self.main_window, "错误",
                                f"错词表文件 {self.mistake_word_file_path} 格式错误，已重置。")
            self._update_mistake_count_label()  # Update label after reset
        except Exception as e:
            print(f"❌ 加载错词表失败: {e}")
            self.mistake_vocabulary = []  # Use self.main_window for QMessageBox
            QMessageBox.warning(
                self.main_window, "错误", f"加载错词表失败: {e}\n请检查 assets/mistake_words.json 文件。")

    def _load_self_registered_vocabulary(self):  # NEW: 加载自主录入词汇
        """
        从 main_window 的 self_register_vocab_ctrl 获取自主录入的单词数据。
        """
        if hasattr(self.main_window, 'self_register_vocab_ctrl') and self.main_window.self_register_vocab_ctrl:
            self.self_registered_vocabulary = self.main_window.self_register_vocab_ctrl.user_vocab_data
            random.shuffle(self.self_registered_vocabulary)
            # Ensure all self-registered words have 'pronunciation' and 'example' fields for consistent display
            for word_obj in self.self_registered_vocabulary:
                word_obj.setdefault('pronunciation', '')
                word_obj.setdefault('example', '')
            print(f"✅ 自主录入词汇表加载成功，共 {len(self.self_registered_vocabulary)} 词。")
        else:
            self.self_registered_vocabulary = []
            print("⚠️ 无法获取自主录入词汇表，SelfRegisterVocabManager 未初始化或无数据。")
        self._update_self_register_count_label()

    def _save_mistake_vocabulary(self):
        """
        [首席架构师审计]
        功能：将当前错词表持久化到动态路径。
        接入点：解决打包后 App 内部只读问题。
        """

        try:
         # 2. 严格执行写入动作 (确保缩进为 4 个空格的倍数)
            with open(self.mistake_word_file_path, "w", encoding="utf-8") as f:
                json.dump(self.mistake_vocabulary, f,
                          ensure_ascii=False, indent=4)

            # 3. 记录审计日志
            print(f"✅ 错词表已保存至审计路径: {self.mistake_word_file_path}")
            print(f"📊 当前错词总数: {len(self.mistake_vocabulary)}")

            # 4. 触发 UI 同步信号
            # 务必传递数据对象，维持国立大学硕士应有的严谨逻辑
            self.mistake_vocabulary_changed.emit(self.mistake_vocabulary)

        except Exception as e:
            # 5. 异常回执
            print(f"❌ 错词持久化失败: {str(e)}")
            # 使用 self.main_window 作为父窗口弹出警告
            QtWidgets.QMessageBox.critical(
                self.main_window, "系统错误", f"无法保存错词数据:\n{e}")

    def _display_mode_selection_prompt(self):
        """
        在用户选择闯关模式前，显示提示信息并禁用输入和确认按钮。
        """
        if self.v_disp:
            self.v_disp.setHtml(
                "<div style='text-align: center; padding: 40px; font-size: 20px; color: #555555;'>请选择闯关模式：<br><br>📚 常规闯关 或 ❌ 错词闯关 或 📝 自主录入闯关</div>")  # NEW: 更新提示
        if self.v_input:
            self.v_input.clear()
            self.v_input.setEnabled(False)
        if self.btn_confirm:
            self.btn_confirm.setEnabled(False)
        self.timer.stop()  # Ensure timer is stopped if it was ever started (prevents AttributeError)



    def _add_or_reset_mistake_word(self, word_obj):
        """
        将单词添加到错词表，如果已存在则重置正确计数。
        """
        # 🆕 修复：添加词之前先确保错词表已从文件加载
        if not self.mistake_vocabulary:  # 如果内存中为空，尝试从文件加载
            self._load_mistake_vocabulary()
        
        found = False
        for i, item in enumerate(self.mistake_vocabulary):
            if item["word"].lower() == word_obj["word"].lower():
                self.mistake_vocabulary[i]["correct_count"] = 0  # 重置计数
                found = True
                print(f"🔄 错词 '{word_obj['word']}' 已重置计数。")
                break
        if not found:
            new_mistake = {"word": word_obj["word"], "content": word_obj["content"], "correct_count": 0,
                           "pronunciation": word_obj.get("pronunciation", ""), "example": word_obj.get("example", "")}
            self.mistake_vocabulary.append(new_mistake)
            print(f"➕ 错词 '{word_obj['word']}' 已添加到错词表。")
        self._save_mistake_vocabulary()
        self._update_mistake_count_label()

    def _increment_mistake_word_correct_count(self, word_obj):
        """
        增加错词的正确计数，如果达到3次则移除。
        """
        # 🆕 修复：操作之前先确保错词表已从文件加载
        if not self.mistake_vocabulary:  # 如果内存中为空，尝试从文件加载
            self._load_mistake_vocabulary()
        
        for i, item in enumerate(self.mistake_vocabulary):
            if item["word"].lower() == word_obj["word"].lower():
                self.mistake_vocabulary[i]["correct_count"] += 1
                print(
                    f"⬆️ 错词 '{word_obj['word']}' 正确计数: {self.mistake_vocabulary[i]['correct_count']}")
                if self.mistake_vocabulary[i]["correct_count"] >= 3:
                    del self.mistake_vocabulary[i]  # 移除单词
                    print(f"🗑️ 错词 '{word_obj['word']}' 已从错词表移除 (正确3次)。")
                self._save_mistake_vocabulary()
                self._update_mistake_count_label()
                return True  # Indicate that the word was removed
        return False  # Indicate that the word was not removed (or not found)

    def switch_challenge_mode(self, mode):
        """
        切换单词闯关模式（常规、错词表或自主录入）。
        """
        if mode not in ["regular", "mistake_list", "self_register"]:  # NEW: 添加自主录入模式
            print(f"无效的闯关模式: {mode}")
            return

        # 启用输入框和确认按钮
        self.v_input.setEnabled(True)
        self.btn_confirm.setEnabled(True)

        self.current_challenge_mode = mode
        self.current_idx = 0  # 切换模式后重置索引
        self.load_active_vocabulary()  # 重新加载当前模式的词汇
        self.show_next()
        print(f"已切换到 {mode} 模式。")
        self._update_challenge_mode_buttons()  # Update button styles
        # Update mistake count label after switching mode
        self._update_mistake_count_label()
        # NEW: Update self-register count label
        self._update_self_register_count_label()

    def load_active_vocabulary(self):
        """
        根据当前模式加载相应的词汇表。
        """
        if self.current_challenge_mode == "regular":
            self._load_regular_vocabulary()
            self.active_vocabulary = self.vocabulary
        elif self.current_challenge_mode == "mistake_list":
            self._load_mistake_vocabulary()
            self.active_vocabulary = self.mistake_vocabulary
            if not self.active_vocabulary:  # 如果错词表为空，自动切换回常规模式
                QMessageBox.information(self.main_window, "提示", "错词表为空，已自动切换到常规闯关模式。")
                self.current_challenge_mode = "regular"  # Use self.main_window for QMessageBox
                self._load_regular_vocabulary()
                self.active_vocabulary = self.vocabulary
                # 再次更新按钮样式以反映自动切换
                self._update_challenge_mode_buttons()
        elif self.current_challenge_mode == "self_register":  # NEW: 自主录入模式
            self._load_self_registered_vocabulary()
            self.active_vocabulary = self.self_registered_vocabulary
            if not self.active_vocabulary:  # 如果自主录入词汇表为空，自动切换回常规模式
                QMessageBox.information(self.main_window, "提示", "自主录入词汇表为空，已自动切换到常规闯关模式。")
                self.current_challenge_mode = "regular"
                self._load_regular_vocabulary()
                self.active_vocabulary = self.vocabulary
                self._update_challenge_mode_buttons()

        self._update_mistake_count_label()  # 确保在加载完词汇后更新标签
        self._update_self_register_count_label()  # NEW: 确保在加载完词汇后更新标签
        print(
            f"DEBUG: Active vocabulary after loading: {len(self.active_vocabulary)} words.")
        if not self.active_vocabulary:  # 如果两种模式都加载失败，提供一个默认词汇
            self.active_vocabulary = [{"word": "hello", "content": "你好", "pronunciation": "/həˈloʊ/",
                                       "example": "Hello, how are you?"}]  # Fallback with more details

        random.shuffle(self.active_vocabulary)  # 确保当前活动的词汇表是打乱的
        print(f"当前活动词汇表已加载，共 {len(self.active_vocabulary)} 词。")

    def _update_challenge_mode_buttons(self):
        """
        更新闯关模式按钮的样式。
        """
        if self.btn_challenge_regular:
            self.btn_challenge_regular.setStyleSheet(
                self._get_button_style(self.current_challenge_mode == "regular"))
        if self.btn_challenge_mistake:
            self.btn_challenge_mistake.setStyleSheet(
                self._get_button_style(self.current_challenge_mode == "mistake_list"))
        if self.btn_challenge_self_register:  # NEW: 更新自主录入闯关按钮样式
            self.btn_challenge_self_register.setStyleSheet(
                self._get_button_style(self.current_challenge_mode == "self_register"))

    def _get_button_style(self, is_active):
        """
        根据按钮是否激活返回对应的样式。
        """
        if is_active:
            return """
				QPushButton {
					background-color: #2196F3;
					color: white;
					border: none;
					border-radius: 6px;
					font-size: 14px;
					font-weight: bold;
					padding: 8px 16px;
				}
			"""
        else:
            return """
				QPushButton {
					background-color: #e0e0e0;
					color: #333333;
					border: none;
					border-radius: 6px;
					font-size: 14px;
					padding: 8px 16px;
				}
				QPushButton:hover {
					background-color: #d0d0d0;
				}
			"""

    def _update_mistake_count_label(self):
        """
        更新错词表数量显示。
        """
        if self.lbl_mistake_count:
            self.lbl_mistake_count.setText(
                f"错词表 ({len(self.mistake_vocabulary)} 词)")

    def _update_self_register_count_label(self):  # NEW: 更新自主录入单词数显示
        """
        更新自主录入单词数显示。
        """
        if self.lbl_self_register_count:
            self.lbl_self_register_count.setText(
                f"自主录入 ({len(self.self_registered_vocabulary)} 词)")

    def show_next(self, error_msg="", additional_message_html=""):
        """
        显示下一个词汇的中文释义，并根据需要显示错误提示。
        """
        if not self.v_disp or not self.v_input:
            return

        if not self.active_vocabulary:
            self.v_disp.setHtml(
                "<div style='text-align: center; padding: 20px; font-size: 20px; color: #e74c3c;'>词汇表为空，请检查！</div>")
            self.v_input.clear()
            self.v_input.setEnabled(False)
            self.btn_confirm.setEnabled(False)
            self.timer.stop()  # Ensure timer is stopped
            print("DEBUG: Active vocabulary is empty, displaying error message.")
            return
        else:
            self.v_input.setEnabled(True)
            self.btn_confirm.setEnabled(True)

        # Check current_idx bounds
        if not (0 <= self.current_idx < len(self.active_vocabulary)):
            print(
                f"ERROR: current_idx ({self.current_idx}) out of bounds for active_vocabulary (len {len(self.active_vocabulary)}). Resetting to 0.")
            self.current_idx = 0  # Reset index to prevent crash
            if not self.active_vocabulary:  # If still empty after reset, display error
                self.v_disp.setHtml(
                    "<div style='text-align: center; padding: 20px; font-size: 20px; color: #e74c3c;'>词汇表为空，请检查！</div>")
                self.v_input.clear()
                self.v_input.setEnabled(False)
                self.btn_confirm.setEnabled(False)
                self.timer.stop()
                return

        curr = self.active_vocabulary[self.current_idx]
        print(
            f"DEBUG: Displaying word: {curr.get('word', 'N/A')}, content: {curr.get('content', 'N/A')}")

        # Apply normalization to the content before displaying
        normalized_content = _normalize_full_width_to_half_width(
            curr['content'])

        html_content_parts = []

        # Always display the word content
        html_content_parts.append(f"""
			<div style='text-align: center; padding: 20px;'>
				<div style='font-size: 14px; color: #999999; font-weight: 600; margin-bottom: 16px;'>
					第 {self.current_idx + 1} 关
				</div>
				<div style='font-size: 32px; color: #333333; font-weight: 500; line-height: 1.4;'> 
					{normalized_content}
				</div>
		""")

        # Add pronunciation and example if available in the word object
        if curr.get('pronunciation'):
            html_content_parts.append(
                f"<div style='font-size: 18px; color: #666666; margin-top: 8px;'>{curr.get('pronunciation', '')}</div>")
        if curr.get('example'):
            html_content_parts.append(
                f"<div style='font-size: 14px; color: #888888; margin-top: 12px; font-style: italic;'>例句: {curr.get('example', '')}</div>")

        # Display additional message HTML if present (e.g., word removed from mistake list)
        if additional_message_html:
            html_content_parts.append(additional_message_html)

        if error_msg:
            html_content_parts.append(f"""
				<div style='margin-top: 16px;'>
					<span style='font-size: 16px; color: #d32f2f; font-weight: bold;'>
						✅ 正确答案: {error_msg.capitalize()}
					</span>
				</div>
			""")

        html_content_parts.append("</div></body></html>")
        html = "".join(html_content_parts)

        self.v_disp.setHtml(html)

        # Only clear input and start timer if it's a new word (not an error display)
        if not error_msg:
            self.v_input.clear()
            self.v_input.setFocus()
            self.time_left = 15
            if self.t_label:
                self.t_label.setText(str(self.time_left))

            if self.main_window.stack.currentIndex() == self.main_window.stack.indexOf(self.vocab_page_widget):
                self.timer.start(1000)

    def tick(self):
        """
        计时器滴答事件处理函数，更新倒计时显示，并在时间到时自动显示答案。
        """
        self.time_left -= 1
        if self.t_label:
            self.t_label.setText(str(self.time_left))
        if self.time_left <= 0:
            self.timer.stop()
            # Ensure current_idx is valid before accessing active_vocabulary
            if self.active_vocabulary and 0 <= self.current_idx < len(self.active_vocabulary):
                target = self.active_vocabulary[self.current_idx]['word'].strip(
                )
                # When time runs out, it's considered an incorrect answer for display purposes
                additional_message_html = ""
                if self.current_challenge_mode == "regular":
                    additional_message_html = "<div style='font-size: 14px; color: #e74c3c; margin-top: 5px;'>已登录到错词表</div>"

                self.show_next(
                    error_msg=target, additional_message_html=additional_message_html)  # 错误时显示正确答案

                # Also add to mistake list if in regular mode
                if self.current_challenge_mode == "regular":
                    current_word_obj = self.active_vocabulary[self.current_idx]
                    self._add_or_reset_mistake_word(current_word_obj)

                QtCore.QTimer.singleShot(2000, self.go_next)  # 2秒后自动跳转
            else:  # Fallback if active_vocabulary is empty or index is invalid
                print(
                    "ERROR: Timer ticked but active_vocabulary is empty or current_idx is out of bounds.")
                self.show_next()  # Attempt to show next, which will show "词汇表为空" if still empty

    def check_answer(self):
        """
        检查用户输入的答案是否正确，并根据结果更新UI样式。
        """
        self.timer.stop()
        user_in = self.v_input.text().strip().lower()

        if not self.active_vocabulary or not (0 <= self.current_idx < len(self.active_vocabulary)):
            print(
                "ERROR: No active vocabulary or invalid current_idx when checking answer.")
            return  # Do nothing if no active vocabulary or invalid index

        current_word_obj = self.active_vocabulary[self.current_idx]
        target = current_word_obj['word'].strip().lower()

        # Clear any previous notification
        self._notification_message_for_next_display = ""

        if user_in == target:
            self.v_input.setStyleSheet("""
				QLineEdit {
					font-size: 18px;
					border: 1px solid #4CAF50;
					background-color: #f1f8f4;
					border-radius: 6px;
					padding: 0px 16px;
					color: #333333;
					outline: none;
					font-family: "Arial", "Microsoft YaHei"; /* Consistent font */
				}
			""")

            removed_from_mistake_list = False
            # 如果是错词表模式，且回答正确，增加正确计数
            if self.current_challenge_mode == "mistake_list":
                removed_from_mistake_list = self._increment_mistake_word_correct_count(
                    current_word_obj)

            if removed_from_mistake_list:
                self._notification_message_for_next_display = f"<div style='font-size: 14px; color: #27ae60; margin-top: 5px;'>你三次答对了。从错词表里删除的字样</div>"

            QtCore.QTimer.singleShot(600, self.go_next)

        else:  # Incorrect answer
            self.v_input.setStyleSheet("""
				QLineEdit {
					font-size: 18px;
					border: 1px solid #f44336;
					background-color: #fef1f1;
					border-radius: 6px;
					padding: 0px 16px;
					color: #333333;
					outline: none;
					font-family: "Arial", "Microsoft YaHei"; /* Consistent font */
				}
			""")

            additional_message_html = ""
            # 如果是常规闯关模式，且回答错误，显示已登录到错词表
            if self.current_challenge_mode == "regular":
                additional_message_html = "<div style='font-size: 14px; color: #e74c3c; margin-top: 5px;'>已登录到错词表</div>"

            self.show_next(error_msg=target,
                           additional_message_html=additional_message_html)

            # 如果回答错误，添加到错词表或重置计数
            # NEW: 只有在常规闯关或错词闯关模式下才更新错词表
            if self.current_challenge_mode in ["regular", "mistake_list"]:
                self._add_or_reset_mistake_word(current_word_obj)
                print(
                    f"DEBUG: Word '{current_word_obj['word']}' added/reset in mistake list.")
            QtCore.QTimer.singleShot(2000, self.go_next)  # 2秒后自动跳转

    def go_next(self):
        """
        切换到下一个词汇。
        """
        if not self.active_vocabulary:
            self.show_next()  # 显示空词汇表提示
            return

        self.current_idx = (self.current_idx + 1) % len(self.active_vocabulary)

        # 传递之前存储的通知消息给下一个 show_next 调用
        message_for_next_display = self._notification_message_for_next_display
        self._notification_message_for_next_display = ""  # 清空，防止重复显示
        self.show_next(additional_message_html=message_for_next_display)
