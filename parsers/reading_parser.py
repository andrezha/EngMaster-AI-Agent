import re
import os

def parse_reading_txt(file_content):
    """
    通用解析器：解析 data 目录下所有题型的 TXT 文件。
    支持阅读理解、七选五、完形填空等题型的统一标签格式。
    
    标签格式说明：
    - YEAR: 年份
    - CAT: 卷区/类别
    - [PASSAGE] 正文内容
    - [QUESTIONS] 题目区域
    - [OPTIONS (A-G)] 七选五选项列表
    - [ANSWERS] 答案区域
    - [ANALYSIS] 解析区域
    - 【文章正文】完形填空正文
    - 【选项列表】完形填空选项
    - 【参考答案】完形填空答案
    - 【答案解析】完形填空解析
    """
    result = {
        "year": "",
        "category": "",
        "passage": "",
        "items": [],
        "original_analysis": "",
        "question_type": "unknown"  # 用于区分题型：reading/cloze/seven_five/grammar
    }
    
    # 检测是否为语法填空格式（优先检测）
    # 语法填空的特征：包含"阅读下面材料/短文，在空白处填入适当内容"
    if ("阅读下面材料" in file_content or "阅读下面短文" in file_content) and "空白处填入" in file_content:
        result["question_type"] = "grammar"
        return _parse_grammar(file_content, result)
    
    # 检测是否为完形填空格式
    if "【文章正文】" in file_content:
        result["question_type"] = "cloze"
        return _parse_cloze(file_content, result)
    
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


