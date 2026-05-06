# These functions are specifically for parsing full exam sections in main.py.
import re
# They assume that q_text and analysis_text are already normalized to half-width.

def _parse_reading_items_full_exam_robust(q_text, analysis_text):
    """
    【全真战场专用】解析阅读理解题目的具体逻辑。
    """
    items = [] # Initialize items list
    sequential_answers = re.findall(r'^\s*([A-G])\s*[．\.]', analysis_text, re.MULTILINE)
    explicit_ans_map = {} # Initialize explicit_ans_map

    # Define the robust pattern to capture question blocks.
    # It looks for a question ID (e.g., "28.") and captures everything until the next question ID or end of text.
    # This is more robust than trying to capture options within the main block regex.
    question_block_pattern = re.compile(
        r'(\d+)\s*[\.\)]\s*(.*?)(?=\s*\d+\s*[\.\)]\s*|\Z)', re.DOTALL # Group 1: QID, Group 2: rest of the block
    ) # Added missing closing parenthesis
    seq_ans_idx = 0
    print(f"DEBUG: _parse_reading_items_full_exam_robust - q_text starts with: {q_text[0]!r}, isdigit: {q_text[0].isdigit()}")
    print(f"DEBUG: _parse_reading_items_full_exam_robust - q_text (repr, full, before loop): {repr(q_text)}")
    print(f"DEBUG: _parse_reading_items_full_exam_robust - question_block_pattern (pattern): {question_block_pattern.pattern!r}")
    
    temp_matches = list(question_block_pattern.finditer(q_text))
    print(f"DEBUG: _parse_reading_items_full_exam_robust - question_block_pattern found {len(temp_matches)} matches.")
    if temp_matches:
        print(f"DEBUG: _parse_reading_items_full_exam_robust - First match groups: {repr(temp_matches[0].groups())}")
    
    # Iterate through the q_text to find all question blocks
    for block_match in temp_matches:
        q_id_from_text = (block_match.group(1) or "").strip() # Extract QID
        block_content = (block_match.group(2) or "").strip()
        print(f"DEBUG: Q{q_id_from_text} - Extracted block_content (repr, first 200 chars): {repr(block_content[:200])}")

        question_stem = ""

        options = {} # Initialize options for each question
        # Standardize option prefixes in block_content before parsing options
        # This ensures "A", "A.", "A)" all become "A. " for consistent parsing
        # For full exam, strictly match A-D
        standardized_block_content = re.sub(r'([A-D])\s*[\.\)]?\s*', r'\1. ', block_content)
        print(f"DEBUG: Q{q_id_from_text} - Standardized block_content (repr, full): {repr(standardized_block_content)}") # Print full standardized content with repr
        
        # --- More granular debugging for options parsing ---
        print(f"DEBUG: Q{q_id_from_text} - Standardized block_content (repr, full): {repr(standardized_block_content)}")
        
        # Test for presence of any option label
        any_label_found = re.search(r'[A-D]\.', standardized_block_content) # Strictly match A-D
        print(f"DEBUG: Q{q_id_from_text} - Any option label (A., B., C., D.) found: {bool(any_label_found)}")

        # Parse options from the block_content
        # Adjusted pattern: ensure content starts with a non-whitespace character
        # For full exam, strictly match A-D
        options_pattern = r'([A-D])\.\s*(\S[\s\S]*?)(?=\s*[A-D]\.|\s*\Z)' # Simplified pattern expecting "A. "
        print(f"DEBUG: Q{q_id_from_text} - Options pattern used: {options_pattern!r}")
        options_found = list(re.finditer(options_pattern, standardized_block_content, re.DOTALL))
        
        if options_found:
            print(f"DEBUG: Q{q_id_from_text} - Options found by regex (count {len(options_found)}). First match: {repr(options_found[0].groups()) if options_found else 'N/A'}")
            for i, opt_match in enumerate(options_found):
                label = opt_match.group(1)
                content = opt_match.group(2)
                print(f"DEBUG: Q{q_id_from_text} - Option {label}: Content (repr): {repr(content)}")
            first_option_start_pos = options_found[0].start()
            
            question_stem = standardized_block_content[:first_option_start_pos].strip() # Extract stem before first option
            for opt_match in options_found:
                label = opt_match.group(1).upper() # Convert to uppercase for consistency
                content = (opt_match.group(2) or "").strip() # Option content
                options[label] = content
            print(f"DEBUG: Q{q_id_from_text} - Populated options: {options}")
        else:
            question_stem = standardized_block_content # If no options found, the whole block is the stem
        # Only add if options are successfully parsed (for multiple choice questions)
        if options:
            # Try to get answer from explicit map first, then sequential answers
            answer = explicit_ans_map.get(q_id_from_text, "") # Get answer from map
            if not answer and seq_ans_idx < len(sequential_answers):
                answer = sequential_answers[seq_ans_idx]
                seq_ans_idx += 1
            items.append({ # Corrected unclosed parenthesis
                'q_id': q_id_from_text,
                'content': question_stem,
                'options': options,
                'answer': answer
            })
        else:
            print(f"DEBUG: Q{q_id_from_text} - Options dictionary is empty, item not added.")
            # If no options are found, it might be a malformed question or a different type
            # For reading comprehension, we expect options. Log a warning.
            print(f"DEBUG:   No options parsed for Q{q_id_from_text}. Item not added as reading comprehension.")

    print(f"DEBUG: _parse_reading_items_full_exam returning {len(items)} items.")
    return items # Added missing return statement

