# -*- coding: utf-8 -*-
import sys
import os
import re
import random
import traceback
import PySide6

# 导入单实例运行所需的锁类
from PySide6.QtCore import QLockFile, QDir

# ============ [0. 解决高分屏/缩放导致的 UI 乱版] ============
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

# ============ [1. 核心：定义唯一的绝对根目录] ============
if hasattr(sys, '_MEIPASS'):
    # 打包环境：指向 PyInstaller 临时解压目录
    BASE_DIR = sys._MEIPASS
else:
    # 本地环境：指向 main.py 所在的绝对文件夹路径
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    """ 将相对路径转换为绝对路径，确保本地和打包环境一致 """
    return os.path.join(BASE_DIR, relative_path)

# ============ [2. 修复 PySide6 插件路径] ============
pyside6_dir = os.path.dirname(PySide6.__file__)
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(pyside6_dir, 'plugins', 'platforms')

# ============ [3. 模块搜索路径] ============
# 🟢 物理挪动后：现在 word_list_view 在根目录，我们只需要注入 BASE_DIR 即可
for p in [BASE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ============ [4. 模块导入] ============
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget, QLineEdit, QFrame, QButtonGroup)
from PySide6.QtUiTools import QUiLoader

try:
    # 🟢 物理挪动后，这里直接从当前目录导入，最稳健
    from vocab_module import VocabManager
    from word_list_view import WordListView
    from exam_module import ExamManager
    from utils import normalize_exam_text
    from self_register_vocab_module import SelfRegisterVocabManager
    from phrase_irregular_module import PhraseIrregularChallengeView, PhraseIrregularListView
    # from analyzer_module import AnalyzerManager  # AI 模块目前不启用
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    raise

# ============ [5. 内部工具函数] ============
def _internal_full_exam_parser(text):
    from parsers.full_exam_specific_parsers import (
        _parse_grammar_items_full_exam,
        _parse_seven_five_items_full_exam,
        _parse_cloze_items_full_exam,
        _parse_reading_items_full_exam_robust
    )

    text = normalize_exam_text(text)
    sections = re.split(r'\[\[SECTION:\s*(.*?)\]\]', text)
    data_list = []
    analysis_tag_start = text.lower().find('[analysis]')
    global_analysis_text = ""
    if analysis_tag_start != -1:
        global_analysis_text = text[analysis_tag_start + len('[analysis]'):].strip()

    NAME_MAP = {"READING_PASSAGE_A": "阅读理解 A", "7_OUT_OF_5": "七选五", "CLOZE": "完形填空", "GRAMMAR": "语法填空"}
    TYPE_MAP = {"READING_PASSAGE_A": "reading", "7_OUT_OF_5": "seven_five", "CLOZE": "cloze", "GRAMMAR": "grammar"}

    for i in range(1, len(sections), 2):
        sec_name = sections[i].strip()
        sec_body = sections[i+1].strip()
        q_tag = sec_body.lower().find('[questions]')
        if q_tag == -1: continue
        passage = sec_body[:q_tag].strip()
        q_text = normalize_exam_text(sec_body[q_tag + len('[questions]'):].strip())
        q_type = TYPE_MAP.get(sec_name, "reading")

        parsed_items = []
        if q_type == "grammar": parsed_items = _parse_grammar_items_full_exam(q_text, global_analysis_text)
        elif q_type == "seven_five": parsed_items = _parse_seven_five_items_full_exam(q_text, global_analysis_text, passage)
        elif q_type == "cloze": parsed_items = _parse_cloze_items_full_exam(q_text, global_analysis_text)
        elif q_type == "reading": parsed_items = _parse_reading_items_full_exam_robust(q_text, global_analysis_text)

        items = []
        for item_dict in (parsed_items if isinstance(parsed_items, list) else []):
            item_dict['q_id'] = re.sub(r'\D', '', str(item_dict.get('q_id', '')))
            items.append(item_dict)
        data_list.append({"category": NAME_MAP.get(sec_name, sec_name), "question_type": q_type, "passage": passage, "items": items, "original_analysis": global_analysis_text})
    return data_list

