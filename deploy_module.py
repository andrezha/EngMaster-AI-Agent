import sys
import os
import warnings
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6 import uic

# 1. 屏蔽启动时的冗余警告和联网检查
warnings.filterwarnings("ignore")
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# 导入 PaddleOCR
try:
    from paddleocr import PaddleOCR
except ImportError:
    print("❌ 错误：未检测到 paddleocr 库，请运行 pip install paddleocr")
    sys.exit(1)

# --- 异步识图线程：专门负责处理图片识别，不卡住界面 ---
class OCRWorker(QThread):
    result_ready = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, ocr_engine, img_path):
        super().__init__()
        self.ocr_engine = ocr_engine
        self.img_path = img_path

    def run(self):
        try:
            # 执行识别逻辑
            result = self.ocr_engine.ocr(self.img_path, cls=True)
            # 将识别出来的各行文字合并为一个列表
            lines = [line[1][0] for line in result[0]] if result and result[0] else []
            self.result_ready.emit(lines)
        except Exception as e:
            self.error_signal.emit(str(e))

# --- 主程序窗口 ---
class HighSchoolEnglishAI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # A. 获取当前文件的绝对路径
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(self.base_path, "resources", "main_window.ui")
        
        # B. 加载 UI 界面
        try:
            uic.loadUi(ui_path, self)
        except Exception as e:
            print(f"❌ UI文件加载失败: {e}")
            sys.exit(1)

        # C. 初始化 OCR 引擎 (这里已彻底移除 show_log 和 use_gpu 参数)
        print("🏗️  正在启动本地 OCR 引擎 (PaddleOCR 3.4.0)...")
        try:
            self.ocr = PaddleOCR(
                det_model_dir=os.path.join(self.base_path, "models", "det"),
                rec_model_dir=os.path.join(self.base_path, "models", "rec"),
                cls_model_dir=os.path.join(self.base_path, "models", "cls"),
                use_angle_cls=True,
                device='cpu',  # 必须使用 device 代替 use_gpu
                lang="ch"      # 删除了 show_log，防止报错
            )
            print("✅ 引擎启动成功！")
        except Exception as e:
            # 如果 models 文件夹没放对文件，会在这里报错
            QMessageBox.critical(self, "启动失败", f"OCR 模型加载失败！\n请确保 models 下有 det/rec/cls 子文件夹且内含模型。\n错误: {e}")

        # D. 绑定按钮点击事件
        # 确保你的 UI 里的按钮 ObjectName 叫 btn_select
        self.btn_select.clicked.connect(self.start_ocr_task)

    def start_ocr_task(self):
        """点击选图按钮后的逻辑"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择英语试卷图片", "", "Images (*.jpg *.png *.jpeg)"
        )
        
        if file_path:
            # 更新界面状态
            self.left_text_edit.setPlaceholderText("🔍 正在识别中，请稍候...")
            self.left_text_edit.clear()
            self.btn_select.setEnabled(False) # 识别时禁用按钮

            # 开启异步线程
            self.worker = OCRWorker(self.ocr, file_path)
            self.worker.result_ready.connect(self.on_ocr_success)
            self.worker.error_signal.connect(self.on_ocr_error)
            self.worker.start()

    def on_ocr_success(self, text_list):
        """识别成功，把文字填入左侧文本框"""
        if text_list:
            self.left_text_edit.setPlainText("\n".join(text_list))
        else:
            self.left_text_edit.setPlainText("⚠️ 未发现文字或识别失败。")
        self.btn_select.setEnabled(True)

    def on_ocr_error(self, error_msg):
        """识别过程中报错"""
        QMessageBox.warning(self, "识别出错", f"OCR 运行出错: {error_msg}")
        self.btn_select.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HighSchoolEnglishAI()
    window.show()
    sys.exit(app.exec())
    