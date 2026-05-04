import re

# These functions are specifically for parsing full exam sections in main.py.
# They assume that q_text and analysis_text are already normalized to half-width.

def _parse_reading_items_full_exam(q_text, analysis_text):
    """
    【全真战场专用】解析阅读理解题目的具体逻辑。
    """
    """
    Parses reading comprehension items for the full exam.
    Optimized for robust item and answer extraction.
    """
    items = []
    # Make regex more robust for full-width/half-width numbers and dots in analysis
    explicit_ans_map = dict(re.findall(r'(\d+)\s*[．\.]\s*([A-G])(?:\s*[．\.]|\s|$)', analysis_text))
    sequential_answers = re.findall(r'^\s*([A-G])\s*[．\.]', analysis_text, re.MULTILINE)

    # Define the robust pattern to capture question blocks.
    # It looks for a question ID (e.g., "28.") and captures everything until the next question ID or end of text.
    # This is more robust than trying to capture options within the main block regex.
    question_block_pattern = re.compile(
        r'(\d+)\s*[\.\)]\s*(.*?)(?=\n*\d+\s*[\.\)]\s*|\Z)',  # Group 1: QID, Group 2: rest of the block
        re.DOTALL
    )

    seq_ans_idx = 0
    # Iterate through the q_text to find all question blocks
    for block_match in question_block_pattern.finditer(q_text):
        q_id_from_text = (block_match.group(1) or "").strip()
        block_content = (block_match.group(2) or "").strip()

        question_stem = ""
        options = {}

        # Parse options from the block_content
        options_pattern = r'([A-D])\s*[\.\)]\s*(.*?)(?=\n*[A-D]\s*[\.\)]\s*|\Z)'
        options_found = list(re.finditer(options_pattern, block_content, re.DOTALL))
        
        if options_found:
            first_option_start_pos = options_found[0].start()
            question_stem = block_content[:first_option_start_pos].strip()
            
            for opt_match in options_found:
                label = opt_match.group(1).upper()
                content = (opt_match.group(2) or "").strip()
                options[label] = content
        else:
            question_stem = block_content # If no options found, the whole block is the stem

        # Only add if options are successfully parsed (for multiple choice questions)
        if options:
            # Try to get answer from explicit map first, then sequential answers
            answer = explicit_ans_map.get(q_id_from_text, "")
            if not answer and seq_ans_idx < len(sequential_answers):
                answer = sequential_answers[seq_ans_idx]
                seq_ans_idx += 1

            items.append({
                "q_id": q_id_from_text, # Use the q_id extracted from the block
                "answer": answer,
                "content": question_stem,
                "options": options
            })
        else:
            # If no options are found, it might be a malformed question or a different type
            # For reading comprehension, we expect options. Log a warning.
            print(f"DEBUG:   No options parsed for Q{q_id_from_text}. Item not added as reading comprehension.")

    print(f"DEBUG: _parse_reading_items_full_exam returning {len(items)} items.")
    return items

def _parse_cloze_items_full_exam(options_text, analysis_text):
    """
    【全真战场专用】解析完形填空题目的具体逻辑。
    """
    """
    Parses cloze items for the full exam.
    Optimized for robust item and answer extraction.
    """ # The analysis_text is already normalized to half-width in main.py
    items = []
    explicit_ans_map = dict(re.findall(r'(\d+)\s*[．\.]\s*([A-D])(?:\s*[．\.]|\s|$)', analysis_text))
    sequential_answers = re.findall(r'^\s*([A-D])\s*[．\.]', analysis_text, re.MULTILINE)

    # Robust pattern to capture QID and all options for cloze tests
    # It looks for: QID. A. OptionA B. OptionB C. OptionC D. OptionD
    # The lookahead ensures it stops before the next QID. A. or end of text
    cloze_pattern = re.compile(
        r'(\d+)\s*[．\.]\s*'  # Question ID (Group 1)
        r'A\s*[．\.]\s*(.*?)\s*'  # Option A content (Group 2)
        r'B\s*[．\.]\s*(.*?)\s*'  # Option B content (Group 3)
        r'C\s*[．\.]\s*(.*?)\s*'  # Option C content (Group 4)
        r'D\s*[．\.]\s*(.*?)\s*'  # Option D content (Group 5)
        r'(?=\n*\d+\s*[．\.]\s*A\s*[．\.]\s*|\Z)', # Lookahead for next question or end of text
        re.DOTALL
    )

    seq_ans_idx = 0
    for m in cloze_pattern.finditer(options_text):
        q_id = (m.group(1) or "").strip()
        
        options_for_q = {
            "A": (m.group(2) or "").strip(),
            "B": (m.group(3) or "").strip(),
            "C": (m.group(4) or "").strip(),
            "D": (m.group(5) or "").strip()
        }

        # Try to get answer from explicit map first, then sequential answers
        answer = explicit_ans_map.get(q_id, "")
        if not answer and seq_ans_idx < len(sequential_answers):
            answer = sequential_answers[seq_ans_idx]
            seq_ans_idx += 1
        
        items.append({"q_id": q_id, "answer": answer, "options": options_for_q})
    print(f"DEBUG: _parse_cloze_items_full_exam returning {len(items)} items.")
    return items

