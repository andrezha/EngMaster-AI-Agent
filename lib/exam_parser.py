import os
import random
import re

def build():
    # 1. 绝对路径定位
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    output_dir = os.path.join(data_dir, "模拟试卷")
    
    # 确定文件名后缀
    suffix = "2026"
    read_path = os.path.join(data_dir, "阅读理解")
    if os.path.exists(read_path):
        read_files = [f for f in os.listdir(read_path) if f.endswith('.txt')]
        if read_files:
            m = re.search(r'(\d+)', read_files[0])
            if m: suffix = m.group(1)
    
    target_path = os.path.join(output_dir, f"高考模拟_{suffix}.txt")

    # 高考 45 题硬规格
    PLAN = [
        {"folder": "阅读理解", "need": 4, "tag": "READING", "counts": [3, 4, 4, 4]},
        {"folder": "七选五",   "need": 1, "tag": "7_OUT_OF_5", "counts": [5]},
        {"folder": "完形填空", "need": 1, "tag": "CLOZE", "counts": [15]},
        {"folder": "语法填空", "need": 1, "tag": "GRAMMAR", "counts": [10]}
    ]

    full_text = f"[[EXAM_TITLE]]\n高考英语整卷模拟练习 (编号: {suffix})\n\n"
    global_id = 21

    print(f"开始检查文件夹...")

    for cfg in PLAN:
        folder = os.path.join(data_dir, cfg["folder"])
        if not os.path.exists(folder):
            print(f"❌ 找不到文件夹: {cfg['folder']}")
            continue
        
        files = [f for f in os.listdir(folder) if f.endswith('.txt')]
        if not files:
            print(f"⚠️ 文件夹为空: {cfg['folder']}")
            continue
            
        selected = random.sample(files, min(cfg["need"], len(files)))

        for i, fname in enumerate(selected):
            with open(os.path.join(folder, fname), 'r', encoding='utf-8') as f:
                content = f.read()

            # 拆分大块
            parts = re.split(r'\[\s*QUESTIONS\s*\]|\[\s*ANALYSIS\s*\]', content, flags=re.IGNORECASE)
            passage = re.sub(r'(FILENAME|YEAR|CAT|TITLE):.*', '', parts[0]).strip()
            
            q_area = parts[1].strip() if len(parts) > 1 else ""
            a_area = parts[2].strip() if len(parts) > 2 else ""

            # 提取题目逻辑
            # 先按 A. B. C. D. 切
            q_list = re.findall(r'(?:^|\n).*?\s*A\.\s+.*?B\.\s+.*?C\.\s+.*?D\.\s+.*?(?=\n|$)', q_area, re.S)
            # 如果没切出来（七选五或语法填空），按数字切
            if not q_list:
                q_list = [it.strip() for it in re.split(r'\n\s*\d+\.\s*', "\n" + q_area) if len(it.strip()) > 5]
            
            # 提取答案逻辑
            a_list = [it.strip() for it in re.split(r'\n\s*\d+\.\s*', "\n" + a_area) if len(it.strip()) > 1]

            # 强制填充到规格要求的题数
            needed = cfg["counts"][i] if i < len(cfg["counts"]) else cfg["counts"][0]
            
            new_qs = ""
            new_as = ""
            for j in range(needed):
                # 如果原文件里确实没题，就用占位符防止 global_id 停住
                raw_q = q_list[j] if j < len(q_list) else (q_list[0] if q_list else "Question content missing in source file.")
                raw_a = a_list[j] if j < len(a_list) else (a_list[0] if a_list else "Analysis missing.")
                
                # 严格从 raw_q 中提取题号和内容
                q_id_match = re.match(r'(\d+)\.\s*(.*)', raw_q.strip(), re.DOTALL)
                if q_id_match:
                    current_q_id = q_id_match.group(1)
                    clean_q_content = q_id_match.group(2).strip()
                else:
                    # 如果 raw_q 没有以数字开头，则认为格式不符合预期，使用占位符并警告
                    print(f"⚠️ 警告: 题目内容 '{raw_q.strip()[:50]}...' 未以数字题号开头。使用占位符 ID。")
                    current_q_id = "XX" # 占位符 ID
                    clean_q_content = raw_q.strip()

                # 严格从 raw_a 中提取题号和内容
                a_id_match = re.match(r'(\d+)\.\s*(.*)', raw_a.strip(), re.DOTALL)
                if a_id_match:
                    clean_a_content = a_id_match.group(2).strip()
                else:
                    # 如果 raw_a 没有以数字开头，则使用原始内容
                    clean_a_content = raw_a.strip()

                new_qs += f"{current_q_id}. {clean_q_content}\n\n" # 使用提取到的题号
                new_as += f"{current_q_id}. {clean_a_content}\n"   # 使用提取到的题号
                global_id += 1
            sec_tag = f"READING_PASSAGE_{chr(65+i)}" if cfg["tag"] == "READING" else cfg["tag"]
            full_text += f"[[SECTION: {sec_tag}]]\n{passage}\n\n[QUESTIONS]\n{new_qs}\n[ANALYSIS]\n{new_as}\n\n"

    # 物理覆盖写入
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    
    print("-" * 30)
    print(f"📊 任务完成！总题数: {global_id - 21}")
    print(f"📍 文件已生成/覆盖: {os.path.basename(target_path)}")
    print(f"📂 存放目录: {output_dir}")
    print("-" * 30)

if __name__ == "__main__":
    build()
