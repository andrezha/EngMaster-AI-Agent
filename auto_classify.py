import os
import shutil

def classify_by_content():
    # 1. 定义源和目标
    src_dir = os.path.expanduser("~/Desktop/Gaokao_Library")
    dst_dir = os.path.join(os.path.dirname(__file__), "data")

    # 2. 定义特征词库（只要文件内容包含这些词，就归类）
    rules = {
        "完形填空": ["cloze", "完形", "完型"],
        "阅读理解": ["reading", "阅读"],
        "语法填空": ["grammar", "fill", "语法填空"],
        "七选五": ["seven", "7选5", "七选五"],
        "短文改错": ["error", "correction", "改错"]
    }

    if not os.path.exists(src_dir):
        print("❌ 桌面找不到 Gaokao_Library")
        return

    # 清理并创建 data 目录
    if os.path.exists(dst_dir): shutil.rmtree(dst_dir)
    os.makedirs(dst_dir)

    count = 0
    # 3. 遍历文件
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                try:
                    # 读取前 500 个字符进行内容识别
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(500).lower()
                    
                    # 识别题型
                    target_cat = "其他"
                    for cat, keywords in rules.items():
                        if any(kw in content for kw in keywords):
                            target_cat = cat
                            break
                    
                    # 搬运
                    target_path = os.path.join(dst_dir, target_cat)
                    os.makedirs(target_path, exist_ok=True)
                    shutil.copy2(file_path, os.path.join(target_path, file))
                    count += 1
                except:
                    continue

    print(f"✅ 处理完成！共分类搬运 {count} 个文件到项目 data 目录下。")
    # 打印结果看看
    for folder in os.listdir(dst_dir):
        f_path = os.path.join(dst_dir, folder)
        if os.path.isdir(f_path):
            print(f"📂 {folder}: 包含 {len(os.listdir(f_path))} 个题")

if __name__ == "__main__":
    classify_by_content()