import sys
import os

# Add the current directory to sys.path to allow importing parsers
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from parsers.reading_parser import parse_reading_txt

file_path = "data/阅读理解/2015_47.txt"

# 尝试打开并读取文件内容
# 如果文件不存在，则打印错误信息并退出
# 否则，将文件内容存储在 'content' 变量中
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print(f"File not found: {file_path}")
    sys.exit(1)

parsed_data = parse_reading_txt(content)

print(f"[TARGET_FILE] {os.path.basename(file_path)}")
print("-" * 40)

# 遍历解析后的题目列表
for item in parsed_data.get('items', []):
    raw_content = item.get('content', '')
    q_id = item.get('q_id', item.get('id', ''))
    
    print(f"[RAW_CONTENT] {repr(raw_content)}")
    
    # 将全角句号替换为半角句号，以便后续正则表达式匹配
    clean_content = raw_content.replace('．', '.')
    
    # 查找选项 A, B, C, D 的起始位置
    posA = clean_content.find("A.")
    posB = clean_content.find("B.")
    posC = clean_content.find("C.")
    posD = clean_content.find("D.")
    
    print(f"[POSITIONS] A:{posA}, B:{posB}, C:{posC}, D:{posD}")
    
    # 初始化题干和选项列表
    q_text = ""
    options = []
    
    # 如果所有选项都找到且顺序正确，则进行切分
    if posA != -1 and posB != -1 and posC != -1 and posD != -1 and posA < posB < posC < posD:
        # 提取题干（A 选项之前的内容）
        q_text = clean_content[:posA].strip()
        # 提取各个选项的内容
        optA = clean_content[posA:posB].strip()
        optB = clean_content[posB:posC].strip()
        optC = clean_content[posC:posD].strip()
        optD = clean_content[posD:].strip()
        options = [optA, optB, optC, optD]
    else:
        # 如果选项不完整或顺序错误，则将整个内容视为题干，选项为空
        q_text = clean_content.strip()
        options = []
        
    print(f"[SPLIT_RESULT] q_text: {q_text}")
    print(f"[SPLIT_RESULT] options: {options}")
    print("-" * 40)
