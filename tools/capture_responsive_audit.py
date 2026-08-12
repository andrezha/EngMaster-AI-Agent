"""Capture representative pages at the supported restored-window size."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main
from edition_config import resolve_edition


def main_capture():
    output = ROOT / "build" / "responsive_audit"
    output.mkdir(parents=True, exist_ok=True)
    os.environ["RECALLLEX_DATA_DIR"] = str(output / "data")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.license_entitlements = frozenset()
    app.watermark_settings = None
    window = main.EngMasterApplication(resolve_edition("trial_zhongkao"))
    window.showNormal()
    window.resize(1000, 620)
    window.show()
    app.main_window = window

    def capture():
        pages = (
            ("01_memory_home", "btn_nav_scientific_memory"),
            ("02_vocab_challenge", "btn_nav_vocab"),
            ("03_word_list", "btn_nav_core_vocab"),
            ("04_operation_guide", "btn_operation_guide"),
            ("05_purchase", "btn_switch_edition"),
        )
        for filename, button_name in pages:
            button = window.ui_root.findChild(QtWidgets.QPushButton, button_name)
            if button is not None:
                button.click()
                app.processEvents()
                window.grab().save(str(output / f"{filename}.png"))
        window.close()
        app.quit()

    QtCore.QTimer.singleShot(6000, capture)
    app.exec()


if __name__ == "__main__":
    main_capture()
