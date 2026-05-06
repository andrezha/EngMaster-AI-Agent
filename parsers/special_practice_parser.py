import re
from typing import List, Dict, Optional, Tuple

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
    与高考真题解析器完全隔离。
    """
    def __init__(self):
        self.metadata_patterns = {
            "FILENAME": re.compile(r'^FILENAME:\s*(.*)'),
            "YEAR": re.compile(r'^YEAR:\s*(\d{4})'),
            "CAT": re.compile(r'^CAT:\s*(.*)'),
            "TITLE": re.compile(r'^TITLE:\s*(.*)')
        }
        self.question_start_marker_pattern = re.compile(r'^\s*\[(?:QUESTIONS|OPTIONS)\]\s*$', re.IGNORECASE) # Modified to match [OPTIONS] or [QUESTIONS]
        self.analysis_start_marker_pattern = re.compile(r'^\s*\[ANALYSIS\]\s*$', re.IGNORECASE)

        # Regex for explicitly numbered questions (e.g., "59. What is...")
        self.explicit_question_pattern = re.compile(r'^\s*(\d+)\.\s*(.*)')
        # Regex for options (e.g., "A. Option text")
        self.option_pattern = re.compile(r'^\s*([A-D])\.\s*(.*)')
        # Regex for analysis lines (e.g., "59. B. Main Idea.")
        self.analysis_line_pattern = re.compile(r'^\s*(\d+)\.\s*([A-D])\.\s*(.*)')

    def parse_file(self, file_path: str) -> Tuple[Dict[str, str], str, List[SpecializedPracticeQuestion]]:
        """
        解析指定的专项练习txt文件，返回一个元组：
        (metadata, passage_text, questions_list)
        """
        metadata: Dict[str, str] = {}
        passage_lines: List[str] = []
        questions: List[SpecializedPracticeQuestion] = []
        
        current_state = "METADATA" # METADATA, PASSAGE, QUESTIONS, ANALYSIS

        current_question_number: Optional[int] = None
        current_question_text_lines: List[str] = []
        current_options: Dict[str, str] = {}
        current_correct_answer: Optional[str] = None
        current_analysis_text: Optional[str] = None
        question_counter = 0 # To assign sequential numbers to questions
        analysis_lines_buffer: Dict[int, Tuple[str, str]] = {} # To store (answer, full_analysis_text) per question number
        
        # Helper to finalize a question and add it to the questions list
        def finalize_current_question():
            nonlocal current_question_number, current_question_text_lines, current_options, current_correct_answer, current_analysis_text
            if current_question_number is not None and current_question_text_lines:
                questions.append(SpecializedPracticeQuestion(
                    question_number=current_question_number,
                    question_text="\n".join(current_question_text_lines).strip(),
                    options=current_options.copy(), # Use copy to avoid modification issues
                    correct_answer=current_correct_answer,
                    analysis_text=current_analysis_text
                ))
            # Reset for next question
            current_question_number = None
            current_question_text_lines = []
            current_options = {}
            current_correct_answer = None
            current_analysis_text = None
        current_correct_answer: Optional[str] = None
        current_analysis_text: Optional[str] = None
        question_counter = 0 # To assign sequential numbers to questions
        analysis_lines_buffer: Dict[int, Tuple[str, str]] = {} # To store (answer, full_analysis_text) per question number
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
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
                        # If no metadata pattern matched, assume passage starts
                        current_state = "PASSAGE"
                        passage_lines.append(stripped_line) # Add this line to passage
                    continue

                if self.question_start_marker_pattern.match(stripped_line):
                    current_state = "QUESTIONS"
                    question_counter = 0 # Reset counter for questions in this section
                    continue

                if self.analysis_start_marker_pattern.match(stripped_line):
                    current_state = "ANALYSIS"
                    finalize_current_question() # Finalize the last question before analysis
                    continue

                if current_state == "PASSAGE":
                    passage_lines.append(stripped_line)

                elif current_state == "QUESTIONS":
                    explicit_q_match = self.explicit_question_pattern.match(stripped_line)
                    option_match = self.option_pattern.match(stripped_line)

                    if explicit_q_match:
                        # Found an explicitly numbered question
                        finalize_current_question() # Save previous question if any
                        current_question_number = int(explicit_q_match.group(1))
                        question_counter = current_question_number # Sync counter with explicit number
                        current_question_text_lines.append(explicit_q_match.group(2).strip()) # Add question text
                        current_options = {} # Reset options for the new question
                    elif option_match:
                        # Found an option
                        if current_question_number is None:
                            # This means an option appeared before any question text was explicitly started.
                            # We should assume this option belongs to a new question.
                            question_counter += 1
                            current_question_number = question_counter
                            current_question_text_lines.append("") # Placeholder for question text
                            print(f"Warning: Option '{stripped_line}' found without preceding question text at line {line_num}. Assigned to Q{current_question_number}.")
                        current_options[option_match.group(1)] = option_match.group(2).strip()
                    else:
                        # This line is neither an explicit question nor an option.
                        # It's either a continuation of question text, or a new implicitly numbered question.
                        if current_question_number is not None and current_options:
                            # We just finished options for the previous question, so this new line must be a new question.
                            finalize_current_question()
                            question_counter += 1
                            current_question_number = question_counter
                            current_question_text_lines.append(stripped_line)
                            current_options = {} # Reset options for the new question
                        elif current_question_number is not None:
                            # Continuation of current question text (multi-line question)
                            current_question_text_lines.append(stripped_line)
                        else: # First question in the section, or after a finalized question, and not an explicit number
                            question_counter += 1
                            current_question_number = question_counter
                            current_question_text_lines.append(stripped_line)

                elif current_state == "ANALYSIS":
                    analysis_match = self.analysis_line_pattern.match(stripped_line)
                    if analysis_match:
                        q_num = int(analysis_match.group(1))
                        ans = analysis_match.group(2)
                        full_analysis_text = analysis_match.group(3).strip() # Capture the full analysis text
                        analysis_lines_buffer[q_num] = (ans, full_analysis_text)
        
        # After loop, ensure the last question is finalized if the file didn't end with ANALYSIS
        if current_question_number is not None and current_question_text_lines:
            finalize_current_question()

        # Second pass to apply analysis text and correct answers to questions
        for q in questions:
            if q.question_number in analysis_lines_buffer:
                ans, full_analysis_text = analysis_lines_buffer[q.question_number]
                q.correct_answer = ans
                q.analysis_text = full_analysis_text

        return metadata, "\n".join(passage_lines).strip(), questions