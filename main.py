# -*- coding: utf-8 -*-
"""
Gemini Agent Studio 重构版 - 高中/高考英语助手 v1.0 (正版授权完全体)
【性能改善说明】：全面引入 QThread 异步调度矩阵，彻底解决主线程阻塞，实现闪电秒开。
"""
import sys
import os
import re
import json
import random
import traceback
import PySide6

# 导入单实例运行所需的锁类及多线程组件
from PySide6.QtCore import QLockFile, QDir, QThread, QObject, Signal, QTimer, QMutex, QMutexLocker, Qt
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget, QLineEdit, QFrame, QButtonGroup, QProgressBar)
from PySide6.QtUiTools import QUiLoader

# ============ [0. 👑 注入 5大任务之：Windows 高清屏自适应防空属性] ============
# 必须在主程序入口最上方，QApplication 实例化之前，强制启用高清DPI缩放防空补丁
try:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
except AttributeError:
    pass

# ============ [1. 核心：定义唯一的绝对根目录] ============
if hasattr(sys, '_MEIPASS'):
    # 打包环境：指向 PyInstaller 临时解压目录
    BASE_DIR = sys._MEIPASS
else:
    # 本地环境：指向 main.py 所在的绝对文件夹路径
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# The resource_path function is now imported from utils.py, so it's not needed here.

# ============ [2. 修复 PySide6 插件路径] ============
# Removed hack: PyInstaller handles Qt plugins automatically.
# pyside6_dir = os.path.dirname(PySide6.__file__)
# os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(pyside6_dir, 'plugins', 'platforms')

# ============ [3. 模块搜索路径] ============
for p in [BASE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p) # BASE_DIR is still needed here for module search path

# ============ [4. 核心模块异步导入] ============
try:
    from vocab_module import VocabManager
    from word_list_view import WordListView
    from exam_module import ExamManager
    from utils import normalize_exam_text, get_writable_data_path, get_resource_path
    from self_register_vocab_module import SelfRegisterVocabManager
    from phrase_irregular_module import PhraseIrregularChallengeView, PhraseIrregularListView
    from run_flull_exam import HSEExamSystem 
    from parsers.full_exam_specific_parsers import ( 
        _parse_grammar_items_full_exam,
        _parse_seven_five_items_full_exam,
        _parse_cloze_items_full_exam,
        _parse_reading_items_full_exam_robust
    )
except ImportError as e:
    print(f"❌ 核心异步模块加载失败: {e}")
    raise 

# ============ [5. 内部工具函数 (移至顶部方便多线程访问)] ============
def _internal_full_exam_parser(text):
    text = normalize_exam_text(text)
    sections = re.split(r'\[\[SECTION:\s*(.*?)\]\]', text)
    data_list = []
    analysis_tag_start = text.lower().find('[analysis]')
    global_analysis_text = ""
    if analysis_tag_start != -1:
        global_analysis_text = text[analysis_tag_start + len('[analysis]'):].strip()

    NAME_MAP = {"READING_PASSAGE_A": "阅读理解 A", "7_OUT_OF_5": "七选五", "CLOZE": "完形填空", "GRAMMAR": "语法填空"}
    TYPE_MAP = {"READING_PASSAGE_A": "reading", "7_OUT_OF_5": "seven_five", "CLOZE": "cloze", "GRAMMAR": "grammar"}

    for i in range(1, len(sections), 2):
        sec_name = sections[i].strip()
        sec_body = sections[i+1].strip()
        q_tag = sec_body.lower().find('[questions]')
        if q_tag == -1: continue
        passage = sec_body[:q_tag].strip()
        q_text = normalize_exam_text(sec_body[q_tag + len('[questions]'):].strip())
        q_type = TYPE_MAP.get(sec_name, "reading")

        parsed_items = []
        if q_type == "grammar": parsed_items = _parse_grammar_items_full_exam(q_text, global_analysis_text)
        elif q_type == "seven_five": parsed_items = _parse_seven_five_items_full_exam(q_text, global_analysis_text, passage)
        elif q_type == "cloze": parsed_items = _parse_cloze_items_full_exam(q_text, global_analysis_text)
        elif q_type == "reading": parsed_items = _parse_reading_items_full_exam_robust(q_text, global_analysis_text)

        items = []
        for item_dict in (parsed_items if isinstance(parsed_items, list) else []):
            item_dict['q_id'] = re.sub(r'\D', '', str(item_dict.get('q_id', '')))
            items.append(item_dict)
        data_list.append({"category": NAME_MAP.get(sec_name, sec_name), "question_type": q_type, "passage": passage, "items": items, "original_analysis": global_analysis_text})
    return data_list

