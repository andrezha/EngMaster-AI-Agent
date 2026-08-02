# -*- coding: utf-8 -*-
"""
EngMaster英语词汇分级学习平台 V1.0
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
from PySide6 import QtWidgets, QtCore, QtGui
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
    from utils import get_writable_data_path, get_resource_path, set_active_edition
    from edition_config import (
        ALL_EDITIONS,
        EDITIONS,
        PAGE_PHRASE_CHALLENGE,
        PAGE_PHRASE_LIST,
        PAGE_SELF_REGISTER,
        PAGE_VOCAB_CHALLENGE,
        PAGE_WORD_LIST,
        RELEASED_EDITION_IDS,
        TRIAL_EDITION,
        TRIAL_EDITIONS,
        edition_was_explicitly_requested,
        extract_edition_args,
        is_trial_edition,
        resolve_edition,
    )
    from watermark_modes import parse_watermark_args
    from ui_styles import apply_application_ui_baseline
except ImportError as e:
    print(f"❌ 核心异步模块加载失败: {e}")
    raise


_feature_modules_loaded = False
SETTINGS_ORGANIZATION = "EngMaster"
SETTINGS_APPLICATION = "EnglishVocabularyPlatform"
LAST_EDITION_SETTING_KEY = "edition/last_active"
VOCABULARY_SCOPE_NOTICE = (
    "本软件词汇及学习内容范围主要参考国家英语课程标准、相关英语考试大纲及公开考试要求，"
    "由开发者结合不同学习阶段的实际需求整理编排。本软件为个人开发的英语学习辅助工具，"
    "并非教育主管部门、学校或考试机构官方指定软件。"
)


def _app_settings():
    return QtCore.QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)


def load_last_edition(settings=None):
    """Return the last valid edition, or None on first launch/stale settings."""
    settings = settings or _app_settings()
    edition_id = str(settings.value(LAST_EDITION_SETTING_KEY, "") or "").strip().lower()
    return ALL_EDITIONS.get(edition_id)


def save_last_edition(edition, settings=None):
    settings = settings or _app_settings()
    config = resolve_edition(edition)
    settings.setValue(LAST_EDITION_SETTING_KEY, config.edition_id)
    settings.sync()


def load_last_trial_edition(settings=None):
    edition = load_last_edition(settings)
    return edition if edition is not None and is_trial_edition(edition) else None


def _load_feature_modules():
    """Load feature pages after the first window frame is available."""
    global _feature_modules_loaded
    global VocabManager, WordListView
    global SelfRegisterVocabManager

    if _feature_modules_loaded:
        return

    from vocab_module import VocabManager
    from word_list_view import WordListView
    from self_register_vocab_module import SelfRegisterVocabManager
    _feature_modules_loaded = True

# ============ [5. QThread Worker 异步数据加载] ============
class VocabLoaderWorker(QObject):
    finished = Signal()
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, vocabulary_path):
        super().__init__()
        self.vocabulary_path = vocabulary_path

    def run(self):
        print("[DEBUG] VocabLoaderWorker.run started")
        try:
            vocab_path = get_resource_path(self.vocabulary_path)
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

# ============ [6. 主窗口核心完全体] ============
class EngMasterApplication(QMainWindow):
    _data_mutex = QMutex()

    def __init__(self, edition=None):
        super().__init__()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            apply_application_ui_baseline(app)
        print("[DEBUG] EngMasterApplication.__init__ entered")
        self.edition = resolve_edition(edition)
        self.is_trial = is_trial_edition(self.edition)
        app = QtWidgets.QApplication.instance()
        self.license_entitlements = frozenset(
            getattr(app, "license_entitlements", frozenset()))
        self.has_formal_license = bool(self.license_entitlements)
        set_active_edition(self.edition.edition_id)
        self.watermark_settings = getattr(QtWidgets.QApplication.instance(), "watermark_settings", None)
        self.watermark_mode = getattr(self.watermark_settings, "mode", "licensed")
        self.setWindowTitle(self.edition.window_title)
        self.nav_buttons = {} 
        self._active_shared_nav_button = None
        self.nav_button_target_map = {
            "btn_nav_vocab": 0, 
            "btn_nav_core_vocab": "word_list_index",
            "btn_nav_phrase_challenge": "phrase_irregular_challenge_index",
            "btn_nav_phrase_list": "phrase_irregular_list_index",
            "btn_nav_irregular_challenge": "phrase_irregular_challenge_index",
            "btn_nav_irregular_list": "phrase_irregular_list_index",
            "btn_nav_self_register": "self_register_vocab_index",
            "btn_quick_overview": "quick_overview_index",
            "btn_learning_guide": "learning_guide_index",
            "btn_operation_guide": "operation_guide_index",
            "btn_common_questions": "common_questions_index",
            "btn_user_notice": "user_notice_index",
            "btn_version_info": "version_info_index",
            "btn_free_trial": "trial_center_index",
            "btn_switch_edition": "version_management_index",
            "btn_trial_center": "trial_center_index",
        }

        # 属性预定义（线程安全的灯塔指针）
        self.word_list_index = -1
        self.self_register_vocab_index = -1
        self.phrase_irregular_challenge_index = -1
        self.phrase_irregular_list_index = -1
        self.quick_overview_index = -1
        self.learning_guide_index = -1
        self.operation_guide_index = -1
        self.common_questions_index = -1
        self.user_notice_index = -1
        self.version_info_index = -1
        self.version_management_index = -1
        self.trial_center_index = -1

        self.vocab_ctrl = None
        self.word_list_widget = None
        self.self_register_vocab_ctrl = None
        self.phrase_irregular_challenge_widget = None
        self.phrase_irregular_list_widget = None
        self.quick_overview_widget = None
        self.learning_guide_widget = None
        self.operation_guide_widget = None
        self.common_questions_widget = None
        self.user_notice_widget = None
        self.version_info_widget = None
        self.version_management_widget = None
        self.trial_center_widget = None

        self.vocab_loader_done = False
        self.self_register_loader_done = False

        # 异步启动骨架层UI
        self._setup_loading_screen()

        res_dir = get_resource_path("resources")
        self.setCentralWidget(self.loading_widget)
        # Show only after an opaque page is attached; otherwise Windows may
        # briefly paint an empty/background window during edition changes.
        self.showMaximized()

        # Return quickly so the event loop can paint a useful loading page.
        # Main UI parsing, feature imports and page wiring happen afterwards.
        QtCore.QTimer.singleShot(200, lambda: self._finish_startup(res_dir))

    def _finish_startup(self, res_dir):
        try:
            _load_feature_modules()

            self.loader = QUiLoader()
            main_ui_path = os.path.join(res_dir, "main_window.ui")
            self.ui_root = self.loader.load(main_ui_path)
            if not self.ui_root:
                raise RuntimeError(f"核心 UI 资产加载失败:\n{main_ui_path}")

            loading_widget = self.takeCentralWidget()
            self.setCentralWidget(self.ui_root)
            self.stack = self.ui_root.findChild(QStackedWidget, "stackedWidget")
            if not self.stack:
                raise RuntimeError("核心 UI 缺少 stackedWidget")

            self.stack.insertWidget(0, loading_widget)
            self.stack.setCurrentIndex(0)
            print(f"[DEBUG] loading screen inserted, currentIndex={self.stack.currentIndex()}, widget0={type(self.stack.widget(0)).__name__}")
            self.stack.currentChanged.connect(self._update_nav_button_styles)

            self._setup_trial_mode_banner()
            self._configure_edition_ui()
            self._setup_edition_switcher()
            self._bind_nav_events()
            self._setup_notice_button()
            self._setup_scrollable_sidebar()
            self._apply_sidebar_style()
            self._update_nav_button_styles(self.stack.currentIndex())
            QtCore.QTimer.singleShot(0, self._start_async_loaders)
        except Exception as e:
            self.loading_progress_bar.setRange(0, 1)
            self.loading_label.setText("启动失败")
            QMessageBox.critical(self, "启动失败", f"功能模块加载失败:\n{e}")

    def _setup_loading_screen(self):
        self.loading_widget = QWidget()
        self.loading_widget.setStyleSheet("background-color:#f4f7fb;")
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

    def _configure_edition_ui(self):
        """Apply edition branding and hide pages that are not in this edition."""
        phrase_count, irregular_count = self._edition_phrase_irregular_counts()
        button_pages = {
            "btn_nav_vocab": PAGE_VOCAB_CHALLENGE,
            "btn_nav_core_vocab": PAGE_WORD_LIST,
            "btn_nav_phrase_challenge": PAGE_PHRASE_CHALLENGE,
            "btn_nav_phrase_list": PAGE_PHRASE_LIST,
            "btn_nav_irregular_challenge": PAGE_PHRASE_CHALLENGE,
            "btn_nav_irregular_list": PAGE_PHRASE_LIST,
            "btn_nav_self_register": PAGE_SELF_REGISTER,
        }
        suffix = "体验版" if self.is_trial else ""
        button_labels = {
            "btn_nav_vocab": f"{self.edition.base_display_name}词汇闯关\n{self.edition.word_count}词{suffix}",
            "btn_nav_core_vocab": f"{self.edition.base_display_name}词汇表\n{self.edition.word_count}词{suffix}",
            "btn_nav_phrase_challenge": f"常用短语闯关\n{phrase_count}条{suffix}",
            "btn_nav_phrase_list": f"常用短语表\n{phrase_count}条{suffix}",
            "btn_nav_irregular_challenge": f"常用不规则动词闯关\n{irregular_count}组{suffix}",
            "btn_nav_irregular_list": f"常用不规则动词表\n{irregular_count}组{suffix}",
            "btn_nav_self_register": (
                "自主登记单词\n最多30词体验版" if self.is_trial
                else "自主登记单词"),
        }
        for button_name, page_id in button_pages.items():
            button = self.ui_root.findChild(QPushButton, button_name)
            if button is None:
                continue
            button.setText(button_labels[button_name])
            button.setVisible(self.edition.page_enabled(page_id))

        nav_layout = self.ui_root.findChild(QtWidgets.QVBoxLayout, "nav_v_layout")
        if nav_layout is not None:
            ordered_names = (
                "btn_nav_core_vocab", "btn_nav_vocab",
                "btn_nav_phrase_list", "btn_nav_phrase_challenge",
                "btn_nav_irregular_list", "btn_nav_irregular_challenge",
                "btn_nav_self_register",
            )
            ordered_buttons = [
                self.ui_root.findChild(QPushButton, name) for name in ordered_names]
            for button in ordered_buttons:
                if button is not None:
                    nav_layout.removeWidget(button)
            for index, button in enumerate(ordered_buttons):
                if button is not None:
                    nav_layout.insertWidget(index, button)

        challenge_button = self.ui_root.findChild(QPushButton, "btn_challenge_regular")
        if challenge_button is not None:
            challenge_button.setText(self.edition.challenge_title)

    def _edition_phrase_irregular_counts(self):
        def visible_count(relative_path, exclude_candidates=False):
            try:
                with open(get_resource_path(relative_path), "r", encoding="utf-8") as source:
                    rows = json.load(source)
                if not isinstance(rows, list):
                    return 0
                if exclude_candidates:
                    rows = [row for row in rows if row.get("tier", "core") != "candidate"]
                return len(rows)
            except (OSError, ValueError, TypeError):
                return 0

        phrase_count = visible_count(self.edition.phrase_path, True)
        irregular_count = visible_count(self.edition.irregular_verbs_path)
        if self.is_trial:
            phrase_count = min(20, phrase_count)
            irregular_count = min(15, irregular_count)
        return phrase_count, irregular_count

    def _setup_trial_mode_banner(self):
        if not self.is_trial or hasattr(self, "trial_mode_banner"):
            return
        main_layout = self.ui_root.findChild(QtWidgets.QHBoxLayout, "main_layout")
        if main_layout is None:
            return
        main_layout.removeWidget(self.stack)
        self.trial_content_container = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(self.trial_content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.trial_mode_banner = QtWidgets.QLabel(
            f"免费体验版  ·  {self.edition.base_display_name}30词体验词库  ·  自主登记最多30词")
        self.trial_mode_banner.setObjectName("trial_mode_banner")
        self.trial_mode_banner.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.trial_mode_banner.setFixedHeight(42)
        self.trial_mode_banner.setStyleSheet(
            "background:#fef3c7; color:#92400e; border-bottom:2px solid #f59e0b; "
            "font-size:15px; font-weight:700; padding:0 14px;")
        content_layout.addWidget(self.trial_mode_banner)
        content_layout.addWidget(self.stack, 1)
        main_layout.addWidget(self.trial_content_container, 1)

    def _setup_edition_switcher(self):
        """Show the current edition and a permanent switch entry above navigation."""
        nav_layout = self.ui_root.findChild(QtWidgets.QVBoxLayout, "nav_v_layout")
        if nav_layout is None:
            return

        section_style = (
            "color:#64748b; font-size:12px; font-weight:700; "
            "padding:2px 12px 0 12px;")
        divider_style = "background:#d7dee8; border:none; margin:0 10px;"

        self.lbl_version_section = QtWidgets.QLabel("版本与体验")
        self.lbl_version_section.setObjectName("lbl_version_section")
        self.lbl_version_section.setStyleSheet(section_style)

        self.edition_switch_frame = QtWidgets.QFrame()
        self.edition_switch_frame.setObjectName("edition_switch_frame")
        self.edition_switch_frame.setStyleSheet(
            "QFrame#edition_switch_frame { background:#ecfdf5; border:none; "
            "border-radius:8px; }"
        )
        frame_layout = QtWidgets.QVBoxLayout(self.edition_switch_frame)
        frame_layout.setContentsMargins(12, 9, 12, 10)
        frame_layout.setSpacing(4)
        caption = QtWidgets.QLabel("当前学习版本")
        caption.setStyleSheet(
            "border:none; color:#64748b; font-size:11px; font-weight:700;")
        current_text = self.edition.product_title
        self.lbl_current_edition = QtWidgets.QLabel(current_text)
        self.lbl_current_edition.setObjectName("lbl_current_edition")
        self.lbl_current_edition.setWordWrap(True)
        self.lbl_current_edition.setStyleSheet(
            "border:none; color:#15803d; font-size:14px; font-weight:700;")
        self.btn_free_trial = QtWidgets.QPushButton("免费体验")
        self.btn_free_trial.setObjectName("btn_free_trial")
        self.btn_free_trial.setMinimumHeight(44)
        self.btn_free_trial.setEnabled(False)
        self.btn_free_trial.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_free_trial.clicked.connect(self.show_trial_center)

        switch_text = "正式版管理与购买"
        self.btn_switch_edition = QtWidgets.QPushButton(switch_text)
        self.btn_switch_edition.setObjectName("btn_switch_edition")
        self.btn_switch_edition.setMinimumHeight(44)
        self.btn_switch_edition.setEnabled(False)
        self.btn_switch_edition.setToolTip(
            "词库加载完成后可在主页面管理正式版和免费体验")
        self.btn_switch_edition.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_switch_edition.clicked.connect(self.show_version_management)
        frame_layout.addWidget(caption)
        frame_layout.addWidget(self.lbl_current_edition)

        self.current_edition_divider = QtWidgets.QFrame()
        self.current_edition_divider.setObjectName("current_edition_divider")
        self.current_edition_divider.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.current_edition_divider.setFixedHeight(1)
        self.current_edition_divider.setStyleSheet(divider_style)

        self.edition_nav_divider = QtWidgets.QFrame()
        self.edition_nav_divider.setObjectName("edition_nav_divider")
        self.edition_nav_divider.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.edition_nav_divider.setFixedHeight(1)
        self.edition_nav_divider.setStyleSheet(divider_style)

        self.lbl_learning_section = QtWidgets.QLabel(
            "体验版学习功能" if self.is_trial else "学习功能")
        self.lbl_learning_section.setObjectName("lbl_learning_section")
        self.lbl_learning_section.setStyleSheet(section_style)

        nav_layout.insertWidget(0, self.lbl_version_section)
        nav_layout.insertWidget(1, self.edition_switch_frame)
        nav_layout.insertWidget(2, self.current_edition_divider)
        nav_layout.insertWidget(3, self.btn_free_trial)
        nav_layout.insertWidget(4, self.btn_switch_edition)
        nav_layout.insertWidget(5, self.edition_nav_divider)
        nav_layout.insertWidget(6, self.lbl_learning_section)

    def _setup_trial_center_button(self):
        if not self.is_trial:
            return
        nav_layout = self.ui_root.findChild(QtWidgets.QVBoxLayout, "nav_v_layout")
        if nav_layout is None:
            return
        self.btn_trial_center = QtWidgets.QPushButton("免费体验中心")
        self.btn_trial_center.setObjectName("btn_trial_center")
        self.btn_trial_center.setMinimumHeight(44)
        self.btn_trial_center.clicked.connect(self.show_trial_center)
        self.nav_buttons[self.btn_trial_center.objectName()] = self.btn_trial_center
        nav_layout.insertWidget(1, self.btn_trial_center)

    def _pause_learning_before_edition_switch(self):
        if self.vocab_ctrl is not None and hasattr(self.vocab_ctrl, "learning_store"):
            self.vocab_ctrl.learning_store.pause(
                getattr(self.vocab_ctrl, "current_challenge_mode", "regular"))
        phrase_view = self.phrase_irregular_challenge_widget
        if phrase_view is not None and hasattr(phrase_view, "learning_store"):
            phrase_view.learning_store.pause(
                getattr(phrase_view, "current_category", "phrase"))

    def request_edition_switch(self):
        """Backward-compatible entry that now opens the in-app management page."""
        self.show_version_management()

    def request_trial_activation(self):
        """Trial-center purchase entry now opens the shared management page."""
        self.show_version_management()

    def open_taobao_purchase(self, edition_id=None, product_title=""):
        """Open the store homepage or a version-specific product page."""
        from purchase_config import open_taobao_purchase
        return open_taobao_purchase(
            self, edition_id=edition_id, product_title=product_title)

    def get_purchase_machine_id(self):
        """Expose the local identifier to the in-page purchase workflow."""
        return get_machine_id()

    def activate_code_from_page(self, activation_code):
        """Activate a cumulative code without reopening the legacy code dialog."""
        machine_id = self.get_purchase_machine_id()
        code = str(activation_code or "").strip()
        ok, payload = verify_activation_code(code, machine_id)
        if not ok:
            return False, f"激活码无效：{payload}"

        new_entitlements = _license_entitlements_from_payload(payload)
        current_entitlements = frozenset(self.license_entitlements)
        missing_existing = current_entitlements - new_entitlements
        if missing_existing:
            return False, (
                "这枚激活码没有包含当前已经拥有的版本："
                f"{_license_entitlement_text(missing_existing)}。"
                "请让客服提供包含原权限和新增权限的累计激活码。"
            )

        released_entitlements = frozenset(new_entitlements) & frozenset(
            RELEASED_EDITION_IDS)
        if not released_entitlements:
            return False, "激活码没有包含当前已经开放的正式版本权限。"

        try:
            save_license_file(
                get_license_path(),
                machine_id,
                code,
                purchase_code=code,
                license_payload=payload,
            )
        except Exception as exc:
            return False, f"保存授权文件失败：{exc}"

        self.license_entitlements = released_entitlements
        self.has_formal_license = True
        app = QtWidgets.QApplication.instance()
        app.license_active = True
        app.license_entitlements = released_entitlements

        # Let the success text remain visible briefly, then repaint management
        # status so newly unlocked versions turn green without reopening a dialog.
        if (self.version_management_widget is not None
                and self.stack.currentWidget() is self.version_management_widget):
            QtCore.QTimer.singleShot(
                1000, self.version_management_widget.refresh)
        return True, (
            "激活成功，已解锁："
            f"{_license_entitlement_text(released_entitlements)}。"
            "现在可以进入正式版管理选择学习版本。"
        )

    def show_version_management(self):
        if not (self.vocab_loader_done and self.self_register_loader_done):
            return
        if self.version_management_widget is None:
            from version_management import VersionManagementView
            self.version_management_widget = VersionManagementView(self)
            self.stack.addWidget(self.version_management_widget)
        else:
            self.version_management_widget.refresh()
        self.version_management_index = self.stack.indexOf(
            self.version_management_widget)
        self.nav_button_target_map["btn_switch_edition"] = (
            self.version_management_index)
        self.stack.setCurrentIndex(self.version_management_index)

    def request_version_from_management(self, edition_id):
        selected = resolve_edition(edition_id)
        if selected.edition_id == self.edition.edition_id:
            return
        if (not is_trial_edition(selected)
                and selected.edition_id not in self.license_entitlements):
            return
        self._pause_learning_before_edition_switch()
        save_last_edition(selected)
        self.btn_switch_edition.setEnabled(False)
        self._reload_for_edition(selected)

    def activate_from_management(self):
        """Accept a cumulative code and derive all released permissions from it."""
        previous_entitlements = frozenset(self.license_entitlements)
        new_entitlements = activate_license(
            self, requested_entitlements=previous_entitlements)
        if not new_entitlements:
            return
        self.license_entitlements = frozenset(new_entitlements)
        self.has_formal_license = True
        app = QtWidgets.QApplication.instance()
        app.license_active = True
        app.license_entitlements = self.license_entitlements
        newly_unlocked = self.license_entitlements - previous_entitlements
        preferred_order = ("gaokao", "zhongkao", "cet4", "cet6", "kaoyan")
        target = next(
            (key for key in preferred_order if key in newly_unlocked), None)
        if target is not None:
            self.request_version_from_management(target)
        elif self.version_management_widget is not None:
            self.version_management_widget.refresh()

    def activate_gaokao_from_management(self):
        """Compatibility alias retained for older callers."""
        self.activate_from_management()

    def request_trial_level_switch(self, edition_id):
        """Switch from one of the five cards embedded in the trial center."""
        selected = TRIAL_EDITIONS.get(str(edition_id))
        if selected is None or selected.edition_id == self.edition.edition_id:
            return
        save_last_edition(selected)
        self._pause_learning_before_edition_switch()
        self._reload_for_edition(selected)

    def _reload_for_edition(self, selected):
        """Replace this window after it has stopped using the old edition namespace."""
        app = QtWidgets.QApplication.instance()
        app.setQuitOnLastWindowClosed(False)

        # Keep one motionless, opaque surface above both windows while the old
        # data namespace is destroyed and the new one loads.  This prevents the
        # desktop, an empty native window, or changing page backgrounds from
        # flashing during a trial-level switch.
        cover = QtWidgets.QWidget(
            None,
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint,
        )
        cover.setObjectName("edition_switch_cover")
        cover.setStyleSheet("QWidget#edition_switch_cover { background:#f4f7fb; }")
        cover_layout = QtWidgets.QVBoxLayout(cover)
        cover_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        cover_title = QtWidgets.QLabel(f"正在切换到 {selected.display_name}版")
        cover_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        cover_title.setStyleSheet(
            "color:#334155; font-size:22px; font-weight:700; background:transparent;")
        cover_hint = QtWidgets.QLabel("正在准备体验内容，请稍候…")
        cover_hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        cover_hint.setStyleSheet(
            "color:#64748b; font-size:14px; margin-top:10px; background:transparent;")
        cover_layout.addWidget(cover_title)
        cover_layout.addWidget(cover_hint)
        app.edition_switch_cover = cover
        cover.showMaximized()
        cover.raise_()
        app.processEvents()

        def create_replacement():
            replacement = EngMasterApplication(selected)
            app.main_window = replacement
            app.setQuitOnLastWindowClosed(True)

        # Build the replacement only after the old window and all of its page
        # controllers are destroyed, so no old-edition timer can write through
        # the newly selected global data namespace.
        self.destroyed.connect(
            lambda *_args: QtCore.QTimer.singleShot(0, create_replacement))
        self.hide()
        self.close()
        self.deleteLater()

    def _start_async_loaders(self):

        # 使用独立线程加载核心词库和自主登记模块，避免主线程阻塞
        self.vocab_thread = QThread()
        self.self_register_vocab_thread = QThread()

        self.vocab_worker = VocabLoaderWorker(self.edition.vocabulary_path)
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
                self._sync_challenge_user_vocab_counts()
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
                self._sync_challenge_user_vocab_counts()
                self.loading_label.setText("✅ 自主登记词库模块已完成加载。")
            except Exception as e:
                self._on_loader_error(f"自主登记模块初始化失败: {e}")
                return

    def _sync_challenge_user_vocab_counts(self):
        """异步模块加载或用户词库变化后，同步闯关页的两项数量。"""
        if self.vocab_ctrl is None:
            return
        self.vocab_ctrl._load_self_registered_vocabulary()
        self.vocab_ctrl._update_mistake_count_label()
        self.vocab_ctrl._update_self_register_count_label()

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
        if self.self_register_vocab_ctrl is not None:
            self.self_register_vocab_index = self.stack.indexOf(self.self_register_vocab_ctrl)
            self.nav_button_target_map["btn_nav_self_register"] = self.self_register_vocab_index
        if self.word_list_widget is not None:
            self.word_list_index = self.stack.indexOf(self.word_list_widget)
            self.nav_button_target_map["btn_nav_core_vocab"] = self.word_list_index
        if self.phrase_irregular_challenge_widget is not None:
            self.phrase_irregular_challenge_index = self.stack.indexOf(self.phrase_irregular_challenge_widget)
            self.nav_button_target_map["btn_nav_phrase_challenge"] = self.phrase_irregular_challenge_index
            self.nav_button_target_map["btn_nav_irregular_challenge"] = self.phrase_irregular_challenge_index
        if self.phrase_irregular_list_widget is not None:
            self.phrase_irregular_list_index = self.stack.indexOf(self.phrase_irregular_list_widget)
            self.nav_button_target_map["btn_nav_phrase_list"] = self.phrase_irregular_list_index
            self.nav_button_target_map["btn_nav_irregular_list"] = self.phrase_irregular_list_index
        for button_name, widget_name, index_name in (
            ("btn_quick_overview", "quick_overview_widget", "quick_overview_index"),
            ("btn_learning_guide", "learning_guide_widget", "learning_guide_index"),
            ("btn_operation_guide", "operation_guide_widget", "operation_guide_index"),
            ("btn_common_questions", "common_questions_widget", "common_questions_index"),
            ("btn_user_notice", "user_notice_widget", "user_notice_index"),
            ("btn_version_info", "version_info_widget", "version_info_index"),
            ("btn_free_trial", "trial_center_widget", "trial_center_index"),
            ("btn_switch_edition", "version_management_widget", "version_management_index"),
        ):
            widget = getattr(self, widget_name)
            if widget is not None:
                index = self.stack.indexOf(widget)
                setattr(self, index_name, index)
                self.nav_button_target_map[button_name] = index
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
            if hasattr(self, "btn_switch_edition"):
                self.btn_switch_edition.setEnabled(True)
                self.btn_switch_edition.setToolTip(
                    "在主页面查看正式版状态和授权")
            if hasattr(self, "btn_free_trial"):
                self.btn_free_trial.setEnabled(True)
                self.btn_free_trial.setToolTip("选择初中、高考、四级、六级或考研免费体验")
            self.loading_progress_bar.setRange(0, 1)
            settings = _app_settings()
            if self.is_trial:
                self._safe_nav_to_word_list()
            elif not settings.value("guides/quick_overview_seen_v1", False, type=bool):
                self.show_quick_overview()
                settings.setValue("guides/quick_overview_seen_v1", True)
            else:
                self.stack.setCurrentIndex(0)
                self._update_nav_button_styles(0)
            app = QtWidgets.QApplication.instance()
            cover = getattr(app, "edition_switch_cover", None)
            if cover is not None:
                cover.close()
                cover.deleteLater()
                app.edition_switch_cover = None
                self.raise_()
                self.activateWindow()

    def _bind_nav_events(self):
        root = self.ui_root
        nav_map = {
            "btn_nav_vocab": lambda: self.stack.setCurrentIndex(0), 
            "btn_nav_core_vocab": self._safe_nav_to_word_list,
            "btn_nav_phrase_challenge": self.show_phrase_irregular_challenge,
            "btn_nav_phrase_list": self.show_phrase_irregular_list,
            "btn_nav_irregular_challenge": self.show_irregular_challenge,
            "btn_nav_irregular_list": self.show_irregular_list,
            "btn_nav_self_register": self._safe_nav_to_self_register,
        }
        button_pages = {
            "btn_nav_vocab": PAGE_VOCAB_CHALLENGE,
            "btn_nav_core_vocab": PAGE_WORD_LIST,
            "btn_nav_phrase_challenge": PAGE_PHRASE_CHALLENGE,
            "btn_nav_phrase_list": PAGE_PHRASE_LIST,
            "btn_nav_irregular_challenge": PAGE_PHRASE_CHALLENGE,
            "btn_nav_irregular_list": PAGE_PHRASE_LIST,
            "btn_nav_self_register": PAGE_SELF_REGISTER,
        }
        for btn_name, handler in nav_map.items():
            if not self.edition.page_enabled(button_pages[btn_name]):
                continue
            btn = root.findChild(QPushButton, btn_name)
            if btn:
                btn.clicked.connect(handler)
                self.nav_buttons[btn_name] = btn 

    def _setup_notice_button(self):
        nav_layout = self.ui_root.findChild(QtWidgets.QVBoxLayout, "nav_v_layout")
        if nav_layout is None:
            return
        self.lbl_help_section = QtWidgets.QLabel("学习帮助")
        self.lbl_help_section.setObjectName("lbl_help_section")
        self.lbl_help_section.setStyleSheet(
            "color:#64748b; font-size:12px; font-weight:700; padding:2px 12px 0 12px;")

        help_divider = self.ui_root.findChild(QtWidgets.QFrame, "nav_divider")
        if help_divider is not None:
            help_divider.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            help_divider.setFixedHeight(1)
            help_divider.setStyleSheet(
                "background:#d7dee8; border:none; margin:0 10px;")
        self.btn_quick_overview = QPushButton("60秒快速了解")
        self.btn_quick_overview.setObjectName("btn_quick_overview")
        self.btn_quick_overview.clicked.connect(self.show_quick_overview)
        self.btn_learning_guide = QPushButton("学习方法指南")
        self.btn_learning_guide.setObjectName("btn_learning_guide")
        self.btn_learning_guide.clicked.connect(self.show_learning_guide)
        self.btn_operation_guide = QPushButton("软件操作说明")
        self.btn_operation_guide.setObjectName("btn_operation_guide")
        self.btn_operation_guide.clicked.connect(self.show_operation_guide)
        self.btn_common_questions = QPushButton("常见问题")
        self.btn_common_questions.setObjectName("btn_common_questions")
        self.btn_common_questions.clicked.connect(self.show_common_questions)
        for button in (
            self.btn_quick_overview,
            self.btn_learning_guide,
            self.btn_operation_guide,
            self.btn_common_questions,
        ):
            button.setMinimumHeight(44)
            self.nav_buttons[button.objectName()] = button
        self.btn_user_notice = QPushButton("用户须知与免责声明")
        self.btn_user_notice.setObjectName("btn_user_notice")
        self.btn_user_notice.setMinimumHeight(52)
        self.btn_user_notice.clicked.connect(self.show_user_notice_page)
        self.btn_version_info = QPushButton("版本与授权信息")
        self.btn_version_info.setObjectName("btn_version_info")
        self.btn_version_info.setMinimumHeight(52)
        self.btn_version_info.clicked.connect(self.show_version_info_page)
        self.nav_buttons[self.btn_user_notice.objectName()] = self.btn_user_notice
        self.nav_buttons[self.btn_version_info.objectName()] = self.btn_version_info
        insert_index = max(0, nav_layout.count() - 1)
        nav_layout.insertWidget(insert_index, self.lbl_help_section)
        nav_layout.insertWidget(insert_index + 1, self.btn_quick_overview)
        nav_layout.insertWidget(insert_index + 2, self.btn_learning_guide)
        nav_layout.insertWidget(insert_index + 3, self.btn_operation_guide)
        nav_layout.insertWidget(insert_index + 4, self.btn_common_questions)
        nav_layout.insertWidget(insert_index + 5, self.btn_user_notice)
        nav_layout.insertWidget(insert_index + 6, self.btn_version_info)

    def _setup_scrollable_sidebar(self):
        """Keep the current edition visible and make every remaining entry reachable."""
        nav_layout = self.ui_root.findChild(QtWidgets.QVBoxLayout, "nav_v_layout")
        if nav_layout is None or hasattr(self, "sidebar_scroll"):
            return

        self.sidebar_scroll = QtWidgets.QScrollArea()
        self.sidebar_scroll.setObjectName("sidebar_scroll")
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sidebar_scroll.setStyleSheet("""
            QScrollArea#sidebar_scroll { background:transparent; border:none; }
            QScrollBar:vertical { background:#e5eaf1; width:12px; margin:2px 0; border-radius:6px; }
            QScrollBar::handle:vertical { background:#7890ad; min-height:42px; border-radius:6px; }
            QScrollBar::handle:vertical:hover { background:#2563eb; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
        """)

        scroll_content = QtWidgets.QWidget()
        scroll_content.setObjectName("sidebar_scroll_content")
        scroll_content.setStyleSheet("background:transparent;")
        self.sidebar_scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        self.sidebar_scroll_layout.setContentsMargins(0, 0, 2, 0)
        self.sidebar_scroll_layout.setSpacing(8)
        self.sidebar_scroll_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        # Version information, free trial and formal-version management stay
        # fixed. Scrolling begins exactly at the "学习功能" heading.
        while nav_layout.count() > 6:
            item = nav_layout.takeAt(6)
            widget = item.widget()
            if widget is not None:
                self.sidebar_scroll_layout.addWidget(widget)
        self.sidebar_scroll_layout.addStretch(1)
        self.sidebar_scroll.setWidget(scroll_content)

        self.sidebar_scroll_hint = QtWidgets.QPushButton("向下滚动查看更多功能  ↓")
        self.sidebar_scroll_hint.setObjectName("sidebar_scroll_hint")
        self.sidebar_scroll_hint.setFixedHeight(32)
        self.sidebar_scroll_hint.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.sidebar_scroll_hint.setToolTip("也可以把鼠标放在左侧栏内，使用滚轮浏览")
        self.sidebar_scroll_hint.setStyleSheet("""
            QPushButton { background:#dbeafe; color:#1d4ed8; border:1px solid #93c5fd;
                border-radius:8px; font-size:12px; font-weight:700; padding:0 6px; }
            QPushButton:hover { background:#bfdbfe; border-color:#3b82f6; }
            QPushButton:pressed { background:#93c5fd; }
        """)
        self.sidebar_scroll_hint.clicked.connect(self._move_sidebar_from_hint)
        bar = self.sidebar_scroll.verticalScrollBar()
        bar.rangeChanged.connect(lambda _minimum, _maximum: self._update_sidebar_scroll_hint())
        bar.valueChanged.connect(lambda _value: self._update_sidebar_scroll_hint())

        nav_layout.addWidget(self.sidebar_scroll, 1)
        nav_layout.addWidget(self.sidebar_scroll_hint)
        self._fit_sidebar_to_longest_label()
        QtCore.QTimer.singleShot(0, self._update_sidebar_scroll_hint)

    def _fit_sidebar_to_longest_label(self):
        nav_bar = self.ui_root.findChild(QtWidgets.QFrame, "nav_bar")
        if nav_bar is None:
            return
        metrics = QtGui.QFontMetrics(QtGui.QFont("Microsoft YaHei UI", 10))
        longest = 0
        for button in self.nav_buttons.values():
            for line in button.text().splitlines():
                longest = max(longest, metrics.horizontalAdvance(line))
        # Text padding, outer margins and the visible scroll bar are included.
        fitted_width = max(205, min(225, longest + 66))
        nav_bar.setMinimumWidth(fitted_width)
        nav_bar.setMaximumWidth(fitted_width)

    def _move_sidebar_from_hint(self):
        bar = self.sidebar_scroll.verticalScrollBar()
        if bar.value() >= bar.maximum():
            bar.setValue(0)
        else:
            bar.setValue(min(bar.maximum(), bar.value() + max(120, bar.pageStep() - 30)))

    def _update_sidebar_scroll_hint(self):
        if not hasattr(self, "sidebar_scroll_hint"):
            return
        bar = self.sidebar_scroll.verticalScrollBar()
        has_more = bar.maximum() > 0
        self.sidebar_scroll_hint.setVisible(has_more)
        if not has_more:
            return
        if bar.value() >= bar.maximum():
            self.sidebar_scroll_hint.setText("已到最下方 · 返回顶部  ↑")
        elif bar.value() > 0:
            self.sidebar_scroll_hint.setText("继续向下滚动查看更多  ↓")
        else:
            self.sidebar_scroll_hint.setText("向下滚动查看更多功能  ↓")

    def show_quick_overview(self):
        if self.quick_overview_widget is None:
            from guide_pages import QuickOverviewView
            self.quick_overview_widget = QuickOverviewView(self)
            self.stack.addWidget(self.quick_overview_widget)
            self.quick_overview_index = self.stack.indexOf(
                self.quick_overview_widget)
            self.nav_button_target_map["btn_quick_overview"] = (
                self.quick_overview_index)
        self.stack.setCurrentIndex(self.quick_overview_index)

    def show_learning_guide(self):
        if self.learning_guide_widget is None:
            from experience_guide import ExperienceGuideView
            self.learning_guide_widget = ExperienceGuideView(self)
            self.stack.addWidget(self.learning_guide_widget)
            self.learning_guide_index = self.stack.indexOf(
                self.learning_guide_widget)
            self.nav_button_target_map["btn_learning_guide"] = (
                self.learning_guide_index)
        self.stack.setCurrentIndex(self.learning_guide_index)

    def show_operation_guide(self):
        if self.operation_guide_widget is None:
            from guide_pages import OperationGuideView
            self.operation_guide_widget = OperationGuideView(self)
            self.stack.addWidget(self.operation_guide_widget)
            self.operation_guide_index = self.stack.indexOf(
                self.operation_guide_widget)
            self.nav_button_target_map["btn_operation_guide"] = (
                self.operation_guide_index)
        self.stack.setCurrentIndex(self.operation_guide_index)

    def show_common_questions(self):
        if self.common_questions_widget is None:
            from guide_pages import CommonQuestionsView
            self.common_questions_widget = CommonQuestionsView(self)
            self.stack.addWidget(self.common_questions_widget)
            self.common_questions_index = self.stack.indexOf(
                self.common_questions_widget)
            self.nav_button_target_map["btn_common_questions"] = (
                self.common_questions_index)
        self.stack.setCurrentIndex(self.common_questions_index)

    def show_user_notice_page(self):
        if self.user_notice_widget is None:
            from guide_pages import InformationTextView
            self.user_notice_widget = InformationTextView(
                "用户须知与免责声明",
                "请仔细阅读软件定位、内容说明、单机授权、本地数据和退款说明。",
                get_legal_notice_text(),
                "user_notice_view",
                self,
            )
            self.stack.addWidget(self.user_notice_widget)
            self.user_notice_index = self.stack.indexOf(self.user_notice_widget)
            self.nav_button_target_map["btn_user_notice"] = self.user_notice_index
        self.stack.setCurrentIndex(self.user_notice_index)

    def show_version_info_page(self):
        from guide_pages import InformationTextView
        info_text = get_version_info_text()
        if self.version_info_widget is None:
            self.version_info_widget = InformationTextView(
                "版本与授权信息",
                "查看当前软件版本、授权状态、已解锁内容和本机识别码。",
                info_text,
                "version_info_view",
                self,
            )
            self.stack.addWidget(self.version_info_widget)
            self.version_info_index = self.stack.indexOf(self.version_info_widget)
            self.nav_button_target_map["btn_version_info"] = self.version_info_index
        else:
            self.version_info_widget.set_text(info_text)
        self.stack.setCurrentIndex(self.version_info_index)

    def show_trial_center(self):
        if self.trial_center_widget is None:
            from trial_center import TrialCenterView
            self.trial_center_widget = TrialCenterView(self)
            self.stack.addWidget(self.trial_center_widget)
            self.trial_center_index = self.stack.indexOf(self.trial_center_widget)
            self.nav_button_target_map["btn_free_trial"] = self.trial_center_index
        self.stack.setCurrentIndex(self.trial_center_index)

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

    def show_word_mistake_list(self, data=None):
        if not self._ensure_word_list_widget() or self.word_list_index == -1:
            return
        self.word_list_widget.open_mistake_list(data)
        self.stack.setCurrentIndex(self.word_list_index)

    def _safe_nav_to_self_register(self):
        if self.self_register_vocab_ctrl is None:
            QMessageBox.warning(self, "提示", "自主登记模块异步总线尚未同步完毕，请稍候...")
            return
        if self.self_register_vocab_index != -1:
            self.stack.setCurrentIndex(self.self_register_vocab_index)

    def _ensure_phrase_irregular_challenge_widget(self):
        if not self.edition.page_enabled(PAGE_PHRASE_CHALLENGE):
            return False
        if self.phrase_irregular_challenge_widget is None:
            from phrase_irregular_module import PhraseIrregularChallengeView
            self.phrase_irregular_challenge_widget = PhraseIrregularChallengeView(self)
            self.stack.addWidget(self.phrase_irregular_challenge_widget)
            self.phrase_irregular_challenge_index = self.stack.indexOf(self.phrase_irregular_challenge_widget)
            self.nav_button_target_map["btn_nav_phrase_challenge"] = self.phrase_irregular_challenge_index
            self.nav_button_target_map["btn_nav_irregular_challenge"] = self.phrase_irregular_challenge_index
        return True

    def _ensure_phrase_irregular_list_widget(self):
        if not self.edition.page_enabled(PAGE_PHRASE_LIST):
            return False
        if self.phrase_irregular_list_widget is None:
            from phrase_irregular_module import PhraseIrregularListView
            self.phrase_irregular_list_widget = PhraseIrregularListView(self)
            self.stack.addWidget(self.phrase_irregular_list_widget)
            self.phrase_irregular_list_index = self.stack.indexOf(self.phrase_irregular_list_widget)
            self.nav_button_target_map["btn_nav_phrase_list"] = self.phrase_irregular_list_index
            self.nav_button_target_map["btn_nav_irregular_list"] = self.phrase_irregular_list_index
        return True

    def show_phrase_irregular_challenge(self):
        self._show_phrase_irregular_challenge_category("phrase", "btn_nav_phrase_challenge")

    def show_irregular_challenge(self):
        self._show_phrase_irregular_challenge_category("irregular", "btn_nav_irregular_challenge")

    def _show_phrase_irregular_challenge_category(self, category, nav_button):
        if self._ensure_phrase_irregular_challenge_widget() and self.phrase_irregular_challenge_index != -1:
            self._active_shared_nav_button = nav_button
            self.phrase_irregular_challenge_widget.set_entry_scope(
                "irregular" if category.startswith("irregular") else "phrase")
            self.phrase_irregular_challenge_widget._switch_category(category)
            self.stack.setCurrentIndex(self.phrase_irregular_challenge_index)
            self._update_nav_button_styles(self.phrase_irregular_challenge_index)

    def show_phrase_irregular_list(self):
        self.show_phrase_irregular_table("phrase")

    def show_irregular_list(self):
        self.show_phrase_irregular_table("irregular")

    def show_phrase_irregular_table(self, table_type):
        if not self._ensure_phrase_irregular_list_widget() or self.phrase_irregular_list_index == -1:
            return
        self.phrase_irregular_list_widget.refresh_mistake_tables()
        self.phrase_irregular_list_widget.set_entry_scope(
            "irregular" if table_type.startswith("irregular") else "phrase")
        self.phrase_irregular_list_widget._show_table(table_type)
        self._active_shared_nav_button = (
            "btn_nav_irregular_list" if table_type.startswith("irregular")
            else "btn_nav_phrase_list")
        self.stack.setCurrentIndex(self.phrase_irregular_list_index)
        self._update_nav_button_styles(self.phrase_irregular_list_index)

    def _apply_sidebar_style(self):
        self.inactive_nav_style = """
            QPushButton { min-height: 55px; border-radius: 10px; text-align: left; padding-left: 20px; font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif; font-size: 15px; font-weight: 600; background-color: transparent; color: #475569; border: 1px solid transparent; }
            QPushButton:hover { background-color: #e8f1ff; color: #1d4ed8; border-color: #dbeafe; }
        """
        self.active_nav_style = """
            QPushButton { min-height: 55px; border-radius: 10px; text-align: left; padding-left: 20px; font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif; font-size: 15px; font-weight: 600; background-color: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
            QPushButton:hover { background-color: #dbeafe; color: #1d4ed8; border-color: #bfdbfe; }
        """
        nav_btns = ["btn_free_trial", "btn_switch_edition", "btn_nav_vocab", "btn_nav_core_vocab", "btn_nav_phrase_challenge", "btn_nav_phrase_list", "btn_nav_irregular_challenge", "btn_nav_irregular_list", "btn_nav_self_register", "btn_quick_overview", "btn_learning_guide", "btn_operation_guide", "btn_common_questions", "btn_user_notice", "btn_version_info"]
        for name in nav_btns:
            btn = self.ui_root.findChild(QPushButton, name)
            if btn:
                self.nav_buttons[name] = btn 
                btn.setStyleSheet(self.inactive_nav_style) 

    def _update_nav_button_styles(self, current_stack_index):
        shared_buttons = {
            "btn_nav_phrase_challenge", "btn_nav_irregular_challenge",
            "btn_nav_phrase_list", "btn_nav_irregular_list",
        }
        for btn_name, btn_obj in self.nav_buttons.items():
            target_index_identifier = self.nav_button_target_map.get(btn_name)
            target_index = -1
            if isinstance(target_index_identifier, int): 
                target_index = target_index_identifier
            elif isinstance(target_index_identifier, str): 
                target_index = getattr(self, target_index_identifier, -1)
            shared_matches = (
                btn_name not in shared_buttons
                or btn_name == self._active_shared_nav_button)
            if target_index != -1 and current_stack_index == target_index and shared_matches:
                btn_obj.setStyleSheet(self.active_nav_style)
            else:
                btn_obj.setStyleSheet(self.inactive_nav_style)


# ============ [8. 👑 注入 5大任务之：一机一码离线授权激活大闸] ============
LICENSE_PRODUCT_ID = "engmaster-vocabulary-platform"
TOOL_DISPLAY_NAME = "EngMaster英语词汇分级学习平台 V1.0"
TOOL_VERSION = "v1.0.0"
BUILD_DATE = "2026-08-01"
TERMS_VERSION = "2026.06.28"
PRIVACY_VERSION = "2026.06.28"
REFUND_VERSION = "2026.06.28"
RECOMMENDED_OS_TEXT = "Windows 10 / Windows 11 64 位系统"
LICENSE_PUBLIC_N = int(
    "28775124575322634497630194562493205248451792233793484992462518909492031796087444659631193235143344782483730732025675973619125043891315519797328207298137327962837303041858425898732956948468058347522333942909932463217082936203298836737661621873254886770711111279670238437512397114508322120513285728053743377345990522667546431345851293680492019660724038530092135323717074630242455906633496054000548263245819585891412388129191402684716710881278766068589187373114113639112557957618530888807277659122560456937774567503707757874692756981241100528898001868420979776774112765051802987112637709752566838799945407160880000001167",
    10,
)
LICENSE_PUBLIC_E = 65537
LICENSE_FORMAT_VERSION = 3
FORMAL_EDITION_IDS = tuple(EDITIONS.keys())
LEGACY_LICENSE_ENTITLEMENTS = frozenset({"gaokao"})
LICENSE_EDITION_NAMES = {
    "zhongkao": "初中英语1600词汇版",
    "gaokao": "高考英语3800词汇版",
    "cet4": "大学英语四级4500词汇版",
    "cet6": "大学英语六级5500词汇版",
    "kaoyan": "考研英语5500词汇版",
}


def _license_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _license_b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _normalize_license_entitlements(values, *, legacy=False):
    if legacy:
        return LEGACY_LICENSE_ENTITLEMENTS
    if not isinstance(values, (list, tuple, set, frozenset)):
        return frozenset()
    normalized = []
    for value in values:
        edition_id = str(value).strip().lower()
        if edition_id not in EDITIONS:
            # A newer generator may already know a future product edition that
            # this older customer application cannot display yet.  Preserve
            # all currently supported permissions and ignore only the unknown
            # future IDs; an all-unknown code still fails as having no usable
            # entitlement.
            continue
        if edition_id not in normalized:
            normalized.append(edition_id)
    return frozenset(normalized)


def _license_entitlements_from_payload(payload):
    try:
        version = int(payload.get("version", 0))
    except (TypeError, ValueError):
        version = 0
    return _normalize_license_entitlements(
        payload.get("entitlements"), legacy=version < LICENSE_FORMAT_VERSION)


def _license_entitlement_text(entitlements):
    ordered = [
        LICENSE_EDITION_NAMES[edition_id]
        for edition_id in FORMAL_EDITION_IDS
        if edition_id in set(entitlements or ())
    ]
    return "、".join(ordered) if ordered else "无正式版本权限"


def get_license_path() -> str:
    return os.path.join(os.path.expanduser("~"), ".EngMaster", "licensing.dat")


def _license_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _load_license_data(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_license_data(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


_INVALID_HARDWARE_IDS = {
    "", "0", "NONE", "UNKNOWN", "DEFAULTSTRING", "DEFAULT",
    "TOBEFILLEDBYOEM", "NOTSPECIFIED", "NOTAPPLICABLE", "N/A",
    "SYSTEMSERIALNUMBER", "BASEBOARDSERIALNUMBER", "INVALID",
}


def _normalize_hardware_id(value) -> str:
    """Normalize an SMBIOS identifier and reject common OEM placeholders."""
    normalized = re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
    if normalized in _INVALID_HARDWARE_IDS:
        return ""
    if len(normalized) < 4 or len(set(normalized)) == 1:
        return ""
    return normalized


def _smbios_string(strings, index: int) -> str:
    if not index or index > len(strings):
        return ""
    return _normalize_hardware_id(strings[index - 1])


def _read_windows_smbios_ids() -> dict:
    """Read stable hardware IDs through the Windows firmware API.

    This is a read-only Win32 call: it does not launch PowerShell/WMIC and does
    not require administrator privileges.  An empty mapping means the firmware
    table was unavailable or contained only OEM placeholder values.
    """
    if sys.platform != "win32":
        return {}
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_table = kernel32.GetSystemFirmwareTable
        get_table.argtypes = [
            wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD]
        get_table.restype = wintypes.UINT
        provider = int.from_bytes(b"RSMB", "big")
        size = get_table(provider, 0, None, 0)
        if size < 8 or size > 16 * 1024 * 1024:
            return {}
        buffer = ctypes.create_string_buffer(size)
        received = get_table(provider, 0, buffer, size)
        if received < 8:
            return {}
        raw = bytes(buffer.raw[:received])
        table_length = int.from_bytes(raw[4:8], "little")
        table = raw[8:8 + min(table_length, len(raw) - 8)]

        result = {}
        offset = 0
        while offset + 4 <= len(table):
            structure_type = table[offset]
            structure_length = table[offset + 1]
            if structure_length < 4 or offset + structure_length > len(table):
                break
            formatted = table[offset:offset + structure_length]
            strings_start = offset + structure_length
            strings_end = strings_start
            while (strings_end + 1 < len(table) and
                   table[strings_end:strings_end + 2] != b"\x00\x00"):
                strings_end += 1
            if strings_end + 1 >= len(table):
                break
            string_blob = table[strings_start:strings_end]
            strings = [
                item.decode("latin-1", errors="ignore")
                for item in string_blob.split(b"\x00") if item]

            if structure_type == 1:  # SMBIOS System Information
                if structure_length >= 24:
                    uuid_bytes = formatted[8:24]
                    if (uuid_bytes != b"\x00" * 16 and
                            uuid_bytes != b"\xff" * 16):
                        result["system_uuid"] = uuid_bytes.hex().upper()
                if structure_length > 7:
                    serial = _smbios_string(strings, formatted[7])
                    if serial:
                        result["system_serial"] = serial
            elif structure_type == 2 and structure_length > 7:
                serial = _smbios_string(strings, formatted[7])
                if serial:
                    result["baseboard_serial"] = serial
            elif structure_type == 3 and structure_length > 7:
                # Some manufacturers expose the device/BIOS service serial on
                # the chassis record rather than the system record.
                serial = _smbios_string(strings, formatted[7])
                if serial and "system_serial" not in result:
                    result["system_serial"] = serial

            offset = strings_end + 2
            if structure_type == 127:
                break
        return result
    except Exception as exc:
        print(f"[DEBUG] SMBIOS read unavailable: {exc}")
        return {}


def _read_windows_machine_guid() -> str:
    if sys.platform != "win32":
        return ""
    try:
        import winreg

        with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography") as key:
            machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        return _normalize_hardware_id(machine_guid)
    except Exception:
        return ""


def _machine_component_digest(label: str, value: str) -> str:
    material = f"EngMaster-AI-Agent|machine-v3|{label}|{value}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def get_machine_id() -> str:
    """Return one copyable ID containing independent stable component hashes."""
    hardware = _read_windows_smbios_ids()
    component_values = (
        ("U", hardware.get("system_uuid", "")),
        ("B", hardware.get("baseboard_serial", "")),
        ("S", hardware.get("system_serial", "")),
        ("G", _read_windows_machine_guid()),
    )
    components = [
        f"{label}{_machine_component_digest(label, value)}"
        for label, value in component_values if value]
    if not components:
        import platform
        import uuid

        fallback = "|".join((
            platform.node(), platform.system(), platform.machine(),
            str(uuid.getnode())))
        components.append("F" + _machine_component_digest("F", fallback))
    return "EMPC3-" + "-".join(components)


def _parse_machine_id(machine_id: str) -> dict:
    normalized = re.sub(r"\s+", "", str(machine_id or "").upper())
    if not normalized.startswith("EMPC3-"):
        return {}
    parsed = {}
    for token in normalized[6:].split("-"):
        if re.fullmatch(r"[UBSGF][0-9A-F]{16}", token):
            parsed[token[0]] = token[1:]
    return parsed


def machine_ids_match(licensed_machine_id: str, current_machine_id: str) -> bool:
    """Match the same physical PC while tolerating one unavailable component."""
    licensed = re.sub(r"\s+", "", str(licensed_machine_id or "").upper())
    current = re.sub(r"\s+", "", str(current_machine_id or "").upper())
    if not licensed or not current:
        return False
    if licensed == current:
        return True
    old_parts = _parse_machine_id(licensed)
    new_parts = _parse_machine_id(current)
    if not old_parts or not new_parts:
        return False

    # Any matching validated SMBIOS anchor identifies the same physical PC.
    for label in ("U", "B", "S"):
        if old_parts.get(label) and old_parts[label] == new_parts.get(label):
            return True
    # MachineGuid is only a compatibility fallback when no hardware anchor is
    # available on at least one side; a hardware mismatch must not be ignored.
    old_has_hardware = any(old_parts.get(label) for label in ("U", "B", "S"))
    new_has_hardware = any(new_parts.get(label) for label in ("U", "B", "S"))
    return (not old_has_hardware or not new_has_hardware) and bool(
        old_parts.get("G") and old_parts["G"] == new_parts.get("G"))


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
        if activation_code.startswith("EM3-"):
            payload_part, signature_part = activation_code[4:].split(".", 1)
            payload_bytes = _license_b64decode(payload_part)
            signature_bytes = _license_b64decode(signature_part)
            signature_int = int.from_bytes(signature_bytes, "big")
            digest_int = int.from_bytes(hashlib.sha256(payload_bytes).digest(), "big")
            if pow(signature_int, LICENSE_PUBLIC_E, LICENSE_PUBLIC_N) != digest_int:
                return False, "激活码签名无效。"
            payload = json.loads(payload_bytes.decode("utf-8"))
            if payload.get("product") != LICENSE_PRODUCT_ID:
                return False, "激活码不适用于当前软件。"
            if not machine_ids_match(payload.get("machine_id", ""), machine_id):
                return False, "激活码与当前电脑不匹配。"
            if int(payload.get("version", 0)) != LICENSE_FORMAT_VERSION:
                return False, "激活码版本不受支持。"
            entitlements = _license_entitlements_from_payload(payload)
            if not entitlements:
                return False, "激活码没有包含可用的正式版本权限。"
            payload = dict(payload)
            payload["entitlements"] = [
                edition_id for edition_id in FORMAL_EDITION_IDS
                if edition_id in entitlements]
            return True, payload

        if activation_code.startswith("EM2-"):
            signature_bytes = _license_b64decode(activation_code[4:])
            signature_int = int.from_bytes(signature_bytes, "big")
            payload_bytes = f"{LICENSE_PRODUCT_ID}|{machine_id}|v2".encode("utf-8")
            digest_int = int.from_bytes(hashlib.sha256(payload_bytes).digest(), "big")
            if pow(signature_int, LICENSE_PUBLIC_E, LICENSE_PUBLIC_N) != digest_int:
                return False, "激活码与当前电脑不匹配。"
            return True, {
                "product": LICENSE_PRODUCT_ID,
                "machine_id": machine_id,
                "version": 2,
                "entitlements": ["gaokao"],
                "legacy": True,
            }

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
        if not machine_ids_match(payload.get("machine_id", ""), machine_id):
            return False, "激活码与当前电脑不匹配。"
        payload = dict(payload)
        entitlements = _license_entitlements_from_payload(payload)
        if not entitlements:
            return False, "激活码没有包含可用的正式版本权限。"
        payload["entitlements"] = [
            edition_id for edition_id in FORMAL_EDITION_IDS
            if edition_id in entitlements]
        return True, payload
    except Exception:
        return False, "激活码格式无效。"


def load_license_state(path: str, machine_id: str):
    """Return the verified signed payload, or None for an invalid license."""
    try:
        data = _load_license_data(path)
        activation_code = str(data.get("activation_code", "")).strip()
        licensed_machine_id = str(data.get("machine_id", "")).strip()
        stable_fingerprint = str(data.get("machine_fingerprint", "")).strip()

        # New licenses are signed for the stable ID directly.
        ok, payload = verify_activation_code(activation_code, machine_id)
        if ok:
            if stable_fingerprint and not machine_ids_match(
                    stable_fingerprint, machine_id):
                return None
            if not stable_fingerprint:
                data["machine_fingerprint"] = machine_id
                data["machine_id_scheme"] = "stable-v2"
            entitlements = _license_entitlements_from_payload(payload)
            stored_entitlements = list(data.get("entitlements") or [])
            normalized_entitlements = [
                edition_id for edition_id in FORMAL_EDITION_IDS
                if edition_id in entitlements]
            if stored_entitlements != normalized_entitlements:
                data["entitlements"] = normalized_entitlements
            _write_license_data(path, data)
            return payload

        # Backward compatibility: an old code remains cryptographically checked
        # against the ID it was originally issued for.  On the first upgraded
        # start, bind that valid local license to this computer's stable ID.
        if not licensed_machine_id:
            return None
        legacy_ok, payload = verify_activation_code(
            activation_code, licensed_machine_id)
        if not legacy_ok:
            return None
        if stable_fingerprint and not machine_ids_match(
                stable_fingerprint, machine_id):
            return None
        if not stable_fingerprint:
            data["machine_fingerprint"] = machine_id
            data["machine_id_scheme"] = "stable-v2-migrated"
            data["migrated_at"] = _license_now()
        entitlements = _license_entitlements_from_payload(payload)
        data["entitlements"] = [
            edition_id for edition_id in FORMAL_EDITION_IDS
            if edition_id in entitlements]
        _write_license_data(path, data)
        return payload
    except Exception as e:
        print(f"[DEBUG] license read/verify error: {e}")
        return None


def load_license_file(path: str, machine_id: str) -> bool:
    """Compatibility boolean used by older UI and diagnostic code."""
    return load_license_state(path, machine_id) is not None


def save_license_file(
        path: str, machine_id: str, activation_code: str,
        purchase_code="", license_payload=None):
    now = _license_now()
    payload = license_payload or {}
    entitlements = _license_entitlements_from_payload(payload)
    if not entitlements:
        ok, verified_payload = verify_activation_code(activation_code, machine_id)
        if not ok:
            raise ValueError(str(verified_payload))
        payload = verified_payload
        entitlements = _license_entitlements_from_payload(payload)
    license_data = {
        "version": LICENSE_FORMAT_VERSION,
        "product": LICENSE_PRODUCT_ID,
        "tool_name": TOOL_DISPLAY_NAME,
        "tool_version": TOOL_VERSION,
        "build_date": BUILD_DATE,
        "machine_id": machine_id,
        "machine_fingerprint": machine_id,
        "machine_id_scheme": "stable-v2",
        "activation_code": activation_code.strip(),
        "purchase_code": str(purchase_code).strip(),
        "entitlements": [
            edition_id for edition_id in FORMAL_EDITION_IDS
            if edition_id in entitlements],
        "license_payload": payload,
        "activated_at": now,
        "accepted_at": now,
        "terms_version": TERMS_VERSION,
        "privacy_version": PRIVACY_VERSION,
        "refund_version": REFUND_VERSION,
    }
    _write_license_data(path, license_data)


def _delete_license_and_exit(path: str, reason: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"[DEBUG] failed to remove license file: {e}")
    QMessageBox.critical(None, "授权已失效", f"当前授权状态无效：{reason}\n软件将退出。")
    sys.exit(0)


def show_activation_dialog(
        machine_id: str, parent=None, requested_entitlements=None):
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("EngMaster英语词汇分级学习平台 单机激活")
    dialog.setModal(True)
    dialog.setMinimumSize(600, 320)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)

    title = QtWidgets.QLabel("EngMaster 正式版本单机激活")
    title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
    layout.addWidget(title)

    current_entitlements = frozenset(getattr(
        QtWidgets.QApplication.instance(), "license_entitlements", frozenset()))
    current_text = _license_entitlement_text(current_entitlements)
    newly_requested = frozenset(requested_entitlements or ()) - current_entitlements
    requested_text = _license_entitlement_text(newly_requested)
    activation_scope = (
        f"本次新增购买：{requested_text}"
        if newly_requested
        else "本次激活：将根据激活码自动识别可用的正式版本权限"
    )
    hint = QtWidgets.QLabel(
        "请输入客服提供的累计单机激活码。软件会根据当前机器识别码在本机校验，"
        "激活成功后即可离线使用。\n"
        f"当前正式版权限：{current_text}\n"
        f"{activation_scope}"
    )
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

    purchase_label = QtWidgets.QLabel("单机激活码：")
    layout.addWidget(purchase_label)
    purchase_input = QtWidgets.QLineEdit()
    purchase_input.setPlaceholderText("例如：EM3-xxxx（旧版 EM2 激活码仍可使用）")
    purchase_input.setMinimumHeight(36)
    layout.addWidget(purchase_input)

    error_label = QtWidgets.QLabel("")
    error_label.setStyleSheet("color: #dc2626; font-size: 13px;")
    error_label.setWordWrap(True)
    layout.addWidget(error_label)

    button_row = QtWidgets.QHBoxLayout()
    button_row.addStretch(1)
    cancel_button = QtWidgets.QPushButton("退出")
    activate_button = QtWidgets.QPushButton("激活")
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
            error_label.setText("请输入单机激活码。")
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
        "欢迎使用EngMaster英语词汇分级学习平台 V1.0。请您在使用前仔细阅读以下内容。\n\n"
        "1. 工具定位\n"
        "本工具仅作为英语学习、复习和练习辅助使用，主要用于词汇、短语、不规则动词和练习内容的整理与复习。"
        "本工具不属于官方教学系统、考试系统或认证软件，也不代表任何学校、考试机构或官方单位。\n\n"
        "2. 学习效果说明\n"
        "本工具旨在帮助用户提高复习效率，但学习效果因个人基础、学习时间、使用方法等因素而异。"
        "本工具不承诺任何考试成绩、提分幅度、录取结果或学习结果。\n\n"
        "3. 内容说明\n"
        f"{VOCABULARY_SCOPE_NOTICE}\n\n"
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
        "本工具采用单机使用方式。一个单机激活码原则上仅限绑定一台电脑使用。单机激活码一经绑定设备后，如用户更换电脑、"
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


def get_version_info_text():
    machine_id = get_machine_id()
    license_path = get_license_path()
    license_status = "未检测到有效授权"
    license_data = {}
    if os.path.exists(license_path):
        try:
            payload = load_license_state(license_path, machine_id)
            ok = payload is not None
            license_data = _load_license_data(license_path)
            license_status = "已激活" if ok else "授权文件无效或不属于当前电脑"
        except Exception:
            license_status = "授权文件读取失败"

    return (
        f"工具名称：{TOOL_DISPLAY_NAME}\n"
        f"当前版本：{TOOL_VERSION}\n"
        f"构建日期：{BUILD_DATE}\n"
        f"推荐系统：{RECOMMENDED_OS_TEXT}\n"
        f"授权方式：单机绑定激活\n"
        f"授权状态：{license_status}\n"
        f"已解锁版本：{_license_entitlement_text(license_data.get('entitlements', []))}\n"
        f"本机识别码：{machine_id}\n\n"
        f"词汇范围说明：\n{VOCABULARY_SCOPE_NOTICE}\n\n"
        f"免责声明版本：{TERMS_VERSION}\n"
        f"隐私说明版本：{PRIVACY_VERSION}\n"
        f"退款说明版本：{REFUND_VERSION}\n"
        f"已同意条款时间：{license_data.get('accepted_at', '未记录')}\n"
        f"激活时间：{license_data.get('activated_at', '未记录')}\n"
    )


def show_version_info_dialog(parent=None):
    info_text = get_version_info_text()

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
    """Return locally verified formal-edition entitlements; empty means trial."""
    print("[DEBUG] check_licensing_gate start")
    license_path = get_license_path()

    if os.path.exists(license_path):
        # Trial users do not need a hardware query during startup.  Read the
        # fingerprint only when a local formal license actually needs checking.
        machine_id = get_machine_id()
        payload = load_license_state(license_path, machine_id)
        if payload is not None:
            entitlements = _license_entitlements_from_payload(payload)
            print(f"[DEBUG] local license verified: {sorted(entitlements)}")
            return entitlements
        print("[DEBUG] existing local license is invalid for this computer")
    print("[DEBUG] no valid license; continuing in isolated free trial mode")
    return frozenset()


def show_purchase_edition_dialog(current_entitlements=None, parent=None):
    """Choose the formal editions to purchase and return cumulative permissions."""
    current_entitlements = _normalize_license_entitlements(
        current_entitlements or ())
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("选择要购买的英语版本")
    dialog.setModal(True)
    dialog.setMinimumWidth(540)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(28, 24, 28, 24)
    layout.setSpacing(12)

    title = QtWidgets.QLabel("请选择要购买的正式版本")
    title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet(
        "font-size:21px; font-weight:700; color:#111827; margin-bottom:4px;")
    layout.addWidget(title)

    hint = QtWidgets.QLabel(
        "当前 V1.0 仅开放高考英语正式版。初中、四级、六级和考研正式版仍在开发中，"
        "暂不开放购买；相应级别的30词免费体验仍可正常使用。")
    hint.setWordWrap(True)
    hint.setStyleSheet("font-size:14px; color:#4b5563; margin-bottom:6px;")
    layout.addWidget(hint)

    choices = {}
    for edition_id in FORMAL_EDITION_IDS:
        checkbox = QtWidgets.QCheckBox(LICENSE_EDITION_NAMES[edition_id])
        checkbox.setObjectName(f"purchase_edition_{edition_id}")
        checkbox.setMinimumHeight(42)
        if edition_id not in RELEASED_EDITION_IDS:
            checkbox.setEnabled(False)
            checkbox.setText("🛠 " + checkbox.text() + "（正式版开发中，暂未开放购买）")
            checkbox.setStyleSheet(
                "QCheckBox:disabled { font-size:16px; color:#b45309; "
                "padding:5px 10px; }")
        elif edition_id in current_entitlements:
            checkbox.setChecked(True)
            checkbox.setEnabled(False)
            checkbox.setText("🔓 " + checkbox.text() + "（已购买，将保留）")
            checkbox.setStyleSheet(
                "QCheckBox:disabled { font-size:16px; color:#15803d; "
                "padding:5px 10px; }")
        else:
            checkbox.setStyleSheet(
                "QCheckBox { font-size:16px; color:#1f2937; padding:5px 10px; }")
        choices[edition_id] = checkbox
        layout.addWidget(checkbox)

    error_label = QtWidgets.QLabel("")
    error_label.setObjectName("purchase_error_label")
    error_label.setWordWrap(True)
    error_label.setStyleSheet("color:#dc2626; font-size:13px;")
    layout.addWidget(error_label)

    button_row = QtWidgets.QHBoxLayout()
    button_row.addStretch(1)
    cancel_button = QtWidgets.QPushButton("取消")
    continue_button = QtWidgets.QPushButton("下一步：输入激活码")
    continue_button.setObjectName("btn_confirm_purchase_editions")
    continue_button.setDefault(True)
    continue_button.setMinimumHeight(40)
    button_row.addWidget(cancel_button)
    button_row.addWidget(continue_button)
    layout.addLayout(button_row)

    selected = {"entitlements": None}

    def accept_selection():
        chosen = frozenset(
            edition_id for edition_id, checkbox in choices.items()
            if checkbox.isChecked() and edition_id in RELEASED_EDITION_IDS)
        newly_selected = chosen - current_entitlements
        if not newly_selected:
            error_label.setText("请至少选择一个尚未购买的英语版本。")
            return
        selected["entitlements"] = chosen
        dialog.accept()

    cancel_button.clicked.connect(dialog.reject)
    continue_button.clicked.connect(accept_selection)
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        return selected["entitlements"]
    return None


def activate_license(parent=None, requested_entitlements=None):
    """Activate or upgrade a signed set of formal editions entirely offline."""
    license_path = get_license_path()
    machine_id = get_machine_id()
    requested_entitlements = _normalize_license_entitlements(
        requested_entitlements or ())

    if not show_user_notice_dialog():
        return False

    while True:
        purchase_code = show_activation_dialog(
            machine_id,
            parent=parent,
            requested_entitlements=requested_entitlements,
        )
        if not purchase_code:
            return False
        activation_code = purchase_code.strip()
        ok, message = verify_activation_code(activation_code, machine_id)
        if not ok:
            QMessageBox.warning(parent, "激活失败", f"激活码无效：{message}")
            continue

        new_entitlements = _license_entitlements_from_payload(message)
        app = QtWidgets.QApplication.instance()
        current_entitlements = frozenset(
            getattr(app, "license_entitlements", frozenset()))
        missing_existing = current_entitlements - new_entitlements
        if missing_existing:
            QMessageBox.warning(
                parent,
                "激活码权限不完整",
                "这枚激活码没有包含当前已经拥有的版本："
                f"{_license_entitlement_text(missing_existing)}。\n\n"
                "为避免覆盖原有权限，请让客服生成包含原权限和新增权限的累计激活码。",
            )
            continue

        missing_requested = requested_entitlements - new_entitlements
        if missing_requested:
            QMessageBox.warning(
                parent,
                "激活码与购买版本不一致",
                "这枚激活码没有包含您刚才选择购买的版本："
                f"{_license_entitlement_text(missing_requested)}。\n\n"
                "请核对购买版本，或联系客服重新提供正确的累计激活码。",
            )
            continue

        try:
            save_license_file(
                license_path,
                machine_id,
                activation_code,
                purchase_code=purchase_code,
                license_payload=message,
            )
            released_entitlements = frozenset(new_entitlements) & frozenset(
                RELEASED_EDITION_IDS)
            QMessageBox.information(
                parent,
                "激活成功",
                "当前电脑已完成单机激活。\n\n已解锁版本："
                f"{_license_entitlement_text(released_entitlements)}",
            )
            app.license_active = True
            app.license_entitlements = released_entitlements
            return released_entitlements
        except Exception as e:
            QMessageBox.critical(parent, "激活失败", f"保存授权文件失败:\n{e}")
            continue

def show_edition_selection_dialog(
        default_edition=None, parent=None, include_trial=True, entitlements=None):
    """Select an available edition at first launch or from inside the app."""
    default_config = resolve_edition(default_edition)
    if entitlements is None:
        app = QtWidgets.QApplication.instance()
        entitlements = getattr(app, "license_entitlements", frozenset())
    unlocked_editions = frozenset(entitlements or ())
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("选择学习版本")
    dialog.setModal(True)
    dialog.setMinimumWidth(520)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(28, 24, 28, 24)
    layout.setSpacing(14)

    title = QtWidgets.QLabel("请选择本次要学习的英语版本")
    title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet("font-size: 21px; font-weight: bold; color: #111827;")
    layout.addWidget(title)

    hint = QtWidgets.QLabel(
        "高考英语正式版现已开放；其他正式版本仍在开发中，各级免费体验均可使用")
    hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    hint.setStyleSheet("font-size: 14px; color: #6b7280; margin-bottom: 8px;")
    layout.addWidget(hint)

    selected = {"edition": None}
    upgraded = {"done": False}
    edition_descriptions = {
        "trial": "免费体验版（可选择初中、高考、四级、六级或考研）",
        "zhongkao": "初中英语词汇",
        "gaokao": "高考英语词汇与短语",
        "cet4": "大学英语四级词汇",
        "cet6": "大学英语六级词汇",
        "kaoyan": "考研英语词汇",
    }

    def choose(edition_id):
        if edition_id == "trial":
            if is_trial_edition(default_config):
                selected["edition"] = default_config
            else:
                selected["edition"] = TRIAL_EDITIONS.get(
                    f"trial_{default_config.edition_id}", TRIAL_EDITION)
        else:
            if edition_id not in RELEASED_EDITION_IDS:
                QMessageBox.information(
                    dialog,
                    "正式版开发中",
                    f"“{LICENSE_EDITION_NAMES[edition_id]}”正式版仍在开发中，"
                    "当前暂未开放购买和使用。\n\n"
                    "您可以进入免费体验版，体验对应级别的30词学习流程。",
                )
                return
            if edition_id not in unlocked_editions:
                QMessageBox.information(
                    dialog,
                    "该版本尚未解锁",
                    f"“{LICENSE_EDITION_NAMES[edition_id]}”正式版尚未购买。\n\n"
                    "可以先进入免费体验，购买后再使用包含该版本权限的新激活码升级。",
                )
                return
            selected["edition"] = ALL_EDITIONS[edition_id]
        dialog.accept()

    edition_ids = ["zhongkao", "gaokao", "cet4", "cet6", "kaoyan"]
    if include_trial:
        edition_ids.insert(0, "trial")
    for edition_id in edition_ids:
        label = edition_descriptions[edition_id]
        if edition_id != "trial":
            if edition_id not in RELEASED_EDITION_IDS:
                label += "　🛠 开发中 · 敬请期待"
            else:
                label += (
                    "　🔓 已解锁" if edition_id in unlocked_editions
                    else "　🔒 未解锁")
        if (edition_id == default_config.edition_id or
                edition_id == "trial" and is_trial_edition(default_config)):
            label += "（当前）"
        button = QPushButton(label)
        button.setObjectName(f"btn_select_{edition_id}")
        button.setMinimumHeight(58)
        button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        if edition_id == "trial":
            button_style = (
                "QPushButton { text-align:left; padding:0 20px; font-size:16px; "
                "font-weight:bold; border:1px solid #d1d5db; border-radius:10px; "
                "background:white; color:#1f2937; } QPushButton:hover { "
                "border-color:#2563eb; background:#eff6ff; }")
        elif edition_id not in RELEASED_EDITION_IDS:
            button_style = (
                "QPushButton { text-align:left; padding:0 20px; font-size:16px; "
                "font-weight:bold; border:1px solid #fde68a; border-radius:10px; "
                "background:#fffbeb; color:#b45309; } QPushButton:hover { "
                "border-color:#f59e0b; background:#fef3c7; }")
        elif edition_id in unlocked_editions:
            button_style = (
                "QPushButton { text-align:left; padding:0 20px; font-size:16px; "
                "font-weight:bold; border:1px solid #86efac; border-radius:10px; "
                "background:#f0fdf4; color:#15803d; } QPushButton:hover { "
                "border-color:#22c55e; background:#dcfce7; }")
        else:
            button_style = (
                "QPushButton { text-align:left; padding:0 20px; font-size:16px; "
                "font-weight:bold; border:1px solid #d1d5db; border-radius:10px; "
                "background:#f8fafc; color:#94a3b8; } QPushButton:hover { "
                "border-color:#94a3b8; background:#f1f5f9; }")
        button.setStyleSheet(button_style)
        button.clicked.connect(lambda checked=False, key=edition_id: choose(key))
        layout.addWidget(button)

    cancel_button = QPushButton("退出")
    cancel_button.clicked.connect(dialog.reject)
    bottom_row = QtWidgets.QHBoxLayout()
    if set(RELEASED_EDITION_IDS) - unlocked_editions:
        upgrade_button = QPushButton("输入新激活码 / 增加版本权限")
        upgrade_button.setObjectName("btn_upgrade_license")
        upgrade_button.setMinimumHeight(40)
        upgrade_button.setStyleSheet(
            "QPushButton { background:#7c3aed; color:white; border:none; "
            "border-radius:8px; font-size:14px; font-weight:bold; padding:0 16px; } "
            "QPushButton:hover { background:#6d28d9; }")

        def upgrade_license():
            app = QtWidgets.QApplication.instance()
            current_entitlements = frozenset(
                getattr(app, "license_entitlements", frozenset()))
            requested_entitlements = show_purchase_edition_dialog(
                current_entitlements, parent=dialog)
            if not requested_entitlements:
                return
            new_entitlements = activate_license(
                dialog, requested_entitlements=requested_entitlements)
            if not new_entitlements:
                return
            upgraded["done"] = True
            dialog.accept()

        upgrade_button.clicked.connect(upgrade_license)
        bottom_row.addWidget(upgrade_button)
    bottom_row.addStretch(1)
    bottom_row.addWidget(cancel_button)
    layout.addLayout(bottom_row)

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    if upgraded["done"]:
        app = QtWidgets.QApplication.instance()
        return show_edition_selection_dialog(
            default_config,
            parent=parent,
            include_trial=include_trial,
            entitlements=getattr(app, "license_entitlements", frozenset()),
        )
    return selected["edition"]


if __name__ == "__main__":
    edition_explicit = edition_was_explicitly_requested(sys.argv)
    active_edition, edition_argv = extract_edition_args(sys.argv)
    watermark_settings, qt_argv = parse_watermark_args(edition_argv)
    sys.argv = qt_argv
    app = QApplication(sys.argv)
    app.watermark_settings = watermark_settings
    app.setStyle("Fusion")
    apply_application_ui_baseline(app)

    # 1. 物理单实例锁：防止用户短时间内高频狂点导致多进程死锁
    lock_path = os.path.join(QDir.tempPath(), "EngMaster_Vocabulary_Platform_Unique.lock")
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

    # 2. A valid local license enters formal editions; otherwise the program
    # opens in a remembered or newly selected, difficulty-matched free trial.
    license_entitlements = (
        frozenset(check_licensing_gate()) & frozenset(RELEASED_EDITION_IDS))
    license_active = bool(license_entitlements)
    app.license_active = license_active
    app.license_entitlements = license_entitlements

    if not license_active:
        remembered_trial = load_last_trial_edition()
        if edition_explicit and is_trial_edition(active_edition):
            pass
        elif remembered_trial is not None:
            active_edition = remembered_trial
        else:
            # First-time users enter the high-school sample immediately and
            # choose any of the five levels from cards inside the trial page.
            active_edition = TRIAL_EDITION
        save_last_edition(active_edition)
    else:
        # A remembered or command-line formal edition may no longer be covered
        # after a legacy-license migration. Never let that bypass entitlements.
        if (not is_trial_edition(active_edition)
                and active_edition.edition_id not in license_entitlements):
            active_edition = EDITIONS[next(
                edition_id for edition_id in FORMAL_EDITION_IDS
                if edition_id in license_entitlements)]

    if license_active and not edition_explicit:
        remembered_edition = load_last_edition()
        if (remembered_edition is not None and (
                is_trial_edition(remembered_edition)
                or remembered_edition.edition_id in license_entitlements)):
            active_edition = remembered_edition
        else:
            active_edition = EDITIONS[next(
                edition_id for edition_id in FORMAL_EDITION_IDS
                if edition_id in license_entitlements)]
            save_last_edition(active_edition)

    # 3. 释放完全体主程序
    window = EngMasterApplication(active_edition)
    app.main_window = window
    QtCore.QTimer.singleShot(0, lambda: show_os_compatibility_warning(window))

    sys.exit(app.exec())
