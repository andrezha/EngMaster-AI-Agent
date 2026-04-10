#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试完形填空解析器
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsers.reading_parser import parse_reading_txt

def test_cloze_parser():
    """测试完形填空解析器"""
    
    # 读取测试文件
    test_file = "data/完形填空/CLOZE_2010_01_AI.txt"
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("测试文件内容预览：")
        print("=" * 50)
        print(content[:500] + "...")
        print("=" * 50)
        
        # 解析文件
        result = parse_reading_txt(content)
        
        print("\n解析结果：")
        print("=" * 50)
        print(f"题型: {result.get('question_type', 'unknown')}")
        print(f"年份: {result.get('year', '')}")
        print(f"类别: {result.get('category', '')}")
        print(f"标题: {result.get('title', '')}")
        print(f"文章长度: {len(result.get('passage', ''))}")
        print(f"题目数量: {len(result.get('items', []))}")
        
        # 显示前几个题目
        items = result.get('items', [])
        for i, item in enumerate(items[:3]):
            print(f"\n题目 {i+1}:")
            print(f"  题号: {item.get('q_id', '')}")
            print(f"  答案: {item.get('answer', '')}")
            print(f"  选项: {item.get('options', {})}")
            print(f"  解析: {item.get('analysis', '')[:100]}...")
        
        # 调试：显示解析过程
        print("\n调试信息：")
        print("=" * 50)
        if "[ANALYSIS]" in content:
            analysis_part = content.split("[ANALYSIS]")[1].strip()
            print("分析文本预览：")
            print(analysis_part[:200] + "...")
            
            # 测试正则匹配
            import re
            analysis_blocks = re.split(r'(?=\d+\.\s*[A-D]\.)', analysis_part)
            print(f"\n分割后的块数: {len(analysis_blocks)}")
            for j, block in enumerate(analysis_blocks[:3]):
                block = block.strip()
                if not block:
                    continue
                print(f"  块 {j+1}: {block[:50]}...")
                q_match = re.match(r'(\d+)\.\s*([A-D])\.', block)
                if q_match:
                    print(f"    匹配到题号: {q_match.group(1)}, 答案: {q_match.group(2)}")
                else:
                    print(f"    未匹配到题号和答案")
        
        print("\n完整解析文本预览：")
        print("=" * 50)
        analysis = result.get('original_analysis', '')
        print(analysis[:300] + "..." if len(analysis) > 300 else analysis)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cloze_parser()