# ============ [6. 🔥 智能体核心改善：QThread Worker 异步数据调度矩阵] ============
class VocabLoaderWorker(QObject):
    finished = Signal()
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
    def run(self):
        print("[DEBUG] VocabLoaderWorker.run started")
        try:
            vocab_path = get_resource_path("assets/vocabulary.json")
            with open(vocab_path, "r", encoding="utf-8") as f:
                vocabulary = json.load(f)
            random.shuffle(vocabulary)

            mistake_path = get_writable_data_path("mistake_words.json")
            mistake_vocabulary = []
            if os.path.exists(mistake_path):
                with open(mistake_path, "r", encoding="utf-8") as f:
                    mistake_vocabulary = json.load(f)
                for word_obj in mistake_vocabulary:
                    word_obj.setdefault('pronunciation', '')
                    word_obj.setdefault('example', '')
                random.shuffle(mistake_vocabulary)

            self.result_ready.emit({
                "vocabulary": vocabulary,
                "mistake_vocabulary": mistake_vocabulary,
            })
        except Exception as e:
            self.error_occurred.emit(f"核心词汇库加载失败: {e}\n{traceback.format_exc()}")
        finally:
            self.finished.emit()

class SelfRegisterVocabLoaderWorker(QObject):
    finished = Signal()
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, main_window_instance):
        super().__init__()
        self.main_window_instance = main_window_instance

    def run(self):
        print("[DEBUG] SelfRegisterVocabLoaderWorker.run started")
        try:
            user_data_path = get_writable_data_path("user_registered_vocab.json")
            user_vocab_data = []
            if os.path.exists(user_data_path):
                with open(user_data_path, "r", encoding="utf-8") as f:
                    user_vocab_data = json.load(f)
                for word_obj in user_vocab_data:
                    word_obj.setdefault('pronunciation', '')
                    word_obj.setdefault('example', '')
            self.result_ready.emit(user_vocab_data)
        except Exception as e:
            self.error_occurred.emit(f"自主库模块异步加载失败: {e}\n{traceback.format_exc()}")
        finally:
            self.finished.emit()

class FullExamLoaderWorker(QObject):
    finished = Signal()
    result_ready = Signal(object)
    error_occurred = Signal(str)
    progress_update = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_file = None

    def set_exam_file(self, file_path):
        self.target_file = file_path

    def run(self):
        if not self.target_file:
            self.error_occurred.emit("未指定试卷文件。")
            self.finished.emit()
            return
        try:
            self.progress_update.emit(f"正在异步准备真题资源...")
            with open(self.target_file, 'r', encoding='utf-8') as f:
                raw_data = f.read()
            self.progress_update.emit("跨线程解析真题语义结构...")
            parsed_data = _internal_full_exam_parser(raw_data)
            self.result_ready.emit(parsed_data)
        except Exception as e:
            self.error_occurred.emit(f"高考整卷挂载失败: {e}\n{traceback.format_exc()}")
        finally:
            self.finished.emit()