def _parse_seven_five_items_full_exam(options_text, analysis_text, passage):
    """
    【全真战场专用】解析七选五题目的具体逻辑。
    """
    """
    Parses seven-five items for the full exam.
    Optimized for robust item and answer extraction.
    """
    items = []
    explicit_ans_map = dict(re.findall(r'(\d+)\s*\.\s*([A-G])(?:\s*\.|\s|$)', analysis_text))
    sequential_answers = re.findall(r'^\s*([A-G])\s*\.', analysis_text, re.MULTILINE)

    # Extract options from options_text (assuming A-G are listed)
    # options_text is already normalized in main.py before calling this function, so this is redundant.
    options_list = []
    for line in options_text.splitlines(): # options_text should contain the A-G options
        m = re.match(r'^([A-G])\s*\.\s*(.*)', line.strip()) # Robust for full-width/half-width
        if m: options_list.append({"label": m.group(1), "content": (m.group(2) or "").strip()})

    blank_numbers = sorted(set(re.findall(r'(?<!\d)(\d{2})(?!\d)', passage)))
    
    seq_ans_idx = 0
    for q_id in blank_numbers:
        answer = explicit_ans_map.get(q_id, "")
        if not answer and seq_ans_idx < len(sequential_answers):
            answer = sequential_answers[seq_ans_idx]
            seq_ans_idx += 1
        items.append({"q_id": q_id, "answer": answer, "options": options_list})
    print(f"DEBUG: _parse_seven_five_items_full_exam returning {len(items)} items.")
    return items

def _parse_grammar_items_full_exam(q_text, analysis_text):
    """
    【全真战场专用】解析语法填空题目的具体逻辑。
    """
    """
    Parses grammar fill-in-the-blanks items for the full exam.
    Optimized for robust item and answer extraction.
    """
    items = []
    
    # First, try to extract answers from an [OPTIONS] section within q_text
    # q_text is already normalized in main.py before calling this function.
    local_options_match = re.search(r'\[OPTIONS\]\s*(.*)', q_text, re.DOTALL | re.IGNORECASE)
    local_answers_map = {}
    if local_options_match:
        options_section = local_options_match.group(1).strip()
        # Regex to find "N. answer" or "N. answer / answer"
        local_ans_pattern = re.findall(r'(\d+)\s*\.\s*(.*?)(?=\n*\d+\s*\.|\Z)', options_section or "", re.DOTALL)
        for q_id, ans in local_ans_pattern:
            local_answers_map[q_id] = (ans or "").strip()
        # Remove the [OPTIONS] section from q_text for question parsing
        q_text_for_questions = (q_text[:local_options_match.start()] or "").strip()
    else:
        q_text_for_questions = (q_text or "").strip()
    # Fallback to global analysis_text if no local [OPTIONS]
    if not local_answers_map:
        ans_pattern = re.findall(r'(\d+)\s*\.\s*(.*?)(?=\n*\d+\s*\.|\Z)', analysis_text or "", re.DOTALL)
        for q_id, ans in ans_pattern: local_answers_map[q_id] = ans.strip()
    
    question_pattern = re.compile(r'(\d+)\s*\.\s*\((.*?)\)', re.DOTALL) # Robust for full-width/half-width
    
    for match in question_pattern.finditer(q_text_for_questions):
        q_id = (match.group(1) or "").strip()
        content_in_parentheses = (match.group(2) or "").strip()
        
        items.append({
            "q_id": q_id,
            "answer": local_answers_map.get(q_id, ""),
            "content": content_in_parentheses,
            "options": []
        })
    print(f"DEBUG: _parse_grammar_items_full_exam returning {len(items)} items.")
    return items