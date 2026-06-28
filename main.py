# -*- coding: utf-8 -*-
"""
高中/高考英语单词助手 v1.0
【性能改善说明】：引入 QThread 异步调度，减少主线程阻塞。
"""
import sys
import os
import re
import json
import random
import traceback
import base64
import datetime
import hashlib
import threading
import PySide6

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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
    from watermark_modes import parse_watermark_args
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

# ============ [6. QThread Worker 异步数据加载] ============
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
            self.progress_update.emit(f"正在准备模拟练习资源...")
            with open(self.target_file, 'r', encoding='utf-8') as f:
                raw_data = f.read()
            self.progress_update.emit("正在解析模拟练习结构...")
            parsed_data = _internal_full_exam_parser(raw_data)
            self.result_ready.emit(parsed_data)
        except Exception as e:
            self.error_occurred.emit(f"整卷模拟练习挂载失败: {e}\n{traceback.format_exc()}")
        finally:
            self.finished.emit()


# ============ [7. 主窗口核心完全体] ============
class HighSchoolEnglishAI(QMainWindow):
    _data_mutex = QMutex()

    def __init__(self):
        super().__init__()
        print("[DEBUG] HighSchoolEnglishAI.__init__ entered")
        self.watermark_settings = getattr(QtWidgets.QApplication.instance(), "watermark_settings", None)
        self.watermark_mode = getattr(self.watermark_settings, "mode", "licensed")
        # 🎯 👑 注入 5大任务之：软件全局品牌名称更名
        self.setWindowTitle("高中/高考英语单词助手 v1.0")
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
        self._setup_notice_button()
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

    def _on_loader_error(self, loader_name, message=None):
        if message is None:
            message = loader_name
            loader_name = ""
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

    def _setup_notice_button(self):
        nav_layout = self.ui_root.findChild(QtWidgets.QVBoxLayout, "nav_v_layout")
        if nav_layout is None:
            return
        self.btn_user_notice = QPushButton("用户须知与免责声明")
        self.btn_user_notice.setObjectName("btn_user_notice")
        self.btn_user_notice.setMinimumHeight(52)
        self.btn_user_notice.clicked.connect(lambda: show_user_notice_dialog(require_accept=False))
        self.btn_version_info = QPushButton("版本与授权信息")
        self.btn_version_info.setObjectName("btn_version_info")
        self.btn_version_info.setMinimumHeight(52)
        self.btn_version_info.clicked.connect(lambda: show_version_info_dialog(self))
        insert_index = max(0, nav_layout.count() - 1)
        nav_layout.insertWidget(insert_index, self.btn_user_notice)
        nav_layout.insertWidget(insert_index + 1, self.btn_version_info)

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
        path = get_resource_path("data/模拟试卷")
        if not os.path.exists(path):
            print(f"[整卷模拟] 未找到目录: {path}")
            QMessageBox.warning(self, "出厂提示", "未找到本地模拟试卷数据目录。")
            return
        files = [f for f in os.listdir(path) if f.endswith(".txt")]
        print(f"[整卷模拟] 目标目录: {path}")
        print(f"[整卷模拟] 发现试卷文件: {files}")
        if not files:
            print(f"[整卷模拟] 目录中没有 .txt 试卷文件")
            QMessageBox.information(self, "提示", "模拟试卷目录下暂无有效练习资源。")
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

        loading_label = QtWidgets.QLabel("正在解析整卷模拟练习...")
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
        self.full_exam_worker.set_exam_file(os.path.join(get_resource_path("data/模拟试卷"), random.choice(files)))
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
        print("[整卷模拟] 已解析完毕，开始构建界面...")
        with QMutexLocker(self._data_mutex):
            try:
                self.full_view = HSEExamSystem(parsed_data)
                self.full_exam_index = self.stack.addWidget(self.full_view)
                self.stack.setCurrentIndex(self.full_exam_index)
                self.nav_button_target_map["btn_nav_full_exam"] = self.full_exam_index
                self._update_nav_button_styles(self.full_exam_index)
                print(f"[整卷模拟] 界面构建成功，索引={self.full_exam_index}")
            except Exception as e:
                print(f"[整卷模拟错误] 界面构建失败: {e}")
                QMessageBox.critical(self, "异步加载熔断", f"整卷模拟界面构建失败: {e}")

    def _on_full_exam_error(self, message):
        if hasattr(self, '_full_exam_loading_dialog') and self._full_exam_loading_dialog:
            self._full_exam_loading_dialog.done(0)
            self._full_exam_loading_dialog = None
        print(f"[整卷模拟错误] {message}")
        QMessageBox.critical(self, "异步加载熔断", message)

    def _apply_sidebar_style(self):
        self.inactive_nav_style = """
            QPushButton { min-height: 55px; border-radius: 12px; text-align: left; padding-left: 20px; font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 15px; font-weight: bold; background-color: transparent; color: #495057; border: none; }
            QPushButton:hover { background-color: #e9ecef; }
        """
        self.active_nav_style = """
            QPushButton { min-height: 55px; border-radius: 12px; text-align: left; padding-left: 20px; font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 15px; font-weight: bold; background-color: #007bff; color: white; border: none; }
            QPushButton:hover { background-color: #0056b3; }
        """
        nav_btns = ["btn_nav_vocab", "btn_nav_core_vocab", "btn_nav_phrase_challenge", "btn_nav_phrase_list", "btn_nav_gaokao", "btn_nav_full_exam", "btn_nav_self_register", "btn_user_notice", "btn_version_info"]
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
LICENSE_PRODUCT_ID = "engmaster-ai-agent"
TOOL_DISPLAY_NAME = "高中/高考英语单词助手 v1.0"
TOOL_VERSION = "v1.0.0"
BUILD_DATE = "2026-05-30"
TERMS_VERSION = "2026.06.28"
PRIVACY_VERSION = "2026.06.28"
REFUND_VERSION = "2026.06.28"
RECOMMENDED_OS_TEXT = "Windows 10 / Windows 11 64 位系统"
LICENSE_PUBLIC_N = int(
    "a432074d3fc90a89d5ec32aa4f2816bcd25dea15cb6fdee7a6029de81a4340e4"
    "fdfd6cbe16c77fe9ceac30ccd964b3912462f68ffa4c38a73ec389ead0fc4fc8"
    "b2944414d84ed090f58d317090d80b5d185786b06757f8157d6ef80d1227d"
    "685106fd74b1d33ffcf626687f1870ea9e554f36205241d5a9bfbf09f689a"
    "10aacf7c17c79fd5b50214e93dd717055c37354e8e099f8cf98e8c7ec135"
    "3edc0f43c1afe95b754001abbc3ad763e96bd2f5c74d3cd3880f151bf5f"
    "363bf38f43fb82848fa8b211286f8d3673d8c3e6d7ec3036e8bb77555f"
    "5d0a90ca95357665b9e1d8c3c00fcdb36a6a65137a07139de668d8c3a"
    "58fad7cbf3867b2a3e6866dbfa75",
    16,
)
LICENSE_PUBLIC_E = 65537
LICENSE_API_BASE_URL = "https://shrill-wildflower-3ea1-high-school-english-auth.andrezhao.workers.dev"
LICENSE_CHECK_INTERVAL_DAYS = 7
LICENSE_REVOKE_STATUSES = {"revoked", "not_found", "expired", "machine_mismatch", "disabled"}


