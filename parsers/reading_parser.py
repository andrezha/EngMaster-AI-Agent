import re
import os

def parse_reading_txt(file_content):
    """
    专门解析 data 目录下的阅读理解 TXT 文件。
    它识别 [PASSAGE] 标签和 --- Q_XX (ANSWER: X) --- 标记。
    """
    # 提取基本信息
    year_match = re.search(r'YEAR:\s*(.*)', file_content)
    cat_match = re.search(r'CAT:\s*(.*)', file_content)
    
    # 提取正文：精准截取 [PASSAGE] 之后到题目分隔符之前
    passage = ""
    if "[PASSAGE]" in file_content:
        # 截取 [PASSAGE] 之后的内容
        after_passage = file_content.split("[PASSAGE]")[1]
        # 截取到第一个题目分隔线 === 之前
        passage = after_passage.split("="*50)[0].strip()

    # 提取题目：只认物理分隔符 "--- Q_"
    # 这能彻底避开 9.80 这种金额干扰
    q_blocks = file_content.split("--- Q_")[1:]
    questions = []
    
    for block in q_blocks:
        # 第一行包含题号和答案，例如 "56 (ANSWER: B) ---"
        lines = block.split("\n")
        header = lines[0]
        
        id_match = re.search(r'(\d+)', header)
        ans_match = re.search(r'ANSWER:\s*([A-D/NA]+)', header)
        
        if id_match:
            # 剩下的部分是题干和选项
            # 去掉第一行 header，并去掉 --- 结尾
            content_body = "\n".join(lines[1:]).strip()
            # 如果结尾还有多余的 ---，清理掉
            content_body = content_body.split("---")[0].strip()
            
            questions.append({
                "q_id": id_match.group(1),
                "answer": ans_match.group(1) if ans_match else "",
                "content": content_body
            })

    return {
        "year": year_match.group(1).strip() if year_match else "",
        "category": cat_match.group(1).strip() if cat_match else "",
        "passage": passage,
        "items": questions
    }