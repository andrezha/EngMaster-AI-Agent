import os
import re
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL

# --- Configuration ---
# 输入的纯文本单词表文件，假设它在当前脚本的同级目录
INPUT_TXT_FILE = "HSE_Vocabulary_常规词汇_英文+中文_20260504.txt"
# 输出的 Word 文档文件，将在当前脚本的同级目录生成
OUTPUT_DOCX_FILE = "Vocabulary_A4_Table.docx"

# 中文释义的最大显示长度，过长会被截断，也用于计算默写区域的长度
MAX_CONTENT_LENGTH = 35 
# 默写区域额外增加的下划线字符数，提供更多书写空间
BLANK_BUFFER_CHARS = 5 
# 默写区域使用的下划线字符
BLANK_CHAR = " " # 将下划线字符改为一个空格

# Word 文档字体设置
FONT_NAME = "Microsoft YaHei" # 推荐使用支持中文的字体，如微软雅黑
FONT_SIZE_VISIBLE = 10 # 可见内容的字体大小 (Pt)
FONT_SIZE_BLANK = 10   # 默写区域下划线的字体大小 (Pt)

# Word 表格行高设置 (厘米)
ROW_HEIGHT_CM = 0.8 

# --- Helper to parse the text table ---
def parse_txt_table(file_path):
    """
    从纯文本表格文件中解析单词数据。
    文件格式预期为 text_table_generator.py 生成的 "英文+中文" 模式。
    """
    words_data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 过滤掉边框线和表头线，只保留数据行
        # 数据行以 '|' 开头，且不是表头（表头是第一行数据行）
        data_lines = [line for line in lines if line.strip().startswith('|') and not line.strip().startswith('+')]
        
        if len(data_lines) > 1:
            data_lines = data_lines[1:] # 跳过表头行
        else:
            print(f"⚠️ 警告: 文件 '{file_path}' 中没有找到有效的数据行。")
            return []

        for line in data_lines:
            parts = line.split('|')
            # 预期格式: ['', ' word ', ' content ', '']
            if len(parts) >= 4: 
                word = parts[1].strip()
                content = parts[2].strip()
                if word and content:
                    words_data.append({"word": word, "content": content})
    except FileNotFoundError:
        print(f"❌ 错误: 文件 '{file_path}' 未找到。")
    except Exception as e:
        print(f"❌ 读取或解析文件 '{file_path}' 时发生错误: {e}")
    return words_data

