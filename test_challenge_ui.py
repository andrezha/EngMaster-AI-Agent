import tempfile
import unittest
import json
from pathlib import Path

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

import phrase_irregular_module
import self_register_vocab_module
import vocab_module
import word_list_view
from challenge_history_dialog import RoundHistoryDialog
from edition_config import TRIAL_EDITIONS


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
        for button in (
            manager.btn_challenge_regular,
            manager.btn_challenge_mistake,
            manager.btn_challenge_self_register,
        ):
            self.assertEqual(button.height(), 36)
            self.assertGreaterEqual(button.minimumWidth(), 140)
            self.assertIn("font-weight:600", button.styleSheet())
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
        self.assertEqual(
            view.lbl_phrase_mistake_count.text(), "查看短语错词表（0） →")
        self.assertEqual(
            view.lbl_irregular_mistake_count.text(),
            "查看不规则动词错词表（0） →")
        self.assertIn("background:#dbeafe", view.lbl_phrase_mistake_count.styleSheet())
        self.assertIn("核心短语", view.status_label.text())
        self.assertIn("第 1 / 7 关", view.status_label.text())
        self.assertIn("本关 1 / 50", view.status_label.text())
        first_item = view.active_items[0]

        view.answer_input.clear()
        QtTest.QTest.keyClick(view.answer_input, QtCore.Qt.Key.Key_Return)
        self.assertEqual(view.active_items[0], first_item)
        self.assertIn("本关 1 / 50", view.status_label.text())

        view.answer_input.setText("definitely-wrong")
        QtTest.QTest.mouseClick(
            view.btn_check, QtCore.Qt.MouseButton.LeftButton)
        self.assertIn("本关错词 1", view.status_label.text())
        self.assertEqual(view.active_items[0], first_item)
        self.assertFalse(hasattr(view, "btn_next"))
        view._next_question()
        self.assertIn("本关 1 / 50", view.status_label.text())

        view.answer_input.setText(first_item["p"])
        QtTest.QTest.keyClick(view.answer_input, QtCore.Qt.Key.Key_Return)
        QtTest.QTest.qWait(1300)
        self.assertIn("本关 2 / 50", view.status_label.text())
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

    def test_phrase_and_irregular_entries_hide_each_others_controls(self):
        window = QtWidgets.QMainWindow()
        window.show_phrase_irregular_table = lambda _table_type: None
        challenge = phrase_irregular_module.PhraseIrregularChallengeView(window)
        challenge.set_entry_scope("phrase")
        self.assertFalse(challenge.btn_phrase.isHidden())
        self.assertFalse(challenge.btn_phrase_mistake.isHidden())
        self.assertTrue(challenge.btn_irregular.isHidden())
        self.assertTrue(challenge.lbl_irregular_mistake_count.isHidden())
        challenge.set_entry_scope("irregular")
        self.assertTrue(challenge.btn_phrase.isHidden())
        self.assertTrue(challenge.lbl_phrase_mistake_count.isHidden())
        self.assertFalse(challenge.btn_irregular.isHidden())
        self.assertFalse(challenge.btn_irregular_mistake.isHidden())

        tables = phrase_irregular_module.PhraseIrregularListView(window)
        tables.set_entry_scope("phrase")
        self.assertFalse(tables.btn_phrases_table.isHidden())
        self.assertTrue(tables.btn_irregulars_table.isHidden())
        tables.set_entry_scope("irregular")
        self.assertTrue(tables.btn_phrase_mistake_table.isHidden())
        self.assertFalse(tables.btn_irregulars_table.isHidden())
        self.assertFalse(tables.btn_irregular_mistake_table.isHidden())
        challenge.close()
        tables.close()
        window.close()

    def test_all_phrase_levels_are_selectable_with_independent_progress(self):
        window = QtWidgets.QMainWindow()
        window.show_phrase_irregular_table = lambda _table_type: None
        view = phrase_irregular_module.PhraseIrregularChallengeView(window)
        self.assertEqual(len(view.phrase_level_buttons), 10)

        first_mode = view._round_mode()
        view.round_store.mark_wrong(first_mode)
        view._select_phrase_level(7)
        self.assertIn("扩展短语", view.status_label.text())
        self.assertIn("第 1 / 3 关", view.status_label.text())
        self.assertEqual(len(view.active_items), 50)
        self.assertEqual(view.round_store.progress(view._round_mode())["wrong"], 0)

        view._select_phrase_level(0)
        self.assertEqual(view._round_mode(), first_mode)
        self.assertEqual(view.round_store.progress(first_mode)["wrong"], 1)
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

    def test_word_list_can_filter_one_initial_and_search_within_it(self):
        window = QtWidgets.QMainWindow()
        view = word_list_view.WordListView(window)
        view.all_regular_words = [
            {"word": "apple", "content": "苹果"},
            {"word": "answer", "content": "答案"},
            {"word": "book", "content": "书"},
        ]
        view.initial_filter_combo.setCurrentIndex(
            view.initial_filter_combo.findData("a"))
        self.assertEqual(
            view.initial_filter_combo.currentText(),
            "显示 A 字母开头单词",
        )
        self.assertEqual(
            [item["word"] for item in view.display_words],
            ["apple", "answer"],
        )
        self.assertEqual(
            view.lbl_filter_status.text(), "当前：A 字母开头单词，共 2 词")
        view.search_input.setText("答案")
        self.assertEqual(
            [item["word"] for item in view.display_words], ["answer"])
        self.assertEqual(
            view.lbl_filter_status.text(), "当前：A 字母开头单词，共 1 词")

        view.btn_show_all_letters.click()
        self.assertEqual(view.initial_filter_combo.currentIndex(), -1)
        self.assertEqual(view.search_input.text(), "")
        self.assertEqual(
            [item["word"] for item in view.display_words],
            ["apple", "answer", "book"],
        )
        self.assertEqual(view.lbl_filter_status.text(), "当前：全部词汇，共 3 词")
        view.close()
        window.close()

    def test_self_registered_list_has_matching_language_display_modes(self):
        window = QtWidgets.QMainWindow()
        manager = self_register_vocab_module.SelfRegisterVocabManager(
            window,
            initial_user_vocab_data=[{"word": "custom", "content": "自定义"}],
        )
        self.assertFalse(any(
            "背诵显示" in label.text()
            for label in manager.findChildren(QtWidgets.QLabel)
        ))
        self.assertTrue(manager.btn_show_both.isChecked())
        self.assertEqual(manager.vocab_table.item(0, 1).text(), "custom")
        self.assertEqual(manager.vocab_table.item(0, 2).text(), "自定义")

        QtTest.QTest.mouseClick(
            manager.btn_only_english, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(manager.display_mode, "english")
        self.assertEqual(manager.vocab_table.item(0, 1).text(), "custom")
        self.assertEqual(manager.vocab_table.item(0, 2).text(), "")

        QtTest.QTest.mouseClick(
            manager.btn_only_chinese, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(manager.display_mode, "chinese")
        self.assertEqual(manager.vocab_table.item(0, 1).text(), "")
        self.assertEqual(manager.vocab_table.item(0, 2).text(), "自定义")

        QtTest.QTest.mouseClick(
            manager.btn_show_both, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(manager.display_mode, "both")
        self.assertEqual(manager.vocab_table.item(0, 1).text(), "custom")
        self.assertEqual(manager.vocab_table.item(0, 2).text(), "自定义")
        self.assertEqual(
            sum(button.isChecked() for button in [
                manager.btn_show_both,
                manager.btn_only_english,
                manager.btn_only_chinese,
            ]),
            1,
        )
        manager.close()
        window.close()

    def test_trial_self_registration_stops_at_thirty_words(self):
        window = QtWidgets.QMainWindow()
        window.edition = TRIAL_EDITIONS["trial_gaokao"]
        rows = [
            {"word": f"custom{index}", "content": f"自定义{index}"}
            for index in range(30)
        ]
        manager = self_register_vocab_module.SelfRegisterVocabManager(
            window, initial_user_vocab_data=rows)
        self.assertEqual(manager.word_limit, 30)
        self.assertIn("已登记 30 词", manager.limit_label.text())
        self.assertIn("还可登记 0 词", manager.limit_label.text())
        self.assertFalse(manager.add_word_button.isEnabled())
        self.assertFalse(manager.english_word_input.isEnabled())
        manager.user_vocab_data.pop()
        manager._refresh_table()
        self.assertTrue(manager.add_word_button.isEnabled())
        self.assertIn("还可登记 1 词", manager.limit_label.text())
        manager.close()
        window.close()

    def test_phrase_tables_use_core_extension_and_word_list_display_modes(self):
        window = QtWidgets.QMainWindow()
        view = phrase_irregular_module.PhraseIrregularListView(window)

        self.assertEqual(view.current_phrase_filter, "core")
        self.assertFalse(hasattr(view, "btn_phrase_all"))
        self.assertEqual(
            view.phrase_table.rowCount(),
            sum(item.get("tier") == "core" for item in view.phrases),
        )
        header = view.phrase_table.horizontalHeader()
        self.assertEqual(
            header.sectionResizeMode(1), QtWidgets.QHeaderView.ResizeMode.Fixed)
        for column in (2, 3, 4):
            self.assertEqual(
                header.sectionResizeMode(column),
                QtWidgets.QHeaderView.ResizeMode.Stretch)

        core_items = [item for item in view.phrases if item.get("tier") == "core"]
        row = next(
            index for index, item in enumerate(core_items)
            if all(item.get(field) for field in ("p", "m", "en", "cn"))
        )
        view._set_phrase_display_mode("english")
        self.assertTrue(view.phrase_table.item(row, 1).text())
        self.assertEqual(view.phrase_table.item(row, 2).text(), "")
        self.assertTrue(view.phrase_table.item(row, 3).text())
        self.assertEqual(view.phrase_table.item(row, 4).text(), "")

        view._set_phrase_display_mode("chinese")
        self.assertEqual(view.phrase_table.item(row, 1).text(), "")
        self.assertTrue(view.phrase_table.item(row, 2).text())
        self.assertEqual(view.phrase_table.item(row, 3).text(), "")
        self.assertTrue(view.phrase_table.item(row, 4).text())

        view._set_phrase_filter("extension")
        self.assertEqual(
            view.phrase_table.rowCount(),
            sum(item.get("tier") == "extension" for item in view.phrases),
        )
        view.close()
        window.close()

    def test_irregular_tables_offer_memorization_display_modes(self):
        window = QtWidgets.QMainWindow()
        view = phrase_irregular_module.PhraseIrregularListView(window)
        row = next(
            index for index, item in enumerate(view.irregulars)
            if all(item.get(field) for field in (
                "infinitive", "past_tense", "past_participle", "meaning"))
        )

        view._show_table("irregular")
        self.assertTrue(view.phrase_display_controls.isHidden())
        self.assertFalse(view.irregular_display_controls.isHidden())

        view._set_irregular_display_mode("changes")
        self.assertTrue(view.irregular_table.item(row, 1).text())
        self.assertEqual(view.irregular_table.item(row, 2).text(), "")
        self.assertEqual(view.irregular_table.item(row, 3).text(), "")
        self.assertTrue(view.irregular_table.item(row, 4).text())

        view._set_irregular_display_mode("chinese")
        self.assertEqual(view.irregular_table.item(row, 1).text(), "")
        self.assertEqual(view.irregular_table.item(row, 2).text(), "")
        self.assertEqual(view.irregular_table.item(row, 3).text(), "")
        self.assertTrue(view.irregular_table.item(row, 4).text())

        view._set_irregular_display_mode("all")
        self.assertTrue(view.irregular_table.item(row, 1).text())
        self.assertTrue(view.irregular_table.item(row, 2).text())
        self.assertTrue(view.irregular_table.item(row, 3).text())
        view.close()
        window.close()

    def test_export_button_uses_explicit_readable_chinese_font(self):
        window = QtWidgets.QMainWindow()
        view = word_list_view.WordListView(window)
        self.assertEqual(view.btn_export.text(), "生成错词打印表  ▼")
        self.assertIn("Microsoft YaHei UI", view.btn_export.font().family())
        self.assertEqual(view.btn_export.font().weight(), QtGui.QFont.Weight.DemiBold)
        self.assertIn("font-size: 14px", view.btn_export.styleSheet())
        self.assertGreaterEqual(view.btn_export.minimumWidth(), 158)
        self.assertIn("#16a34a", view.btn_export.styleSheet())
        self.assertEqual(view.header_primary_row.indexOf(view.btn_mis) + 1,
                         view.header_primary_row.indexOf(view.search_input))
        self.assertEqual(view.header_primary_row.indexOf(view.search_input) + 1,
                         view.header_primary_row.indexOf(view.btn_export))
        self.assertEqual(view.header_display_row.indexOf(view.btn_only_chinese) + 1,
                         view.header_display_row.indexOf(view.initial_filter_combo))
        self.assertEqual(view.header_display_row.indexOf(view.initial_filter_combo) + 1,
                         view.header_display_row.indexOf(view.btn_show_all_letters))
        self.assertGreaterEqual(view.initial_filter_combo.width(), 205)
        self.assertEqual(view.btn_show_all_letters.text(), "显示全部")
        self.assertGreaterEqual(view.btn_show_both.minimumWidth(), 112)
        self.assertEqual(view.btn_mis.text(), "查看单词错词表（0） →")
        action_texts = [
            action.text()
            for action in view.btn_export.menu().actions()
            if not action.isSeparator()
        ]
        self.assertTrue(action_texts)
        self.assertTrue(all("错词" in text for text in action_texts))
        self.assertFalse(any("自主录入" in text for text in action_texts))
        view.close()
        window.close()

    def test_trial_print_dropdown_explains_scope_and_disables_outputs(self):
        window = QtWidgets.QMainWindow()
        window.edition = TRIAL_EDITIONS["trial_gaokao"]
        view = word_list_view.WordListView(window)

        self.assertEqual(view.btn_export.text(), "体验版打印说明  ▼")
        self.assertIn("#f59e0b", view.btn_export.styleSheet())
        self.assertEqual(
            view.trial_print_header_label.text(), "体验版暂不支持打印")

        output_actions = [
            action for action in view.btn_export.menu().actions()
            if not action.isSeparator()
            and action is not view.trial_print_header_action
        ]
        self.assertTrue(output_actions)
        self.assertTrue(all(not action.isEnabled() for action in output_actions))
        self.assertTrue(all(
            action.text().startswith("正式版可打印：")
            for action in output_actions
        ))
        view.close()
        window.close()


if __name__ == "__main__":
    unittest.main()