def _license_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _license_b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def get_license_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".HighSchoolEnglishHelper", "licensing.dat")


def _license_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _parse_license_time(value: str):
    if not value:
        return None
    try:
        normalized = str(value).replace("Z", "+00:00")
        parsed = datetime.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed
    except Exception:
        return None


def _license_check_due(license_data: dict) -> bool:
    last_check = _parse_license_time(str(license_data.get("last_check_time", "")))
    if last_check is None:
        return True
    age = datetime.datetime.now(datetime.timezone.utc) - last_check
    return age >= datetime.timedelta(days=LICENSE_CHECK_INTERVAL_DAYS)


def _load_license_data(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_license_data(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _extract_activation_code(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    direct = data.get("activation_code") or data.get("code")
    if direct:
        return str(direct).strip()
    for key in ("license", "license_data", "data", "payload"):
        nested = data.get(key)
        if isinstance(nested, dict):
            found = nested.get("activation_code") or nested.get("code")
            if found:
                return str(found).strip()
    return ""


def _extract_license_id(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    direct = data.get("license_id") or data.get("id")
    if direct:
        return str(direct).strip()
    for key in ("license", "license_data", "data", "payload"):
        nested = data.get(key)
        if isinstance(nested, dict):
            found = nested.get("license_id") or nested.get("id")
            if found:
                return str(found).strip()
    return ""


def _license_status(data: dict) -> str:
    if not isinstance(data, dict):
        return "invalid_response"
    status = data.get("status")
    if status:
        return str(status).strip().lower()
    if data.get("ok") is True or data.get("valid") is True or data.get("auth") is True:
        return "active"
    if data.get("ok") is False or data.get("valid") is False or data.get("auth") is False:
        raw_status = str(data.get("msg") or data.get("message") or data.get("error") or "denied").strip().lower()
        if "not" in raw_status and "found" in raw_status:
            return "not_found"
        if "revok" in raw_status:
            return "revoked"
        if "expire" in raw_status:
            return "expired"
        if "machine" in raw_status or "device" in raw_status or "fingerprint" in raw_status:
            return "machine_mismatch"
        return "denied"
    return "active" if _extract_activation_code(data) else "invalid_response"


def _post_license_api(action: str, payload: dict) -> dict:
    import requests

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"EngMasterLicenseClient/{TOOL_VERSION}",
    }
    request_payload = dict(payload)
    request_payload["action"] = action
    urls = [
        f"{LICENSE_API_BASE_URL.rstrip('/')}/{action}",
        LICENSE_API_BASE_URL.rstrip("/"),
    ]
    last_error = None
    for url in urls:
        try:
            response = requests.post(url, json=request_payload, headers=headers, timeout=15)
            if response.status_code == 404 and url != urls[-1]:
                continue
            try:
                data = response.json()
            except Exception:
                data = {"ok": False, "status": "invalid_response", "message": response.text[:300]}
            data.setdefault("http_status", response.status_code)
            return data
        except Exception as e:
            last_error = e
    raise RuntimeError(str(last_error) if last_error else "license api request failed")


def get_machine_id() -> str:
    parts = []
    try:
        import platform

        parts.append(platform.node())
        parts.append(platform.system())
        parts.append(platform.machine())
    except Exception:
        pass

    try:
        import uuid

        parts.append(str(uuid.getnode()))
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                parts.append(str(machine_guid))
        except Exception:
            pass

    material = "|".join(part.strip().lower() for part in parts if str(part).strip())
    digest = hashlib.sha256(("EngMaster-AI-Agent-machine-v1|" + material).encode("utf-8")).hexdigest().upper()
    compact = digest[:32]
    return "-".join(compact[i:i + 8] for i in range(0, len(compact), 8))


def get_os_compatibility_status():
    if sys.platform != "win32":
        return False, "当前不是 Windows 系统。本工具推荐在 Windows 10 / Windows 11 64 位系统中使用。"
    try:
        import platform

        release = platform.release()
        arch = platform.machine().lower()
        is_supported_release = release in {"10", "11"}
        is_64_bit = "64" in arch or arch in {"amd64", "x86_64"}
        if is_supported_release and is_64_bit:
            return True, f"当前系统符合推荐环境：Windows {release} 64 位。"
        return False, (
            f"当前系统环境可能不在推荐范围内：Windows {release} / {platform.machine()}。"
            f"本工具推荐使用 {RECOMMENDED_OS_TEXT}。"
        )
    except Exception:
        return False, f"无法确认当前系统环境。本工具推荐使用 {RECOMMENDED_OS_TEXT}。"


def show_os_compatibility_warning(parent=None):
    ok, message = get_os_compatibility_status()
    if not ok:
        QtWidgets.QMessageBox.warning(parent, "系统环境提示", message + "\n\n继续使用可能出现兼容性问题。")


def verify_activation_code(activation_code: str, machine_id: str):
    try:
        activation_code = activation_code.strip()
        if activation_code.startswith("EM2-"):
            signature_bytes = _license_b64decode(activation_code[4:])
            signature_int = int.from_bytes(signature_bytes, "big")
            payload_bytes = f"{LICENSE_PRODUCT_ID}|{machine_id}|v2".encode("utf-8")
            digest_int = int.from_bytes(hashlib.sha256(payload_bytes).digest(), "big")
            if pow(signature_int, LICENSE_PUBLIC_E, LICENSE_PUBLIC_N) != digest_int:
                return False, "激活码与当前电脑不匹配。"
            return True, {"product": LICENSE_PRODUCT_ID, "machine_id": machine_id, "version": 2}

        payload_part, signature_part = activation_code.strip().split(".", 1)
        payload_bytes = _license_b64decode(payload_part)
        signature_bytes = _license_b64decode(signature_part)
        signature_int = int.from_bytes(signature_bytes, "big")
        digest_int = int.from_bytes(hashlib.sha256(payload_bytes).digest(), "big")
        if pow(signature_int, LICENSE_PUBLIC_E, LICENSE_PUBLIC_N) != digest_int:
            return False, "激活码签名无效。"

        payload = json.loads(payload_bytes.decode("utf-8"))
        if payload.get("product") != LICENSE_PRODUCT_ID:
            return False, "激活码不适用于当前软件。"
        if payload.get("machine_id") != machine_id:
            return False, "激活码与当前电脑不匹配。"
        return True, payload
    except Exception:
        return False, "激活码格式无效。"


def load_license_file(path: str, machine_id: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        activation_code = str(data.get("activation_code", "")).strip()
        ok, _ = verify_activation_code(activation_code, machine_id)
        return ok
    except Exception as e:
        print(f"[DEBUG] license read/verify error: {e}")
        return False


def save_license_file(path: str, machine_id: str, activation_code: str, cloud_data=None, purchase_code=""):
    now = _license_now()
    cloud_data = cloud_data if isinstance(cloud_data, dict) else {}
    license_data = {
        "version": 2,
        "product": LICENSE_PRODUCT_ID,
        "tool_name": TOOL_DISPLAY_NAME,
        "tool_version": TOOL_VERSION,
        "build_date": BUILD_DATE,
        "machine_id": machine_id,
        "activation_code": activation_code.strip(),
        "license_id": _extract_license_id(cloud_data),
        "purchase_code": str(purchase_code).strip(),
        "activated_at": now,
        "accepted_at": now,
        "last_check_time": now,
        "terms_version": TERMS_VERSION,
        "privacy_version": PRIVACY_VERSION,
        "refund_version": REFUND_VERSION,
        "cloud_status": _license_status(cloud_data),
    }
    _write_license_data(path, license_data)


def _activate_with_cloud(purchase_code: str, machine_id: str) -> dict:
    payload = {
        "purchase_code": purchase_code,
        "purchaseCode": purchase_code,
        "taobao_code": purchase_code,
        "taobaoCode": purchase_code,
        "code": purchase_code,
        "license_key": purchase_code,
        "key": purchase_code,
        "machine_id": machine_id,
        "machineId": machine_id,
        "device_id": machine_id,
        "deviceId": machine_id,
        "fingerprint": machine_id,
        "product": LICENSE_PRODUCT_ID,
        "product_id": LICENSE_PRODUCT_ID,
        "productId": LICENSE_PRODUCT_ID,
        "tool_version": TOOL_VERSION,
        "app_version": TOOL_VERSION,
        "version": TOOL_VERSION,
    }
    data = _post_license_api("activate", payload)
    status = _license_status(data)
    if status != "active":
        return {"ok": False, "status": status, "message": data.get("message") or data.get("error") or "授权码不可用。", "raw": data}
    activation_code = _extract_activation_code(data)
    if not activation_code:
        return {"ok": False, "status": "missing_activation_code", "message": "云端未返回 activation_code。", "raw": data}
    ok, message = verify_activation_code(activation_code, machine_id)
    if not ok:
        return {"ok": False, "status": "invalid_signature", "message": str(message), "raw": data}
    return {"ok": True, "activation_code": activation_code, "cloud_data": data}


def _check_with_cloud(license_data: dict, machine_id: str) -> dict:
    payload = {
        "purchase_code": license_data.get("purchase_code", ""),
        "purchaseCode": license_data.get("purchase_code", ""),
        "taobao_code": license_data.get("purchase_code", ""),
        "taobaoCode": license_data.get("purchase_code", ""),
        "code": license_data.get("purchase_code", ""),
        "license_key": license_data.get("purchase_code", ""),
        "key": license_data.get("purchase_code", ""),
        "license_id": license_data.get("license_id", ""),
        "licenseId": license_data.get("license_id", ""),
        "machine_id": machine_id,
        "machineId": machine_id,
        "device_id": machine_id,
        "deviceId": machine_id,
        "fingerprint": machine_id,
        "activation_code": license_data.get("activation_code", ""),
        "activationCode": license_data.get("activation_code", ""),
        "product": LICENSE_PRODUCT_ID,
        "product_id": LICENSE_PRODUCT_ID,
        "productId": LICENSE_PRODUCT_ID,
        "tool_version": TOOL_VERSION,
        "app_version": TOOL_VERSION,
        "version": TOOL_VERSION,
    }
    data = _post_license_api("check", payload)
    status = _license_status(data)
    return {"ok": status == "active", "status": status, "raw": data, "message": data.get("message") or data.get("error") or ""}


def _delete_license_and_exit(path: str, reason: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"[DEBUG] failed to remove license file: {e}")
    QMessageBox.critical(None, "授权已失效", f"当前授权状态无效：{reason}\n软件将退出。")
    sys.exit(0)


def _silent_cloud_check(path: str, machine_id: str, license_data: dict):
    def worker():
        try:
            result = _check_with_cloud(license_data, machine_id)
            status = result.get("status", "")
            if result.get("ok"):
                latest = dict(license_data)
                latest["last_check_time"] = _license_now()
                latest["cloud_status"] = "active"
                cloud_data = result.get("raw") or {}
                license_id = _extract_license_id(cloud_data)
                if license_id:
                    latest["license_id"] = license_id
                _write_license_data(path, latest)
                print("[DEBUG] cloud license check ok")
            elif status in LICENSE_REVOKE_STATUSES:
                print(f"[DEBUG] cloud license revoked: {status}")
                try:
                    if os.path.exists(path):
                        os.remove(path)
                finally:
                    os._exit(0)
            else:
                print(f"[DEBUG] cloud license check failed softly: {status}")
        except Exception as e:
            print(f"[DEBUG] cloud license check network/soft failure: {e}")

    threading.Thread(target=worker, daemon=True).start()


def show_activation_dialog(machine_id: str):
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("高中/高考英语单词助手 v1.0 联网激活")
    dialog.setModal(True)
    dialog.setMinimumSize(600, 320)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)

    title = QtWidgets.QLabel("高中/高考英语单词助手 v1.0 联网激活")
    title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
    layout.addWidget(title)

    hint = QtWidgets.QLabel("请输入淘宝购买码。软件会联网完成授权绑定，激活成功后日常可离线使用，并按约定周期进行授权状态校验。")
    hint.setWordWrap(True)
    hint.setStyleSheet("font-size: 14px; color: #374151;")
    layout.addWidget(hint)

    machine_row = QtWidgets.QHBoxLayout()
    machine_input = QtWidgets.QLineEdit(machine_id)
    machine_input.setReadOnly(True)
    machine_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    copy_machine_button = QtWidgets.QPushButton("复制本机识别码")
    machine_row.addWidget(machine_input, 1)
    machine_row.addWidget(copy_machine_button)
    layout.addLayout(machine_row)

    purchase_label = QtWidgets.QLabel("淘宝购买码：")
    layout.addWidget(purchase_label)
    purchase_input = QtWidgets.QLineEdit()
    purchase_input.setPlaceholderText("例如：TEST-2026-DEBUG")
    purchase_input.setMinimumHeight(36)
    layout.addWidget(purchase_input)

    error_label = QtWidgets.QLabel("")
    error_label.setStyleSheet("color: #dc2626; font-size: 13px;")
    error_label.setWordWrap(True)
    layout.addWidget(error_label)

    button_row = QtWidgets.QHBoxLayout()
    button_row.addStretch(1)
    cancel_button = QtWidgets.QPushButton("退出")
    activate_button = QtWidgets.QPushButton("联网激活")
    activate_button.setDefault(True)
    button_row.addWidget(cancel_button)
    button_row.addWidget(activate_button)
    layout.addLayout(button_row)

    result = {"purchase_code": None}

    def copy_machine_id():
        QtWidgets.QApplication.clipboard().setText(machine_id)
        copy_machine_button.setText("已复制")

    def accept_purchase_code():
        purchase_code = purchase_input.text().strip()
        if not purchase_code:
            error_label.setText("请输入淘宝购买码。")
            return
        result["purchase_code"] = purchase_code
        dialog.accept()

    copy_machine_button.clicked.connect(copy_machine_id)
    cancel_button.clicked.connect(dialog.reject)
    activate_button.clicked.connect(accept_purchase_code)
    purchase_input.returnPressed.connect(accept_purchase_code)

    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        return result["purchase_code"]
    return None

def get_legal_notice_text() -> str:
    return (
        f"《用户须知与免责声明》\n"
        f"版本号：{TERMS_VERSION}\n"
        f"隐私说明版本：{PRIVACY_VERSION}\n"
        f"退款说明版本：{REFUND_VERSION}\n"
        f"生效日期：{BUILD_DATE}\n\n"
        "欢迎使用高中/高考英语单词助手 v1.0。请您在使用前仔细阅读以下内容。\n\n"
        "1. 工具定位\n"
        "本工具仅作为英语学习、复习和练习辅助使用，主要用于词汇、短语、不规则动词和练习内容的整理与复习。"
        "本工具不属于官方教学系统、考试系统或认证软件，也不代表任何学校、考试机构或官方单位。\n\n"
        "2. 学习效果说明\n"
        "本工具旨在帮助用户提高复习效率，但学习效果因个人基础、学习时间、使用方法等因素而异。"
        "本工具不承诺任何考试成绩、提分幅度、录取结果或学习结果。\n\n"
        "3. 内容说明\n"
        "本工具中的词汇、短语、例句、解析、练习内容等仅供学习参考。由于资料整理、版本差异或输入错误等原因，"
        "内容可能存在不完善之处。用户应结合教材、课堂内容、教师指导及官方考试要求进行学习和判断。\n\n"
        "本工具内置练习题为模拟训练内容，不代表真实考试题目，不构成考试预测、押题承诺或提分保证。\n\n"
        "4. 使用说明\n"
        "请用户在正常电脑环境下使用本工具。因系统环境、第三方安全工具拦截、误删文件、非正常修改工具文件、"
        "非官方渠道获取等原因导致无法正常使用的，可联系客服协助排查。\n"
        f"本工具推荐使用环境为：{RECOMMENDED_OS_TEXT}。Windows 7、Windows 8、精简版系统、受限账户环境、"
        "网吧或学校机房受限系统、虚拟机环境、ARM 版 Windows、Mac、iPad、手机、安卓平板等环境暂不作为推荐环境，"
        "可能出现无法启动、无法激活、界面异常或数据保存异常等情况。\n\n"
        "5. 使用限制与设备绑定\n"
        "本工具采用单机使用方式。一个购买码原则上仅限绑定一台电脑使用。购买码一经绑定设备后，如用户更换电脑、"
        "重装系统、更换主板或因系统环境变化导致本机识别码改变，可能需要重新授权或通过购买平台联系客服处理。"
        "未经许可，请勿转卖、共享、破解、修改、打包传播或用于其他商业分发行为。\n\n"
        "6. 隐私与本机识别码说明\n"
        "本工具为完成单机激活，会在本机生成本机识别码。本机识别码主要由设备环境信息经哈希计算生成，"
        "用于判断激活码是否适用于当前电脑。用户通过购买平台向客服提供本机识别码时，本方仅将其用于生成、"
        "核验和处理激活授权，不用于广告推广、用户画像或其他无关用途。本方会在合理必要范围内保存订单信息、"
        "本机识别码及激活处理记录，用于售后、换绑核验和纠纷处理。\n\n"
        "7. 本地数据\n"
        "本工具的错词记录、自主词库、学习记录或使用配置等数据主要保存在用户本机。删除软件、清理系统文件、"
        "重装系统、更换设备、磁盘损坏或用户误删文件，可能导致本地学习数据丢失。请用户自行妥善备份重要学习数据。"
        "因上述原因造成的本地学习数据丢失，不属于软件质量问题；本方可尽力协助排查，但不保证完全恢复。\n\n"
        "8. 退款说明\n"
        "本工具属于数字化学习辅助工具，具有可复制、可下载、可激活使用的特点。一经发送下载链接、提供安装包、"
        "生成或发送专属激活码、或完成激活后，非工具自身质量问题原则上不支持无理由退款。"
        "如因本工具自身原因导致无法正常安装、激活或使用，请先通过购买平台联系客服处理；经客服排查确认确属"
        "工具自身问题且无法解决的，可按平台规则协商退款或处理。因用户电脑系统环境、第三方安全工具拦截、"
        "用户误删文件、非官方渠道获取、擅自修改文件、不会操作但拒绝配合排查、购买后主观不想使用、"
        "使用非推荐系统环境等原因导致的问题，原则上不作为退款理由。\n\n"
        "9. 服务支持\n"
        "如使用过程中遇到安装、激活或功能问题，请通过购买平台联系客服，并提供订单信息、问题截图和本机识别码，"
        "以便协助处理。\n\n"
        "10. 责任说明\n"
        "在法律允许范围内，本工具按现状提供学习辅助服务。本方不对因使用或无法使用本工具导致的考试结果不理想、"
        "学习计划变化、间接损失等承担责任。但依法不能免除的责任除外。\n\n"
        "11. 同意使用\n"
        "用户继续安装、激活或使用本工具，即表示已阅读、理解并同意以上内容。"
    )


def show_version_info_dialog(parent=None):
    machine_id = get_machine_id()
    license_path = get_license_path()
    license_status = "未检测到有效授权"
    license_data = {}
    if os.path.exists(license_path):
        try:
            with open(license_path, "r", encoding="utf-8") as f:
                license_data = json.load(f)
            activation_code = str(license_data.get("activation_code", "")).strip()
            ok, _ = verify_activation_code(activation_code, machine_id)
            license_status = "已激活" if ok else "授权文件无效或不属于当前电脑"
        except Exception:
            license_status = "授权文件读取失败"

    info_text = (
        f"工具名称：{TOOL_DISPLAY_NAME}\n"
        f"当前版本：{TOOL_VERSION}\n"
        f"构建日期：{BUILD_DATE}\n"
        f"推荐系统：{RECOMMENDED_OS_TEXT}\n"
        f"授权方式：单机绑定激活\n"
        f"授权状态：{license_status}\n"
        f"本机识别码：{machine_id}\n\n"
        f"免责声明版本：{TERMS_VERSION}\n"
        f"隐私说明版本：{PRIVACY_VERSION}\n"
        f"退款说明版本：{REFUND_VERSION}\n"
        f"已同意条款时间：{license_data.get('accepted_at', '未记录')}\n"
        f"激活时间：{license_data.get('activated_at', '未记录')}\n"
    )

    QtWidgets.QMessageBox.information(parent, "版本与授权信息", info_text)


def show_user_notice_dialog(require_accept=True):
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("用户须知与免责声明")
    dialog.setModal(True)
    dialog.setMinimumSize(640, 520)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)

    title = QtWidgets.QLabel("用户须知与免责声明")
    title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
    layout.addWidget(title)

    notice_text = QtWidgets.QTextEdit()
    notice_text.setReadOnly(True)
    notice_text.setPlainText(get_legal_notice_text())
    notice_text.setStyleSheet("font-size: 14px;")
    layout.addWidget(notice_text, 1)

    button_row = QtWidgets.QHBoxLayout()
    button_row.addStretch(1)
    if require_accept:
        agree_checkbox = QtWidgets.QCheckBox("我已阅读、理解并同意以上《用户须知与免责声明》")
        agree_checkbox.setStyleSheet("font-size: 14px;")
        layout.addWidget(agree_checkbox)

        cancel_button = QtWidgets.QPushButton("退出")
        continue_button = QtWidgets.QPushButton("继续激活")
        continue_button.setEnabled(False)
        continue_button.setDefault(True)
        button_row.addWidget(cancel_button)
        button_row.addWidget(continue_button)

        agree_checkbox.toggled.connect(continue_button.setEnabled)
        cancel_button.clicked.connect(dialog.reject)
        continue_button.clicked.connect(dialog.accept)
    else:
        close_button = QtWidgets.QPushButton("关闭")
        close_button.setDefault(True)
        button_row.addWidget(close_button)
        close_button.clicked.connect(dialog.accept)
    layout.addLayout(button_row)

    return dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted


def check_licensing_gate():
    print("[DEBUG] check_licensing_gate start")
    license_dir = os.path.join(os.path.expanduser("~"), ".HighSchoolEnglishHelper")
    license_path = os.path.join(license_dir, "licensing.dat")
    machine_id = get_machine_id()

    if os.path.exists(license_path):
        try:
            license_data = _load_license_data(license_path)
            activation_code = str(license_data.get("activation_code", "")).strip()
            ok, message = verify_activation_code(activation_code, machine_id)
            if ok:
                print("[DEBUG] local machine-bound license verified")
                if _license_check_due(license_data):
                    print("[DEBUG] cloud license check is due; starting silent check")
                    _silent_cloud_check(license_path, machine_id, license_data)
                return True
            print(f"[DEBUG] local license invalid: {message}")
        except Exception as e:
            print(f"[DEBUG] existing license read/verify error: {e}")

    if not show_user_notice_dialog():
        sys.exit(0)

    while True:
        purchase_code = show_activation_dialog(machine_id)
        if not purchase_code:
            sys.exit(0)
        try:
            result = _activate_with_cloud(purchase_code, machine_id)
        except Exception as e:
            QMessageBox.warning(None, "联网激活失败", f"无法连接授权服务器，请检查网络后重试。\n\n{e}")
            continue

        if not result.get("ok"):
            status = result.get("status", "unknown")
            message = result.get("message", "购买码无效或不可用。")
            QMessageBox.warning(None, "激活失败", f"云端返回：{status}\n{message}")
            continue

        try:
            os.makedirs(license_dir, exist_ok=True)
            save_license_file(
                license_path,
                machine_id,
                result["activation_code"],
                cloud_data=result.get("cloud_data") or {},
                purchase_code=purchase_code,
            )
            QMessageBox.information(None, "激活成功", "当前电脑已联网激活，可以开始使用高中/高考英语单词助手 v1.0。")
            return True
        except Exception as e:
            QMessageBox.critical(None, "激活失败", f"保存授权文件失败:\n{e}")
            continue

if __name__ == "__main__":
    watermark_settings, qt_argv = parse_watermark_args(sys.argv)
    sys.argv = qt_argv
    app = QApplication(sys.argv)
    app.watermark_settings = watermark_settings
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
    QtCore.QTimer.singleShot(0, lambda: show_os_compatibility_warning(window))

    sys.exit(app.exec())