# ============ [6. 主窗口类] ============
class HighSchoolEnglishAI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HSE-AI 英语智胜工作站")
        self.showMaximized()

        # Navigation button management
        self.nav_buttons = {} # Stores QPushButton objects
        # Maps button object name to the instance variable holding its target QStackedWidget index
        self.nav_button_target_map = {
            "btn_nav_vocab": 0, # Fixed index for vocab page
            "btn_nav_core_vocab": "word_list_index",
            "btn_nav_phrase_challenge": "phrase_irregular_challenge_index",
            "btn_nav_phrase_list": "phrase_irregular_list_index",
            "btn_nav_gaokao": "gk_idx",
            "btn_nav_full_exam": None, # Full exam is dynamically added, index changes
            "btn_nav_self_register": "self_register_vocab_index",
            # "btn_nav_scan": "ai_analyzer_index" # AI module not enabled
        }

        # 🎯 属性预定义，这是子模块生存的“灯塔”
        self.base_path = BASE_DIR
        self.word_list_index = -1
        self.self_register_vocab_index = -1
        self.ai_analyzer_index = -1
        self.phrase_irregular_challenge_index = -1
        self.phrase_irregular_list_index = -1
        self.gk_idx = -1

        self.vocab_ctrl = None
        self.exam_ctrl = None
        self.word_list_widget = None
        self.self_register_vocab_ctrl = None # 初始化自主录入词汇控制器

        # 资源加载
        res_dir = resource_path("resources")
        loader = QUiLoader()
        main_ui_path = os.path.join(res_dir, "main_window.ui")

        self.ui_root = loader.load(main_ui_path)
        if not self.ui_root:
            QMessageBox.critical(None, "错误", f"无法加载核心 UI 文件:\n{main_ui_path}")
            sys.exit(1)

        self.setCentralWidget(self.ui_root)
        self.stack = self.ui_root.findChild(QStackedWidget, "stackedWidget")

        # Connect the currentChanged signal for button highlighting
        self.stack.currentChanged.connect(self._update_nav_button_styles)

        # 先加载高考页面 UI
        self._setup_gaokao_page(res_dir, loader)

        try:
            # 1. 词汇管理延迟初始化，避免阻塞首屏显示
            self.vocab_ctrl = None
            QtCore.QTimer.singleShot(0, self._init_vocab_module)

            # 核心词汇表、专项练习、自主登记、AI 解析都延迟创建，减少启动时开销
            # 只有默认页面和高考页面 UI 会在启动时加载
            self.word_list_widget = None

            self._ensure_self_register_widget() # 确保自主录入模块及其数据在启动时加载
            # 3. 专项练习只在用户打开高考页面时初始化
            self.exam_ctrl = None

            # 4. 默认先不创建额外模块，点击时再加载

        except Exception as e:
            print("⚠️ 初始化业务模块异常:")
            traceback.print_exc()

        self._bind_nav_events() # Bind events and populate self.nav_buttons
        self._apply_sidebar_style() # Apply initial styles to all buttons
        self.stack.setCurrentIndex(0)
        self._update_nav_button_styles(self.stack.currentIndex()) # Set initial highlight

    def _setup_gaokao_page(self, res_dir, loader):
        gk_ui_path = os.path.join(res_dir, "page_gaokao.ui")
        self.page_gaokao_widget = loader.load(gk_ui_path)
        if self.page_gaokao_widget:
            self.stack.addWidget(self.page_gaokao_widget)
            self.gk_idx = self.stack.indexOf(self.page_gaokao_widget)

    def _bind_nav_events(self):
        root = self.ui_root
        # Map button names to their corresponding navigation methods
        nav_map = {
            "btn_nav_vocab": lambda: self.stack.setCurrentIndex(0),
            "btn_nav_core_vocab": self._safe_nav_to_word_list,
            "btn_nav_phrase_challenge": self.show_phrase_irregular_challenge,
            "btn_nav_phrase_list": self.show_phrase_irregular_list,
            "btn_nav_gaokao": self.show_gaokao_page,
            "btn_nav_full_exam": self.switch_to_full_exam,
            "btn_nav_self_register": self._safe_nav_to_self_register,
            # "btn_nav_scan": self._safe_nav_to_analyzer # AI module not enabled
        }

        for btn_name, handler in nav_map.items():
            btn = root.findChild(QPushButton, btn_name)
            if btn:
                btn.clicked.connect(handler)
                self.nav_buttons[btn_name] = btn # Store button reference

    def _ensure_word_list_widget(self):
        if self.word_list_widget is None:
            self.word_list_widget = WordListView(self)
            self.stack.addWidget(self.word_list_widget)
            self.word_list_index = self.stack.indexOf(self.word_list_widget)
            if hasattr(self.word_list_widget, 'refresh_mistake_list'):
            # Update the target map for this dynamically added page
                self.nav_button_target_map["btn_nav_core_vocab"] = "word_list_index"
                self.vocab_ctrl.mistake_vocabulary_changed.connect(self.word_list_widget.refresh_mistake_list)

    def _ensure_self_register_widget(self):
        if self.self_register_vocab_ctrl is None:
            self.self_register_vocab_ctrl = SelfRegisterVocabManager(self)
            self.stack.addWidget(self.self_register_vocab_ctrl)
            self.self_register_vocab_index = self.stack.indexOf(self.self_register_vocab_ctrl)
            # Update the target map for this dynamically added page
            self.nav_button_target_map["btn_nav_self_register"] = "self_register_vocab_index"

    # def _ensure_analyzer_widget(self):
    #     if self.ai_analyzer_widget is None:
    #         self.ai_analyzer_widget = AnalyzerManager(self)
    #         self.stack.addWidget(self.ai_analyzer_widget)
    #         self.ai_analyzer_index = self.stack.indexOf(self.ai_analyzer_widget)

    def _safe_nav_to_word_list(self):
        self._ensure_word_list_widget()
        if self.word_list_index != -1:
            self.stack.setCurrentIndex(self.word_list_index)

    def _safe_nav_to_self_register(self):
        self._ensure_self_register_widget()
        if self.self_register_vocab_index != -1:
            self.stack.setCurrentIndex(self.self_register_vocab_index)

    def _ensure_phrase_irregular_challenge_widget(self):
        if self.phrase_irregular_challenge_index == -1:
            widget = PhraseIrregularChallengeView(self)
            self.stack.addWidget(widget)
            self.phrase_irregular_challenge_index = self.stack.indexOf(widget)
            # Update the target map for this dynamically added page
            self.nav_button_target_map["btn_nav_phrase_challenge"] = "phrase_irregular_challenge_index"

    def _ensure_phrase_irregular_list_widget(self):
        if self.phrase_irregular_list_index == -1:
            widget = PhraseIrregularListView(self)
            self.stack.addWidget(widget)
            self.phrase_irregular_list_index = self.stack.indexOf(widget)
            # Update the target map for this dynamically added page
            self.nav_button_target_map["btn_nav_phrase_list"] = "phrase_irregular_list_index"

    def show_phrase_irregular_challenge(self):
        self._ensure_phrase_irregular_challenge_widget()
        if self.phrase_irregular_challenge_index != -1:
            self.stack.setCurrentIndex(self.phrase_irregular_challenge_index)

    def show_phrase_irregular_list(self):
        self._ensure_phrase_irregular_list_widget()
        if self.phrase_irregular_list_index != -1:
            self.stack.setCurrentIndex(self.phrase_irregular_list_index)

    # def _safe_nav_to_analyzer(self):
    #     self._ensure_analyzer_widget()
    #     if self.ai_analyzer_index != -1:
    #         self.stack.setCurrentIndex(self.ai_analyzer_index)

    def show_gaokao_page(self):
        if self.gk_idx != -1:
            if self.exam_ctrl is None:
                self.exam_ctrl = ExamManager(self, self.page_gaokao_widget)
            self.stack.setCurrentIndex(self.gk_idx) # The _update_nav_button_styles will handle main nav highlight

    def switch_to_full_exam(self):
        path = resource_path("data/真题试卷")
        if not os.path.exists(path):
            QMessageBox.warning(self, "提示", "找不到试卷数据目录")
            return
        files = [f for f in os.listdir(path) if f.endswith(".txt")]
        if not files: return

        try:
            from run_flull_exam import HSEExamSystem

            target_file = os.path.join(path, random.choice(files))
            with open(target_file, 'r', encoding='utf-8') as f:
                data = _internal_full_exam_parser(f.read())
            self.full_view = HSEExamSystem(data)
            self.stack.setCurrentIndex(self.stack.addWidget(self.full_view))
        except Exception as e:
            # Add the full_view to the stack and get its index
            full_exam_index = self.stack.addWidget(self.full_view)
            self.stack.setCurrentIndex(full_exam_index)
            # Update the target map for full exam, as its index is dynamic
            self.nav_button_target_map["btn_nav_full_exam"] = full_exam_index
            self._update_nav_button_styles(full_exam_index) # Manually update styles as currentChanged might not fire if index is same
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载试卷失败: {e}")

    def _apply_sidebar_style(self):
        # Base styles for navigation buttons
        self.inactive_nav_style = """
            QPushButton {
                min-height: 55px;
                border-radius: 12px;
                text-align: left;
                padding-left: 20px;
                font-weight: bold;
                background-color: transparent; /* Default inactive background */
                color: #495057; /* Default inactive text color */
                border: none;
            }
            QPushButton:hover {
                background-color: #e9ecef; /* Light hover effect */
            }
        """
        self.active_nav_style = """
            QPushButton {
                min-height: 55px;
                border-radius: 12px;
                text-align: left;
                padding-left: 20px;
                font-weight: bold;
                background-color: #007bff; /* Active background color (Bootstrap primary blue) */
                color: white; /* Active text color */
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3; /* Darker hover effect for active button */
            }
        """

        nav_btns = ["btn_nav_vocab", "btn_nav_core_vocab", "btn_nav_phrase_challenge", "btn_nav_phrase_list", "btn_nav_gaokao", "btn_nav_full_exam", "btn_nav_self_register"]  # btn_nav_scan 暂不启用
        for name in nav_btns:
            btn = self.ui_root.findChild(QPushButton, name)
            if btn:
                self.nav_buttons[name] = btn # Store button object
                btn.setStyleSheet(self.inactive_nav_style) # Apply initial inactive style

    def _update_nav_button_styles(self, current_stack_index):
        """
        Updates the style of navigation buttons based on the currently active QStackedWidget index.
        """
        for btn_name, btn_obj in self.nav_buttons.items():
            target_index_identifier = self.nav_button_target_map.get(btn_name)

            target_index = -1
            if isinstance(target_index_identifier, int): # Fixed index (e.g., 0 for vocab)
                target_index = target_index_identifier
            elif isinstance(target_index_identifier, str): # Dynamic index stored in an instance variable
                target_index = getattr(self, target_index_identifier, -1)
            # For "btn_nav_full_exam", target_index_identifier might be None initially,
            # or an int after it's added. If it's None, it means the page hasn't been added yet.

            if target_index != -1 and current_stack_index == target_index:
                btn_obj.setStyleSheet(self.active_nav_style)
            else:
                btn_obj.setStyleSheet(self.inactive_nav_style)

    def _init_vocab_module(self):
        try:
            if self.vocab_ctrl is None:
                self.vocab_ctrl = VocabManager(self)
        except Exception as e:
            print("⚠️ 词汇模块延迟初始化失败:")
            traceback.print_exc()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 🎯 核心修改：单实例运行锁
    # 在临时目录创建一个锁文件
    lock_path = os.path.join(QDir.tempPath(), "HSE_AI_Workstation_Unique.lock")
    lock_file = QLockFile(lock_path)

    # 尝试锁定，如果失败说明已有程序在运行
    if not lock_file.tryLock(100):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("运行提示")
        msg_box.setText("程序已经在运行中！")
        msg_box.setInformativeText("请在任务栏查找已打开的窗口，请勿重复启动。")
        msg_box.setIcon(QMessageBox.Information)
        # 统一样式防止乱版
        msg_box.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
        msg_box.exec()
        sys.exit(0)

    # 锁定成功，启动窗口
    window = HighSchoolEnglishAI()
    window.show()

    # 结束后系统会自动释放锁文件
    sys.exit(app.exec())