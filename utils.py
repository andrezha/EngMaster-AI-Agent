# RecallLex shared path helpers
import os
import re
import sys

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

def normalize_exam_text(text):
    """
    【专项练习/单词录入专用 - 纯净解析版】
    此函数对应专项练习，不带黑框处理！
    功能：仅做基础全角转半角映射，不执行 re.sub 剔除，不执行 strip()。
    确保练习资源 JSON 的物理位置不发生 1 字节的偏移。
    """
    if text is None:
        return ""

    text = str(text)
    
    # 映射表：数字
    m = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
    }
    for f, h in m.items():
        text = text.replace(f, h)
    
    # 映射表：标点
    text = text.replace('．', '.').replace('【', '[').replace('】', ']').replace('（', '(').replace('）', ')')
    
    # 映射表：英文字母
    for i in range(65, 91): text = text.replace(chr(i + 65248), chr(i))
    for i in range(97, 123): text = text.replace(chr(i + 65248), chr(i))
    
    # 映射表：空格
    text = text.replace('　', ' ')
    
    return text
def get_resource_path(relative_path):
    """
    【首席架构师特供：动态资源溯源函数】
    功能：自动处理开发环境与 PyInstaller 打包环境(MEIPASS)的路径差异。
    """
    if hasattr(sys, '_MEIPASS'):
        # 打包环境：指向临时解压目录
        return os.path.join(sys._MEIPASS, relative_path)

    # 开发环境：指向当前项目根目录
    base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

_ACTIVE_EDITION_ID = "gaokao"


def set_active_edition(edition_id):
    """Select the edition namespace used for writable learning data."""
    global _ACTIVE_EDITION_ID
    normalized = str(edition_id or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]+", normalized):
        raise ValueError(f"Invalid edition id: {edition_id!r}")
    _ACTIVE_EDITION_ID = normalized


def get_writable_data_path(filename):
    """
    [架构师审计版] 确保路径在 Windows (APPDATA) 和 macOS 下均合法
    """
    override_dir = os.environ.get("RECALLLEX_DATA_DIR", "").strip()
    if override_dir:
        data_dir = os.path.abspath(override_dir)
    elif sys.platform == 'darwin':  # macOS 路径
        data_dir = os.path.expanduser("~/Library/Application Support/RecallLex")
    elif sys.platform == 'win32': # Windows 路径
        # 修正：Windows 下 APPDATA 往往是必须的
        data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser("~")), "RecallLex")
    else:
        data_dir = os.path.expanduser("~/.RecallLex")

    # Preserve existing high-school paths; new editions use isolated folders.
    if _ACTIVE_EDITION_ID != "gaokao":
        data_dir = os.path.join(data_dir, "editions", _ACTIVE_EDITION_ID)

    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
            
    return os.path.normpath(os.path.join(data_dir, filename))
