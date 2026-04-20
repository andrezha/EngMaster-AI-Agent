import re

def parse_reading_txt(file_content):
    """
    解析单个试卷 TXT 文件的内容，提取基础信息、文章、题目、选项、答案和解析。
    """
    """
    【HSE-AI 工业级解析器】
    解决：阅读理解题目抓取不全、只显示一题的问题。
    """
    result = {
        "year": "", "category": "", "passage": "",
        "items": [], "original_analysis": "", "question_type": "unknown"
    }

    # 1. 基础信息提取
    year_match = re.search(r'YEAR:\s*(.*)', file_content)
    cat_match = re.search(r'CAT:\s*(.*)', file_content)
    result["year"] = year_match.group(1).strip() if year_match else ""
    result["category"] = cat_match.group(1).strip() if cat_match else ""

    # 2. 定位锚点
    pos_title = file_content.find("TITLE:")
    pos_q_tag = re.search(r'\[(?:OPTIONS|QUESTIONS)\]', file_content)
    pos_analysis = file_content.find("[ANALYSIS]")

    # 3. 提取正文
    if pos_title != -1 and pos_q_tag:
        result["passage"] = file_content[pos_title+6:pos_q_tag.start()].strip()
    
    # 4. 提取解析
    if pos_analysis != -1:
        result["original_analysis"] = file_content[pos_analysis + 10:].strip()

    # 5. 提取题目并判定题型
    if pos_q_tag:
        end_pos = pos_analysis if pos_analysis != -1 else len(file_content)
        q_section = file_content[pos_q_tag.end():end_pos].strip()
        
        # 判定逻辑
        if "语法填空" in result["category"]:
            result["question_type"] = "grammar"
            result["items"] = _parse_grammar_items(q_section, result["original_analysis"]) # Pass q_section for grammar
            print(f"DEBUG: parse_reading_txt calling _parse_grammar_items with q_section (len {len(q_section)}) and analysis (len {len(result['original_analysis'])})")
        elif re.search(r'\d+\.\s*A\.', q_section) and "阅读" not in result["category"]:
            result["question_type"] = "cloze"
            result["items"] = _parse_cloze_items(q_section, result["original_analysis"])
        else:
            if "七选五" in result["category"]:
                result["question_type"] = "seven_five"
                print(f"DEBUG: parse_reading_txt calling _parse_seven_five_items with q_section (len {len(q_section)}), analysis (len {len(result['original_analysis'])}) and passage (len {len(result['passage'])})")
                result["items"] = _parse_seven_five_items(q_section, result["original_analysis"], result["passage"])
            else:
                result["question_type"] = "reading"
                # 【关键点】：传入解析文本，方便提取答案
                print(f"DEBUG: parse_reading_txt calling _parse_reading_items with q_section (len {len(q_section)}) and analysis (len {len(result['original_analysis'])})")
                result["items"] = _parse_reading_items(q_section, result["original_analysis"])

    return result

