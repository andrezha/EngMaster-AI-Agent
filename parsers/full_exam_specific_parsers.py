import re

# These functions are specifically for parsing full exam sections in main.py.
# They are duplicated from parsers/reading_parser.py to ensure isolation
# and can be independently modified for full exam specific formats if needed.

def _parse_reading_items_full_exam(q_text, analysis_text):
    """
    【全真战场专用】解析阅读理解题目的具体逻辑。
    """
    """
    Parses reading comprehension items for the full exam.
    Optimized for robust item and answer extraction.
    """
    items = []
    explicit_ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-G])(?:\s*[\.\)]|\s|$)', analysis_text))
    sequential_answers = re.findall(r'^\s*([A-G])\s*[\.\)]', analysis_text, re.MULTILINE)

    question_blocks_matches = re.finditer(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n*\d+\s*[\.\)]\s*|\Z)', q_text, re.DOTALL)
    
    seq_ans_idx = 0
    q_count = 0
    for match in question_blocks_matches:
        q_id = match.group(1).strip()
        block_content = match.group(2).strip()
        
        question_stem = ""
        options = {}
        
        options_pattern = r'([A-D])\s*[\.\)]\s*(.*?)(?=\n*[A-D]\s*[\.\)]\s*|\Z)'
        options_found = list(re.finditer(options_pattern, block_content, re.DOTALL))
        
        if options_found:
            first_option_start_pos = options_found[0].start()
            question_stem = block_content[:first_option_start_pos].strip()
            
            for opt_match in options_found:
                label = opt_match.group(1).upper()
                content = opt_match.group(2).strip()
                options[label] = content
        else:
            question_stem = block_content

        if options:
            items.append({
                "q_id": q_id,
                "answer": explicit_ans_map.get(q_id, "") or \
                          (sequential_answers[seq_ans_idx] if seq_ans_idx < len(sequential_answers) else ""),
                "content": question_stem,
                "options": options
            })
            q_count += 1
            if not explicit_ans_map.get(q_id) and seq_ans_idx < len(sequential_answers):
                seq_ans_idx += 1

    print(f"DEBUG: _parse_reading_items_full_exam returning {len(items)} items.")
    return items

def _parse_cloze_items_full_exam(options_text, analysis_text):
    """
    【全真战场专用】解析完形填空题目的具体逻辑。
    """
    """
    Parses cloze items for the full exam.
    Optimized for robust item and answer extraction.
    """
    items = []
    explicit_ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-D])(?:\s*[\.\)]|\s|$)', analysis_text))
    sequential_answers = re.findall(r'^\s*([A-D])\s*[\.\)]', analysis_text, re.MULTILINE)
    pattern = re.finditer(r'(\d+)\.\s*A\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(.*?)(?=\d+\.\s*A\.|$)', options_text, re.S)
    
    seq_ans_idx = 0
    for m in pattern:
        q_id = m.group(1)
        answer = explicit_ans_map.get(q_id, "")
        if not answer and seq_ans_idx < len(sequential_answers):
            answer = sequential_answers[seq_ans_idx]
            seq_ans_idx += 1
        items.append({"q_id": q_id, "answer": answer, "options": {"A": m.group(2).strip(), "B": m.group(3).strip(), "C": m.group(4).strip(), "D": m.group(5).strip()}})
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
    options_list = []
    for line in options_text.splitlines():
        m = re.match(r'^([A-G])\s*[\.\)]\s*(.*)', line.strip())
        if m: options_list.append({"label": m.group(1), "content": m.group(2).strip()})
    
    explicit_ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-G])(?:\s*[\.\)]|\s|$)', analysis_text))
    sequential_answers = re.findall(r'^\s*([A-G])\s*[\.\)]', analysis_text, re.MULTILINE)

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
    answers_map = {}
    ans_pattern = re.findall(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n\d+\s*[\.\)]|\Z)', analysis_text, re.DOTALL)
    for q_id, ans in ans_pattern: answers_map[q_id] = ans.strip()
    
    question_pattern = re.compile(r'(\d+)\s*[\.\)]\s*\((.*?)\)', re.DOTALL)
    
    for match in question_pattern.finditer(q_text):
        q_id = match.group(1).strip()
        content_in_parentheses = match.group(2).strip()
        
        items.append({
            "q_id": q_id,
            "answer": answers_map.get(q_id, ""),
            "content": content_in_parentheses,
            "options": []
        })
    print(f"DEBUG: _parse_grammar_items_full_exam returning {len(items)} items.")
    return items