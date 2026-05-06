def generate_text_table(data, columns, column_headers, output_mode="normal", num_entry_columns=1):
    """
    生成纯文本格式的表格，支持多列词条布局和默写模式。

    Args:
        data (list of dict): 包含单词数据的列表，每个字典代表一个单词。
                              例如：[{"word": "apple", "content": "苹果"}, ...]
        columns (list of str): 在 "normal" 模式下需要输出的字段名列表，例如 ["word", "content"]。
        column_headers (list of str): 在 "normal" 模式下对应 columns 的列标题，例如 ["英文单词", "中文释义"]。
        output_mode (str): 输出模式。"normal" (常规表格), "english_dictation" (英文默写中文),
                           "chinese_dictation" (中文默写英文)。
        num_entry_columns (int): 在默写模式下，每行显示多少个词条（例如，2表示左右并排显示两个词条）。

    Returns:
        str: 格式化后的纯文本表格。
    """
    if not data or not columns or not column_headers:
        return "没有数据可用于生成表格。"

    # Determine the actual columns and headers based on output_mode
    # For dictation modes, 'columns' and 'column_headers' parameters are overridden
    effective_columns = []
    effective_column_headers = []
    
    if output_mode == "english_dictation":
        effective_columns = ["word", "blanks_for_content"]
        effective_column_headers = ["英文单词", "中文默写"]
    elif output_mode == "chinese_dictation":
        effective_columns = ["content", "blanks_for_word"]
        effective_column_headers = ["中文释义", "英文默写"]
    else: # "normal" mode
        effective_columns = columns
        effective_column_headers = column_headers

    if len(effective_columns) != len(effective_column_headers):
        raise ValueError("effective_columns 和 effective_column_headers 的长度必须一致。")

    # 计算每列的最大宽度
    # This needs to be done across all data items, considering all potential columns.
    
    # Initialize widths with header lengths
    column_widths = [len(header) for header in effective_column_headers]

    # Calculate content widths for non-blank columns
    for item in data:
        for i, col in enumerate(effective_columns):
            if col.startswith("blanks_for_"): # Blanks width is determined by the other column's max content
                continue
            cell_content = str(item.get(col, '')) if item.get(col) is not None else ''
            column_widths[i] = max(column_widths[i], len(cell_content))

    # Determine the width for the "blanks" column based on the *other* column's max content
    # and ensure a reasonable minimum for writing.
    if "blanks_for_content" in effective_columns:
        blanks_col_idx = effective_columns.index("blanks_for_content")
        max_content_len = 0
        for item in data:
            max_content_len = max(max_content_len, len(str(item.get("content", ''))))
        # Ensure blanks column has a reasonable minimum width, e.g., 15-20 characters
        column_widths[blanks_col_idx] = max(max_content_len + 5, 20) # Add some buffer for writing
    
    if "blanks_for_word" in effective_columns:
        blanks_col_idx = effective_columns.index("blanks_for_word")
        max_word_len = 0
        for item in data:
            max_word_len = max(max_word_len, len(str(item.get("word", ''))))
        # Ensure blanks column has a reasonable minimum width
        column_widths[blanks_col_idx] = max(max_word_len + 5, 20) # Add some buffer for writing

    # 调整列宽，确保至少有最小宽度
    min_col_width = 10
    column_widths = [max(width, min_col_width) for width in column_widths]
    final_column_widths = column_widths # Rename for clarity

    # 构建表格
    table_lines = []

    # Generate the header row for one entry block
    single_entry_header_parts = []
    for i, header in enumerate(effective_column_headers):
        single_entry_header_parts.append(f" {header.ljust(final_column_widths[i])} ")
    single_entry_header_line = "|" + "|".join(single_entry_header_parts) + "|"
    
    # Generate the top border for one entry block
    single_entry_top_border_parts = []
    for width in final_column_widths:
        single_entry_top_border_parts.append("-" * (width + 2))
    single_entry_top_border = "+" + "+".join(single_entry_top_border_parts) + "+"
    
    # Combine headers and borders for num_entry_columns
    # Use 3 spaces as separator between entry blocks
    full_header_line = "   ".join([single_entry_header_line] * num_entry_columns)
    full_top_border = "   ".join([single_entry_top_border] * num_entry_columns)
    
    table_lines.append(full_top_border)
    table_lines.append(full_header_line)
    table_lines.append(full_top_border)

    # Process data in chunks of num_entry_columns
    for i in range(0, len(data), num_entry_columns):
        row_of_entries = data[i : i + num_entry_columns]
        
        data_lines_for_this_row_parts = [] # List of strings, each string is one entry's data line
        for item in row_of_entries:
            single_entry_data_parts = []
            for col_idx, col in enumerate(effective_columns):
                cell_content = ""
                if col.startswith("blanks_for_"):
                    cell_content = "_" * final_column_widths[col_idx]
                else:
                    cell_content = str(item.get(col, '')) if item.get(col) is not None else ''
                single_entry_data_parts.append(f" {cell_content.ljust(final_column_widths[col_idx])} ")
            data_lines_for_this_row_parts.append("|" + "|".join(single_entry_data_parts) + "|")
        
        # Pad with empty entries if not enough words to fill the last row
        while len(data_lines_for_this_row_parts) < num_entry_columns:
            empty_entry_parts = []
            for col_idx, col in enumerate(effective_columns):
                empty_entry_parts.append(f" {''.ljust(final_column_widths[col_idx])} ")
            data_lines_for_this_row_parts.append("|" + "|".join(empty_entry_parts) + "|")
            
        table_lines.append("   ".join(data_lines_for_this_row_parts))

    table_lines.append(full_top_border)

    return "\n".join(table_lines)

# 示例用法 (可用于测试)
if __name__ == "__main__":
    sample_data = [
        {"word": "apple", "content": "苹果"},
        {"word": "banana", "content": "香蕉"},
        {"word": "cat", "content": "猫，猫科动物"},
        {"word": "dog", "content": "狗"},
        {"word": "elephant", "content": "大象"},
        {"word": "fox", "content": "狐狸"},
    ]

    # 仅英文
    print("--- 仅英文 ---")
    print(generate_text_table(sample_data, ["word"], ["英文单词"]))

    # 仅中文
    print("\n--- 仅中文 ---")
    print(generate_text_table(sample_data, ["content"], ["中文释义"]))

    # 英文+中文
    print("\n--- 英文+中文 ---")
    print(generate_text_table(sample_data, ["word", "content"], ["英文单词", "中文释义"]))

    # 英文默写中文 (2列)
    print("\n--- 英文默写中文 (2列) ---")
    print(generate_text_table(sample_data, [], [], output_mode="english_dictation", num_entry_columns=2))

    # 中文默写英文 (2列)
    print("\n--- 中文默写英文 (2列) ---")
    print(generate_text_table(sample_data, [], [], output_mode="chinese_dictation", num_entry_columns=2))