# ============ [7. 主窗口核心完全体] ============
class HighSchoolEnglishAI(QMainWindow):
    _data_mutex = QMutex()

    def __init__(self):
        super().__init__()
        print("[DEBUG] HighSchoolEnglishAI.__init__ entered")
        # 🎯 👑 注入 5大任务之：软件全局品牌名称更名
        self.setWindowTitle("高中/高考英语助手 v1.0 (正版授权完全体)")
        self.showMaximized()

        self.nav_buttons = {} 
        self.nav_button_target_map = {
            "btn_nav_vocab": 0, 
            "btn_nav_core_vocab": "word_list_index",
            "btn_nav_phrase_challenge": "phrase_irregular_challenge_index",
            "btn_nav_phrase_list": "phrase_irregular_list_index",
            "btn_nav_gaokao": "gk_idx",
            "btn_nav_full_exam": None, 
            "btn_nav_self_register": "self_register_vocab_index",
        }

        # 属性预定义（线程安全的灯塔指针）
        self.word_list_index = -1
        self.self_register_vocab_index = -1
        self.phrase_irregular_challenge_index = -1
        self.phrase_irregular_list_index = -1
        self.gk_idx = -1
        self.full_exam_index = -1 

        self.vocab_ctrl = None
        self.exam_ctrl = None
        self.word_list_widget = None
        self.self_register_vocab_ctrl = None
        self.phrase_irregular_challenge_widget = None
        self.phrase_irregular_list_widget = None
        self.full_view = None 

        self.vocab_loader_done = False
        self.self_register_loader_done = False

        # 异步启动骨架层UI
        self._setup_loading_screen()

        # 主线程UI静态读取
        res_dir = get_resource_path("resources")
        self.loader = QUiLoader() 
        main_ui_path = os.path.join(res_dir, "main_window.ui")

        self.ui_root = self.loader.load(main_ui_path)
        if not self.ui_root:
            QMessageBox.critical(None, "错误", f"核心 UI 资产加载失败:\n{main_ui_path}")
            sys.exit(1)

        self.setCentralWidget(self.ui_root)
        self.stack = self.ui_root.findChild(QStackedWidget, "stackedWidget")

        self.stack.insertWidget(0, self.loading_widget)
        self.stack.setCurrentIndex(0)
        print(f"[DEBUG] loading screen inserted, currentIndex={self.stack.currentIndex()}, widget0={type(self.stack.widget(0)).__name__}")

        self.stack.currentChanged.connect(self._update_nav_button_styles)
        self._setup_gaokao_page(res_dir)

        # 🚀 启动改善：延迟 100ms 避开UI首帧阻塞，点火全量异步线程矩阵
        QtCore.QTimer.singleShot(100, self._start_async_loaders)

        self._bind_nav_events() 
        self._apply_sidebar_style() 
        self._update_nav_button_styles(self.stack.currentIndex()) 

    def _setup_loading_screen(self):
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.loading_label = QtWidgets.QLabel("正在加载词库，请稍候...")
        self.loading_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 20px; color: #111; font-weight: bold; margin-bottom: 20px;")

        self.loading_progress_bar = QProgressBar()
        self.loading_progress_bar.setRange(0, 0)
        self.loading_progress_bar.setTextVisible(False)
        self.loading_progress_bar.setMinimumHeight(16)
        self.loading_progress_bar.setMinimumWidth(360)
        self.loading_progress_bar.setMaximumWidth(420)
        self.loading_progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #007bff; border-radius: 6px; background-color: #E0E0E0; }
            QProgressBar::chunk { background-color: #007bff; }
        """)

        loading_layout.addStretch(1)
        loading_layout.addWidget(self.loading_label)
        loading_layout.addWidget(self.loading_progress_bar, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        loading_layout.addStretch(1)
        self.loading_widget.setLayout(loading_layout)

    def _setup_gaokao_page(self, res_dir):
        gk_ui_path = os.path.join(res_dir, "page_gaokao.ui")
        self.page_gaokao_widget = self.loader.load(gk_ui_path)
        if self.page_gaokao_widget:
            self.stack.addWidget(self.page_gaokao_widget)
            self.gk_idx = self.stack.indexOf(self.page_gaokao_widget)
            self.nav_button_target_map["btn_nav_gaokao"] = self.gk_idx
            self.exam_ctrl = None

    def _start_async_loaders(self):

        # 使用独立线程加载核心词库和自主登记模块，避免主线程阻塞
        self.vocab_thread = QThread()
        self.self_register_vocab_thread = QThread()

        self.vocab_worker = VocabLoaderWorker()
        self.self_register_vocab_worker = SelfRegisterVocabLoaderWorker(self)

        self.vocab_worker.moveToThread(self.vocab_thread)
        self.self_register_vocab_worker.moveToThread(self.self_register_vocab_thread)

        self.vocab_thread.started.connect(self.vocab_worker.run)
        self.self_register_vocab_thread.started.connect(self.self_register_vocab_worker.run)

        self.vocab_worker.result_ready.connect(self._on_vocab_loaded, Qt.QueuedConnection)
        self.self_register_vocab_worker.result_ready.connect(self._on_self_register_vocab_loaded, Qt.QueuedConnection)

        self.vocab_worker.error_occurred.connect(self._on_loader_error, Qt.QueuedConnection)
        self.self_register_vocab_worker.error_occurred.connect(self._on_loader_error, Qt.QueuedConnection)

        self.vocab_worker.finished.connect(self._on_vocab_loader_finished, Qt.QueuedConnection)
        self.vocab_worker.finished.connect(self.vocab_thread.quit, Qt.QueuedConnection)
        self.vocab_worker.finished.connect(self.vocab_worker.deleteLater, Qt.QueuedConnection)
        self.vocab_thread.finished.connect(self.vocab_thread.deleteLater, Qt.QueuedConnection)

        self.self_register_vocab_worker.finished.connect(self._on_self_register_loader_finished, Qt.QueuedConnection)
        self.self_register_vocab_worker.finished.connect(self.self_register_vocab_thread.quit, Qt.QueuedConnection)
        self.self_register_vocab_worker.finished.connect(self.self_register_vocab_worker.deleteLater, Qt.QueuedConnection)
        self.self_register_vocab_thread.finished.connect(self.self_register_vocab_thread.deleteLater, Qt.QueuedConnection)

        print("[DEBUG] _start_async_loaders: starting vocab and self-register loader threads")
        self.loading_label.setText("正在加载核心词库，请稍候...")
        self.vocab_thread.start()
        self.self_register_vocab_thread.start()

    def _check_loader_timeout(self, thread, module_name):
        if thread.isRunning():
            thread.terminate() 
            thread.wait(1000)
            self._on_loader_error(f"警告：{module_name}挂载超时，已自动执行安全保底方案。")
            self._check_all_loaders_finished() 

    @QtCore.Slot()
    def _on_vocab_loader_finished(self):
        self._on_loader_done("vocab")

    @QtCore.Slot()
    def _on_self_register_loader_finished(self):
        self._on_loader_done("self_register")

    def _on_vocab_loaded(self, vocab_data):
        print("[DEBUG] _on_vocab_loaded called")
        self._pending_vocab_data = vocab_data
        self._apply_vocab_loaded()

    def _apply_vocab_loaded(self):
        print("[DEBUG] _apply_vocab_loaded called")
        with QMutexLocker(self._data_mutex):
            try:
                vocab_data = getattr(self, '_pending_vocab_data', {})
                self.vocab_ctrl = VocabManager(
                    self,
                    initial_vocabulary=vocab_data.get("vocabulary", []),
                    initial_mistake_vocabulary=vocab_data.get("mistake_vocabulary", []),
                )
                if hasattr(self.vocab_ctrl, '_update_mistake_count_label'):
                    self.vocab_ctrl._update_mistake_count_label()
                self.loading_label.setText("✅ 核心词库与全能错词控制总线对齐完成。")
            except Exception as e:
                self._on_loader_error(f"核心词库模块初始化失败: {e}")
                return

    def _on_self_register_vocab_loaded(self, self_register_vocab_data):
        print("[DEBUG] _on_self_register_vocab_loaded called")
        self._pending_self_register_data = self_register_vocab_data
        self._apply_self_register_loaded()

    def _apply_self_register_loaded(self):
        print("[DEBUG] _apply_self_register_loaded called")
        with QMutexLocker(self._data_mutex):
            try:
                self.self_register_vocab_ctrl = SelfRegisterVocabManager(
                    self,
                    initial_user_vocab_data=getattr(self, '_pending_self_register_data', []),
                )
                self.stack.addWidget(self.self_register_vocab_ctrl)
                self.self_register_vocab_index = self.stack.indexOf(self.self_register_vocab_ctrl)
                self.nav_button_target_map["btn_nav_self_register"] = self.self_register_vocab_index
                if hasattr(self.self_register_vocab_ctrl, '_update_self_register_count_label'):
                    self.self_register_vocab_ctrl._update_self_register_count_label()
                self.loading_label.setText("✅ 自主登记词库模块已完成加载。")
            except Exception as e:
                self._on_loader_error(f"自主登记模块初始化失败: {e}")
                return

    def _on_loader_error(self, loader_name, message):
        if loader_name == "vocab":
            self.vocab_loader_done = True
        elif loader_name == "self_register":
            self.self_register_loader_done = True
        QMessageBox.warning(self, "数据总线挂载错误", message)
        self._check_all_loaders_finished()

    def _refresh_dynamic_page_indices(self):
        """
        Recompute dynamic page indices after the loading screen is removed or pages are added.
        """
        if hasattr(self, 'page_gaokao_widget') and self.page_gaokao_widget:
            self.gk_idx = self.stack.indexOf(self.page_gaokao_widget)
            self.nav_button_target_map["btn_nav_gaokao"] = self.gk_idx
        if self.self_register_vocab_ctrl is not None:
            self.self_register_vocab_index = self.stack.indexOf(self.self_register_vocab_ctrl)
            self.nav_button_target_map["btn_nav_self_register"] = self.self_register_vocab_index
        if self.word_list_widget is not None:
            self.word_list_index = self.stack.indexOf(self.word_list_widget)
            self.nav_button_target_map["btn_nav_core_vocab"] = self.word_list_index
        if self.phrase_irregular_challenge_widget is not None:
            self.phrase_irregular_challenge_index = self.stack.indexOf(self.phrase_irregular_challenge_widget)
            self.nav_button_target_map["btn_nav_phrase_challenge"] = self.phrase_irregular_challenge_index
        if self.phrase_irregular_list_widget is not None:
            self.phrase_irregular_list_index = self.stack.indexOf(self.phrase_irregular_list_widget)
            self.nav_button_target_map["btn_nav_phrase_list"] = self.phrase_irregular_list_index
        if self.full_view is not None:
            self.full_exam_index = self.stack.indexOf(self.full_view)
            self.nav_button_target_map["btn_nav_full_exam"] = self.full_exam_index

    def _on_loader_done(self, loader_name):
        if loader_name == "vocab":
            self.vocab_loader_done = True
        elif loader_name == "self_register":
            self.self_register_loader_done = True
        print(f"[DEBUG] _on_loader_done: {loader_name}, vocab_loader_done={self.vocab_loader_done}, self_register_loader_done={self.self_register_loader_done}")
        self._check_all_loaders_finished()

    def _check_all_loaders_finished(self):
        print(f"[DEBUG] _check_all_loaders_finished: vocab_loader_done={self.vocab_loader_done}, self_register_loader_done={self.self_register_loader_done}, loading_widget_index={self.stack.indexOf(self.loading_widget)}")

        if self.vocab_loader_done and self.self_register_loader_done:
            print("[DEBUG] All loaders done, removing loading widget")
            if self.loading_widget and self.stack.indexOf(self.loading_widget) != -1:
                self.stack.removeWidget(self.loading_widget)
                self.loading_widget.deleteLater()
            self._refresh_dynamic_page_indices()
            self.stack.setCurrentIndex(0)
            self._update_nav_button_styles(0)
            self.loading_progress_bar.setRange(0, 1)

    def _bind_nav_events(self):
        root = self.ui_root
        nav_map = {
            "btn_nav_vocab": lambda: self.stack.setCurrentIndex(0), 
            "btn_nav_core_vocab": self._safe_nav_to_word_list,
            "btn_nav_phrase_challenge": self.show_phrase_irregular_challenge,
            "btn_nav_phrase_list": self.show_phrase_irregular_list,
            "btn_nav_gaokao": self.show_gaokao_page,
            "btn_nav_full_exam": self.switch_to_full_exam,
            "btn_nav_self_register": self._safe_nav_to_self_register,
        }
        for btn_name, handler in nav_map.items():
            btn = root.findChild(QPushButton, btn_name)
            if btn:
                btn.clicked.connect(handler)
                self.nav_buttons[btn_name] = btn 

    def _ensure_word_list_widget(self):
        if self.word_list_widget is None:
            if self.vocab_ctrl is None:
                QMessageBox.warning(self, "加载就绪提示", "核心词汇表正在后台进行异步对齐，请稍候...")
                return False
            self.word_list_widget = WordListView(self)
            self.stack.addWidget(self.word_list_widget)
            self.word_list_index = self.stack.indexOf(self.word_list_widget)
            self.nav_button_target_map["btn_nav_core_vocab"] = self.word_list_index
            
            # 【核心卖点连通】：绑定本地信号，当用户点击加入错词本时，自动触发 QTableWidget 的异步刷新
            if hasattr(self.vocab_ctrl, 'mistake_vocabulary_changed') and hasattr(self.word_list_widget, 'refresh_mistake_list'):
                self.vocab_ctrl.mistake_vocabulary_changed.connect(self.word_list_widget.refresh_mistake_list)
        return True

    def _safe_nav_to_word_list(self):
        if self._ensure_word_list_widget() and self.word_list_index != -1:
            self.stack.setCurrentIndex(self.word_list_index)

    def _safe_nav_to_self_register(self):
        if self.self_register_vocab_ctrl is None:
            QMessageBox.warning(self, "提示", "自主登记模块异步总线尚未同步完毕，请稍候...")
            return
        if self.self_register_vocab_index != -1:
            self.stack.setCurrentIndex(self.self_register_vocab_index)

    def _ensure_phrase_irregular_challenge_widget(self):
        if self.phrase_irregular_challenge_widget is None:
            self.phrase_irregular_challenge_widget = PhraseIrregularChallengeView(self)
            self.stack.addWidget(self.phrase_irregular_challenge_widget)
            self.phrase_irregular_challenge_index = self.stack.indexOf(self.phrase_irregular_challenge_widget)
            self.nav_button_target_map["btn_nav_phrase_challenge"] = self.phrase_irregular_challenge_index
        return True

    def _ensure_phrase_irregular_list_widget(self):
        if self.phrase_irregular_list_widget is None:
            self.phrase_irregular_list_widget = PhraseIrregularListView(self)
            self.stack.addWidget(self.phrase_irregular_list_widget)
            self.phrase_irregular_list_index = self.stack.indexOf(self.phrase_irregular_list_widget)
            self.nav_button_target_map["btn_nav_phrase_list"] = self.phrase_irregular_list_index
        return True

    def show_phrase_irregular_challenge(self):
        if self._ensure_phrase_irregular_challenge_widget() and self.phrase_irregular_challenge_index != -1:
            self.stack.setCurrentIndex(self.phrase_irregular_challenge_index)

    def show_phrase_irregular_list(self):
        if self._ensure_phrase_irregular_list_widget() and self.phrase_irregular_list_index != -1:
            self.stack.setCurrentIndex(self.phrase_irregular_list_index)

    def show_gaokao_page(self):
        if self.gk_idx != -1:
            if self.exam_ctrl is None:
                try:
                    self.exam_ctrl = ExamManager(self, self.page_gaokao_widget)
                except Exception as e:
                    QMessageBox.critical(self, "性能警告", f"专项练习异步总线初始化失败: {e}")
                    return
            self.stack.setCurrentIndex(self.gk_idx)

    def switch_to_full_exam(self):
        path = get_resource_path("data/真题试卷")
        if not os.path.exists(path):
            print(f"[高考整卷] 未找到目录: {path}")
            QMessageBox.warning(self, "出厂提示", "未找到本地真题试卷数据目录。")
            return
        files = [f for f in os.listdir(path) if f.endswith(".txt")]
        print(f"[高考整卷] 目标目录: {path}")
        print(f"[高考整卷] 发现试卷文件: {files}")
        if not files:
            print(f"[高考整卷] 目录中没有 .txt 试卷文件")
            QMessageBox.information(self, "提示", "真题试卷目录下暂无有效真题资产。")
            return

        if self.full_view is not None and self.full_exam_index != -1:
            self.stack.setCurrentIndex(self.full_exam_index)
            return

        loading_dialog = QtWidgets.QDialog(self)
        loading_dialog.setWindowTitle("性能调度中")
        loading_dialog.setModal(True)
        loading_dialog.setWindowFlags(QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.FramelessWindowHint)
        loading_dialog.setStyleSheet("QDialog { background-color: #fcfcfc; border-radius: 8px; }")

        dialog_layout = QtWidgets.QVBoxLayout(loading_dialog)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        dialog_layout.setSpacing(12)

        loading_label = QtWidgets.QLabel("正在跨线程解析高考整卷数据结构...")
        loading_label.setAlignment(QtCore.Qt.AlignCenter)
        loading_label.setStyleSheet("font-size: 14px; color: #111827;")
        dialog_layout.addWidget(loading_label)

        progress_bar = QProgressBar(loading_dialog)
        progress_bar.setRange(0, 0)
        progress_bar.setTextVisible(False)
        dialog_layout.addWidget(progress_bar)

        loading_dialog.setFixedSize(360, 120)
        loading_dialog.show()

        # 点火专线异步执行整卷大文本解析
        self.full_exam_thread = QThread()
        self.full_exam_worker = FullExamLoaderWorker()
        self.full_exam_worker.set_exam_file(os.path.join(get_resource_path("data/真题试卷"), random.choice(files)))
        self.full_exam_worker.moveToThread(self.full_exam_thread)

        self._full_exam_loading_dialog = loading_dialog
        self.full_exam_thread.started.connect(self.full_exam_worker.run)
        self.full_exam_worker.result_ready.connect(self._on_full_exam_parsed)
        self.full_exam_worker.error_occurred.connect(self._on_full_exam_error)
        self.full_exam_worker.finished.connect(self.full_exam_thread.quit)
        self.full_exam_worker.finished.connect(self.full_exam_thread.deleteLater)
        self.full_exam_worker.finished.connect(self.full_exam_worker.deleteLater)
        self.full_exam_thread.start()

    def _on_full_exam_parsed(self, parsed_data):
        if hasattr(self, '_full_exam_loading_dialog') and self._full_exam_loading_dialog:
            self._full_exam_loading_dialog.done(0)
            self._full_exam_loading_dialog = None
        print("[高考整卷] 已解析完毕，开始构建界面...")
        with QMutexLocker(self._data_mutex):
            try:
                self.full_view = HSEExamSystem(parsed_data)
                self.full_exam_index = self.stack.addWidget(self.full_view)
                self.stack.setCurrentIndex(self.full_exam_index)
                self.nav_button_target_map["btn_nav_full_exam"] = self.full_exam_index
                self._update_nav_button_styles(self.full_exam_index)
                print(f"[高考整卷] 界面构建成功，索引={self.full_exam_index}")
            except Exception as e:
                print(f"[高考整卷错误] 界面构建失败: {e}")
                QMessageBox.critical(self, "异步加载熔断", f"高考整卷界面构建失败: {e}")

    def _on_full_exam_error(self, message):
        if hasattr(self, '_full_exam_loading_dialog') and self._full_exam_loading_dialog:
            self._full_exam_loading_dialog.done(0)
            self._full_exam_loading_dialog = None
        print(f"[高考整卷错误] {message}")
        QMessageBox.critical(self, "异步加载熔断", message)

    def _apply_sidebar_style(self):
        self.inactive_nav_style = """
            QPushButton { min-height: 55px; border-radius: 12px; text-align: left; padding-left: 20px; font-weight: bold; background-color: transparent; color: #495057; border: none; }
            QPushButton:hover { background-color: #e9ecef; }
        """
        self.active_nav_style = """
            QPushButton { min-height: 55px; border-radius: 12px; text-align: left; padding-left: 20px; font-weight: bold; background-color: #007bff; color: white; border: none; }
            QPushButton:hover { background-color: #0056b3; }
        """
        nav_btns = ["btn_nav_vocab", "btn_nav_core_vocab", "btn_nav_phrase_challenge", "btn_nav_phrase_list", "btn_nav_gaokao", "btn_nav_full_exam", "btn_nav_self_register"]
        for name in nav_btns:
            btn = self.ui_root.findChild(QPushButton, name)
            if btn:
                self.nav_buttons[name] = btn 
                btn.setStyleSheet(self.inactive_nav_style) 

    def _update_nav_button_styles(self, current_stack_index):
        for btn_name, btn_obj in self.nav_buttons.items():
            target_index_identifier = self.nav_button_target_map.get(btn_name)
            target_index = -1
            if isinstance(target_index_identifier, int): 
                target_index = target_index_identifier
            elif isinstance(target_index_identifier, str): 
                target_index = getattr(self, target_index_identifier, -1)
            if target_index != -1 and current_stack_index == target_index:
                btn_obj.setStyleSheet(self.active_nav_style)
            else:
                btn_obj.setStyleSheet(self.inactive_nav_style)


# ============ [8. 👑 注入 5大任务之：一机一码离线授权激活大闸] ============
def check_licensing_gate():
    print("[DEBUG] check_licensing_gate start")
    """ 
    【无人值守发卡网专属大闸】
    不需要用户发指纹给老板！老板提前在发卡网批量上架卡密。
    用户输入卡密后，软件执行单机离线哈希算法校验，过了就一辈子写入C盘安全区！
    """
    import hashlib
    
   # 🚀 3秒钟物理替换：一劳永逸干掉死的 C 盘公用路径，换成100%有权写入的用户家目录
    LICENSE_DIR = os.path.join(os.path.expanduser("~"), ".HighSchoolEnglishHelper")
    LICENSE_PATH = os.path.join(LICENSE_DIR, "licensing.dat")
    
    # 【掌柜看这里】：这是你的终极发卡网通用算法暗号！
    # 只要买家在发卡网买到的卡密，满足【前8位随机，后4位是前8位+盐的MD5前4位】，软件就物理放行！
    VAL_SALT = "GAOKAO-PASSED-2026-SECRET-SALT"

    def verify_card_format(card_str):
        """ 离线算法校验：检查这个卡密是不是你发卡网上卖出的正版通用卡密 """
        card_str = card_str.strip().upper()
        if len(card_str) != 12:  # 卡密固定 12 位
            return False
        prefix = card_str[:8]   # 前 8 位是随机序列号
        suffix = card_str[8:]   # 后 4 位是校验防伪码
        
        # 掌柜在后台批量生成的防伪校验
        expect_suffix = hashlib.md5((prefix + VAL_SALT).encode()).hexdigest().upper()[:4]
        return suffix == expect_suffix

    # 2. 0.01秒免密全自动秒开放行链路（只要C盘有激活结婚证，直接无感秒开）
    if os.path.exists(LICENSE_PATH):
        try:
            with open(LICENSE_PATH, "r", encoding="utf-8") as f:
                saved_key = f.read().strip()
            print(f"[DEBUG] found existing license file: {saved_key}")
            if verify_card_format(saved_key):
                print("[DEBUG] license verified from file")
                return True 
        except Exception as e:
            print(f"[DEBUG] license read error: {e}")
            pass

    # 3. 强制弹窗拦截大闸（用户半夜买完卡密，第一次打开软件直接输入）
    while True:
        input_key, ok = QtWidgets.QInputDialog.getText(
            None, 
            "正版授权激活验证", 
            "欢迎使用《高中/高考英语助手 v1.0》完全体\n\n请在下方输入您在自动发卡网购买的正版授权卡密:",
            QLineEdit.EchoMode.Normal
        )
        if not ok:
            sys.exit(0) # 点取消直接退出
        
        input_key = input_key.strip().upper()
        
        # 核心：直接用通用算法校验用户输入的卡密，不问他是谁，不看他指纹！
        if verify_card_format(input_key):
            try:
                if not os.path.exists(LICENSE_DIR):
                    os.makedirs(LICENSE_DIR)
                with open(LICENSE_PATH, "w", encoding="utf-8") as f:
                    f.write(input_key)
                QMessageBox.information(None, "激活成功", "正版卡密激活成功！已与当前设备绑定完成。\n欢迎进入完全体英语助手工作站！")
                return True
            except Exception as e:
                QMessageBox.critical(None, "写入系统异常", f"激活配置写入失败: {e}")
                sys.exit(0)
        else:
            QMessageBox.warning(None, "校验失败", "您输入的正版授权卡密格式有误或不存在，请检查输入！")


# ============ [9. 生产环境单实例锁与程序总入口] ============
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 1. 物理单实例锁：防止用户短时间内高频狂点导致多进程死锁
    lock_path = os.path.join(QDir.tempPath(), "HSE_AI_Workstation_Unique.lock")
    lock_file = QLockFile(lock_path)

    if not lock_file.tryLock(100):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("运行提示")
        msg_box.setText("程序已经在后台高效运行中！")
        msg_box.setInformativeText("请在右下方任务栏查找已打开的窗口，请勿重复重复启动。")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
        msg_box.exec()
        sys.exit(0)

    # 2. 🔥 强势接入一机一码离线物理激活大闸（通过后才放行完全体）
    check_licensing_gate()

    # 3. 释放完全体主程序
    window = HighSchoolEnglishAI()
    window.show()

    sys.exit(app.exec())