import re
import os

def parse_reading_txt(file_content):
    """
    通用解析器：解析 data 目录下所有题型的 TXT 文件。
    支持阅读理解、七选五等题型的统一标签格式。
    
    标签格式说明：
    - YEAR: 年份
    - CAT: 卷区/类别
    - [PASSAGE] 正文内容
    - [QUESTIONS] 题目区域
    - [OPTIONS (A-G)] 七选五选项列表
    - [ANSWERS] 答案区域
    - [ANALYSIS] 解析区域
    """
    result = {
        "year": "",
        "category": "",
        "passage": "",
        "items": [],
        "original_analysis": "",
        "question_type": "unknown"  # 用于区分题型：reading/cloze/seven_five
    }
    
    # 提取基本信息
    year_match = re.search(r'YEAR:\s*(.*)', file_content)
    cat_match = re.search(r'CAT:\s*(.*)', file_content)
    
    if year_match:
        result["year"] = year_match.group(1).strip()
    if cat_match:
        result["category"] = cat_match.group(1).strip()
    
    # 提取正文：截取 [PASSAGE] 之后的内容
    passage = ""
    if "[PASSAGE]" in file_content:
        after_passage = file_content.split("[PASSAGE]")[1]
        # 截取到 [QUESTIONS] 或分隔线之前
        if "[QUESTIONS]" in after_passage:
            passage = after_passage.split("[QUESTIONS]")[0].strip()
        else:
            passage = after_passage.split("=" * 30)[0].strip()
    
    result["passage"] = passage
    
    # 提取题目区域（[QUESTIONS] 到 [ANSWERS]/[ANALYSIS] 之间）
    questions_section = ""
    if "[QUESTIONS]" in file_content:
        questions_part = file_content.split("[QUESTIONS]")[1]
        if "[ANSWERS]" in questions_part:
            questions_section = questions_part.split("[ANSWERS]")[0]
        elif "[ANALYSIS]" in questions_part:
            questions_section = questions_part.split("[ANALYSIS]")[0]
        else:
            questions_section = questions_part
    
    # 提取解析区域
    analysis = ""
    if "[ANALYSIS]" in file_content:
        analysis_part = file_content.split("[ANALYSIS]")[1]
        analysis = analysis_part.strip()
    result["original_analysis"] = analysis
    
    # 检测题型并解析题目
    # 检查是否是七选五题型（有 [OPTIONS (A-G)] 标签）
    if "[OPTIONS (A-G)]" in file_content or "[OPTIONS]" in file_content:
        result["question_type"] = "seven_five"
        result["items"] = _parse_seven_five(questions_section, file_content)
    else:
        # 默认按阅读理解格式解析
        result["question_type"] = "reading"
        result["items"] = _parse_reading_questions(questions_section)
    
    return result


def _parse_reading_questions(questions_section):
    """解析阅读理解题目（单选题格式：[Q_XX] (ANS: X)）"""
    questions = []
    
    if not questions_section.strip():
        return questions
    
    # 尝试新格式: [Q_XX] (ANS: X)
    # 使用正则分割题目块
    new_pattern = re.split(r'(?=\[Q_\d+\])', questions_section)
    new_blocks = [b.strip() for b in new_pattern if b.strip() and b.strip().startswith('[Q_')]
    
    if new_blocks:
        for block in new_blocks:
            lines = block.split("\n")
            header = lines[0]
            
            # 提取题号: [Q_24] -> 24
            id_match = re.search(r'\[Q_(\d+)\]', header)
            # 提取答案: (ANS: D) -> D
            ans_match = re.search(r'\(ANS:\s*([A-D/NA]+)\)', header)
            
            if id_match:
                content_body = "\n".join(lines[1:]).strip()
                # 清理末尾的多余分隔线
                content_body = re.split(r'\n\s*={3,}', content_body)[0].strip()
                
                questions.append({
                    "q_id": id_match.group(1),
                    "answer": ans_match.group(1) if ans_match else "",
                    "content": content_body
                })
    else:
        # 回退到旧格式: --- Q_XX (ANSWER: X) ---
        q_blocks = questions_section.split("--- Q_")[1:]
        
        for block in q_blocks:
            lines = block.split("\n")
            header = lines[0]
            
            id_match = re.search(r'(\d+)', header)
            ans_match = re.search(r'ANSWER:\s*([A-D/NA]+)', header)
            
            if id_match:
                content_body = "\n".join(lines[1:]).strip()
                content_body = content_body.split("---")[0].strip()
                
                questions.append({
                    "q_id": id_match.group(1),
                    "answer": ans_match.group(1) if ans_match else "",
                    "content": content_body
                })
    
    return questions


