# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/main.py
import sys
import os
import re
import time
import PySide6
import random
import traceback

# ============ [0. 解决高分屏/缩放导致的 UI 乱版] ============
# 必须在创建 QApplication 之前设置环境，防止 4K 屏显示错位
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

# ============ [3. 注入模块搜索路径] ============
# 关键：由于 word_list_view 等在 lib 下，必须注入 lib 路径
lib_path = os.path.join(BASE_DIR, "lib")
parsers_dir = os.path.join(BASE_DIR, "parsers")

for p in [BASE_DIR, lib_path, parsers_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ============ [4. 模块导入] ============
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget, QLineEdit, QFrame, QButtonGroup)
from PySide6.QtUiTools import QUiLoader

try:
    # 此时 sys.path 已经配置好，可以从 lib 正常导入 WordListView
    from vocab_module import VocabManager
    from word_list_view import WordListView
    from run_flull_exam import HSEExamSystem
    from parsers.full_exam_specific_parsers import (
        _parse_grammar_items_full_exam,
        _parse_seven_five_items_full_exam,
        _parse_cloze_items_full_exam,
        _parse_reading_items_full_exam_robust
    )
    from exam_module import ExamManager
    from utils import normalize_exam_text
    from self_register_vocab_module import SelfRegisterVocabManager
    from analyzer_module import AnalyzerManager
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    raise

# ============ [5. 内部工具函数] ============
def _internal_full_exam_parser(text):
    """整卷真题解析逻辑"""
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

        # 🎯 属性预定义，防止初始化中途报错导致界面按钮点击崩溃
        self.base_path = BASE_DIR
        self.word_list_index = -1
        self.self_register_vocab_index = -1
        self.ai_analyzer_index = -1
        self.gk_idx = -1

        self.vocab_ctrl = None
        self.exam_ctrl = None
        self.word_list_widget = None

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

        # 先加载高考页面 UI (ExamManager 依赖它)
        self._setup_gaokao_page(res_dir, loader)

        try:
            # 1. 启动单词闯关模块
            self.vocab_ctrl = VocabManager(self)

            # 2. 启动核心词汇表模块 (在 lib/word_list_view.py)
            self.word_list_widget = WordListView(self)
            self.stack.addWidget(self.word_list_widget)
            self.word_list_index = self.stack.indexOf(self.word_list_widget)

            # 安全连接错词更新信号
            if self.vocab_ctrl and hasattr(self.word_list_widget, 'refresh_mistake_list'):
                self.vocab_ctrl.mistake_vocabulary_changed.connect(self.word_list_widget.refresh_mistake_list)

            # 3. 启动专项练习控制器
            if self.page_gaokao_widget:
                self.exam_ctrl = ExamManager(self, self.page_gaokao_widget)

            # 4. 启动自主登记模块
            self.self_register_vocab_ctrl = SelfRegisterVocabManager(self)
            self.stack.addWidget(self.self_register_vocab_ctrl)
            self.self_register_vocab_index = self.stack.indexOf(self.self_register_vocab_ctrl)

            # 5. 启动 AI 解析模块
            self.ai_analyzer_widget = AnalyzerManager(self)
            self.stack.addWidget(self.ai_analyzer_widget)
            self.ai_analyzer_index = self.stack.indexOf(self.ai_analyzer_widget)

        except Exception as e:
            print("⚠️ 初始化业务模块异常:")
            traceback.print_exc()

        self._bind_nav_events()
        self._apply_sidebar_style()
        self.stack.setCurrentIndex(0)

    def _setup_gaokao_page(self, res_dir, loader):
        gk_ui_path = os.path.join(res_dir, "page_gaokao.ui")
        self.page_gaokao_widget = loader.load(gk_ui_path)
        if self.page_gaokao_widget:
            self.stack.addWidget(self.page_gaokao_widget)
            self.gk_idx = self.stack.indexOf(self.page_gaokao_widget)

    def _bind_nav_events(self):
        root = self.ui_root
        root.findChild(QPushButton, "btn_nav_vocab").clicked.connect(lambda: self.stack.setCurrentIndex(0))
        root.findChild(QPushButton, "btn_nav_core_vocab").clicked.connect(self._safe_nav_to_word_list)
        root.findChild(QPushButton, "btn_nav_gaokao").clicked.connect(self.show_gaokao_page)
        root.findChild(QPushButton, "btn_nav_full_exam").clicked.connect(self.switch_to_full_exam)
        root.findChild(QPushButton, "btn_nav_self_register").clicked.connect(self._safe_nav_to_self_register)
        root.findChild(QPushButton, "btn_nav_scan").clicked.connect(self._safe_nav_to_analyzer)

    def _safe_nav_to_word_list(self):
        if self.word_list_index != -1: self.stack.setCurrentIndex(self.word_list_index)

    def _safe_nav_to_self_register(self):
        if self.self_register_vocab_index != -1: self.stack.setCurrentIndex(self.self_register_vocab_index)

    def _safe_nav_to_analyzer(self):
        if self.ai_analyzer_index != -1: self.stack.setCurrentIndex(self.ai_analyzer_index)

    def show_gaokao_page(self):
        if self.gk_idx != -1:
            self.stack.setCurrentIndex(self.gk_idx)
            if self.exam_ctrl: self.exam_ctrl.update_nav_highlight()

    def switch_to_full_exam(self):
        # 路径适配：确保能找到 data/真题试卷
        path = resource_path("data/真题试卷")
        if not os.path.exists(path):
            QMessageBox.warning(self, "提示", "找不到试卷数据目录")
            return
        files = [f for f in os.listdir(path) if f.endswith(".txt")]
        if not files: return

        try:
            target_file = os.path.join(path, random.choice(files))
            with open(target_file, 'r', encoding='utf-8') as f:
                data = _internal_full_exam_parser(f.read())
            self.full_view = HSEExamSystem(data)
            self.stack.setCurrentIndex(self.stack.addWidget(self.full_view))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载试卷失败: {e}")

    def _apply_sidebar_style(self):
        qss = "QPushButton { min-height: 55px; border-radius: 12px; text-align: left; padding-left: 20px; font-weight: bold; }"
        nav_btns = ["btn_nav_vocab", "btn_nav_core_vocab", "btn_nav_gaokao", "btn_nav_full_exam", "btn_nav_self_register", "btn_nav_scan"]
        for name in nav_btns:
            btn = self.ui_root.findChild(QPushButton, name)
            if btn: btn.setStyleSheet(qss)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 🎯 启用 Fusion 样式，确保不同电脑显示效果一致，不乱版
    app.setStyle("Fusion")
    window = HighSchoolEnglishAI()
    window.show()
    sys.exit(app.exec())