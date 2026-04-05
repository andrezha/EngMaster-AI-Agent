import sys
import os

# Add the current directory to sys.path to allow importing parsers
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from parsers.reading_parser import parse_reading_txt

file_path = "data/阅读理解/2015_47.txt"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except FileNotFoundError:
    print(f"File not found: {file_path}")
    sys.exit(1)

parsed_data = parse_reading_txt(content)

print(f"[TARGET_FILE] {os.path.basename(file_path)}")
print("-" * 40)

for item in parsed_data.get('items', []):
    raw_content = item.get('content', '')
    q_id = item.get('q_id', item.get('id', ''))
    
    print(f"[RAW_CONTENT] {repr(raw_content)}")
    
    clean_content = raw_content.replace('．', '.')
    
    posA = clean_content.find("A.")
    posB = clean_content.find("B.")
    posC = clean_content.find("C.")
    posD = clean_content.find("D.")
    
    print(f"[POSITIONS] A:{posA}, B:{posB}, C:{posC}, D:{posD}")
    
    q_text = ""
    options = []
    
    if posA != -1 and posB != -1 and posC != -1 and posD != -1 and posA < posB < posC < posD:
        q_text = clean_content[:posA].strip()
        optA = clean_content[posA:posB].strip()
        optB = clean_content[posB:posC].strip()
        optC = clean_content[posC:posD].strip()
        optD = clean_content[posD:].strip()
        options = [optA, optB, optC, optD]
    else:
        q_text = clean_content.strip()
        options = []
        
    print(f"[SPLIT_RESULT] q_text: {q_text}")
    print(f"[SPLIT_RESULT] options: {options}")
    print("-" * 40)