# --- Main function to create Word document ---
def create_dictation_document(data, output_file, mode="en_dictate_cn"):
    """
    生成 Word 文档，包含默写表格。

    Args:
        data (list): 包含 {"word": "...", "content": "..."} 字典的列表。
        output_file (str): 输出的 .docx 文件路径。
        mode (str): 默写模式。
                    "en_dictate_cn": 左侧英文，右侧默写中文。
                    "cn_dictate_en": 左侧中文，右侧默写英文。
    """
    document = Document()

    # 设置 A4 页面大小和页边距
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)

    # 定义列标题和数据键，根据默写模式
    if mode == "en_dictate_cn":
        col_headers = ["英文单词", "中文默写", "英文单词", "中文默写"]
        visible_col_key = "word"
        blank_col_key = "content"
    elif mode == "cn_dictate_en":
        col_headers = ["中文释义", "英文默写", "中文释义", "英文默写"]
        visible_col_key = "content"
        blank_col_key = "word"
    else:
        raise ValueError("无效的默写模式。请使用 'en_dictate_cn' 或 'cn_dictate_en'。")

    # 计算列宽 (厘米)
    # A4 可用宽度约 15.92 cm (21 - 2.54*2)
    # 我们创建 4 列的 Word 表格，每两列构成一个单词条目。
    # 目标是每对 (可见内容 + 默写区) 占用约 7.5 cm，总共 15 cm。
    visible_col_width_cm = 3.5 # 可见内容列的宽度
    blank_col_width_cm = 4.0   # 默写区域列的宽度
    
    col_widths_cm = [Cm(visible_col_width_cm), Cm(blank_col_width_cm), Cm(visible_col_width_cm), Cm(blank_col_width_cm)]
    
    table = document.add_table(rows=1, cols=4)
    table.autofit = False # 禁用自动调整，手动控制列宽
    table.allow_autofit = False
    
    # 设置表格列宽
    for i, width_cm in enumerate(col_widths_cm):
        table.columns[i].width = width_cm

    # 表头行
    hdr_cells = table.rows[0].cells
    for i, header_text in enumerate(col_headers):
        paragraph = hdr_cells[i].paragraphs[0]
        run = paragraph.add_run(header_text)
        run.font.name = FONT_NAME
        run.font.size = Pt(FONT_SIZE_VISIBLE)
        run.bold = True
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        
    # 填充数据
    for i in range(0, len(data), 2): # 每循环一次处理两个单词，填充 Word 表格的一行
        row_data = data[i:i+2] # 获取当前行的两个单词数据
        row = table.add_row()
        row.height = Cm(ROW_HEIGHT_CM) # 设置固定行高
        cells = row.cells
        
        for j in range(2): # 遍历当前行的两个单词条目 (左侧和右侧)
            if j < len(row_data):
                item = row_data[j]
                
                # 可见内容
                visible_text = item.get(visible_col_key, "")
                if visible_col_key == "content": # 如果是中文释义，可能需要截断
                    visible_text = visible_text[:MAX_CONTENT_LENGTH]
                
                # 默写区域的下划线长度
                blank_length = 0
                if blank_col_key == "content": # 默写中文
                    # 基于中文释义的实际长度（截断后）加上缓冲
                    blank_length = min(len(item.get(blank_col_key, "")), MAX_CONTENT_LENGTH) + BLANK_BUFFER_CHARS
                elif blank_col_key == "word": # 默写英文
                    # 基于英文单词的实际长度加上缓冲
                    blank_length = len(item.get(blank_col_key, "")) + BLANK_BUFFER_CHARS
                
                blank_text = BLANK_CHAR * blank_length
                
                # 填充 Word 表格的单元格
                # Cell for Visible Content
                p_visible = cells[j*2].paragraphs[0]
                run_visible = p_visible.add_run(visible_text)
                run_visible.font.name = FONT_NAME
                run_visible.font.size = Pt(FONT_SIZE_VISIBLE)
                p_visible.alignment = WD_ALIGN_PARAGRAPH.LEFT
                cells[j*2].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

                # Cell for Blank Dictation Area
                p_blank = cells[j*2 + 1].paragraphs[0]
                run_blank = p_blank.add_run(blank_text)
                run_blank.font.name = FONT_NAME
                run_blank.font.size = Pt(FONT_SIZE_BLANK)
                p_blank.alignment = WD_ALIGN_PARAGRAPH.LEFT
                cells[j*2 + 1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            else:
                # 如果数据不足以填充第二个单词条目，则填充空单元格
                cells[j*2].paragraphs[0].add_run("")
                cells[j*2 + 1].paragraphs[0].add_run("")

    document.save(output_file)
    print(f"✅ Word默写表格已生成: {output_file}")

# --- Main execution ---
if __name__ == "__main__":
    # 获取当前脚本所在的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file_path = os.path.join(script_dir, INPUT_TXT_FILE)
    output_file_path = os.path.join(script_dir, OUTPUT_DOCX_FILE)

    if not os.path.exists(input_file_path):
        print(f"❌ 错误: 输入文件 '{input_file_path}' 不存在。请确保文件已生成。")
    else:
        print(f"🔍 正在读取文件: {input_file_path}")
        parsed_data = parse_txt_table(input_file_path)
        
        if not parsed_data:
            print("⚠️ 警告: 未从 TXT 文件中解析到任何单词数据。无法生成 Word 文档。")
        else:
            print(f"✅ 成功解析 {len(parsed_data)} 个单词。")
            
            # 默认生成“英文默写中文”模式的 Word 文档
            print(f"📝 正在生成 Word 默写表格 (英文默写中文模式)...")
            create_dictation_document(parsed_data, output_file_path, mode="en_dictate_cn")
            
            # 如果您还需要生成“中文默写英文”模式，可以取消注释下面两行
            # output_file_cn_dictate_en = os.path.join(script_dir, "Vocabulary_A4_Table_CN_Dictate_EN.docx")
            # create_dictation_document(parsed_data, output_file_cn_dictate_en, mode="cn_dictate_en")