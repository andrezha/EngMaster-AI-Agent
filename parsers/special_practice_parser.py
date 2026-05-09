import re
from typing import List, Dict, Optional, Tuple
from utils import normalize_exam_text

# --- 1. 定义“专项练习”专用的数据模型 ---
class SpecializedPracticeQuestion:
    """
    表示一个专项练习阅读理解题目及其选项和答案。
    """
    def __init__(self, question_number: int, question_text: str, options: Dict[str, str], correct_answer: Optional[str] = None, analysis_text: Optional[str] = None):
        self.question_number = question_number
        self.question_text = question_text
        self.options = options  # 例如: {'A': 'Option A text', 'B': 'Option B text'}
        self.correct_answer = correct_answer # 例如: 'B'
        self.analysis_text = analysis_text # 存储该题目的完整解析文本

    def __repr__(self):
        options_str = "\n".join([f"  {k}. {v}" for k, v in sorted(self.options.items())])
        analysis_str = f"Analysis: {self.analysis_text}\n" if self.analysis_text else ""
        return (f"Question {self.question_number}:\n"
                f"{self.question_text}\n"
                f"{options_str}\n"
                f"Correct Answer: {self.correct_answer if self.correct_answer else 'N/A'}\n"
                f"{analysis_str}")

# --- 2. 创建独立的“专项练习”文本解析器 ---
class SpecializedPracticeTextParser:
    """
    专门用于解析“专项练习”阅读理解txt文件的解析器。
    """
    def __init__(self):
        self.metadata_patterns = {
            "FILENAME": re.compile(r'^FILENAME:\s*(.*)'),
            "YEAR": re.compile(r'^YEAR:\s*(\d{4})'),
            "CAT": re.compile(r'^CAT:\s*(.*)'),
            "TITLE": re.compile(r'^TITLE:\s*(.*)')
        }
        self.question_start_marker_pattern = re.compile(r'^\s*\[(?:QUESTIONS|OPTIONS)\]\s*$', re.IGNORECASE)
        self.analysis_start_marker_pattern = re.compile(r'^\s*\[ANALYSIS\]\s*$', re.IGNORECASE)
        self.explicit_question_pattern = re.compile(r'^\s*(\d+)\.\s*(.*)')
        self.option_pattern = re.compile(r'^\s*([A-D])\.\s*(.*)')
        self.analysis_line_pattern = re.compile(r'^\s*(\d+)\.\s*([A-D])\.\s*(.*)')

    def parse_file(self, file_path: str) -> Tuple[Dict[str, str], str, List[SpecializedPracticeQuestion]]:
        """
        解析指定的专项练习txt文件。
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        # 【核心修复】：使用专用清洗函数预处理内容，确保全角点等符号被正确处理
        content = normalize_exam_text(raw_content)
        lines = content.splitlines()

        metadata: Dict[str, str] = {}
        passage_lines: List[str] = []
        questions: List[SpecializedPracticeQuestion] = []
        
        current_state = "METADATA"
        current_question_number: Optional[int] = None
        current_question_text_lines: List[str] = []
        current_options: Dict[str, str] = {}
        current_correct_answer: Optional[str] = None
        current_analysis_text: Optional[str] = None
        question_counter = 0
        analysis_lines_buffer: Dict[int, Tuple[str, str]] = {}
        
        def finalize_current_question():
            nonlocal current_question_number, current_question_text_lines, current_options, current_correct_answer, current_analysis_text
            if current_question_number is not None and (current_question_text_lines or current_options):
                questions.append(SpecializedPracticeQuestion(
                    question_number=current_question_number,
                    question_text="\n".join(current_question_text_lines).strip(),
                    options=current_options.copy(),
                    correct_answer=current_correct_answer,
                    analysis_text=current_analysis_text
                ))
            current_question_number = None
            current_question_text_lines = []
            current_options = {}
            current_correct_answer = None
            current_analysis_text = None

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                continue

            if current_state == "METADATA":
                matched_metadata = False
                for key, pattern in self.metadata_patterns.items():
                    match = pattern.match(stripped_line)
                    if match:
                        metadata[key] = match.group(1).strip()
                        matched_metadata = True
                        break
                if not matched_metadata:
                    current_state = "PASSAGE"
                    passage_lines.append(stripped_line)
                continue

            if self.question_start_marker_pattern.match(stripped_line):
                current_state = "QUESTIONS"
                question_counter = 0
                continue

            if self.analysis_start_marker_pattern.match(stripped_line):
                current_state = "ANALYSIS"
                finalize_current_question()
                continue

            if current_state == "PASSAGE":
                passage_lines.append(stripped_line)

            elif current_state == "QUESTIONS":
                explicit_q_match = self.explicit_question_pattern.match(stripped_line)
                option_match = self.option_pattern.match(stripped_line)

                if explicit_q_match:
                    finalize_current_question()
                    current_question_number = int(explicit_q_match.group(1))
                    question_counter = current_question_number
                    current_question_text_lines.append(explicit_q_match.group(2).strip())
                    current_options = {}
                elif option_match:
                    if current_question_number is None:
                        question_counter += 1
                        current_question_number = question_counter
                    current_options[option_match.group(1).upper()] = option_match.group(2).strip()
                else:
                    if current_question_number is not None:
                        current_question_text_lines.append(stripped_line)
                    else:
                        question_counter += 1
                        current_question_number = question_counter
                        current_question_text_lines.append(stripped_line)

            elif current_state == "ANALYSIS":
                analysis_match = self.analysis_line_pattern.match(stripped_line)
                if analysis_match:
                    q_num = int(analysis_match.group(1))
                    ans = analysis_match.group(2).upper()
                    full_analysis_text = analysis_match.group(3).strip()
                    analysis_lines_buffer[q_num] = (ans, full_analysis_text)
        
        finalize_current_question()

        for q in questions:
            if q.question_number in analysis_lines_buffer:
                ans, full_analysis_text = analysis_lines_buffer[q.question_number]
                q.correct_answer = ans
                q.analysis_text = full_analysis_text

        return metadata, "\n".join(passage_lines).strip(), questions
