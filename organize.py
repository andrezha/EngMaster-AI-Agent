import os
import shutil

def organize_gaokao_library():
    # 1. 定义源路径（你的桌面文件夹）和 目标路径（当前项目下的 data）
    desktop_path = os.path.expanduser("~/Desktop/Gaokao_Library")
    project_data_path = os.path.join(os.path.dirname(__file__), "data")

    # 2. 定义题型文件夹映射
    categories = {
        "完形填空": ["cloze", "完形"],
        "阅读理解": ["reading", "阅读"],
        "语法填空": ["grammar", "fill", "语法"],
        "七选五": ["seven", "7选5", "七选五"],
        "短文改错": ["error", "correction", "改错"]
    }

    # 检查桌面文件夹是否存在
    if not os.path.exists(desktop_path):
        print(f"❌ 找不到桌面上的文件夹：{desktop_path}")
        return

    # 3. 开始搬运
    count = 0
    for root, dirs, files in os.walk(desktop_path):
        for file in files:
            if file.endswith(".txt"):
                file_lower = file.lower()
                target_cat = "其他" # 默认分类
                
                # 根据文件名匹配题型
                for cat, keywords in categories.items():
                    if any(kw in file_lower for kw in keywords):
                        target_cat = cat
                        break
                
                # 创建目标子文件夹
                target_dir = os.path.join(project_data_path, target_cat)
                os.makedirs(target_dir, exist_ok=True)
                
                # 执行移动（或复制）
                src_file = os.path.join(root, file)
                dst_file = os.path.join(target_dir, file)
                shutil.copy2(src_file, dst_file) # 使用 copy2 保留原始时间戳
                count += 1

    print(f"✅ 搬运完成！共处理 {count} 个文件。")
    print(f"📍 你的题库现在位于：{project_data_path}")

if __name__ == "__main__":
    organize_gaokao_library()