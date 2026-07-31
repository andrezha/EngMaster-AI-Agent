import tempfile
import unittest
import json
from pathlib import Path

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

import phrase_irregular_module
import vocab_module
import word_list_view
from challenge_history_dialog import RoundHistoryDialog


class ChallengeUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_vocab_path = vocab_module.get_writable_data_path
        self.old_phrase_path = phrase_irregular_module.get_writable_data_path
        self.old_word_list_path = word_list_view.get_writable_data_path
        temp_path = lambda filename: str(Path(self.temp_dir.name) / filename)
        vocab_module.get_writable_data_path = temp_path
        phrase_irregular_module.get_writable_data_path = temp_path
        word_list_view.get_writable_data_path = temp_path

    def tearDown(self):
        vocab_module.get_writable_data_path = self.old_vocab_path
        phrase_irregular_module.get_writable_data_path = self.old_phrase_path
        word_list_view.get_writable_data_path = self.old_word_list_path
        self.temp_dir.cleanup()

    def _fake_vocab_window(self):
        window = QtWidgets.QMainWindow()
        window.stack = QtWidgets.QStackedWidget()
        window.setCentralWidget(window.stack)
        window.self_register_vocab_ctrl = None
        window.opened_word_mistakes = None
        window.opened_self_register = False
        window.show_word_mistake_list = lambda data: setattr(
            window, "opened_word_mistakes", list(data))
        window._safe_nav_to_self_register = lambda: setattr(
            window, "opened_self_register", True)
        page = QtWidgets.QWidget()
        page.setObjectName("page_vocab")
        layout = QtWidgets.QVBoxLayout(page)
        controls = [
            (QtWidgets.QLineEdit, "vocab_input"),
            (QtWidgets.QTextEdit, "vocab_display"),
            (QtWidgets.QLabel, "timer_label"),
            (QtWidgets.QPushButton, "btn_confirm"),
        ]
        for widget_class, name in controls:
            widget = widget_class(page)
            widget.setObjectName(name)
            layout.addWidget(widget)
        window.stack.addWidget(page)
        return window

    def test_vocab_status_and_wrong_count_update(self):
        window = self._fake_vocab_window()
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[
                {"word": "alpha", "content": "甲"},
                {"word": "beta", "content": "乙"},
            ],
            initial_mistake_vocabulary=[],
        )
        self.assertIn("第 1 轮", manager.lbl_round_progress.text())
        self.assertIn("本轮 1 / 2", manager.lbl_round_progress.text())
        first_word = manager.active_vocabulary[0]["word"]

        manager.v_input.clear()
        QtTest.QTest.keyClick(manager.v_input, QtCore.Qt.Key.Key_Return)
        self.assertEqual(manager.active_vocabulary[0]["word"], first_word)
        self.assertIn("本轮 1 / 2", manager.lbl_round_progress.text())
        self.assertEqual(len(manager.mistake_vocabulary), 0)

        manager.v_input.setText("definitely-wrong")
        QtTest.QTest.mouseClick(
            manager.btn_confirm, QtCore.Qt.MouseButton.LeftButton)
        self.assertIn("本轮错词 1", manager.lbl_round_progress.text())
        self.assertIn("本轮 1 / 2", manager.lbl_round_progress.text())
        self.assertEqual(manager.active_vocabulary[0]["word"], first_word)
        self.assertEqual(len(manager.mistake_vocabulary), 1)

        manager.v_input.setText("still-wrong")
        QtTest.QTest.keyClick(manager.v_input, QtCore.Qt.Key.Key_Return)
        self.assertEqual(manager.active_vocabulary[0]["word"], first_word)
        self.assertEqual(len(manager.mistake_vocabulary), 1)

        manager.v_input.setText(first_word)
        QtTest.QTest.keyClick(manager.v_input, QtCore.Qt.Key.Key_Return)
        QtTest.QTest.qWait(1300)
        self.assertIn("本轮 2 / 2", manager.lbl_round_progress.text())
        self.assertEqual(len(manager.mistake_vocabulary), 1)
        manager.timer.stop()
        window.close()

    def test_vocab_accepts_an_approved_spelling_variant(self):
        window = self._fake_vocab_window()
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{
                "word": "afterward",
                "accepted_answers": ["afterward", "afterwards"],
                "content": "后来",
            }],
            initial_mistake_vocabulary=[],
        )
        manager.v_input.setText("afterwards")
        manager.check_answer()
        self.assertEqual(manager.mistake_vocabulary, [])
        self.assertTrue(manager._advance_pending)
        manager.advance_timer.stop()
        manager._advance_pending = False
        manager.timer.stop()
        window.close()

    def test_vocab_corrected_mistake_does_not_count_toward_removal(self):
        window = self._fake_vocab_window()
        mistake = {"word": "kept", "content": "保留", "correct_count": 2}
        (Path(self.temp_dir.name) / "mistake_words.json").write_text(
            json.dumps([mistake], ensure_ascii=False, indent=2), encoding="utf-8")
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{"word": "alpha", "content": "甲"}],
            initial_mistake_vocabulary=[mistake],
        )
        manager.switch_challenge_mode("mistake_list")
        manager.v_input.setText("wrong")
        manager.check_answer()
        manager.v_input.setText("kept")
        manager.check_answer()
        QtTest.QTest.qWait(1300)
        kept = next(item for item in manager.mistake_vocabulary if item["word"] == "kept")
        self.assertEqual(kept["correct_count"], 0)
        manager.timer.stop()
        window.close()

    def test_vocab_first_try_correct_still_removes_after_third_success(self):
        window = self._fake_vocab_window()
        mistake = {"word": "mastered", "content": "掌握", "correct_count": 2}
        (Path(self.temp_dir.name) / "mistake_words.json").write_text(
            json.dumps([mistake], ensure_ascii=False, indent=2), encoding="utf-8")
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{"word": "alpha", "content": "甲"}],
            initial_mistake_vocabulary=[mistake],
        )
        manager.switch_challenge_mode("mistake_list")
        manager.v_input.setText("mastered")
        manager.check_answer()
        self.assertFalse(any(
            item["word"] == "mastered" for item in manager.mistake_vocabulary))
        self.assertIn(
            "回答正确。连续 3 次答对，已从单词错词表删除。",
            manager.v_disp.toPlainText(),
        )
        QtTest.QTest.qWait(700)
        self.assertIn(
            "回答正确。连续 3 次答对，已从单词错词表删除。",
            manager.v_disp.toPlainText(),
        )
        QtTest.QTest.qWait(600)
        self.assertNotIn(
            "回答正确。连续 3 次答对，已从单词错词表删除。",
            manager.v_disp.toPlainText(),
        )
        manager.timer.stop()
        window.close()

    def test_vocab_first_try_correct_displays_mistake_success_progress(self):
        window = self._fake_vocab_window()
        mistake = {"word": "steady", "content": "稳定的", "correct_count": 0}
        (Path(self.temp_dir.name) / "mistake_words.json").write_text(
            json.dumps([mistake], ensure_ascii=False, indent=2), encoding="utf-8")
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{"word": "alpha", "content": "甲"}],
            initial_mistake_vocabulary=[mistake],
        )
        manager.switch_challenge_mode("mistake_list")
        manager.v_input.setText("steady")
        manager.check_answer()
        self.assertIn(
            "回答正确。连续答对 1 / 3 次。",
            manager.v_disp.toPlainText(),
        )
        steady = next(
            item for item in manager.mistake_vocabulary
            if item["word"] == "steady"
        )
        self.assertEqual(steady["correct_count"], 1)
        QtTest.QTest.qWait(700)
        self.assertIn(
            "回答正确。连续答对 1 / 3 次。",
            manager.v_disp.toPlainText(),
        )
        QtTest.QTest.qWait(600)
        self.assertNotIn(
            "回答正确。连续答对 1 / 3 次。",
            manager.v_disp.toPlainText(),
        )
        manager.timer.stop()
        window.close()

    def test_vocab_second_first_try_correct_displays_two_of_three(self):
        window = self._fake_vocab_window()
        mistake = {"word": "improve", "content": "改善", "correct_count": 1}
        (Path(self.temp_dir.name) / "mistake_words.json").write_text(
            json.dumps([mistake], ensure_ascii=False, indent=2), encoding="utf-8")
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{"word": "alpha", "content": "甲"}],
            initial_mistake_vocabulary=[mistake],
        )
        manager.switch_challenge_mode("mistake_list")
        manager.v_input.setText("improve")
        manager.check_answer()
        self.assertIn(
            "回答正确。连续答对 2 / 3 次。",
            manager.v_disp.toPlainText(),
        )
        improve = next(
            item for item in manager.mistake_vocabulary
            if item["word"] == "improve"
        )
        self.assertEqual(improve["correct_count"], 2)
        QtTest.QTest.qWait(700)
        self.assertIn(
            "回答正确。连续答对 2 / 3 次。",
            manager.v_disp.toPlainText(),
        )
        QtTest.QTest.qWait(600)
        self.assertNotIn(
            "回答正确。连续答对 2 / 3 次。",
            manager.v_disp.toPlainText(),
        )
        manager.timer.stop()
        window.close()

    def test_self_registered_wrong_answer_enters_word_mistake_list(self):
        window = self._fake_vocab_window()
        window.self_register_vocab_ctrl = type(
            "SelfRegisterStub",
            (),
            {"user_vocab_data": [{"word": "custom", "content": "自定义"}]},
        )()
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{"word": "alpha", "content": "甲"}],
            initial_mistake_vocabulary=[],
        )
        manager.switch_challenge_mode("self_register")
        manager.v_input.setText("wrong")
        manager.check_answer()
        self.assertEqual(manager.active_vocabulary[0]["word"], "custom")
        self.assertTrue(any(
            item["word"] == "custom" for item in manager.mistake_vocabulary))
        self.assertTrue(manager.round_store.is_retry_required("self_register"))
        manager.timer.stop()
        window.close()

    def test_vocab_count_labels_are_clickable(self):
        window = self._fake_vocab_window()
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{"word": "alpha", "content": "甲"}],
            initial_mistake_vocabulary=[{"word": "old", "content": "旧"}],
        )
        QtTest.QTest.mouseClick(
            manager.lbl_mistake_count, QtCore.Qt.MouseButton.LeftButton)
        QtTest.QTest.mouseClick(
            manager.lbl_self_register_count, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(window.opened_word_mistakes[0]["word"], "old")
        self.assertTrue(window.opened_self_register)
        manager.timer.stop()
        window.close()

    def test_vocab_mistake_challenge_shows_wrong_round_record(self):
        window = self._fake_vocab_window()
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{"word": "alpha", "content": "甲"}],
            initial_mistake_vocabulary=[],
        )
        manager.v_input.setText("wrong")
        manager.check_answer()
        manager.switch_challenge_mode("mistake_list")
        self.assertIn("首次在第1轮答错", manager.v_disp.toPlainText())
        manager.timer.stop()
        window.close()

    def test_vocab_initialization_does_not_rewrite_existing_mistake_file(self):
        mistake_path = Path(self.temp_dir.name) / "mistake_words.json"
        original = [{"word": "already-kept", "content": "已保留", "correct_count": 2}]
        mistake_path.write_text(
            json.dumps(original, ensure_ascii=False, indent=4), encoding="utf-8")
        before = mistake_path.read_bytes()
        window = self._fake_vocab_window()
        manager = vocab_module.VocabManager(
            window,
            initial_vocabulary=[{"word": "alpha", "content": "甲"}],
            initial_mistake_vocabulary=original,
        )
        manager.timer.stop()
        self.assertEqual(mistake_path.read_bytes(), before)
        backup_path = next(Path(self.temp_dir.name).glob(
            "mistake_words.json.before_round_upgrade_*.bak"))
        self.assertEqual(backup_path.read_bytes(), before)
        window.close()

    def test_phrase_status_and_mode_independent_progress(self):
        window = QtWidgets.QMainWindow()
        window.opened_phrase_table = None
        window.show_phrase_irregular_table = lambda table_type: setattr(
            window, "opened_phrase_table", table_type)
        view = phrase_irregular_module.PhraseIrregularChallengeView(window)
        self.assertIn("第 1 轮", view.status_label.text())
        self.assertIn("本轮 1 / 571", view.status_label.text())
        first_item = view.active_items[0]

        view.answer_input.clear()
        QtTest.QTest.keyClick(view.answer_input, QtCore.Qt.Key.Key_Return)
        self.assertEqual(view.active_items[0], first_item)
        self.assertIn("本轮 1 / 571", view.status_label.text())

        view.answer_input.setText("definitely-wrong")
        QtTest.QTest.mouseClick(
            view.btn_check, QtCore.Qt.MouseButton.LeftButton)
        self.assertIn("本轮错词 1", view.status_label.text())
        self.assertEqual(view.active_items[0], first_item)
        self.assertFalse(hasattr(view, "btn_next"))
        view._next_question()
        self.assertIn("本轮 1 / 571", view.status_label.text())

        view.answer_input.setText(first_item["p"])
        QtTest.QTest.keyClick(view.answer_input, QtCore.Qt.Key.Key_Return)
        QtTest.QTest.qWait(1300)
        self.assertIn("本轮 2 / 571", view.status_label.text())
        view._switch_category("irregular")
        self.assertIn("本轮 1 / 126", view.status_label.text())
        self.assertIn("本轮错词 0", view.status_label.text())
        QtTest.QTest.mouseClick(
            view.lbl_irregular_mistake_count,
            QtCore.Qt.MouseButton.LeftButton,
        )
        self.assertEqual(window.opened_phrase_table, "irregular_mistake")
        view.close()
        window.close()

    def test_phrase_mistake_shows_wrong_round_and_history_dialog(self):
        window = QtWidgets.QMainWindow()
        window.show_phrase_irregular_table = lambda _table_type: None
        view = phrase_irregular_module.PhraseIrregularChallengeView(window)
        item = view.phrases[0]
        view.learning_store.record_wrong_round("phrase", item, 2)
        view._add_or_reset_mistake_item(
            item,
            view.phrase_mistakes,
            view._phrase_key,
            view.phrase_mistake_file_path,
        )
        view._switch_category("phrase_mistake")
        self.assertIn("首次在第2轮答错", view.wrong_round_label.text())

        dialog = RoundHistoryDialog(
            window, view.learning_store, view._all_round_progress)
        dialog.select_mode("phrase_mistake")
        dialog.refresh()
        self.assertGreaterEqual(dialog.table.rowCount(), 1)
        self.assertEqual(dialog.table.item(0, 1).text(), "待开始")
        dialog.close()
        view.close()
        window.close()

    def test_irregular_requires_both_correct_fields_before_advancing(self):
        window = QtWidgets.QMainWindow()
        window.show_phrase_irregular_table = lambda _table_type: None
        view = phrase_irregular_module.PhraseIrregularChallengeView(window)
        view._switch_category("irregular")
        first_item = view.active_items[0]

        view.irregular_past_input.setText("wrong")
        view.irregular_participle_input.clear()
        QtTest.QTest.keyClick(
            view.irregular_past_input, QtCore.Qt.Key.Key_Return)
        self.assertEqual(view.active_items[0], first_item)
        self.assertIn("本轮错词 0", view.status_label.text())

        view.irregular_past_input.setText("wrong")
        view.irregular_participle_input.setText("wrong")
        QtTest.QTest.keyClick(
            view.irregular_participle_input, QtCore.Qt.Key.Key_Return)
        self.assertEqual(view.active_items[0], first_item)
        self.assertIn("本轮错词 1", view.status_label.text())

        view.irregular_past_input.setText(
            phrase_irregular_module._clean_verb_field(
                first_item.get("past_tense", "")).lower())
        view.irregular_participle_input.setText(
            phrase_irregular_module._clean_verb_field(
                first_item.get("past_participle", "")).lower())
        QtTest.QTest.keyClick(
            view.irregular_participle_input, QtCore.Qt.Key.Key_Return)
        QtTest.QTest.qWait(1300)
        self.assertIn("本轮 2 / 126", view.status_label.text())
        view.close()
        window.close()

    def test_word_list_delayed_initialization_keeps_mistake_target(self):
        window = QtWidgets.QMainWindow()
        view = word_list_view.WordListView(window)
        view.open_mistake_list([{"word": "kept", "content": "保留"}])
        QtTest.QTest.qWait(200)
        self.assertEqual(view.current_list_type, "mistake")
        self.assertTrue(view.btn_mis.isChecked())
        self.assertFalse(view.btn_reg.isChecked())
        view.close()
        window.close()

    def test_language_display_has_three_exclusive_modes(self):
        window = QtWidgets.QMainWindow()
        view = word_list_view.WordListView(window)
        self.assertTrue(view.btn_show_both.isChecked())
        self.assertFalse(view.hide_english)
        self.assertFalse(view.hide_chinese)

        QtTest.QTest.mouseClick(
            view.btn_only_english, QtCore.Qt.MouseButton.LeftButton)
        self.assertFalse(view.hide_english)
        self.assertTrue(view.hide_chinese)
        self.assertTrue(view.btn_only_english.isChecked())
        self.assertFalse(view.btn_show_both.isChecked())

        QtTest.QTest.mouseClick(
            view.btn_only_chinese, QtCore.Qt.MouseButton.LeftButton)
        self.assertTrue(view.hide_english)
        self.assertFalse(view.hide_chinese)
        self.assertFalse(view.btn_only_english.isChecked())
        self.assertTrue(view.btn_only_chinese.isChecked())

        QtTest.QTest.mouseClick(
            view.btn_show_both, QtCore.Qt.MouseButton.LeftButton)
        self.assertFalse(view.hide_english)
        self.assertFalse(view.hide_chinese)
        self.assertTrue(view.btn_show_both.isChecked())
        self.assertEqual(
            sum(button.isChecked() for button in [
                view.btn_show_both,
                view.btn_only_english,
                view.btn_only_chinese,
            ]),
            1,
        )
        view.close()
        window.close()

    def test_export_button_uses_explicit_readable_chinese_font(self):
        window = QtWidgets.QMainWindow()
        view = word_list_view.WordListView(window)
        self.assertEqual(view.btn_export.text(), "生成打印表")
        self.assertIn("Microsoft YaHei UI", view.btn_export.font().family())
        self.assertEqual(view.btn_export.font().weight(), QtGui.QFont.Weight.DemiBold)
        self.assertIn("font-size: 14px", view.btn_export.styleSheet())
        self.assertGreaterEqual(view.btn_export.minimumWidth(), 112)
        view.close()
        window.close()


if __name__ == "__main__":
    unittest.main()
