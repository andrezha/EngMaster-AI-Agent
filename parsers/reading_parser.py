import re

def parse_reading_txt(file_content):
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
            result["items"] = _parse_grammar_items(result["passage"], result["original_analysis"])
        elif re.search(r'\d+\.\s*A\.', q_section) and "阅读" not in result["category"]:
            result["question_type"] = "cloze"
            result["items"] = _parse_cloze_items(q_section, result["original_analysis"])
        else:
            if "七选五" in result["category"]:
                result["question_type"] = "seven_five"
                result["items"] = _parse_seven_five_items(q_section, result["original_analysis"], result["passage"])
            else:
                result["question_type"] = "reading"
                # 【关键点】：传入解析文本，方便提取答案
                result["items"] = _parse_reading_items(q_section, result["original_analysis"])

    return result

def _parse_reading_items(q_text, analysis_text):
    """
    【修复版】物理切割法：确保抓取阅读理解中的所有题目
    """
    items = []
    # 1. 预先抓取答案映射 (例如 56: B, 57: C)
    ans_map = dict(re.findall(r'(\d+)\.\s*([A-G])\.', analysis_text))
    expected_ids = sorted(ans_map.keys(), key=int)
    
    # 2. 物理分割题目：按“数字+点”或者“换行+A.”切割
    # 这种切割方式最稳，能把 56, 57, 58 彻底分开
    raw_blocks = re.split(r'\n(?=\d+\.)|\n(?=[A-Z][a-z\s]+.*?\n[A-D]\.)', q_text)
    
    q_count = 0
    for block in raw_blocks:
        block = block.strip()
        if not block or len(block) < 15: continue # 过滤杂质
        
        # 提取当前块的题号
        id_m = re.match(r'^(\d+)\.', block)
        if id_m:
            q_id = id_m.group(1)
        else:
            # 如果没题号（像你之前的 57, 58），则按顺序匹配解析区的题号
            q_id = expected_ids[q_count] if q_count < len(expected_ids) else f"Ext_{q_count}"

        # 提取选项 A-D
        opt_pattern = re.findall(r'([A-D])\.\s*(.*?)(?=[A-D]\.|$|\n)', block, re.S)
        options = {opt[0]: opt[1].strip() for opt in opt_pattern}
        
        # 提取题干 (去掉选项部分，去掉开头的题号)
        content = re.split(r'[A-D]\.', block)[0].strip()
        content = re.sub(r'^\d+\.\s*', '', content)
        
        # 只有在抓到选项的情况下才认为是一道题
        if options:
            items.append({
                "q_id": q_id,
                "answer": ans_map.get(q_id, ""),
                "content": content,
                "options": options
            })
            q_count += 1
            
    return items

# --- 以下函数保持不变，确保完形/语法/七选五依然正常 ---
def _parse_cloze_items(options_text, analysis_text):
    items = []
    answers = dict(re.findall(r'(\d+)\.\s*([A-D])\.', analysis_text))
    pattern = re.finditer(r'(\d+)\.\s*A\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(.*?)(?=\d+\.\s*A\.|$)', options_text, re.S)
    for m in pattern:
        q_id = m.group(1); items.append({"q_id": q_id, "answer": answers.get(q_id, ""), "options": {"A": m.group(2).strip(), "B": m.group(3).strip(), "C": m.group(4).strip(), "D": m.group(5).strip()}})
    return items

def _parse_seven_five_items(options_text, analysis_text, passage):
    items = []
    options_list = []
    for line in options_text.splitlines():
        m = re.match(r'^([A-G])\.\s*(.*)', line.strip())
        if m: options_list.append({"label": m.group(1), "content": m.group(2).strip()})
    answers = dict(re.findall(r'(\d+)\.\s*([A-G])', analysis_text))
    blank_numbers = sorted(set(re.findall(r'(?<!\d)(\d{2})(?!\d)', passage)))
    for q_id in blank_numbers: items.append({"q_id": q_id, "answer": answers.get(q_id, ""), "options": options_list})
    return items

def _parse_grammar_items(passage_text, analysis_text):
    items = []
    answers_map = {}
    ans_pattern = re.findall(r'(?<!\d)(\d{2})\.\s*([^【\n\s]+)', analysis_text)
    for q_id, ans in ans_pattern: answers_map[q_id] = ans.strip()
    for q_id in sorted(answers_map.keys(), key=int):
        pattern = rf"(?<!\d){q_id}\s*\((.*?)\)"
        match = re.search(pattern, passage_text)
        content_snippet = f"({match.group(1).strip()})" if match else "(填空)"
        items.append({"q_id": q_id, "answer": answers_map.get(q_id, ""), "content": content_snippet, "options": []})
    return items