def _parse_seven_five(questions_section, full_content):
    """
    解析七选五题目
    格式：文章中有空白处，提供 A-G 七个选项
    """
    questions = []
    
    # 提取选项列表 [OPTIONS (A-G)]
    options_text = ""
    if "[OPTIONS (A-G)]" in full_content:
        options_part = full_content.split("[OPTIONS (A-G)]")[1]
        # 截取到 [ANSWERS] 或分隔线之前
        if "[ANSWERS]" in options_part:
            options_text = options_part.split("[ANSWERS]")[0].strip()
        elif "[ANALYSIS]" in options_part:
            options_text = options_part.split("[ANALYSIS]")[0].strip()
        else:
            options_text = options_part.split("=" * 30)[0].strip()
    
    # 解析选项
    options_list = []
    for line in options_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 匹配 A. xxx, B. xxx, ... G. xxx
        opt_match = re.match(r'^([A-G])\.\s*(.+)', line)
        if opt_match:
            options_list.append({
                "label": opt_match.group(1),
                "content": opt_match.group(2).strip()
            })
    
    # 提取答案 [ANSWERS]
    answers_dict = {}
    answers_part = ""
    if "[ANSWERS]" in full_content:
        answers_part = full_content.split("[ANSWERS]")[1]
        if "[ANALYSIS]" in answers_part:
            answers_part = answers_part.split("[ANALYSIS]")[0]
        answers_part = answers_part.strip()
        
        # 解析答案格式：空(1): C  空(2): F  空(3): A  空(4): E  空(5): D
        answer_pattern = re.findall(r'空\((\d+)\):\s*([A-G])', answers_part)
        for blank_num, answer in answer_pattern:
            answers_dict[blank_num] = answer
    
    # 如果没有找到答案，尝试其他格式
    if not answers_dict and answers_part:
        # 尝试 71. C, 72. F 格式（包括全角点）
        answer_pattern = re.findall(r'(\d{2})\s*[．.]\s*([A-G])', answers_part)
        for blank_num, answer in answer_pattern:
            answers_dict[blank_num] = answer
    
    # 如果还是没有找到，尝试从解析区域提取
    analysis = ""
    if not answers_dict and "[ANALYSIS]" in full_content:
        analysis_part = full_content.split("[ANALYSIS]")[1]
        analysis = analysis_part.strip()
        # 尝试 71．C, 72．F 格式（从解析中提取）
        answer_pattern = re.findall(r'(\d{2})\s*[．.]\s*([A-G])', analysis)
        for blank_num, answer in answer_pattern:
            if blank_num not in answers_dict:
                answers_dict[blank_num] = answer
    
    # 在文章中查找空白标记（如 71, 72, 73, 74, 75 或 ___36___ 格式）
    passage = full_content.split("[PASSAGE]")[1] if "[PASSAGE]" in full_content else ""
    if "[QUESTIONS]" in passage:
        passage = passage.split("[QUESTIONS]")[0]
    
    # 查找文章中的空白编号 - 支持多种格式
    blank_numbers = []
    
    # 格式1: ___36___ 或 __36__ 或 _36_（带下划线的空白标记）
    underline_matches = re.findall(r'_+(\d{2})_+', passage)
    if underline_matches:
        blank_numbers = underline_matches
    
    # 格式2: 标准两位数字（使用单词边界匹配）
    if not blank_numbers:
        # 使用更宽松的正则，匹配前后为非数字的两位数字
        standard_matches = re.findall(r'(?<!\d)(\d{2})(?!\d)', passage)
        # 过滤掉已经是下划线格式中匹配到的（避免重复）
        blank_numbers = sorted(set(standard_matches))
    
    # 格式3: (1), (2) 等格式
    if not blank_numbers:
        paren_matches = re.findall(r'\((\d+)\)', passage)
        blank_numbers = sorted(set(paren_matches))
    
    # 去重并排序
    blank_numbers = sorted(set(blank_numbers))
    
    # 🔄 关键修复：如果答案使用的是序号 (1,2,3...) 而空白编号是题号 (71,72,73...)
    # 需要建立映射关系
    if answers_dict and blank_numbers:
        # 检查答案键是否是序号格式 (1,2,3...)
        seq_answers = {}
        for k, v in answers_dict.items():
            if k.isdigit():
                seq_answers[int(k)] = v
        
        if seq_answers:
            # 按顺序映射：第1个空白 -> 空(1), 第2个空白 -> 空(2), ...
            mapped_answers = {}
            for i, blank_num in enumerate(blank_numbers):
                seq_key = i + 1
                if seq_key in seq_answers:
                    mapped_answers[blank_num] = seq_answers[seq_key]
            answers_dict = mapped_answers
    
    # 创建题目项
    for i, blank_num in enumerate(blank_numbers):
        q_id = blank_num
        answer = answers_dict.get(blank_num, "")
        
        # 题目内容就是选项列表
        questions.append({
            "q_id": q_id,
            "answer": answer,
            "content": "",  # 内容在 options 字段中
            "options": options_list
        })
    
    return questions