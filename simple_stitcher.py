import os
import random

def build_raw_stitched_file():
    """
    随机从 'data' 文件夹下的各个题型子文件夹中选择文件，并将它们拼接成一个模拟高考真题试卷文件。
    """
    print("🚀 simple_stitcher.py 脚本开始执行...")

    # --- 1. 强力路径定位逻辑 ---
    # 获取脚本所在的绝对路径 (HighSchoolEnglishAI/lib)
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 尝试寻找 data 文件夹
    data_dir = None
    # 向上寻找 3 层 (lib -> 项目根 -> 根的上一级)
    temp_dir = curr_dir
    for _ in range(3):
        potential_data = os.path.join(temp_dir, "data")
        if os.path.exists(potential_data):
            data_dir = potential_data
            break
        temp_dir = os.path.dirname(temp_dir)

    if not data_dir:
        print(f"❌ 严重错误：无法定位 'data' 文件夹！")
        print(f"当前脚本在: {curr_dir}")
        print("请确保你的项目结构是：HighSchoolEnglishAI/lib/simple_stitcher.py")
        print("如果 'data' 文件夹在其他位置，请手动修改 data_dir 变量。")
        return

    # 确定输出位置
    output_dir = os.path.join(data_dir, "真题试卷")
    output_path = os.path.join(output_dir, "高考模拟_待手动编号.txt")

    print(f"✅ 'data' 文件夹已定位到: {data_dir}")
    # --- 2. 组装规格 ---
    PLAN = [
        {"folder": "阅读理解", "need": 4, "prefix": "READING_PASSAGE"},
        {"folder": "七选五",   "need": 1, "prefix": "7_OUT_OF_5"},
        {"folder": "完形填空", "need": 1, "prefix": "CLOZE"},
        {"folder": "语法填空", "need": 1, "prefix": "GRAMMAR"}
    ]

    final_content = "[[EXAM_TITLE]]\n高考英语全真模拟卷 (待手动校对)\n\n"
    print(f"📂 成功锁定数据源: {data_dir}")

    for cfg in PLAN:
        folder_path = os.path.join(data_dir, cfg["folder"])
        if not os.path.exists(folder_path):
            print(f"⚠️ 还是没找着子文件夹: {cfg['folder']} (跳过)")
            continue

        all_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
        if not all_files:
            print(f"ℹ️ {cfg['folder']} 里面没东西")
            continue

        selected = random.sample(all_files, min(cfg["need"], len(all_files)))

        for i, fname in enumerate(selected):
            print(f"  ➡️ 添加 {cfg['folder']} 中的文件: {fname}")
            with open(os.path.join(folder_path, fname), 'r', encoding='utf-8') as f:
                raw_text = f.read()

            # 清理元数据头
            lines = raw_text.split('\n')
            clean_lines = [ln for ln in lines if not any(k in ln for k in ["FILENAME:", "YEAR:", "CAT:", "TITLE:"])]
            content = "\n".join(clean_lines).strip()

            # 加上 SECTION 标签
            if cfg["prefix"] == "READING_PASSAGE":
                tag = f"{cfg['prefix']}_{chr(65+i)}"
            else:
                tag = cfg["prefix"]

            final_content += f"[[SECTION: {tag}]]\n{content}\n\n"

    # --- 3. 写入 ---
    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print("-" * 50)
    print(f"✨ 缝合成功！")
    print(f"📝 文件名: 高考模拟_待手动编号.txt")
    print(f"📍 完整路径: {output_path}")
    print("-" * 50)

if __name__ == "__main__":
    build_raw_stitched_file()