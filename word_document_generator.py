# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/word_document_generator.py
import os
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement # Import OxmlElement
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn

# --- Configuration ---
# 中文释义的最大显示长度，过长会被截断，也用于计算默写区域的长度
MAX_CONTENT_LENGTH = 35 
# 默写区域额外增加的下划线字符数，提供更多书写空间
BLANK_BUFFER_CHARS = 5 
# 默写区域使用的下划线字符
BLANK_CHAR = "_"

# Word 文档字体设置
FONT_NAME = "Microsoft YaHei" # 推荐使用支持中文的字体，如微软雅黑
FONT_SIZE_INDEX = 9    # 序号字体大小 (Pt)
FONT_SIZE_VISIBLE = 10 # 可见内容的字体大小 (Pt)
FONT_SIZE_BLANK = 10   # 默写区域下划线的字体大小 (Pt)

# --- Main function to create Word document ---
def generate_word_table(data, output_file, mode="normal"):
    """
    生成 Word 文档，包含单词表格。

    Args:
        data (list): 包含 {"word": "...", "content": "..."} 字典的列表。
        output_file (str): 输出的 .docx 文件路径。
        mode (str): 导出模式。
                    "normal": 英文+中文显示模式。
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

    is_dictation_mode = False # Initialize is_dictation_mode here
    blank_col_key = "" # Initialize blank_col_key

    # 定义列标题和数据键，根据模式
    if mode == "en_dictate_cn":
        col_headers = ["序号", "英文单词", "中文默写", "序号", "英文单词", "中文默写"]
        visible_col_key = "word"
        blank_col_key = "content"
        is_dictation_mode = True
    elif mode == "cn_dictate_en":
        col_headers = ["序号", "中文释义", "英文默写", "序号", "中文释义", "英文默写"]
        visible_col_key = "content"
        blank_col_key = "word"
        is_dictation_mode = True
    elif mode == "normal": # 英文+中文显示模式
        col_headers = ["序号", "英文单词", "中文释义", "序号", "英文单词", "中文释义"]
        visible_col_key = "word"
        blank_col_key = "content" # 在 normal 模式下，这个键用于显示中文释义
        is_dictation_mode = False # Explicitly set for normal mode
    else:
        raise ValueError("无效的导出模式。请使用 'normal', 'en_dictate_cn' 或 'cn_dictate_en'。")

    # 计算列宽 (厘米)
    # A4 可用宽度约 15.92 cm (21 - 2.54*2)
    # 我们创建 6 列的 Word 表格，每两组 (序号+可见内容+默写/解释) 构成一行。
    # 每半部分可用宽度 = 15.92 cm / 2 = 7.96 cm
    
    # 用户指定宽度 (转换为厘米)
    # 第1列和第4列（序号）：不设固定宽度，采用自适应包裹（Auto-fit/Wrap），宽度仅取决于数字长度，紧贴文字边缘，不留多余空白。
    # 由于 python-docx 在 table.autofit=False 时必须指定宽度，这里设置一个非常小的固定宽度来模拟“紧贴文字边缘”
    INDEX_COL_WIDTH_CM = 0.8 # cm, slightly increased for better readability of index
    WORD_COL_WIDTH_CM = 1.4 * 2.54   # 1.4 英寸 = 3.556 cm
    
    # 解释/默写列宽度 (剩余宽度)
    EXPLANATION_COL_WIDTH_CM = 7.96 - INDEX_COL_WIDTH_CM - WORD_COL_WIDTH_CM # 7.96 - 0.8 - 3.556 = 3.604 cm
    
    col_widths_cm = [
        Cm(INDEX_COL_WIDTH_CM), Cm(WORD_COL_WIDTH_CM), Cm(EXPLANATION_COL_WIDTH_CM),
        Cm(INDEX_COL_WIDTH_CM), Cm(WORD_COL_WIDTH_CM), Cm(EXPLANATION_COL_WIDTH_CM)
    ]
    
    table = document.add_table(rows=1, cols=6) # 更改为 6 列
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
        run._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME) # For Chinese font
        paragraph.paragraph_format.space_before = Pt(0) # 移除段前间距
        paragraph.paragraph_format.space_after = Pt(0)  # 移除段后间距
        run.font.size = Pt(FONT_SIZE_VISIBLE)
        run.bold = True
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        
    # 填充数据
    for i in range(0, len(data), 2): # 每循环一次处理两个单词，填充 Word 表格的一行
        row_data = data[i:i+2] # 获取当前行的两个单词数据
        row = table.add_row() # 移除固定行高设置，让行高自适应
        cells = row.cells
        
        for j in range(2): # 遍历当前行的两个单词条目 (左侧和右侧)
            if j < len(row_data):
                item = row_data[j]
                
                # 序号
                index_text = str(i + j + 1) # 计算当前单词的序号
                p_index = cells[j*3].paragraphs[0] # 第 j*3 列是序号列
                run_index = p_index.add_run(index_text)
                run_index.font.name = FONT_NAME
                run_index._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
                p_index.paragraph_format.space_before = Pt(0)
                p_index.paragraph_format.space_after = Pt(0)
                run_index.font.size = Pt(FONT_SIZE_INDEX)
                p_index.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cells[j*3].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

                # 可见内容 (英文单词或中文释义)
                visible_text = item.get(visible_col_key, "")
                if visible_col_key == "content": # 如果是中文释义，可能需要截断
                    visible_text = visible_text[:MAX_CONTENT_LENGTH]
                
                p_visible = cells[j*3 + 1].paragraphs[0] # 第 j*3 + 1 列是可见内容列
                run_visible = p_visible.add_run(visible_text)
                run_visible.font.name = FONT_NAME
                run_visible._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
                p_visible.paragraph_format.space_before = Pt(0) # 移除段前间距
                p_visible.paragraph_format.space_after = Pt(0)  # 移除段后间距
                run_visible.font.size = Pt(FONT_SIZE_VISIBLE)
                p_visible.alignment = WD_ALIGN_PARAGRAPH.LEFT
                cells[j*3 + 1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

                # 默写区域或中文释义
                blank_length = 0
                second_col_text = ""
                
                if is_dictation_mode: # 默写模式
                    if blank_col_key == "content": # 默写中文
                        max_len_for_blanks = 0
                        for d_item in data: max_len_for_blanks = max(max_len_for_blanks, min(len(d_item.get("content", "")), MAX_CONTENT_LENGTH))
                        blank_length = max_len_for_blanks + BLANK_BUFFER_CHARS
                    elif blank_col_key == "word": # 默写英文 (blanks for word)
                        max_len_for_blanks = 0
                        for d_item in data: max_len_for_blanks = max(max_len_for_blanks, len(d_item.get("word", "")))
                        blank_length = max_len_for_blanks + BLANK_BUFFER_CHARS
                    second_col_text = BLANK_CHAR * blank_length if blank_length > 0 else "" # 确保 blank_length 大于0
                else: # "normal" 模式，显示第二个可见内容 (中文释义)
                    second_col_text = item.get(blank_col_key, "") # blank_col_key 在 normal 模式下实际是 content

                p_blank = cells[j*3 + 2].paragraphs[0] # 第 j*3 + 2 列是默写/解释列
                run_blank = p_blank.add_run(second_col_text)
                run_blank.font.name = FONT_NAME
                run_blank._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
                p_blank.paragraph_format.space_before = Pt(0) # 移除段前间距
                p_blank.paragraph_format.space_after = Pt(0)  # 移除段后间距
                run_blank.font.size = Pt(FONT_SIZE_BLANK if is_dictation_mode else FONT_SIZE_VISIBLE) # 根据模式选择字体大小
                p_blank.alignment = WD_ALIGN_PARAGRAPH.LEFT
                cells[j*3 + 2].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            else:
                # 如果数据不足以填充第二个单词条目，则填充空单元格
                cells[j*3].paragraphs[0].add_run("") # 序号
                cells[j*3 + 1].paragraphs[0].add_run("") # 可见内容
                cells[j*3 + 2].paragraphs[0].add_run("") # 默写/解释

    # 强制所有单元格的实线边框
    for row in table.rows:
        for cell in row.cells:
            tcPr = cell._element.get_or_add_tcPr()
            
            # Get or add the w:tcBorders element
            tcBorders = tcPr.find(qn('w:tcBorders'))
            if tcBorders is None:
                # Create w:tcBorders element using its prefixed tag name string
                tcBorders = OxmlElement('w:tcBorders') 
                tcPr.append(tcBorders)

            # Define border attributes
            border_attrs = {
                'val': 'single',  # 实线
                'sz': '6',        # 0.5 磅 (1/8 pt = 1/2 pt)
                'color': '000000' # 黑色
            }

            # Set each border (top, left, bottom, right)
            for border_name in ('top', 'left', 'bottom', 'right'):
                # Get or add the specific border element (e.g., w:top)
                border_element = tcBorders.find(qn(f'w:{border_name}'))
                if border_element is None:
                    border_element = OxmlElement(f'w:{border_name}') 
                    tcBorders.append(border_element)
                
                # Set attributes on the border element
                for attr_name, attr_value in border_attrs.items():
                    border_element.set(qn(f'w:{attr_name}'), attr_value)
    document.save(output_file)
    print(f"✅ Word默写表格已生成: {output_file}")
