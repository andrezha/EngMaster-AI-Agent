import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest import mock


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtTest, QtWidgets

import main
from edition_config import EDITIONS
from phrase_irregular_module import PhraseIrregularChallengeView


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "assets/editions/gaokao"


class _MemorySettings:
    def __init__(self):
        self.data = {"guides/quick_overview_seen_v1": True}

    def value(self, key, default=None, **_kwargs):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value

    def sync(self):
        pass


class GaokaoEditionDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_gaokao_config_uses_isolated_complete_data(self):
        edition = EDITIONS["gaokao"]
        self.assertEqual(edition.vocabulary_path, "assets/editions/gaokao/vocabulary.json")
        self.assertEqual(edition.phrase_path, "assets/editions/gaokao/phrases.json")
        self.assertEqual(
            edition.irregular_verbs_path,
            "assets/editions/gaokao/irregular_verbs.json",
        )
        expected = {
            "vocabulary.json": 3800,
            "phrases.json": 450,
            "irregular_verbs.json": 126,
        }
        for name, count in expected.items():
            rows = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
            self.assertEqual(len(rows), count)
        vocabulary = json.loads((DATA_DIR / "vocabulary.json").read_text(encoding="utf-8"))
        variants = {row["word"]: row.get("accepted_answers", []) for row in vocabulary}
        self.assertIn("an", variants["a"])
        self.assertIn("analyze", variants["analyse"])

    def test_challenge_loads_nine_phrase_levels_and_clean_irregulars(self):
        with tempfile.TemporaryDirectory() as data_dir, mock.patch.dict(
            os.environ, {"ENGMASTER_DATA_DIR": data_dir}
        ):
            view = PhraseIrregularChallengeView(
                SimpleNamespace(edition=EDITIONS["gaokao"])
            )
            self.assertEqual(len(view.all_phrases), 450)
            self.assertEqual(len(view.phrase_levels), 9)
            self.assertEqual(len(view.irregulars), 126)
            view.close()

    def test_full_gaokao_window_loads_all_three_data_sections(self):
        with tempfile.TemporaryDirectory() as data_dir, mock.patch.dict(
            os.environ, {"ENGMASTER_DATA_DIR": data_dir}
        ), mock.patch.object(main, "_app_settings", return_value=_MemorySettings()):
            window = main.EngMasterApplication("gaokao")
            deadline = time.monotonic() + 20
            while not (window.vocab_loader_done and window.self_register_loader_done):
                self.app.processEvents()
                if time.monotonic() > deadline:
                    self.fail("gaokao data loaders did not finish")
                time.sleep(0.01)

            self.assertEqual(len(window.vocab_ctrl.vocabulary), 3800)
            self.assertTrue(window._ensure_word_list_widget())
            deadline = time.monotonic() + 5
            while not window.word_list_widget.all_regular_words:
                self.app.processEvents()
                if time.monotonic() > deadline:
                    self.fail("gaokao word list view did not finish loading")
                time.sleep(0.01)
            self.assertEqual(len(window.word_list_widget.all_regular_words), 3800)
            self.assertTrue(window._ensure_phrase_irregular_challenge_widget())
            self.assertEqual(len(window.phrase_irregular_challenge_widget.all_phrases), 450)
            self.assertEqual(len(window.phrase_irregular_challenge_widget.irregulars), 126)
            levels = window.phrase_irregular_challenge_widget.phrase_levels
            self.assertEqual(
                [len(level["items"]) for level in levels],
                [50] * 9,
            )
            self.assertEqual(
                [level["tier"] for level in levels],
                ["core"] * 6 + ["extension"] * 3,
            )

            mistake = {"word": "test", "content": "测试", "correct_count": 0}
            window.vocab_ctrl.mistake_vocabulary = [mistake]
            QtTest.QTest.mouseClick(
                window.vocab_ctrl.lbl_mistake_count,
                QtCore.Qt.MouseButton.LeftButton,
            )
            self.app.processEvents()
            self.assertIs(window.stack.currentWidget(), window.word_list_widget)
            self.assertEqual(window.word_list_widget.current_list_type, "mistake")
            self.assertEqual(window.word_list_widget.all_mistake_words, [mistake])
            window.close()
            self.app.processEvents()
            QtCore.QCoreApplication.sendPostedEvents(
                None, QtCore.QEvent.Type.DeferredDelete
            )


if __name__ == "__main__":
    unittest.main()