def _parse_reading_items(q_text, analysis_text):
    """
    解析阅读理解题目的具体逻辑。
    从 q_text 中提取题干和选项，从 analysis_text 中匹配答案。
    """
    print(f"DEBUG: _parse_reading_items received q_text (len {len(q_text)}): {q_text[:200]}...")
    print(f"DEBUG: _parse_reading_items received analysis_text (len {len(analysis_text)}): {analysis_text[:200]}...")
    items = [] # Initialize items list
    # 1. 预先抓取答案映射 (例如 56: B, 57: C)
    explicit_ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-G])(?:\s*[\.\)]|\s|$)', analysis_text))
    sequential_answers = re.findall(r'^\s*([A-G])\s*[\.\)]', analysis_text, re.MULTILINE) # 提取按顺序的答案 (from global analysis)

    # 2. 物理分割题目：使用 finditer 查找所有题目块
    # 题目块以数字+点开头，捕获到下一个题目块或文本结束
    question_blocks_matches = re.finditer(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n*\d+\s*[\.\)]\s*|\Z)', q_text, re.DOTALL)
    
    seq_ans_idx = 0
    q_count = 0
    regex_pattern_for_blocks = r'(\d+)\s*[\.\)]\s*(.*?)(?=\n*\d+\s*[\.\)]\s*|\Z)' # Define the regex pattern
    print(f"DEBUG: _parse_reading_items q_text (len {len(q_text)}): {q_text[:500]}...") # More q_text debug
    print(f"DEBUG: _parse_reading_items question_blocks_matches (pattern: {regex_pattern_for_blocks!r}): {list(re.finditer(regex_pattern_for_blocks, q_text, re.DOTALL))}")
    for match in question_blocks_matches:
        q_id = match.group(1).strip()
        block_content = match.group(2).strip()
        
        question_stem = ""
        options = {}
        print(f"DEBUG: _parse_reading_items processing Q{q_id}, block_content (len {len(block_content)}): {block_content[:500]}...") # Debug block_content
        
        # 提取选项 A-D
        options_pattern = r'([A-D])\s*[\.\)]\s*(.*?)(?=\n*[A-D]\s*[\.\)]\s*|\Z)'
        options_found = list(re.finditer(options_pattern, block_content, re.DOTALL))
        
        if options_found:
            first_option_start_pos = options_found[0].start()
            question_stem = block_content[:first_option_start_pos].strip()
            
            for opt_match in options_found:
                label = opt_match.group(1).upper()
                content = opt_match.group(2).strip()
                options[label] = content
            print(f"DEBUG: _parse_reading_items for Q{q_id} found options: {options}")
        else:
            question_stem = block_content

        # 只有在抓到选项的情况下才认为是一道题
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

    print(f"DEBUG: _parse_reading_items returning {len(items)} items.")
    return items

def _parse_cloze_items(options_text, analysis_text):
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
    print(f"DEBUG: _parse_cloze_items returning {len(items)} items.")
    return items

def _parse_seven_five_items(options_text, analysis_text, passage):
    print(f"DEBUG: _parse_seven_five_items received options_text (len {len(options_text)}): {options_text[:200]}...")
    print(f"DEBUG: _parse_seven_five_items received analysis_text (len {len(analysis_text)}): {analysis_text[:200]}...")
    print(f"DEBUG: _parse_seven_five_items received passage (len {len(passage)}): {passage[:200]}...")
    """
    解析七选五题目的具体逻辑。
    从 options_text 中提取选项列表，从 passage 中提取空白题号，从 analysis_text 中匹配答案。
    """
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
    print(f"DEBUG: _parse_seven_five_items returning {len(items)} items.")
    return items

def _parse_grammar_items(q_text, analysis_text):
    # In this context, q_text contains "QID. (word)" format.
    """
    解析语法填空题目的具体逻辑。
    从 passage_text 中提取题目内容（带括号的词），从 analysis_text 中匹配答案。
    """
    items = []
    answers_map = {}
    
    # 语法填空答案匹配：匹配任意位数的题号，点/括号，然后捕获答案直到下一个句号、"考查"、"[" 或行尾
    ans_pattern = re.findall(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n\d+\s*[\.\)]|\Z)', analysis_text, re.DOTALL) # QID. Answer phrase
    for q_id, ans in ans_pattern: answers_map[q_id] = ans.strip()
    
    # Parse questions from q_text (e.g., "56. (origin)")
    question_pattern = re.compile(r'(\d+)\s*[\.\)]\s*\((.*?)\)', re.DOTALL)
    
    for match in question_pattern.finditer(q_text):
        q_id = match.group(1).strip()
        content_in_parentheses = match.group(2).strip() # e.g., "origin"
        
        items.append({
            "q_id": q_id,
            "answer": answers_map.get(q_id, ""), # Get answer from the map
            "content": content_in_parentheses, # The word in parentheses is the content
            "options": [] # Grammar fill-in-the-blanks have no options
        })
    print(f"DEBUG: _parse_grammar_items returning {len(items)} items.")
    return items