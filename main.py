import sys
import os
import re # Import the 're' module for regular expressions
import time
import PySide6
import random # Import random for shuffling files

# ============ [1. 环境初始化：必须最先执行] ============
pyside6_dir = os.path.dirname(PySide6.__file__)
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(pyside6_dir, 'plugins', 'platforms')

# ============ [2. 路径适配：支持开发环境与 PyInstaller 打包环境] ============
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# 统一资源目录定义
res_dir = os.path.join(base_path, "resources")
lib_path = os.path.join(base_path, "lib")
data_dir = os.path.join(base_path, "data")
assets_dir = os.path.join(base_path, "assets") # 新增这一行

# 统一注入 lib 路径，确保业务模块加载
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
if base_path not in sys.path:
    sys.path.insert(0, base_path)

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QPushButton, 
                             QStackedWidget, QVBoxLayout, QWidget, QLineEdit)
from PySide6.QtUiTools import QUiLoader

try:
    from vocab_module import VocabManager
    from word_list_view import WordListView 
    from run_flull_exam import HSEExamSystem
    # Import specific parsers for full exam, including the robust reading comprehension parser
    from parsers.full_exam_specific_parsers import _parse_grammar_items_full_exam, _parse_seven_five_items_full_exam, _parse_cloze_items_full_exam, _parse_reading_items_full_exam_robust
    from exam_module import ExamManager 
    from utils import _normalize_full_width_to_half_width # Import from utils
except ImportError as e:
    # This block catches errors during the initial module imports
    # If WordListView is not defined, it means its module failed to load.
    print(f"❌ 模块导入失败: {e}. 请检查相关模块文件是否存在或有语法错误。")
    raise # Re-raise the exception to stop execution if a critical module cannot be loaded

# ==========================================
# 1. 独立解析器 (保留你最核心的解析逻辑)
# ==========================================

def _internal_full_exam_parser(text):
    """
    解析整个高考模拟卷 TXT 文件，将其分割成多个板块，并为每个板块提取题目和解析。
    """
    print("\n" + "="*50)
    print("🚀 [DEBUG] 解析器已启动...")
    
    sections = re.split(r'\[\[SECTION:\s*(.*?)\]\]', text)
    data_list = []
    
    # Extract the global ANALYSIS section first, from the entire text
    # Use find instead of re.search for potentially more robust tag detection
    analysis_tag_start = text.lower().find('[analysis]')
    global_analysis_text = ""
    if analysis_tag_start != -1:
        global_analysis_text = text[analysis_tag_start + len('[analysis]'):].strip()
        if global_analysis_text:
            global_analysis_text = _normalize_full_width_to_half_width(global_analysis_text)
            print(f"   DEBUG: Global analysis text (first 200 chars): {global_analysis_text[:200]}...")
            print(f"   ✅ 全局 [ANALYSIS] 标签已发现，长度: {len(global_analysis_text)} 字")
        else:
            print(f"   ⚠️ 全局 [ANALYSIS] 标签找到，但内容为空。")
    else:
        print(f"   ⚠️ 未能发现全局 [ANALYSIS] 标签。")
        
    NAME_MAP = {
        "READING_PASSAGE_A": "阅读理解 A", "READING_PASSAGE_B": "阅读理解 B",
        "READING_PASSAGE_C": "阅读理解 C", "READING_PASSAGE_D": "阅读理解 D",
        "READING_PASSAGE_E": "阅读理解 E", "7_OUT_OF_5": "七选五", "CLOZE": "完形填空", "GRAMMAR": "语法填空"
    }
    TYPE_MAP = {
        "READING_PASSAGE_A": "reading", "READING_PASSAGE_B": "reading", 
        "READING_PASSAGE_C": "reading", "READING_PASSAGE_D": "reading",
        "READING_PASSAGE_E": "reading", "7_OUT_OF_5": "seven_five", "CLOZE": "cloze", "GRAMMAR": "grammar"
    }

    for i in range(1, len(sections), 2):
        sec_name = sections[i].strip()
        sec_body = sections[i+1].strip()
        print(f"\n📂 正在解析板块: {sec_name}")

        # --- 第一步：切割原文 ---
        questions_tag_start = sec_body.lower().find('[questions]')
        if questions_tag_start == -1:
            print(f"   ❌ [错误] 未能发现 [QUESTIONS] 标签在板块 {sec_name}。跳过此板块。")
            continue # Skip this section if no questions tag

        passage = sec_body[:questions_tag_start].strip()
        q_text = sec_body[questions_tag_start + len('[questions]'):].strip()
        
        # Normalize q_text immediately
        print(f"   DEBUG: q_text BEFORE normalization (first 200 chars): {q_text[:200]}...")
        q_text = _normalize_full_width_to_half_width(q_text)
        print(f"   DEBUG: q_text AFTER normalization (first 200 chars): {q_text[:200]}...")
        print(f"   📝 原文长度: {len(passage)} 字")
        print(f"   ❓ 题目文本长度: {len(q_text)} 字")
        print(f"   DEBUG: Raw q_text (repr, full): {repr(q_text)}")

        parsed_items = [] # Temporary list to hold items returned by specific parsers
        current_question_type = TYPE_MAP.get(sec_name, "reading")

        # Directly call the specific item parser for each question type
        if current_question_type == "grammar":
            parsed_items = _parse_grammar_items_full_exam(q_text, global_analysis_text)
        elif current_question_type == "seven_five":
            parsed_items = _parse_seven_five_items_full_exam(q_text, global_analysis_text, passage)
        elif current_question_type == "cloze":
            parsed_items = _parse_cloze_items_full_exam(q_text, global_analysis_text)
        elif current_question_type == "reading":
            parsed_items = _parse_reading_items_full_exam_robust(q_text, global_analysis_text)
        else:
            print(f"   ⚠️ 未知题型: {current_question_type}。跳过题目解析。")
            parsed_items = []

        print(f"   DEBUG: Parsed items returned by {current_question_type} parser (first 3 items): {parsed_items[:3]}")

        # --- 第二步：对解析器返回的 items 进行健壮性检查和清理 ---
        items = []
        if not isinstance(parsed_items, list):
            print(f"   ⚠️ 解析器 {current_question_type} 返回了非列表类型数据。将其视为空列表。")
        else:
            for item_dict in parsed_items:
                if not isinstance(item_dict, dict):
                    print(f"   ⚠️ 解析器 {current_question_type} 返回的列表中包含非字典类型元素。跳过。")
                    continue
                cleaned_item_dict = {}
                for k, v in item_dict.items():
                    if v is None:
                        cleaned_item_dict[k] = ""
                    elif k == 'options':
                        cleaned_item_dict[k] = v
                    else:
                        cleaned_item_dict[k] = str(v)
                items.append(cleaned_item_dict)

        # 确保所有题目的 q_id 都被规范化为纯半角数字字符串
        normalized_items = []
        for item in items:
            normalized_q_id_str = _normalize_full_width_to_half_width(item.get('q_id', ''))
            item['q_id'] = re.sub(r'\D', '', normalized_q_id_str)
            normalized_items.append(item)
        items = normalized_items

        print(f"   📊 成功提取题目数量: {len(items)} (由 {current_question_type} 解析器处理)")

        data_list_item_analysis = global_analysis_text # Store the global analysis for ResultPage
        data_list.append({
            "category": NAME_MAP.get(sec_name, sec_name),
            "question_type": current_question_type,
            "passage": passage, 
            "items": items,
            "original_analysis": datalist_item_analysis
        })
        
    return data_list

