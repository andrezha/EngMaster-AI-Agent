# EngMaster shared path helpers
import json
import os
import re
import shutil
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

def _normalize_legacy(text):
    """
    Legacy normalization function for special practice and self-register vocabulary.
    """
    if text is None:
        return ""
    text = str(text)
    
    full_to_half_digits = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
    }
    for full, half in full_to_half_digits.items():
        text = text.replace(full, half)
    
    text = text.replace('．', '.')
    text = text.replace('【', '[')
    text = text.replace('】', ']')
    text = text.replace('（', '(')
    text = text.replace('）', ')')
    
    full_to_half_letters = {
        'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E',
        'Ｆ': 'F', 'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J',
        'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O',
        'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T',
        'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y',
        'Ｚ': 'Z',
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',
        'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
        'ｋ': 'k', 'ｌ': 'l', 'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o',
        'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r', 'ｓ': 's', 'ｔ': 't',
        'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x', 'ｙ': 'y',
        'ｚ': 'z'
    }
    for full, half in full_to_half_letters.items():
        text = text.replace(full, half)

    text = text.replace('　', ' ')
    
    return text

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

    # 开发环境：指向 EngMaster 项目根目录
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


def get_active_edition():
    return _ACTIVE_EDITION_ID


def import_legacy_data_to_current_app(source_dir, target_dir=None, keep_only_unanswered=False):
    """
    Import data from an older EngMaster installation into the current writable data folder.

    Parameters
    ----------
    source_dir: str
        Folder containing legacy data files such as mistake_words.json.
    target_dir: str | None
        Destination folder. If omitted, the current app data folder is used.
    keep_only_unanswered: bool
        When True, filter mistake_words.json so only entries with correct_count <= 0
        are retained. This is useful when you want to keep only words that have never
        been answered correctly in the old program.
    """
    source_dir = os.path.abspath(source_dir)
    if target_dir is None:
        target_dir = os.path.dirname(get_writable_data_path("mistake_words.json"))
    else:
        target_dir = os.path.abspath(target_dir)

    os.makedirs(target_dir, exist_ok=True)

    summary = {}
    files_to_copy = [
        "mistake_words.json",
        "challenge_round_progress.json",
        "challenge_learning_records.json",
        "user_registered_vocab.json",
    ]

    for filename in files_to_copy:
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)
        if not os.path.exists(source_path):
            summary[filename] = {"status": "skipped", "reason": "source_missing"}
            continue

        if filename == "mistake_words.json" and keep_only_unanswered:
            with open(source_path, "r", encoding="utf-8") as handle:
                raw_records = json.load(handle)

            filtered_records = []
            for record in raw_records or []:
                if not isinstance(record, dict):
                    continue
                try:
                    correct_count = int(record.get("correct_count", 0))
                except (TypeError, ValueError):
                    correct_count = 0
                if correct_count <= 0:
                    filtered_records.append(record)

            with open(target_path, "w", encoding="utf-8") as handle:
                json.dump(filtered_records, handle, ensure_ascii=False, indent=2)

            summary[filename] = {
                "status": "imported",
                "source_count": len(raw_records or []),
                "kept_count": len(filtered_records),
                "filtered_out_count": len(raw_records or []) - len(filtered_records),
            }
        else:
            shutil.copy2(source_path, target_path)
            summary[filename] = {"status": "imported", "path": target_path}

    return summary


def get_writable_data_path(filename):
    """
    [架构师审计版] 确保路径在 Windows (APPDATA) 和 macOS 下均合法
    """
    override_dir = os.environ.get("ENGMASTER_DATA_DIR", "").strip()
    if override_dir:
        data_dir = os.path.abspath(override_dir)
    elif sys.platform == 'darwin':  # macOS 路径
        data_dir = os.path.expanduser("~/Library/Application Support/EngMaster")
    elif sys.platform == 'win32': # Windows 路径
        # 修正：Windows 下 APPDATA 往往是必须的
        data_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser("~")), "EngMaster")
    else:
        data_dir = os.path.expanduser("~/.EngMaster")

    # Preserve existing high-school paths; new editions use isolated folders.
    if _ACTIVE_EDITION_ID != "gaokao":
        data_dir = os.path.join(data_dir, "editions", _ACTIVE_EDITION_ID)

    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
            
    return os.path.normpath(os.path.join(data_dir, filename))
