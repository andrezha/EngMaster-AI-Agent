import requests
import json
import os
from PySide6.QtCore import QThread, Signal as pyqtSignal # PySide6 uses Signal instead of pyqtSignal

class AIWorker(QThread):
    result_ready = pyqtSignal(str) # PySide6 Signal
    error_occurred = pyqtSignal(str) # PySide6 Signal

    def __init__(self, question_type, question_text):
        super().__init__()
        self.question_type = question_type
        self.question_text = question_text

    def load_prompt(self):
        config_path = "prompts.json"
        # 获取当前文件所在的绝对路径，防止找不到文件
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, config_path)
        
        try:
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    all_prompts = json.load(f)
                p = all_prompts.get(self.question_type, "请分析以下题目：")
                print(f"✅ 成功加载提示词：{self.question_type}") # 👈 调试用
                return p
            else:
                print(f"❌ 找不到文件：{full_path}")
                return "请分析以下题目："
        except Exception as e:
            print(f"❌ 读取配置出错：{str(e)}")
            return "请分析以下题目："

    def run(self):
        try:
            instruction = self.load_prompt()
            
            # 🔥 统一的 Prompt 拼接逻辑
            full_prompt = f"指令：{instruction}\n\n内容：\n{self.question_text}\n\n请开始解析："
            
            payload = {
                "model": "qwen2.5:7b",
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_ctx": 8192,
                    "num_predict": 2048,
                    "top_p": 0.9,
                    "presence_penalty": 0.1  # 👈 调低了！防止 AI 为了避嫌而乱造词
                }
            }

            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "")
                self.result_ready.emit(result.strip())
            else:
                self.error_occurred.emit(f"Ollama错误: {response.status_code}")

        except Exception as e:
            self.error_occurred.emit(f"运行出错: {str(e)}")