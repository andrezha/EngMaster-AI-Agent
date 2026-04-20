import sys
import os
import re
import time
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QPushButton, 
                             QStackedWidget, QVBoxLayout, QWidget, QLineEdit)
from PySide6.QtUiTools import QUiLoader

# ============ 路径配置与自检 ============
base_path = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(base_path, "lib")
if lib_path not in sys.path:
    sys.path.append(lib_path)
if base_path not in sys.path:
    sys.path.append(base_path)

try:
    from vocab_module import VocabManager
    from word_list_view import WordListView 
    from run_flull_exam import HSEExamSystem
    from exam_module import ExamManager 
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")

# ==========================================
# 1. 独立解析器 (专门负责整卷 TXT 格式转换)
# ==========================================
def _internal_full_exam_parser(text):
    import re
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
        print(f"\n📂 正在解析板块: {sec_name}")

        # --- 第一步：切割原文 ---
        p_split = re.split(r'[\[【]\s*QUESTIONS\s*[\]】]', sec_body, flags=re.I)
        passage = p_split[0].strip()
        print(f"   📝 原文长度: {len(passage)} 字")
        
        q_text = ""
        original_analysis = ""
        
        # --- Step 1: Split by [QUESTIONS] to get passage and raw_questions_and_analysis ---
        questions_tag_match = re.search(r'[\[【]\s*QUESTIONS\s*[\]】]', sec_body, flags=re.I)
        if not questions_tag_match:
            print(f"   ❌ [错误] 未能发现 [QUESTIONS] 标签在板块 {sec_name}。跳过此板块。")
            continue # Skip this section if no questions tag

        passage = sec_body[:questions_tag_match.start()].strip()
        raw_questions_and_analysis = sec_body[questions_tag_match.end():].strip()

        # --- Step 2: Split raw_questions_and_analysis by [ANALYSIS] to get q_text and original_analysis ---
        analysis_tag_match = re.search(r'[\[【]\s*ANALYSIS\s*[\]】]', raw_questions_and_analysis, flags=re.I | re.S)
        if analysis_tag_match:
            q_text = raw_questions_and_analysis[:analysis_tag_match.start()].strip()
            original_analysis = raw_questions_and_analysis[analysis_tag_match.end():].strip()
            print(f"   ✅ 发现 [ANALYSIS] 标签，已提取解析内容。")
        else:
            q_text = raw_questions_and_analysis.strip()
            print(f"   ⚠️ 未能发现 [ANALYSIS] 标签，题目内容可能包含解析。")

        print(f"   📝 原文长度: {len(passage)} 字")
        print(f"   DEBUG: 提取的 q_text (前200字):\n{q_text[:200]}...")

        items = []
        seven_five_global_options = [] # This will store the A-G options for seven_five, initialized once

        # --- Special handling for Seven-Five ---
        if TYPE_MAP.get(sec_name, "reading") == "seven_five":
            # For seven_five, q_text contains blank numbers (e.g., 36-40) followed by A-G options.
            # We need to extract these A-G options from q_text.
            
            # Find the last question number in the sequence (e.g., 40)
            # This regex looks for a number followed by a dot or parenthesis, at the start of a line
            last_qid_in_qtext_match = re.findall(r'^\s*(\d+)\s*[\.\)]', q_text, re.MULTILINE)
            last_qid_num = 0
            if last_qid_in_qtext_match:
                last_qid_num = int(last_qid_in_qtext_match[-1]) # Get the last number found

            options_content_for_seven_five = ""
            # Find the start of the A-G options after the last question number
            # This regex looks for 'A.' at the beginning of a line, after the last qid
            options_start_pattern = r'(?:\n|^)\s*A\.\s*'
            options_start_match = re.search(options_start_pattern, q_text)

            if options_start_match:
                options_content_for_seven_five = q_text[options_start_match.start():].strip()
            else:
                # Fallback: if 'A.' not found, assume all content after last qid is options
                if last_qid_num > 0:
                    # Find the position after the last qid in q_text
                    pos_after_last_qid = q_text.rfind(str(last_qid_num)) + len(str(last_qid_num))
                    options_content_for_seven_five = q_text[pos_after_last_qid:].strip()
                else:
                    options_content_for_seven_five = q_text.strip() # If no qids found, assume whole q_text is options

            # Parse A-G options from the extracted content
            option_matches = re.findall(r'([A-G])\.\s*(.*?)(?=\s*[A-G]\.|$|\n)', options_content_for_seven_five, re.S)
            for label, content in option_matches:
                seven_five_global_options.append({"label": label, "content": content.strip()})
            
            print(f"   ✅ 提取七选五全局选项: {len(seven_five_global_options)} 个. 示例: {seven_five_global_options[:2]}")
            if not seven_five_global_options:
                print("   ❌ 警告: 七选五全局选项列表为空，请检查 [QUESTIONS] 标签后的格式。")

            # Generate items for blanks 36-40 (or whatever range is implied)
            # For seven_five, the q_ids are usually explicitly marked in the passage or q_text.
            # Let's try to extract them from the q_text if they are present as numbers.
            # If not, we fall back to the assumed 36-40 range.
            
            # First, try to find explicit question numbers in q_text for seven_five
            seven_five_qids_in_text = re.findall(r'(\d+)\s*[\.\)]', q_text)
            unique_qids = sorted(list(set(seven_five_qids_in_text)), key=int)
            
            if not unique_qids:
                # Fallback to assumed range if no explicit q_ids found in q_text
                print("   ⚠️ 未在七选五题目文本中找到明确题号，假定题号为 36-40。")
                unique_qids = [str(i) for i in range(36, 41)]

            for q_id_str in unique_qids:
                items.append({
                    "q_id": q_id_str,
                    "content": f"请选择第 {q_id_str} 题的答案", # Content for the blank
                    "options": seven_five_global_options # Assign the parsed global options
                })
        else: # 对于阅读理解、完形填空、语法填空，从 q_text 中解析题目
            # Find all question blocks. A question block starts with a number (e.g., 21.)
            # and captures everything until the next question number or the end of the text.
            question_blocks_matches = re.finditer(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n*\d+\s*[\.\)]\s*|\Z)', q_text, re.DOTALL)
            
            for match in question_blocks_matches:
                q_id = match.group(1).strip()
                block_content = match.group(2).strip()
                
                question_stem = ""
                question_options = {}
                
                options_pattern = r'([A-G])\s*[\.\)]\s*(.*?)(?=\n*[A-G]\s*[\.\)]\s*|\Z)' # Changed [A-D] to [A-G] for more flexibility
                options_found = list(re.finditer(options_pattern, block_content, re.DOTALL))
                
                if options_found:
                    first_option_start_pos = options_found[0].start()
                    question_stem = block_content[:first_option_start_pos].strip()
                    
                    for opt_match in options_found:
                        label = opt_match.group(1).upper()
                        content = opt_match.group(2).strip()
                        question_options[label] = content
                else:
                    question_stem = block_content
                
                items.append({
                    "q_id": q_id,
                    "content": question_stem,
                    "options": question_options
                })


        print(f"   📊 成功提取题目数量: {len(items)}")

        data_list.append({
            "category": NAME_MAP.get(sec_name, sec_name),
            "question_type": TYPE_MAP.get(sec_name, "reading"),
            "passage": passage, 
            "items": items,
            "original_analysis": original_analysis # 存储解析内容
        })
        
    print(f"✅ [DEBUG] 解析器完成，共解析出 {len(data_list)} 个板块。")
    print("="*50)
    return data_list

# ==========================================
# 2. 主程序类
# ==========================================
class HighSchoolEnglishAI(QMainWindow):
    def __init__(self):
        super().__init__() 
        self.setWindowTitle("HSE-AI 英语智胜工作站")
        self.showMaximized() 
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        res_dir = os.path.join(self.base_path, "resources")
        
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
        """高考整卷：适配 QWidget 版本，解决 centralWidget 报错"""
        target_file = os.path.join(self.base_path, "data", "真题试卷", "高考模拟卷_2026.txt")
        
        if not os.path.exists(target_file):
            QMessageBox.warning(self, "提示", f"找不到文件: {target_file}")
            return

        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. 解析数据
            data_list = _internal_full_exam_parser(content)
            
            # 2. 实例化 UI，直接传入解析好的 data_list
            # from old.exam_system import HSEExamSystem # 移除局部导入，使用文件顶部的导入
            self.full_exam_view = HSEExamSystem(data_list)
            
            # 3. 渲染数据 (HSEExamSystem 的 __init__ 会调用 update_data)
            # self.full_exam_view.update_data(data_list) # HSEExamSystem's __init__ already calls update_data
            
            # 4. 挂载 (直接 addWidget，不加 centralWidget)
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