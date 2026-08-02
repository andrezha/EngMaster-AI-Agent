import os
import sys
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

import main
from ui_styles import UI_FONT_FAMILY, apply_application_ui_baseline


class _MemorySettings:
    def __init__(self, initial=None):
        self.data = dict(initial or {})
        self.synced = False

    def value(self, key, default=None, **_kwargs):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value

    def sync(self):
        self.synced = True


class EditionSwitchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_last_edition_round_trip_and_stale_value(self):
        settings = _MemorySettings()
        self.assertIsNone(main.load_last_edition(settings))
        main.save_last_edition("cet6", settings)
        self.assertTrue(settings.synced)
        self.assertEqual(main.load_last_edition(settings).edition_id, "cet6")
        settings.data[main.LAST_EDITION_SETTING_KEY] = "removed-edition"
        self.assertIsNone(main.load_last_edition(settings))

    def test_trial_can_be_remembered_as_the_current_edition(self):
        settings = _MemorySettings()
        main.save_last_edition("trial_cet4", settings)
        self.assertEqual(main.load_last_edition(settings).edition_id, "trial_cet4")

    def test_sidebar_switcher_shows_current_edition_above_navigation(self):
        window = main.EngMasterApplication.__new__(main.EngMasterApplication)
        QtWidgets.QMainWindow.__init__(window)
        window.edition = main.EDITIONS["cet4"]
        window.is_trial = False
        window.ui_root = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(window.ui_root)
        layout.setObjectName("nav_v_layout")
        existing_button = QtWidgets.QPushButton("existing")
        layout.addWidget(existing_button)

        main.EngMasterApplication._setup_edition_switcher(window)

        self.assertEqual(layout.itemAt(0).widget(), window.lbl_version_section)
        self.assertEqual(layout.itemAt(1).widget(), window.edition_switch_frame)
        self.assertEqual(layout.itemAt(2).widget(), window.current_edition_divider)
        self.assertEqual(layout.itemAt(3).widget(), window.btn_free_trial)
        self.assertEqual(layout.itemAt(4).widget(), window.btn_switch_edition)
        self.assertEqual(layout.itemAt(5).widget(), window.edition_nav_divider)
        self.assertEqual(layout.itemAt(6).widget(), window.lbl_learning_section)
        self.assertEqual(
            len(window.edition_switch_frame.findChildren(QtWidgets.QPushButton)), 0)
        self.assertEqual(window.lbl_current_edition.text(), "大学英语四级4500词汇版")
        self.assertIn("color:#15803d", window.lbl_current_edition.styleSheet())
        self.assertIn("background:#ecfdf5", window.edition_switch_frame.styleSheet())
        self.assertEqual(window.btn_free_trial.text(), "免费体验")
        self.assertEqual(window.btn_switch_edition.text(), "正式版管理与购买")
        self.assertEqual(window.lbl_version_section.text(), "版本与体验")
        self.assertEqual(window.lbl_learning_section.text(), "学习功能")
        self.assertFalse(window.btn_switch_edition.isEnabled())
        self.assertFalse(window.btn_free_trial.isEnabled())
        window.close()

    def test_application_typography_and_button_cursor_baseline(self):
        apply_application_ui_baseline(self.app)
        self.assertEqual(self.app.font().family(), UI_FONT_FAMILY)
        button = QtWidgets.QPushButton("可点击")
        button.show()
        self.app.processEvents()
        self.assertEqual(
            button.cursor().shape(), QtCore.Qt.CursorShape.PointingHandCursor)
        button.setEnabled(False)
        self.app.processEvents()
        self.assertEqual(button.cursor().shape(), QtCore.Qt.CursorShape.ArrowCursor)
        button.close()

    def test_loaded_window_can_be_replaced_inside_same_process(self):
        settings = _MemorySettings({"guides/quick_overview_seen_v1": True})
        with tempfile.TemporaryDirectory() as data_dir, mock.patch.dict(
            os.environ, {"ENGMASTER_DATA_DIR": data_dir}
        ), mock.patch.object(main, "_app_settings", return_value=settings):
            window = main.EngMasterApplication("zhongkao")
            self.app.main_window = window
            deadline = time.monotonic() + 15
            while not (window.vocab_loader_done and window.self_register_loader_done):
                self.app.processEvents()
                if time.monotonic() > deadline:
                    self.fail("initial edition did not finish loading")
                time.sleep(0.01)

            self.assertTrue(window.btn_switch_edition.isEnabled())
            window._reload_for_edition(main.EDITIONS["cet4"])
            deadline = time.monotonic() + 15
            while self.app.main_window is window:
                self.app.processEvents()
                QtCore.QCoreApplication.sendPostedEvents(
                    None, QtCore.QEvent.Type.DeferredDelete)
                if time.monotonic() > deadline:
                    self.fail("replacement edition window was not created")
                time.sleep(0.01)

            replacement = self.app.main_window
            while not (replacement.vocab_loader_done and replacement.self_register_loader_done):
                self.app.processEvents()
                if time.monotonic() > deadline:
                    self.fail("replacement edition did not finish loading")
                time.sleep(0.01)
            self.assertEqual(replacement.edition.edition_id, "cet4")
            self.assertEqual(replacement.lbl_current_edition.text(), "大学英语四级4500词汇版")
            replacement.close()
            self.app.processEvents()
            main.set_active_edition("gaokao")


if __name__ == "__main__":
    unittest.main()