def _parse_cloze(full_content, result):
    """
    解析完形填空题目
    格式：
    【文章正文】
    ----------------------------------------
    [文章内容]
    
    【选项列表】
    ----------------------------------------
    36. A. breath  B. test  C. seat  D. break
    
    【参考答案】
    ----------------------------------------
    36: C
    
    【答案解析】
    ----------------------------------------
    36．C  考查名词辨析...
    """
    # 1. 提取文章正文：【文章正文】到【选项列表】之间
    passage = ""
    if "【文章正文】" in full_content:
        passage_part = full_content.split("【文章正文】")[1]
        if "【选项列表】" in passage_part:
            passage = passage_part.split("【选项列表】")[0].strip()
        # 去除分隔线
        passage = re.sub(r'-{10,}', '', passage).strip()
    result["passage"] = passage
    
    # 2. 提取选项列表
    options_section = ""
    if "【选项列表】" in full_content:
        options_part = full_content.split("【选项列表】")[1]
        if "【参考答案】" in options_part:
            options_section = options_part.split("【参考答案】")[0].strip()
        else:
            options_section = options_part.strip()
    
    # 3. 提取参考答案
    answers_dict = {}
    if "【参考答案】" in full_content:
        answers_part = full_content.split("【参考答案】")[1]
        if "【答案解析】" in answers_part:
            answers_part = answers_part.split("【答案解析】")[0]
        # 匹配 "36: C" 或 "36：C" 格式
        answer_pattern = re.findall(r'(\d+)\s*[:：]\s*([A-D])', answers_part)
        for q_num, answer in answer_pattern:
            answers_dict[q_num] = answer
    
    # 4. 提取答案解析
    analysis_dict = {}
    if "【答案解析】" in full_content:
        analysis_part = full_content.split("【答案解析】")[1].strip()
        # 按题号分割解析
        # 匹配 "36．" 或 "36." 开头的解析
        analysis_blocks = re.split(r'(?=\d+[．.]\s*[A-D]\s+)', analysis_part)
        for block in analysis_blocks:
            block = block.strip()
            if not block:
                continue
            # 提取题号
            q_match = re.match(r'(\d+)[．.]', block)
            if q_match:
                q_num = q_match.group(1)
                analysis_dict[q_num] = block
    
    # 5. 解析选项
    items = []
    
    # 改进的解析逻辑：使用 findall 直接匹配每个题目的完整内容
    # 匹配格式：题号. A. 选项  B. 选项  C. 选项  D. 选项
    # 关键：D 选项的内容需要精确匹配，不能包含下一个题号的内容
    pattern = re.compile(
        r'(\d+)\.\s*A\.\s*(.*?)\s*B\.\s*(.*?)\s*C\.\s*(.*?)\s*D\.\s*(?:(?=\d+\.\s*A\.)|(?:[^\d]*?)(?:\s*$))',
        re.DOTALL
    )
    
    # 更简单的方法：先找到所有题号位置，然后手动切割
    # 使用正则找到所有 "数字. A." 的位置
    question_starts = []
    for match in re.finditer(r'(\d+)\.\s*A\.', options_section):
        question_starts.append((match.start(), match.group(1)))
    
    # 对每个题目块进行解析
    for i, (start_pos, q_id) in enumerate(question_starts):
        # 确定块的结束位置：下一个题目的开始或字符串末尾
        if i + 1 < len(question_starts):
            end_pos = question_starts[i + 1][0]
        else:
            end_pos = len(options_section)
        
        block = options_section[start_pos:end_pos].strip()
        
        # 提取 A 选项：从 A. 到 B. 之前
        a_match = re.search(r'A\.\s*(.*?)(?=\s*B\.\s)', block)
        opt_a = a_match.group(1).strip() if a_match else ""
        
        # 提取 B 选项：从 B. 到 C. 之前
        b_match = re.search(r'B\.\s*(.*?)(?=\s*C\.\s)', block)
        opt_b = b_match.group(1).strip() if b_match else ""
        
        # 提取 C 选项：从 C. 到 D. 之前
        c_match = re.search(r'C\.\s*(.*?)(?=\s*D\.\s)', block)
        opt_c = c_match.group(1).strip() if c_match else ""
        
        # 提取 D 选项：从 D. 到块末（已经通过切割确保了不会包含下一题）
        d_match = re.search(r'D\.\s*(.*)', block)
        opt_d = d_match.group(1).strip() if d_match else ""
        
        # 数据清洗：去除可能混入的空白字符和多余内容
        opt_a = re.sub(r'\s+', ' ', opt_a).strip()
        opt_b = re.sub(r'\s+', ' ', opt_b).strip()
        opt_c = re.sub(r'\s+', ' ', opt_c).strip()
        opt_d = re.sub(r'\s+', ' ', opt_d).strip()
        
        items.append({
            "q_id": q_id,
            "answer": answers_dict.get(q_id, ""),
            "options": {
                "A": opt_a,
                "B": opt_b,
                "C": opt_c,
                "D": opt_d
            },
            "analysis": analysis_dict.get(q_id, "")
        })
    
    result["items"] = items
    
    # 6. 提取年份和类别（从标题行）
    title_match = re.search(r'完形填空_(\d{4})_（?(.+?)）?', full_content)
    if title_match:
        result["year"] = title_match.group(1).strip()
        result["category"] = title_match.group(2).strip()
    
    # 🎯 7. 提取完整解析文本，用于显示
    if "【答案解析】" in full_content:
        full_analysis = full_content.split("【答案解析】")[1].strip()
        # 去除分隔线
        full_analysis = re.sub(r'-{10,}', '', full_analysis).strip()
        result["original_analysis"] = full_analysis
    
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


