# -*- coding: utf-8 -*-
"""
Verify that the vocabulary challenge display wraps long prompt text without
showing internal scrollbars across regular, mistake-list, and self-register modes.

Run from the project root:
    .\\venv\\Scripts\\python.exe .\\tools\\verify_vocab_display_wrapping.py
"""

import os
import sys
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PySide6 import QtCore, QtWidgets

import vocab_module
from vocab_module import VocabManager


LONG_CONTENT = (
    "[ˌverɪfɪˈkeɪʃn] n. 一个特别长的中文解释；第二个含义也非常长，"
    "用于验证换行；第三个含义继续拉长文本；第四个含义包含多个说明；"
    "第五个含义用于模拟词表里音标加中文多义项的真实场景；第六个含义仍然继续。"
)


class FakeSelfRegisterController:
    def __init__(self, data):
        self.user_vocab_data = data


def build_test_window():
    page = QtWidgets.QWidget()
    page.setObjectName("page_vocab")
    layout = QtWidgets.QVBoxLayout(page)

    timer = QtWidgets.QLabel("15")
    timer.setObjectName("timer_label")
    display = QtWidgets.QTextEdit()
    display.setObjectName("vocab_display")
    input_box = QtWidgets.QLineEdit()
    input_box.setObjectName("vocab_input")
    confirm = QtWidgets.QPushButton("确定")
    confirm.setObjectName("btn_confirm")

    for widget in (timer, display, input_box, confirm):
        layout.addWidget(widget)

    stack = QtWidgets.QStackedWidget()
    stack.addWidget(page)

    main_window = QtWidgets.QWidget()
    main_window.stack = stack
    return main_window, display


def assert_display_state(display, mode_name):
    problems = []
    if display.horizontalScrollBarPolicy() != QtCore.Qt.ScrollBarAlwaysOff:
        problems.append("horizontal scrollbar policy is not AlwaysOff")
    if display.verticalScrollBarPolicy() != QtCore.Qt.ScrollBarAlwaysOff:
        problems.append("vertical scrollbar policy is not AlwaysOff")
    if display.lineWrapMode() != QtWidgets.QTextEdit.LineWrapMode.WidgetWidth:
        problems.append("line wrap mode is not WidgetWidth")
    if display.height() < 130:
        problems.append(f"display height is too small: {display.height()}")
    if display.document().textWidth() <= 0:
        problems.append("document text width was not set")

    if problems:
        raise AssertionError(f"{mode_name} failed: " + "; ".join(problems))

    print(f"PASS {mode_name}: height={display.height()}, textWidth={display.document().textWidth():.1f}")


def main():
    temp_dir = tempfile.mkdtemp(prefix="engmaster-vocab-wrap-")
    vocab_module.get_writable_data_path = lambda name: os.path.join(temp_dir, name)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    word = {"word": "verification", "content": LONG_CONTENT, "pronunciation": "/test/"}

    main_window, display = build_test_window()
    main_window.self_register_vocab_ctrl = FakeSelfRegisterController([dict(word)])

    manager = VocabManager(
        main_window,
        initial_vocabulary=[dict(word)],
        initial_mistake_vocabulary=[dict(word, correct_count=0)],
    )

    checks = [
        ("regular", "常规闯关"),
        ("mistake_list", "错词闯关"),
        ("self_register", "自主录入闯关"),
    ]
    for mode, label in checks:
        manager.switch_challenge_mode(mode)
        app.processEvents()
        assert_display_state(display, label)

    print("All vocabulary challenge display wrapping checks passed.")


if __name__ == "__main__":
    main()