# ==========================================
# 2. 主程序类
# ==========================================
class HighSchoolEnglishAI(QMainWindow):
    """
    主应用程序窗口，负责管理各个功能模块的切换和整体UI布局。
    """
    def __init__(self):
        super().__init__() 
        self.setWindowTitle("HSE-AI 英语智胜工作站")
        self.showMaximized() 
        self.base_path = base_path 
        
        loader = QUiLoader()
        self.ui_root = loader.load(os.path.join(res_dir, "main_window.ui")) 
        if not self.ui_root: return
        self.setCentralWidget(self.ui_root) 

        self.stack = self.ui_root.findChild(QStackedWidget, "stackedWidget")
        self.btn_nav_vocab = self.ui_root.findChild(QPushButton, "btn_nav_vocab")
        self.btn_nav_core_vocab = self.ui_root.findChild(QPushButton, "btn_nav_core_vocab")
        self.btn_nav_gaokao = self.ui_root.findChild(QPushButton, "btn_nav_gaokao")
        self.btn_nav_full_exam = self.ui_root.findChild(QPushButton, "btn_nav_full_exam")

        self.vocab_ctrl = None
        self.word_list_widget = None
        self.word_list_index = -1
        self.exam_ctrl = None
        self._setup_gaokao_page(res_dir, loader)
        
        try:
            self.vocab_ctrl = VocabManager(self)
            self.word_list_widget = WordListView(self)
            if self.word_list_widget:
                self.stack.addWidget(self.word_list_widget)
                self.word_list_index = self.stack.indexOf(self.word_list_widget)
                self.vocab_ctrl.mistake_vocabulary_changed.connect(self.word_list_widget.refresh_mistake_list)
            self.exam_ctrl = ExamManager(self)
        except Exception as e:
            print(f"⚠️ 业务模块初始化异常: {e}")

        self._apply_sidebar_style()
        self._bind_nav_events()
        self.stack.setCurrentIndex(0)
        
        self.stack.currentChanged.connect(self._handle_stack_page_changed)
        
        self.full_exam_files = []
        self.full_exam_file_index = 0

    def _setup_gaokao_page(self, res_dir, loader):
        """
        设置高考专项练习页面，包括加载UI和绑定题型选择按钮。
        """
        gk_ui_path = os.path.join(res_dir, "page_gaokao.ui")
        self.page_gaokao_widget = loader.load(gk_ui_path)
        if self.page_gaokao_widget:
            self.btn_reading = self.page_gaokao_widget.findChild(QPushButton, "gk_btn_reading")
            self.btn_cloze = self.page_gaokao_widget.findChild(QPushButton, "gk_btn_cloze")
            self.btn_7to5 = self.page_gaokao_widget.findChild(QPushButton, "gk_btn_seven_five")
            self.btn_grammar = self.page_gaokao_widget.findChild(QPushButton, "gk_btn_grammar")
            
            if self.btn_reading: self.btn_reading.clicked.connect(lambda: self.load_special_practice("阅读理解"))
            if self.btn_cloze: self.btn_cloze.clicked.connect(lambda: self.load_special_practice("完形填空"))
            if self.btn_7to5: self.btn_7to5.clicked.connect(lambda: self.load_special_practice("七选五"))
            if self.btn_grammar: self.btn_grammar.clicked.connect(lambda: self.load_special_practice("语法填空"))
            
            self.stack.addWidget(self.page_gaokao_widget)
            self.gk_idx = self.stack.indexOf(self.page_gaokao_widget)

    def _bind_nav_events(self):
        """
        绑定侧边栏导航按钮的点击事件。
        """
        self.btn_nav_vocab.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_nav_core_vocab.clicked.connect(self._show_word_list_page)
        self.btn_nav_gaokao.clicked.connect(self.show_gaokao_page)
        self.btn_nav_full_exam.clicked.connect(self.switch_to_full_exam)

    def _handle_stack_page_changed(self, index):
        """
        Handles changes in the QStackedWidget's current page.
        """
        vocab_page_index = 0
        if self.vocab_ctrl:
            if index == vocab_page_index:
                if self.vocab_ctrl.current_challenge_mode is None:
                    self.vocab_ctrl._display_mode_selection_prompt()
                else:
                    self.vocab_ctrl.show_next()

    def _show_word_list_page(self):
        """
        Helper to show the word list page and debug its index.
        """
        if self.word_list_index != -1:
            self.stack.setCurrentIndex(self.word_list_index)
        else:
            QMessageBox.warning(self, "错误", "核心词汇表页面未加载成功，请检查控制台输出。")

    def load_special_practice(self, folder_name):
        """
        加载指定题型的专项练习。
        """
        self.stack.setCurrentIndex(self.gk_idx)
        if self.exam_ctrl:
            self.exam_ctrl.switch_topic(folder_name)

    def switch_to_full_exam(self):
        """
        加载整卷练习
        """
        full_exam_dir = os.path.join(self.base_path, "data", "真题试卷")
        
        if not os.path.exists(full_exam_dir):
            QMessageBox.warning(self, "提示", f"找不到真题试卷目录: {full_exam_dir}")
            return
            
        try:
            available_files = [f for f in os.listdir(full_exam_dir) if f.endswith(".txt")]
            if not available_files:
                QMessageBox.warning(self, "提示", f"真题试卷目录中没有找到任何 .txt 文件: {full_exam_dir}")
                return

            # 如果没有文件缓存，或索引越界，则重新洗牌
            if not self.full_exam_files or self.full_exam_file_index >= len(self.full_exam_files) or self.full_exam_file_index == -1:
                random.shuffle(available_files)
                self.full_exam_files = available_files
                self.full_exam_file_index = 0
                print(f"DEBUG: Full exam files re-shuffled. New order: {self.full_exam_files}")

            target_file_name = self.full_exam_files[self.full_exam_file_index]
            target_file_path = os.path.join(full_exam_dir, target_file_name)
            self.full_exam_file_index += 1
            
            print(f"DEBUG: Loading full exam file: {target_file_path}")

            with open(target_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                QMessageBox.warning(self, "提示", f"文件 {target_file_name} 内容为空，请检查。")
                self.full_exam_file_index = -1
                return
                
            data_list = _internal_full_exam_parser(content)
            if not data_list:
                QMessageBox.warning(self, "提示", f"文件 {target_file_name} 未能解析出任何题目板块，请检查文件格式。")
                self.full_exam_file_index = -1
                return

            self.full_exam_view = HSEExamSystem(data_list)
            new_idx = self.stack.addWidget(self.full_exam_view)
            self.stack.setCurrentIndex(new_idx)

        except Exception as e:
            self.full_exam_file_index = -1
            QMessageBox.critical(self, "错误", f"试卷加载失败: {e}")

    def show_gaokao_page(self):
        """
        显示高考专项练习页面，并更新导航高亮。
        """
        self.stack.setCurrentIndex(self.gk_idx)
        if self.exam_ctrl: 
            self.exam_ctrl.update_nav_highlight()

    def _apply_sidebar_style(self):
        """
        应用侧边栏导航按钮的统一样式。
        """
        qss = "QPushButton { min-height: 55px; border-radius: 12px; text-align: left; padding-left: 20px; font-weight: bold; }"
        btns = [self.btn_nav_vocab, self.btn_nav_core_vocab, self.btn_nav_gaokao, self.btn_nav_full_exam]
        self.sidebar_group = QtWidgets.QButtonGroup(self)
        for btn in btns:
            if btn:
                btn.setCheckable(True)
                btn.setStyleSheet(qss)
                self.sidebar_group.addButton(btn)
        if self.btn_nav_vocab: self.btn_nav_vocab.setChecked(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = HighSchoolEnglishAI()
    window.show()
    sys.exit(app.exec())