def _parse_cloze_items_full_exam(options_text, analysis_text):
    """
    【全真战场专用】解析完形填空题目的具体逻辑。
    """
    items = []
    explicit_ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-D])(?:\s*[\.\)]|\s|$)', analysis_text)) # QID. A.
    sequential_answers = re.findall(r'^\s*([A-D])\s*[\.\)]', analysis_text, re.MULTILINE) # 提取按顺序的答案
    pattern = re.finditer(r'(\d+)\.\s*A\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(.*?)(?=\d+\.\s*A\.|$)', options_text, re.S)
    for m in pattern:
        q_id = m.group(1)
        answer = explicit_ans_map.get(q_id, "")
        if not answer and len(items) < len(sequential_answers): # 如果没有显式答案，尝试使用顺序答案
            answer = sequential_answers[len(items)]
        items.append({"q_id": q_id, "answer": answer, "options": {"A": m.group(2).strip(), "B": m.group(3).strip(), "C": m.group(4).strip(), "D": m.group(5).strip()}})
    print(f"DEBUG: _parse_cloze_items_full_exam returning {len(items)} items.")
    return items

def _parse_seven_five_items_full_exam(options_text, analysis_text, passage):
    """
    【全真战场专用】解析七选五题目的具体逻辑。
    从 options_text 中提取选项列表，从 passage 中提取空白题号，从 analysis_text 中匹配答案。
    """
    print(f"DEBUG: _parse_seven_five_items_full_exam received options_text (len {len(options_text)}): {options_text[:200]}...")
    print(f"DEBUG: _parse_seven_five_items_full_exam received analysis_text (len {len(analysis_text)}): {analysis_text[:200]}...")
    print(f"DEBUG: _parse_seven_five_items_full_exam received passage (len {len(passage)}): {passage[:200]}...")
    
    items = []
    options_list = []
    for line in options_text.splitlines():
        m = re.match(r'^([A-G])\s*[\.\)]\s*(.*)', line.strip()) # 更灵活匹配 A. 或 A) for options list
        if m: options_list.append({"label": m.group(1), "content": m.group(2).strip()})
    
    explicit_ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-G])(?:\s*[\.\)]|\s|$)', analysis_text)) # QID. A.
    sequential_answers = re.findall(r'^\s*([A-G])\s*[\.\)]', analysis_text, re.MULTILINE) # 提取按顺序的答案

    # Use a more robust regex for blank numbers, e.g., \b\d{2}\b
    blank_numbers = sorted(set(re.findall(r'\b(\d{2})\b', passage)))
    
    seq_ans_idx = 0
    for q_id in blank_numbers:
        answer = explicit_ans_map.get(q_id, "")
        if not answer and seq_ans_idx < len(sequential_answers): # 如果没有显式答案，尝试使用顺序答案
            answer = sequential_answers[seq_ans_idx]
            seq_ans_idx += 1
        items.append({"q_id": q_id, "answer": answer, "options": options_list})
    print(f"DEBUG: _parse_seven_five_items_full_exam returning {len(items)} items.")
    return items

def _parse_grammar_items_full_exam(q_text, analysis_text):
    """
    【全真战场专用】解析语法填空题目的具体逻辑。
    从 q_text 中提取题目内容（带括号的词），从 analysis_text 中匹配答案。
    """
    # In this context, q_text contains "QID. (word)" format.
    items = []
    answers_map = {}
    
    # 语法填空答案匹配：匹配任意位数的题号，点/括号，然后捕获答案直到下一个句号、"考查"、"[" 或行尾
    ans_pattern = re.findall(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n\d+\s*[\.\)]|\Z)', analysis_text, re.DOTALL) # QID. Answer phrase
    for q_id, ans in ans_pattern: answers_map[q_id] = ans.strip()
    
    # Parse questions from q_text (e.g., "56. (origin)")
    # This regex will capture the QID and then whatever follows until the next QID or end of string.
    # Then we'll try to extract the "content" (the word to be modified) from that captured text.
    question_blocks = re.finditer(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n*\d+\s*[\.\)]\s*|\Z)', q_text, re.DOTALL)
    
    for match in question_blocks:
        q_id = match.group(1).strip()
        block_content = (match.group(2) or "").strip() # This is the part after QID.
        
        content_to_use = ""
        # Try to find a word in parentheses first
        paren_match = re.search(r'\((.*?)\)', block_content)
        if paren_match:
            content_to_use = paren_match.group(1).strip()
        else:
            # If no parentheses, assume the content is the first word or the whole block if it's short
            words = block_content.split()
            content_to_use = words[0] if words else block_content # Take the first word as the content
        
        items.append({
            "q_id": q_id,
            "answer": answers_map.get(q_id, ""), # Add the answer from the map
            "content": content_to_use, # Add the extracted content
            "options": [] # Grammar fill-in-the-blanks have no options
        })
    print(f"DEBUG: _parse_grammar_items_full_exam returning {len(items)} items.")
    return items
