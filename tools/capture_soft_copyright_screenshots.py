"""Capture brand-consistent screenshots for the V1.0 copyright manual."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CAPTURE_DATA = tempfile.TemporaryDirectory(prefix="yingsicheng-soft-copyright-")
os.environ["RECALLLEX_DATA_DIR"] = CAPTURE_DATA.name

from PySide6 import QtCore, QtWidgets

import main
from export_dialog import ExportDialog


OUT = ROOT / "soft_copyright_yingsicheng_materials" / "screenshots"


def _wait_for(predicate, app, timeout_ms=20000):
    deadline = QtCore.QDeadlineTimer(timeout_ms)
    while not deadline.hasExpired():
        app.processEvents()
        if predicate():
            return True
        QtCore.QThread.msleep(30)
    return bool(predicate())


def _save(widget, filename):
    OUT.mkdir(parents=True, exist_ok=True)
    widget.repaint()
    QtWidgets.QApplication.processEvents()
    image = widget.grab()
    if image.isNull() or not image.save(str(OUT / filename), "PNG"):
        raise RuntimeError(f"无法保存截图：{filename}")


def _capture_modal(open_dialog, filename):
    def capture_and_close():
        dialog = QtWidgets.QApplication.activeModalWidget()
        if dialog is None:
            raise RuntimeError(f"未找到模态窗口：{filename}")
        _save(dialog, filename)
        dialog.reject()

    QtCore.QTimer.singleShot(500, capture_and_close)
    open_dialog()


def main_capture():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.license_entitlements = frozenset({"gaokao"})

    window = main.EngMasterApplication("gaokao")
    window.resize(1600, 1000)
    window.show()
    if not _wait_for(
        lambda: window.vocab_loader_done and window.self_register_loader_done,
        app,
    ):
        raise RuntimeError("等待学习模块加载超时")

    window.show_trial_center()
    _save(window, "01_免费体验中心.png")
    _save(window.trial_center_widget, "02_体验级别选择.png")

    window.show_learning_guide()
    _save(window, "03_学习方法指南.png")

    window._safe_nav_to_word_list()
    _save(window, "04_高中词汇表.png")

    window.stack.setCurrentIndex(0)
    _save(window, "05_高中词汇闯关.png")

    window.show_word_mistake_list([])
    _save(window, "06_错词与学习记录.png")

    window._safe_nav_to_self_register()
    _save(window, "07_自主登记单词.png")

    window.show_version_management()
    _save(window, "08_正式版管理与淘宝购买.png")

    window.show_user_notice_page()
    _save(window, "09_用户须知.png")

    _capture_modal(
        lambda: main.show_activation_dialog(
            "EMPC3-UXXXXXXXXXXXXXXXX-BXXXXXXXXXXXXXXXX",
            parent=window,
            requested_entitlements={"gaokao"},
        ),
        "10_客服信息与单机激活.png",
    )

    window.show_phrase_irregular_list()
    _save(window, "12_短语与不规则动词.png")

    export_dialog = ExportDialog(
        window,
        regular_vocab_data=[{"word": "achievement", "content": "成就"}],
        mistake_vocab_data=[{"word": "recall", "content": "回忆"}],
        self_registered_vocab_data=[],
    )
    export_dialog.show()
    _save(export_dialog, "13_学习资料导出.png")
    export_dialog.close()

    window.close()
    app.processEvents()
    print(f"已生成英思成软著截图：{OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_capture())
