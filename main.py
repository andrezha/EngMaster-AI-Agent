# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/main.py
import sys
import os
import re
import time
import PySide6
import random
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget, QLineEdit, QFrame, QButtonGroup)
from PySide6.QtUiTools import QUiLoader

# 统一注入 lib 路径
base_path = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(base_path, "lib")
for p in [lib_path, base_path]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from vocab_module import VocabManager
    from word_list_view import WordListView
    from run_flull_exam import HSEExamSystem
    from parsers.full_exam_specific_parsers import _parse_grammar_items_full_exam, _parse_seven_five_items_full_exam, _parse_cloze_items_full_exam, _parse_reading_items_full_exam_robust
    from exam_module import ExamManager
    from utils import normalize_exam_text # 使用新函数
    from self_register_vocab_module import SelfRegisterVocabManager
    from analyzer_module import AnalyzerManager
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    raise

def _internal_full_exam_parser(text):
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

class HighSchoolEnglishAI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HSE-AI 英语智胜工作站")
        self.showMaximized()
        self.base_path = base_path
        res_dir = os.path.join(self.base_path, "resources")
        loader = QUiLoader()

        self.ui_root = loader.load(os.path.join(res_dir, "main_window.ui"))
        self.setCentralWidget(self.ui_root)
        self.stack = self.ui_root.findChild(QStackedWidget, "stackedWidget")

        # 先加载子页面 UI
        self._setup_gaokao_page(res_dir, loader)

        try:
            self.vocab_ctrl = VocabManager(self)
            self.word_list_widget = WordListView(self)
            self.stack.addWidget(self.word_list_widget)
            self.word_list_index = self.stack.indexOf(self.word_list_widget)

            # 【修复启动核心】：传入两个参数
            self.exam_ctrl = ExamManager(self, self.page_gaokao_widget)

            # 自主登记模块
            self.self_register_vocab_ctrl = SelfRegisterVocabManager(self)
            self.stack.addWidget(self.self_register_vocab_ctrl)
            self.self_register_vocab_index = self.stack.indexOf(self.self_register_vocab_ctrl)

            self.ai_analyzer_widget = AnalyzerManager(self)
            self.stack.addWidget(self.ai_analyzer_widget)
            self.ai_analyzer_index = self.stack.indexOf(self.ai_analyzer_widget)
        except Exception as e:
            print(f"⚠️ 初始化异常: {e}")

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
        self.ui_root.findChild(QPushButton, "btn_nav_vocab").clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.ui_root.findChild(QPushButton, "btn_nav_core_vocab").clicked.connect(lambda: self.stack.setCurrentIndex(self.word_list_index))
        self.ui_root.findChild(QPushButton, "btn_nav_gaokao").clicked.connect(self.show_gaokao_page)
        self.ui_root.findChild(QPushButton, "btn_nav_full_exam").clicked.connect(self.switch_to_full_exam)
        self.ui_root.findChild(QPushButton, "btn_nav_self_register").clicked.connect(lambda: self.stack.setCurrentIndex(self.self_register_vocab_index))
        self.ui_root.findChild(QPushButton, "btn_nav_scan").clicked.connect(lambda: self.stack.setCurrentIndex(self.ai_analyzer_index))

    def show_gaokao_page(self):
        self.stack.setCurrentIndex(self.gk_idx)
        if self.exam_ctrl: self.exam_ctrl.update_nav_highlight()

    def switch_to_full_exam(self):
        path = os.path.join(self.base_path, "data", "真题试卷")
        files = [f for f in os.listdir(path) if f.endswith(".txt")]
        if not files: return
        with open(os.path.join(path, random.choice(files)), 'r', encoding='utf-8') as f:
            data = _internal_full_exam_parser(f.read())
        self.full_view = HSEExamSystem(data)
        self.stack.setCurrentIndex(self.stack.addWidget(self.full_view))

    def _apply_sidebar_style(self):
        qss = "QPushButton { min-height: 55px; border-radius: 12px; text-align: left; padding-left: 20px; font-weight: bold; }"
        for btn in [self.ui_root.findChild(QPushButton, n) for n in ["btn_nav_vocab", "btn_nav_core_vocab", "btn_nav_gaokao", "btn_nav_full_exam", "btn_nav_self_register", "btn_nav_scan"]]:
            if btn: btn.setStyleSheet(qss)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HighSchoolEnglishAI()
    window.show()
    sys.exit(app.exec())