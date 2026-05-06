# /Users/andrezhao/AI_PJ/HighSchoolEnglishAI/word_document_generator.py
import os
from docx import Document
from docx.shared import Inches, Pt, Cm
import re # 确保导入了 re 模块
from utils import _normalize_full_width_to_half_width # 导入半角转换工具
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
BLANK_CHAR = " " # 将下划线字符改为一个空格

# Word 文档字体设置
FONT_NAME = "Microsoft YaHei" # 推荐使用支持中文的字体，如微软雅黑
FONT_SIZE_INDEX = 9    # 序号字体大小 (Pt)
FONT_SIZE_VISIBLE = 10 # 可见内容的字体大小 (Pt)
FONT_SIZE_BLANK = 10   # 默写区域下划线的字体大小 (Pt)

# --- Helper function to set cell margins ---
def set_cell_margins(cell, top=0, left=0, bottom=0, right=0):
    """
    Sets the margins of a table cell in dxa units (twentieths of a point).
    """
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    
    for margin_name, value in [('top', top), ('left', left), ('bottom', bottom), ('right', right)]:
        margin_element = OxmlElement(f'w:{margin_name}')
        margin_element.set(qn('w:w'), str(value))
        margin_element.set(qn('w:type'), 'dxa')
        tcMar.append(margin_element)
    
    # Remove existing tcMar if any, then append the new one
    existing_tcMar = tcPr.find(qn('w:tcMar'))
    if existing_tcMar is not None:
        tcPr.remove(existing_tcMar)
    tcPr.append(tcMar)


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
        blank_col_key = "content" # 在 normal 模式下，这个键用于显示中文释义，不是默写
        is_dictation_mode = False # Explicitly set for normal mode
    else:
        raise ValueError("无效的导出模式。请使用 'normal', 'en_dictate_cn' 或 'cn_dictate_en'。")

    # 计算列宽 (厘米)
    # A4 可用宽度约 15.92 cm (21 - 2.54*2)
    # 我们创建 6 列的 Word 表格，每三列 (序号+可见内容+默写/解释) 构成一个词条显示块。
    # 每半部分可用宽度 = 15.92 cm / 2 = 7.96 cm

    # 用户指定宽度 (转换为厘米)
    # 第1列和第4列（序号）：为了容纳4位数，并尽可能紧凑
    # 注意：python-docx在table.autofit=False时需要固定宽度。
    # 无法实现像CSS那样完全动态“包裹”内容。
    # 0.4cm 是一个极致压缩的宽度，旨在模拟“一个字符号”的视觉效果。
    # 这意味着两位、三位或四位数字的序号，在Word中很可能会被截断或显示不全。
    # 这是为了严格遵循“不要去计算数字大小，直接固定一个字符号”的指示所做的取舍。
    INDEX_COL_WIDTH_CM = 1.2 # cm, Adjusted to comfortably fit 4 digits (e.g., "9999")

    # 动态计算 WORD_COL_WIDTH_CM
    # 找到所有单词中最长的单词的长度
    max_word_length_chars = 0
    # Refined logic to find the maximum length of "unbreakable" segments
    # This considers spaces, commas, parentheses, and Chinese characters like '或', '是' as soft breaks,
    # but explicitly excludes hyphens from being treated as break points for length calculation.
    max_segment_length_for_width = 0
    if visible_col_key == "word":
        for item in data:
            word_content = _normalize_full_width_to_half_width(item.get("word", "")) # 统一转换为半角
            # Using a regex to split by multiple delimiters, while keeping hyphenated words together.
            # This regex splits by spaces, commas, parentheses (both full and half-width), '或', '是'.
            # It does NOT split by hyphens. Added '/', '[', ']' and ',' as soft break points.
            segments = [s.strip() for s in re.split(r'[ ,()/\[\]或是]+', word_content) if s.strip()]
            
            if segments:
                max_segment_length_for_width = max(max_segment_length_for_width, max(len(s) for s in segments))
            else:
                max_segment_length_for_width = max(max_segment_length_for_width, len(word_content)) # Fallback if no segments
    elif visible_col_key == "content": # 如果可见内容是中文释义，则计算其最大长度
        max_segment_length_for_width = max((min(len(item.get("content", "")), MAX_CONTENT_LENGTH) for item in data), default=0)
    
    # 估算每个字符的宽度 (10pt 字体，粗略估计)
    # 经验值：10pt 字体，一个英文字符大约 0.25 cm
    ESTIMATED_CHAR_WIDTH_CM = 0.25
    
    # 动态计算英文单词列宽度，并设置最小和最大限制
    # 最小1.5cm (从3.0cm降低), 最大6.0cm，加上0.2cm的缓冲
    # 这样短单词的列宽会更窄，减少留白，给中文更多空间。
    # 调整 ESTIMATED_CHAR_WIDTH_CM 为 0.22，更贴近实际视觉宽度。
    ESTIMATED_CHAR_WIDTH_CM = 0.18 # Further reduced to encourage more aggressive wrapping
    
    # Find the actual longest word for debugging
    longest_word_text = ""
    if visible_col_key == "word":
        for item in data:
            word = _normalize_full_width_to_half_width(item.get("word", "")) # For debugging, normalize first
            if len(word) > len(longest_word_text): # This is for debugging, still use full word length
                longest_word_text = word
    
    print(f"DEBUG: 最长英文单词 (for debug): '{longest_word_text}' (长度: {len(longest_word_text)} 字符)")
    calculated_word_width = max_segment_length_for_width * ESTIMATED_CHAR_WIDTH_CM + 0.2
    WORD_COL_WIDTH_CM = min(3.5, max(1.5, calculated_word_width)) # Further reduced max width to 3.5cm

    # A4 可用宽度约 15.92 cm (21 - 2.54*2)
    # 每半部分可用宽度 = 15.92 cm / 2 = 7.96 cm
    remaining_width_for_content = 7.96 - INDEX_COL_WIDTH_CM
    print(f"DEBUG: INDEX_COL_WIDTH_CM: {INDEX_COL_WIDTH_CM:.2f} cm")
    print(f"DEBUG: Calculated WORD_COL_WIDTH_CM (before final adjustment): {WORD_COL_WIDTH_CM:.2f} cm")

    # 解释/默写列宽度 (剩余宽度)
    EXPLANATION_COL_WIDTH_CM = remaining_width_for_content - WORD_COL_WIDTH_CM
    print(f"DEBUG: Initial EXPLANATION_COL_WIDTH_CM: {EXPLANATION_COL_WIDTH_CM:.2f} cm")
    # 确保解释列宽度不为负数，并设置一个合理的最小宽度，例如 3.0cm (为中文提供更多空间)
    # 如果 EXPLANATION_COL_WIDTH_CM 小于 3.0cm，则强制设置为 3.0cm
    # 这意味着 WORD_COL_WIDTH_CM 会被进一步压缩
    MIN_EXPLANATION_COL_WIDTH_CM = 3.0
    if EXPLANATION_COL_WIDTH_CM < MIN_EXPLANATION_COL_WIDTH_CM and remaining_width_for_content - MIN_EXPLANATION_COL_WIDTH_CM >= 1.0: # Ensure word col doesn't go below 1.0cm
        EXPLANATION_COL_WIDTH_CM = MIN_EXPLANATION_COL_WIDTH_CM
        # 重新计算 WORD_COL_WIDTH_CM，以适应 EXPLANATION_COL_WIDTH_CM 的最小宽度
        WORD_COL_WIDTH_CM = remaining_width_for_content - EXPLANATION_COL_WIDTH_CM
        # 确保 WORD_COL_WIDTH_CM 不会变得过小，例如，至少 1.0cm
        if WORD_COL_WIDTH_CM < 1.0:
            WORD_COL_WIDTH_CM = 1.0
            print(f"⚠️ 警告: 解释/默写列宽度已强制设置为 {MIN_EXPLANATION_COL_WIDTH_CM:.2f}cm，英文单词列宽度调整为 {WORD_COL_WIDTH_CM:.2f}cm。这可能导致英文单词列过窄。")
        elif WORD_COL_WIDTH_CM > 3.5: # Re-apply max limit if it was expanded due to explanation col constraint
            WORD_COL_WIDTH_CM = 3.5
        else:
            print(f"⚠️ 警告: 解释/默写列宽度过小 ({EXPLANATION_COL_WIDTH_CM:.2f}cm)，已强制设置为 {MIN_EXPLANATION_COL_WIDTH_CM:.2f}cm。英文单词列宽度调整为 {WORD_COL_WIDTH_CM:.2f}cm。")
    print(f"DEBUG: Final WORD_COL_WIDTH_CM: {WORD_COL_WIDTH_CM:.2f} cm, Final EXPLANATION_COL_WIDTH_CM: {EXPLANATION_COL_WIDTH_CM:.2f} cm")


    col_widths_cm = [
        Cm(INDEX_COL_WIDTH_CM), Cm(WORD_COL_WIDTH_CM), Cm(EXPLANATION_COL_WIDTH_CM), # 左侧三列
        Cm(INDEX_COL_WIDTH_CM), Cm(WORD_COL_WIDTH_CM), Cm(EXPLANATION_COL_WIDTH_CM)  # 右侧三列
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
        run._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman') # 明确设置英文字体
        run._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman') # 明确设置高ANSI字体
        paragraph.paragraph_format.space_before = Pt(0) # 移除段前间距
        paragraph.paragraph_format.space_after = Pt(0)  # 移除段后间距
        run.font.size = Pt(FONT_SIZE_VISIBLE)
        run.bold = True
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        
        # 对序号列的表头也设置0内边距
        if i == 0 or i == 3: # Index columns
            set_cell_margins(hdr_cells[i], top=0, left=0, bottom=0, right=0)

    # 填充数据
    for i in range(0, len(data), 2): # 每循环一次处理两个单词，填充 Word 表格的一行
        row_data = data[i:i+2] # 获取当前行的两个单词数据
        row = table.add_row() # 行高自适应
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
                run_index._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman') # 明确设置英文字体
                run_index._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman') # 明确设置高ANSI字体
                p_index.paragraph_format.space_before = Pt(0)
                p_index.paragraph_format.space_after = Pt(0)
                run_index.font.size = Pt(FONT_SIZE_INDEX)
                p_index.alignment = WD_ALIGN_PARAGRAPH.CENTER # 强制居中对齐，减少视觉留白
                cells[j*3].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                # 设置序号单元格的内边距为0
                set_cell_margins(cells[j*3], top=0, left=0, bottom=0, right=0)


                # 可见内容 (英文单词或中文释义)
                visible_text = item.get(visible_col_key, "")
                visible_text = _normalize_full_width_to_half_width(visible_text) # 统一转换为半角
                if visible_col_key == "content": # 如果是中文释义，可能需要截断
                    visible_text = visible_text[:MAX_CONTENT_LENGTH]
                
                # 如果是英文单词列，在括号前后添加空格，以鼓励Word在这些位置换行
                if visible_col_key == "word":
                    # Step 1: Add spaces around commas and slashes to create soft break points
                    # This helps Word's natural wrapping at these points.
                    # Note: Parentheses and brackets are handled by direct newline insertion below.
                    visible_text = re.sub(r'([,/])', r' \1 ', visible_text)
                    # 清理可能产生的多余空格 (例如，如果括号旁边已经有空格)
                    visible_text = re.sub(r'\s+', ' ', visible_text).strip()

                    # Step 2: Aggressively insert newlines before and after parentheses/brackets (and their content)
                    # This forces them onto their own lines if possible, or makes them very strong break points.
                    # Insert newline before '(' or '['
                    visible_text = re.sub(r'(\s*)(\(|\[)', r'\n\2', visible_text)
                    # Insert newline after ')' or ']'
                    visible_text = re.sub(r'(\)|\])(\s*)', r'\1\n', visible_text)
                    
                    # Step 3: Clean up any resulting empty lines or excessive newlines
                    visible_text = re.sub(r'\n\s*\n', '\n', visible_text) # Replace multiple newlines with single
                    visible_text = visible_text.strip() # Final trim

                p_visible = cells[j*3 + 1].paragraphs[0] # 第 j*3 + 1 列是可见内容列
                run_visible = p_visible.add_run(visible_text)
                run_visible.font.name = FONT_NAME
                run_visible._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
                run_visible._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman') # 明确设置英文字体
                run_visible._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman') # 明确设置高ANSI字体
                p_visible.paragraph_format.space_before = Pt(0) # 移除段前间距
                p_visible.paragraph_format.space_after = Pt(0)  # 移除段后间距
                run_visible.font.size = Pt(FONT_SIZE_VISIBLE)
                p_visible.alignment = WD_ALIGN_PARAGRAPH.LEFT
                cells[j*3 + 1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                # 为可见内容单元格添加微小内边距，鼓励换行
                set_cell_margins(cells[j*3 + 1], left=Pt(1).emu, right=Pt(1).emu)

                # 默写区域或中文释义
                blank_length = 0
                second_col_text = ""
                
                if is_dictation_mode: # 默写模式
                    if blank_col_key == "content": # 默写中文
                        max_content_len_in_data = 0
                        for d_item in data:
                            max_content_len_in_data = max(max_content_len_in_data, min(len(d_item.get("content", "")), MAX_CONTENT_LENGTH))
                        blank_length = max_content_len_in_data + BLANK_BUFFER_CHARS
                    elif blank_col_key == "word": # 默写英文 (blanks for word)
                        max_word_len_in_data = 0
                        for d_item in data:
                            max_word_len_in_data = max(max_word_len_in_data, len(d_item.get("word", "")))
                        blank_length = max_word_len_in_data + BLANK_BUFFER_CHARS
                    second_col_text = BLANK_CHAR * blank_length if blank_length > 0 else "" # 确保 blank_length 大于0
                else: # "normal" 模式，显示第二个可见内容 (中文释义)
                    second_col_text = item.get(blank_col_key, "") # blank_col_key 在 normal 模式下实际是 content
                second_col_text = _normalize_full_width_to_half_width(second_col_text) # 统一转换为半角

                p_blank = cells[j*3 + 2].paragraphs[0] # 第 j*3 + 2 列是默写/解释列
                run_blank = p_blank.add_run(second_col_text)
                run_blank.font.name = FONT_NAME
                run_blank._element.rPr.rFonts.set(qn('w:eastAsia'), FONT_NAME)
                run_blank._element.rPr.rFonts.set(qn('w:ascii'), 'Times New Roman') # 明确设置英文字体
                run_blank._element.rPr.rFonts.set(qn('w:hAnsi'), 'Times New Roman') # 明确设置高ANSI字体
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
