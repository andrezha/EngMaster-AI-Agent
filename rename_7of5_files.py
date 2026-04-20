#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修正 data/七选五 文件夹下的文件名
将所有以 Cloze_ 开头的文件名，前缀替换为 7of5_
确保最终格式为 7of5_年份_篇号.txt
"""

import os
import re
from pathlib import Path

def rename_7of5_files():
    """
    批量重命名 'data/七选五' 文件夹下的文件，将 'Cloze_' 前缀替换为 '7of5_'，并统一格式。
    """
    """批量重命名七选五文件"""
    
    # 定义文件夹路径
    folder_path = Path("data/七选五")
    
    if not folder_path.exists():
        print(f"错误：文件夹 {folder_path} 不存在")
        return
    
    # 获取所有文件
    files = list(folder_path.glob("Cloze_*.txt"))
    
    if not files:
        print("没有找到以 Cloze_ 开头的文件")
        return
    
    # 按文件名排序，确保按顺序处理
    files.sort(key=lambda x: x.name)
    
    print("开始批量重命名文件...")
    print("=" * 50)
    
    # 存储重命名对照信息
    rename_map = []
    
    for file_path in files:
        old_name = file_path.name
        
        # 提取年份和篇号
        match = re.match(r'Cloze_(\d{4})_(\d+)\.txt', old_name)
        if match:
            year = match.group(1)
            article_num = match.group(2)
            
            # 确保篇号是两位数格式
            article_num_padded = article_num.zfill(2)
            
            # 构造新文件名
            new_name = f"7of5_{year}_{article_num_padded}.txt"
            new_path = file_path.parent / new_name
            
            # 执行重命名
            try:
                file_path.rename(new_path)
                rename_map.append((old_name, new_name))
                print(f"✓ {old_name} -> {new_name}")
            except Exception as e:
                print(f"✗ 重命名失败 {old_name}: {e}")
        else:
            print(f"✗ 无法解析文件名格式: {old_name}")
    
    print("=" * 50)
    print(f"重命名完成！共处理了 {len(rename_map)} 个文件")
    
    # 输出对照列表
    print("\n文件名对照列表：")
    print("-" * 50)
    for old_name, new_name in rename_map:
        print(f"{old_name} -> {new_name}")

if __name__ == "__main__":
    rename_7of5_files()