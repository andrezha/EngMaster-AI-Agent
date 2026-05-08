# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/utils.py
import re

def _normalize_full_width_to_half_width(text):
    """
    严格保持 PO 原始函数名 (带下划线)。
    功能：全角转半角 + 彻底剔除 Unicode 私有区导致的音标黑框。
    """
    if text is None:
        return ""

    text = str(text)
    
    # 核心修复：剔除导致黑框的非法字符 (PUA区域 \uE000-\uF8FF)
    text = re.sub(r'[\uE000-\uF8FF]', '', text)
    
    # 全角数字映射
    full_to_half_digits = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
    }
    for full, half in full_to_half_digits.items():
        text = text.replace(full, half)
    
    # 常用全角标点映射
    replacements = {
        '．': '.', '【': '[', '】': ']', '（': '(', '）': ')', '　': ' '
    }
    for full, half in replacements.items():
        text = text.replace(full, half)
    
    # 全角英文字母映射
    for i in range(65, 91):  # A-Z
        text = text.replace(chr(i + 65248), chr(i))
    for i in range(97, 123): # a-z
        text = text.replace(chr(i + 65248), chr(i))
    
    return text.strip()