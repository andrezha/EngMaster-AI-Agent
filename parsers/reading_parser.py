import re
from utils import normalize_exam_text

def parse_reading_txt(file_content):
    """
    专项练习解析器：确保数据完整，杜绝 None 值。
    """
    # 统一使用针对练习的纯净版清洗
    file_content = normalize_exam_text(file_content)

    result = {
        "year": "", "category": "", "passage": "",
        "items": [], "original_analysis": "", "question_type": "unknown"
    }

    # 1. 提取基础信息
    year_match = re.search(r'YEAR:\s*(.*)', file_content)
    cat_match = re.search(r'CAT:\s*(.*)', file_content)
    result["year"] = str(year_match.group(1)).strip() if year_match else ""
    result["category"] = str(cat_match.group(1)).strip() if cat_match else ""

    # 2. 定位锚点
    pos_q_tag = re.search(r'\[(?:OPTIONS|QUESTIONS)\]', file_content)
    pos_analysis = file_content.find("[ANALYSIS]")

    # 3. 提取文章正文
    pos_title = file_content.find("TITLE:")
    if pos_title != -1 and pos_q_tag:
        result["passage"] = file_content[pos_title+6:pos_q_tag.start()].strip()

    # 4. 提取解析原文
    if pos_analysis != -1:
        result["original_analysis"] = file_content[pos_analysis + 10:].strip()

    # 5. 分题型解析题目
    if pos_q_tag:
        end_pos = pos_analysis if pos_analysis != -1 else len(file_content)
        q_section = file_content[pos_q_tag.end():end_pos].strip()

        category = result["category"]
        if "语法填空" in category:
            result["question_type"] = "grammar"
            result["items"] = _parse_grammar_items(q_section, result["original_analysis"])
        elif "完形填空" in category or (re.search(r'\d+[\.\)]\s*A[\.\)]', q_section) and "阅读" not in category):
            result["question_type"] = "cloze"
            result["items"] = _parse_cloze_items(q_section, result["original_analysis"])
        elif "七选五" in category:
            result["question_type"] = "seven_five"
            result["items"] = _parse_seven_five_items(q_section, result["original_analysis"], result["passage"])
        else:
            result["question_type"] = "reading"
            result["items"] = _parse_reading_items(q_section, result["original_analysis"])

    return result

def _parse_reading_items(q_text, analysis_text):
    items = []
    # 预抓取答案映射 (如 28. B)
    ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-G])(?:\s|[\.\)]|$)', analysis_text))
    sequential_answers = re.findall(r'^\s*([A-G])\s*[\.\)]', analysis_text, re.MULTILINE)

    seq_ans_idx = 0
    regex_pattern = r'(\d+)\s*[\.\)]\s*(.*?)(?=\s*\d+\s*[\.\)]\s*|\Z)'
    for match in re.finditer(regex_pattern, q_text, re.DOTALL):
        qid = str(match.group(1)).strip()
        block_content = match.group(2).strip()
        
        # 提取选项 A-D (适配 A. 或 A))
        opts_found = list(re.finditer(r'([A-D])[\.\)]\s*(.*?)(?=\s*[A-D][\.\)]|\Z)', block_content, re.DOTALL))

        options = {}
        stem = block_content
        if opts_found:
            stem = block_content[:opts_found[0].start()].strip()
            for m in opts_found:
                options[m.group(1).upper()] = m.group(2).strip()

        ans = ans_map.get(qid, "")
        if not ans and seq_ans_idx < len(sequential_answers):
            ans = sequential_answers[seq_ans_idx]
            seq_ans_idx += 1

        items.append({
            "q_id": qid,
            "answer": str(ans) if ans else "",
            "content": stem if stem else "根据文章内容选择正确选项",
            "options": options
        })
    return items

def _parse_cloze_items(q_text, analysis_text):
    items = []
    ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-D])(?:\s|[\.\)]|$)', analysis_text))
    # 适配完形填空格式，支持带点或不带点
    pattern = re.finditer(r'(\d+)\s*[\.\)]\s*A[\.\)]\s*(.*?)\s*B[\.\)]\s*(.*?)\s*C[\.\)]\s*(.*?)\s*D[\.\)]\s*(.*?)(?=\d+\s*[\.\)]\s*A[\.\)]|\Z)', q_text, re.DOTALL)
    for m in pattern:
        qid = str(m.group(1))
        items.append({
            "q_id": qid,
            "content": "请选择最符合语境的选项",
            "answer": str(ans_map.get(qid, "")),
            "options": {"A": m.group(2).strip(), "B": m.group(3).strip(), "C": m.group(4).strip(), "D": m.group(5).strip()}
        })
    return items

def _parse_seven_five_items(q_text, analysis_text, passage):
    items = []
    options_dict = {}
    for line in q_text.splitlines():
        m = re.match(r'^([A-G])\s*[\.\)]\s*(.*)', line.strip())
        if m: options_dict[m.group(1)] = m.group(2).strip()
    
    ans_map = dict(re.findall(r'(\d+)\s*[\.\)]\s*([A-G])(?:\s|[\.\)]|$)', analysis_text))
    blank_ids = sorted(set(re.findall(r'\b\d{2}\b', passage)))
    
    for qid in blank_ids:
        qid_str = str(qid)
        items.append({
            "q_id": qid_str,
            "content": "请选择填入此处最合适的句子",
            "answer": str(ans_map.get(qid_str, "")),
            "options": options_dict
        })
    return items

def _parse_grammar_items(q_text, analysis_text):
    items = []
    ans_map = {}
    # 提取详解原文中的第一个核心词
    ans_matches = re.findall(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n\d+\s*[\.\)]|\Z)', analysis_text, re.DOTALL)
    for qid, val in ans_matches:
        ans_map[str(qid)] = str(val).split('.')[0].split(' ')[0].strip()

    for m in re.finditer(r'(\d+)\s*[\.\)]\s*(.*?)(?=\n*\d+\s*[\.\)]\s*|\Z)', q_text, re.DOTALL):
        qid = str(m.group(1)).strip()
        items.append({
            "q_id": qid,
            "content": m.group(2).strip() if m.group(2) else "请写出括号内单词的正确形式",
            "answer": str(ans_map.get(qid, "")),
            "options": {}
        })
    return items
