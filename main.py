import sys
import os
import re
import time
import PySide6

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

# ============ [3. 模块导入] ============
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QPushButton, 
                             QStackedWidget, QVBoxLayout, QWidget, QLineEdit)
from PySide6.QtUiTools import QUiLoader

try:
    from vocab_module import VocabManager
    from word_list_view import WordListView 
    from run_flull_exam import HSEExamSystem
    from exam_module import ExamManager 
except ImportError as e:
    print(f"❌ 业务模块加载偏差: {e}")

# ==========================================
# 1. 独立解析器 (保留你最核心的解析逻辑)
# ==========================================
def _internal_full_exam_parser(text):
    print("\n" + "="*50)
    print("🚀 [DEBUG] 解析器已启动...")
    
    sections = re.split(r'\[\[SECTION:\s*(.*?)\]\]', text)
    data_list = []
    
    NAME_MAP = {
        "READING_PASSAGE_A": "阅读理解 A", "READING_PASSAGE_B": "阅读理解 B",
        "READING_PASSAGE_C": "阅读理解 C", "READING_PASSAGE_D": "阅读理解 D",
        "7_OUT_OF_5": "七选五", "CLOZE": "完形填空", "GRAMMAR": "语法填空"
    }
    TYPE_MAP = {
        "READING_PASSAGE_A": "reading", "READING_PASSAGE_B": "reading", 
        "READING_PASSAGE_C": "reading", "READING_PASSAGE_D": "reading",
        "7_OUT_OF_5": "seven_five", "CLOZE": "cloze", "GRAMMAR": "grammar"
    }

    for i in range(1, len(sections), 2):
        sec_name = sections[i].strip()
        sec_body = sections[i+1].strip()
        
        questions_tag_match = re.search(r'[\[【]\s*QUESTIONS\s*[\]】]', sec_body, flags=re.I)
        if not questions_tag_match: continue

        passage = sec_body[:questions_tag_match.start()].strip()
        raw_questions_and_analysis = sec_body[questions_tag_match.end():].strip()

        analysis_tag_match = re.search(r'[\[【]\s*ANALYSIS\s*[\]】]', raw_questions_and_analysis, flags=re.I | re.S)
        if analysis_tag_match:
            q_text = raw_questions_and_analysis[:analysis_tag_match.start()].strip()
            original_analysis = raw_questions_and_analysis[analysis_tag_match.end():].strip()
        else:
            q_text = raw_questions_and_analysis.strip()
            original_analysis = ""

        items = []
        seven_five_global_options = []

        if TYPE_MAP.get(sec_name, "reading") == "seven_five":
            option_matches = re.findall(r'([A-G])\.\s*(.*?)(?=\s*[A-G]\.|$|\n)', q_text, re.S)
            for label, content in option_matches:
                seven_five_global_options.append({"label": label, "content": content.strip()})
            
            seven_five_qids_in_text = re.findall(r'(\d+)\s*[\.\)]', q_text)
            unique_qids = sorted(list(set(seven_five_qids_in_text)), key=int)
            if not unique_qids: unique_qids = [str(i) for i in range(36, 41)]

            for q_id_str in unique_qids:
                items.append({"q_id": q_id_str, "content": f"请选择第 {q_id_str} 题的答案", "options": seven_five_global_options})
        else:
            question_blocks_matches = re.finditer(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n*\d+\s*[\.\)]\s*|\Z)', q_text, re.DOTALL)
            for match in question_blocks_matches:
                q_id = match.group(1).strip()
                block_content = match.group(2).strip()
                options_found = list(re.finditer(r'([A-G])\s*[\.\)]\s*(.*?)(?=\n*[A-G]\s*[\.\)]\s*|\Z)', block_content, re.DOTALL))
                
                question_options = {}
                if options_found:
                    question_stem = block_content[:options_found[0].start()].strip()
                    for opt_match in options_found:
                        question_options[opt_match.group(1).upper()] = opt_match.group(2).strip()
                else:
                    question_stem = block_content
                
                items.append({"q_id": q_id, "content": question_stem, "options": question_options})

        data_list.append({
            "category": NAME_MAP.get(sec_name, sec_name),
            "question_type": TYPE_MAP.get(sec_name, "reading"),
            "passage": passage, 
            "items": items,
            "original_analysis": original_analysis
        })
        
    return data_list

# ==========================================
# 2. 主程序类
# ==========================================
class HighSchoolEnglishAI(QMainWindow):
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

        self._setup_gaokao_page(res_dir, loader)
        
        try:
            self.vocab_ctrl = VocabManager(self)
            self.word_list_widget = WordListView(self)
            self.stack.addWidget(self.word_list_widget)
            self.word_list_index = self.stack.indexOf(self.word_list_widget)
            self.exam_ctrl = ExamManager(self) 
        except Exception as e:
            print(f"⚠️ 业务模块异常: {e}")

        self._apply_sidebar_style()
        self._bind_nav_events()
        self.stack.setCurrentIndex(0)

    def _setup_gaokao_page(self, res_dir, loader):
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
        self.btn_nav_vocab.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_nav_core_vocab.clicked.connect(lambda: self.stack.setCurrentIndex(self.word_list_index))
        self.btn_nav_gaokao.clicked.connect(self.show_gaokao_page)
        self.btn_nav_full_exam.clicked.connect(self.switch_to_full_exam)
        
    def load_special_practice(self, folder_name):
        self.stack.setCurrentIndex(self.gk_idx)
        if self.exam_ctrl:
            self.exam_ctrl.switch_topic(folder_name)

    def switch_to_full_exam(self):
        target_file = os.path.join(data_dir, "真题试卷", "高考模拟卷_2026.txt")
        if not os.path.exists(target_file):
            QMessageBox.warning(self, "提示", f"找不到文件: {target_file}")
            return
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            data_list = _internal_full_exam_parser(content)
            self.full_exam_view = HSEExamSystem(data_list)
            new_idx = self.stack.addWidget(self.full_exam_view)
            self.stack.setCurrentIndex(new_idx)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"试卷加载失败: {e}")

    def show_gaokao_page(self):
        self.stack.setCurrentIndex(self.gk_idx)
        if self.exam_ctrl: 
            self.exam_ctrl.update_nav_highlight()

    def _apply_sidebar_style(self):
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