def _parse_grammar(full_content, result):
    """
    解析语法填空题目
    格式：
    语法填空_2014_（新课标Ⅰ）
    【文章正文】
    ----------------------------------------
    阅读下面材料，在空白处填入适当的内容（不多于 3个单词）或括号内单词的正确形式。
    [文章内容，包含括号提示词如 61 (be)]
    
    【参考答案】
    ----------------------------------------
    61: was, 62: actually, 63: the, ...
    
    【答案解析】
    ----------------------------------------
    61．was 考查动词过去时态和主谓一致...
    """
    # 0. 先提取年份和类别（从标题行）- 放在最前面
    # 匹配 "语法填空_2014_（新课标Ⅰ）" 或 "语法填空_2014_新课标Ⅰ"（无括号）
    # 先尝试匹配带括号的格式
    title_match = re.search(r'语法填空_(\d{4})_[（\(](.+?)[）\)]', full_content)
    if not title_match:
        # 如果没有括号，尝试匹配无括号格式
        title_match = re.search(r'语法填空_(\d{4})_(.+)', full_content)
    if title_match:
        result["year"] = title_match.group(1).strip()
        result["category"] = title_match.group(2).strip()
    
    # 1. 提取文章正文
    passage = ""
    if "【文章正文】" in full_content:
        passage_part = full_content.split("【文章正文】")[1]
        if "【参考答案】" in passage_part:
            passage = passage_part.split("【参考答案】")[0].strip()
        # 去除分隔线
        passage = re.sub(r'-{10,}', '', passage).strip()
    result["passage"] = passage
    
    # 2. 提取参考答案
    answers_dict = {}
    if "【参考答案】" in full_content:
        answers_part = full_content.split("【参考答案】")[1]
        if "【答案解析】" in answers_part:
            answers_part = answers_part.split("【答案解析】")[0]
        
        # 🎯 关键修复：处理答案格式错乱的问题
        # 有些文件的答案格式非常混乱，如 "61: 【答案】61. educated, 62: 62. development..."
        # 需要提取真实的答案
        
        # 先尝试匹配标准格式 "61: was" 或 "61: which/that"
        answer_pattern = re.findall(r'(\d+)\s*:\s*([^,}]+)', answers_part)
        
        # 检查是否是错位格式（第一个答案是"【解答】"或其他非标准格式）
        if answer_pattern:
            first_answer = answer_pattern[0][1].strip()
            if '【解答】' in first_answer or '【答案】' in first_answer or not re.search(r'[a-zA-Z]', first_answer):
                # 这是错位格式，需要从答案内容中提取真实的题号和答案
                # 格式如 "61: 【答案】61. educated" -> 真实题号是61，答案是educated
                for q_num, answer in answer_pattern:
                    # 从答案内容中提取真实题号，如 "61．educated" -> 61
                    real_match = re.match(r'[【\(]?(?:答案)?[】\)]?\s*(\d+)[．.]\s*([a-zA-Z/]+)', answer.strip())
                    if real_match:
                        real_q_num = real_match.group(1)
                        real_answer = real_match.group(2).strip()
                        answers_dict[real_q_num] = real_answer
            else:
                # 标准格式，直接使用
                for q_num, answer in answer_pattern:
                    # 清理答案，去除题号前缀（如果有的话）
                    clean_answer = re.sub(r'^\d+[．.]\s*', '', answer.strip())
                    answers_dict[q_num] = clean_answer
        
        # 🎯 额外修复：如果答案数量不足10个，尝试从解析中提取
        if len(answers_dict) < 10:
            # 从解析中提取题号和答案
            if full_analysis:
                analysis_pattern = re.findall(r'【(\d+)题详解】.*?故[填应]([^。]+)', full_analysis, re.DOTALL)
                for q_num, answer in analysis_pattern:
                    if q_num not in answers_dict:
                        answers_dict[q_num] = answer.strip()
    
    # 3. 提取完整解析文本
    full_analysis = ""
    if "【答案解析】" in full_content:
        full_analysis = full_content.split("【答案解析】")[1].strip()
    
    # 保存完整解析到 result
    result["original_analysis"] = full_analysis
    
    # 按题号分割解析，构建字典
    analysis_dict = {}
    if full_analysis:
        # 按题号分割解析，匹配 "61．" 或 "61." 开头的解析
        # 先去除分隔线
        clean_analysis = re.sub(r'-{10,}', '\n', full_analysis).strip()
        # 使用正则查找所有题号开头的解析块
        # 匹配格式：换行或开头 + 数字+全角点/半角点+空格+内容
        analysis_pattern = re.findall(r'(?:^|\n)\s*(\d+)[．.]\s*(.*?)(?=(?:\n\s*)?\d+[．.]\s|$)', clean_analysis, re.DOTALL)
        for q_num, block_content in analysis_pattern:
            analysis_dict[q_num] = f"{q_num}．{block_content}".strip()
    
    # 4. 从答案中提取题号（语法填空的题号通常是61-70或41-50）
    # 只使用答案中存在的题号，避免匹配到文章中的年份等数字
    blank_numbers = sorted(answers_dict.keys())
    
    # 5. 创建题目项
    items = []
    for q_id in blank_numbers:
        items.append({
            "q_id": q_id,
            "answer": answers_dict.get(q_id, ""),
            "analysis": analysis_dict.get(q_id, "")
        })
    
    result["items"] = items
    
    return result


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