import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

import main
import purchase_config
from edition_config import (
    EDITIONS,
    PAGE_PHRASE_CHALLENGE,
    PAGE_PHRASE_LIST,
    PAGE_SELF_REGISTER,
    PAGE_VOCAB_CHALLENGE,
    PAGE_WORD_LIST,
    TRIAL_EDITION,
    TRIAL_EDITIONS,
    resolve_edition,
)
from trial_center import TrialCenterView
from utils import get_writable_data_path, set_active_edition
from version_management import VersionManagementView


ROOT = Path(__file__).parent


class _MemorySettings:
    def __init__(self, initial=None):
        self.data = dict(initial or {})

    def value(self, key, default=None, **_kwargs):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value

    def sync(self):
        pass


class TrialModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def tearDown(self):
        set_active_edition("gaokao")

    def test_five_difficulty_matched_word_only_trials_exist(self):
        self.assertEqual(resolve_edition("trial"), TRIAL_EDITION)
        self.assertEqual(
            set(TRIAL_EDITIONS),
            {"trial_zhongkao", "trial_gaokao", "trial_cet4", "trial_cet6", "trial_kaoyan"},
        )
        self.assertEqual(len({item.vocabulary_path for item in TRIAL_EDITIONS.values()}), 5)
        for edition in TRIAL_EDITIONS.values():
            self.assertTrue(edition.page_enabled(PAGE_VOCAB_CHALLENGE))
            self.assertTrue(edition.page_enabled(PAGE_WORD_LIST))
            self.assertTrue(edition.page_enabled(PAGE_SELF_REGISTER))
            self.assertTrue(edition.page_enabled(PAGE_PHRASE_CHALLENGE))
            self.assertTrue(edition.page_enabled(PAGE_PHRASE_LIST))
            rows = json.loads((ROOT / edition.vocabulary_path).read_text(encoding="utf-8"))
            self.assertEqual(len(rows), 30)
            self.assertTrue(all(row.get("word") and row.get("content") for row in rows))

    def test_trial_writable_data_is_isolated_from_formal_editions(self):
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.dict(
            os.environ, {"ENGMASTER_DATA_DIR": temp_dir}
        ):
            set_active_edition("trial_zhongkao")
            trial_path = Path(get_writable_data_path("mistake_words.json"))
            set_active_edition("trial_cet4")
            trial_cet4_path = Path(get_writable_data_path("mistake_words.json"))
            set_active_edition("gaokao")
            gaokao_path = Path(get_writable_data_path("mistake_words.json"))
            set_active_edition("cet4")
            cet4_path = Path(get_writable_data_path("mistake_words.json"))
        self.assertEqual(trial_path.parent, Path(temp_dir) / "editions" / "trial_zhongkao")
        self.assertEqual(trial_cet4_path.parent, Path(temp_dir) / "editions" / "trial_cet4")
        self.assertEqual(gaokao_path.parent, Path(temp_dir))
        self.assertEqual(cet4_path.parent, Path(temp_dir) / "editions" / "cet4")
        self.assertEqual(len({trial_path, trial_cet4_path, gaokao_path, cet4_path}), 4)

    def test_no_license_enters_trial_without_opening_activation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = str(Path(temp_dir) / "missing-license.dat")
            with mock.patch.object(main, "get_license_path", return_value=missing), mock.patch.object(
                main, "get_machine_id", return_value="TEST-MACHINE"
            ) as machine_id, mock.patch.object(
                main, "show_activation_dialog") as activation_dialog:
                self.assertFalse(main.check_licensing_gate())
                machine_id.assert_not_called()
                activation_dialog.assert_not_called()

    def test_purchase_flow_only_allows_released_gaokao_edition(self):
        inspected = {}

        def choose_gaokao(dialog):
            gaokao = dialog.findChild(
                QtWidgets.QCheckBox, "purchase_edition_gaokao")
            cet4 = dialog.findChild(
                QtWidgets.QCheckBox, "purchase_edition_cet4")
            inspected["cet4_enabled"] = cet4.isEnabled()
            inspected["cet4_text"] = cet4.text()
            gaokao.setChecked(True)
            dialog.findChild(
                QtWidgets.QPushButton, "btn_confirm_purchase_editions").click()
            return QtWidgets.QDialog.DialogCode.Accepted

        with mock.patch.object(QtWidgets.QDialog, "exec", choose_gaokao):
            selected = main.show_purchase_edition_dialog()

        self.assertEqual(selected, frozenset({"gaokao"}))
        self.assertFalse(inspected["cet4_enabled"])
        self.assertIn("开发中", inspected["cet4_text"])

    def test_unlicensed_purchase_entry_opens_in_app_version_management(self):
        window = main.EngMasterApplication.__new__(main.EngMasterApplication)
        QtWidgets.QMainWindow.__init__(window)
        window.has_formal_license = False
        window.license_entitlements = frozenset()
        window.show_version_management = mock.Mock()
        with mock.patch.object(main, "show_purchase_edition_dialog") as selector:
            window.request_trial_activation()
        window.show_version_management.assert_called_once_with()
        selector.assert_not_called()
        window.close()

    def test_trial_center_explains_scope_actions_and_data_isolation(self):
        window = QtWidgets.QMainWindow()
        window.edition = TRIAL_EDITIONS["trial_zhongkao"]
        window.stack = QtWidgets.QStackedWidget()
        window.stack.addWidget(QtWidgets.QWidget())
        window.vocab_ctrl = SimpleNamespace(switch_challenge_mode=lambda _mode: None)
        window._safe_nav_to_word_list = lambda: None
        window.show_word_mistake_list = lambda: None
        window._safe_nav_to_self_register = lambda: None
        window.show_phrase_irregular_list = lambda: None
        window.show_phrase_irregular_challenge = lambda: None
        window.request_trial_activation = lambda: None
        window.open_taobao_purchase = lambda: None
        window.get_purchase_machine_id = lambda: "EMPC3-TEST-MACHINE"
        window.activate_code_from_page = lambda _code: (True, "激活成功")
        window.show_user_notice_page = lambda: None
        requested_levels = []
        window.request_trial_level_switch = requested_levels.append
        window.has_formal_license = False
        view = TrialCenterView(window)
        page_text = " ".join(label.text() for label in view.findChildren(QtWidgets.QLabel))
        self.assertIn("初中英语学习者准备的30词体验词库", page_text)
        self.assertNotIn("当前级别", page_text)
        self.assertIn("各类体验数据与正式版本完全隔离", page_text)
        self.assertIn("不会自动混入或覆盖正式数据", page_text)
        self.assertEqual(len(view.findChildren(QtWidgets.QPushButton)), 6)
        self.assertIsNotNone(view.findChild(
            QtWidgets.QPushButton, "btn_trial_go_purchase"))
        self.assertIsNone(view.findChild(
            QtWidgets.QLineEdit, "purchase_machine_id"))
        self.assertIsNone(view.findChild(
            QtWidgets.QPushButton, "btn_trial_word_list"))
        self.assertIsNone(view.findChild(
            QtWidgets.QPushButton, "btn_trial_phrase_challenge"))
        level_button = view.findChild(
            QtWidgets.QPushButton, "btn_trial_level_trial_cet6")
        self.assertIsNotNone(level_button)
        level_button.click()
        self.assertEqual(requested_levels, ["trial_cet6"])
        view.close()
        window.close()

    def test_version_management_is_an_in_app_page_with_trial_and_formal_states(self):
        window = QtWidgets.QMainWindow()
        window.edition = TRIAL_EDITIONS["trial_gaokao"]
        window.license_entitlements = frozenset()
        activated = []
        opened_taobao = []
        window.request_version_from_management = lambda _edition: None
        def open_taobao_purchase(*args, **kwargs):
            opened_taobao.append((args, kwargs))

        window.open_taobao_purchase = open_taobao_purchase
        window.get_purchase_machine_id = lambda: "EMPC3-TEST-MACHINE"
        window.show_user_notice_page = lambda: None

        def activate_code(code):
            activated.append(code)
            return True, "激活成功，已解锁测试版本。"

        window.activate_code_from_page = activate_code
        view = VersionManagementView(window)

        self.assertEqual(view.objectName(), "version_management_view")
        self.assertEqual(len(view.findChildren(QtWidgets.QDialog)), 0)
        guide = view.findChild(QtWidgets.QLabel, "formal_purchase_guide")
        self.assertIn("前往淘宝购买", guide.text())
        self.assertIn("商品规格", guide.text())
        self.assertIn("订单卡片", guide.text())
        self.assertEqual(guide.text().count("\n"), 5)
        manual_notice = view.findChild(
            QtWidgets.QLabel, "purchase_manual_review_notice")
        self.assertIsNotNone(manual_notice)
        self.assertIn("人工核验", manual_notice.text())
        self.assertIn("不会自动即时发送", manual_notice.text())
        self.assertIsNone(view.findChild(
            QtWidgets.QLabel, "purchase_upgrade_notice"))
        options_notice = view.findChild(
            QtWidgets.QLabel, "taobao_purchase_options_notice")
        self.assertIsNotNone(options_notice)
        self.assertIn("单版本", options_notice.text())
        self.assertIn("双版本组合", options_notice.text())
        self.assertIn("四六级组合", options_notice.text())
        self.assertIn("暂不销售", options_notice.text())
        cet4 = view.findChild(QtWidgets.QPushButton, "btn_manage_formal_cet4")
        gaokao = view.findChild(QtWidgets.QPushButton, "btn_manage_formal_gaokao")
        self.assertFalse(cet4.isEnabled())
        self.assertIn("开发中", cet4.text())
        self.assertIn("当前可购买", gaokao.text())
        self.assertFalse(gaokao.isEnabled())
        self.assertEqual(len([
            button for button in view.findChildren(QtWidgets.QPushButton)
            if button.objectName().startswith("btn_manage_trial_")
        ]), 0)
        buy_button = view.findChild(
            QtWidgets.QPushButton, "btn_open_taobao_store")
        activate_button = view.findChild(
            QtWidgets.QPushButton, "btn_purchase_flow_activate")
        self.assertIsNotNone(buy_button)
        self.assertIsNotNone(activate_button)
        store_panel = view.findChild(
            QtWidgets.QFrame, "purchase_activation_panel")
        self.assertIsNotNone(store_panel)
        self.assertIn("background:#ffffff", store_panel.styleSheet())
        self.assertNotIn("#fff7ed", store_panel.styleSheet())
        self.assertIsNone(view.findChild(
            QtWidgets.QPushButton, "btn_edition_purchase_gaokao"))
        self.assertIsNone(view.findChild(
            QtWidgets.QLabel, "purchase_edition_context"))
        buy_button.click()
        order_input = view.findChild(
            QtWidgets.QLineEdit, "purchase_order_number")
        self.assertIsNotNone(order_input)
        copy_button = view.findChild(
            QtWidgets.QPushButton, "btn_copy_purchase_machine_id")
        original_clipboard = "UNCHANGED-WITHOUT-ORDER"
        QtWidgets.QApplication.clipboard().setText(original_clipboard)
        copy_button.click()
        self.assertEqual(
            QtWidgets.QApplication.clipboard().text(), original_clipboard)
        self.assertIn("请先粘贴", view.findChild(
            QtWidgets.QLabel, "purchase_flow_status").text())
        order_input.setText(" 1234 5678 9012 3456 ")
        copy_button.click()
        copied = QtWidgets.QApplication.clipboard().text()
        self.assertNotIn("意向版本", copied)
        self.assertIn("淘宝订单号：1234567890123456", copied)
        self.assertIn("本机识别码：EMPC3-TEST-MACHINE", copied)
        self.assertIn("订单卡片", copied)
        self.assertIn("付款状态", copied)
        self.assertIn("商品规格", copied)
        view.findChild(
            QtWidgets.QLineEdit, "purchase_activation_code").setText("EM3-TEST")
        view.findChild(
            QtWidgets.QCheckBox, "purchase_notice_consent").setChecked(True)
        activate_button.click()
        self.assertEqual(opened_taobao, [((), {})])
        self.assertEqual(activated, ["EM3-TEST"])
        view.resize(520, 700)
        self.app.processEvents()
        view._relayout_formal_buttons()
        self.assertEqual(view._formal_columns, 1)
        self.assertEqual(
            view.scroll.horizontalScrollBarPolicy(),
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.close()
        window.close()

        licensed_window = QtWidgets.QMainWindow()
        licensed_window.edition = EDITIONS["gaokao"]
        licensed_window.license_entitlements = frozenset({"gaokao"})
        licensed_window.request_version_from_management = lambda _edition: None
        licensed_window.open_taobao_purchase = lambda: None
        licensed_window.get_purchase_machine_id = lambda: "EMPC3-LICENSED"
        licensed_window.activate_code_from_page = lambda _code: (True, "成功")
        licensed_window.show_user_notice_page = lambda: None
        licensed_view = VersionManagementView(licensed_window)
        self.assertIsNotNone(licensed_view.findChild(
            QtWidgets.QPushButton, "btn_open_taobao_store"))
        self.assertIsNotNone(licensed_view.findChild(
            QtWidgets.QPushButton, "btn_purchase_flow_activate"))
        self.assertIsNone(licensed_view.findChild(
            QtWidgets.QPushButton, "btn_edition_purchase_gaokao"))
        upgrade_notice = licensed_view.findChild(
            QtWidgets.QLabel, "purchase_upgrade_notice")
        self.assertIsNotNone(upgrade_notice)
        self.assertIn("原有版本", upgrade_notice.text())
        self.assertIn("新增版本", upgrade_notice.text())
        licensed_view.close()
        licensed_window.close()

    def test_taobao_entry_has_safe_pending_and_configured_states(self):
        with mock.patch.object(
            purchase_config.QtWidgets.QMessageBox, "information"
        ) as information, mock.patch.object(
            purchase_config, "TAOBAO_PURCHASE_URL", ""
        ):
            self.assertFalse(purchase_config.open_taobao_purchase())
        self.assertIn("商品地址正在配置", information.call_args.args[2])
        self.assertIn("商品规格中选择", information.call_args.args[2])

        target = "https://item.taobao.com/item.htm?id=1234567890"
        with mock.patch.object(
            purchase_config, "TAOBAO_PURCHASE_URL", target
        ), mock.patch.object(
            purchase_config.QtGui.QDesktopServices,
            "openUrl",
            return_value=True,
        ) as open_url:
            self.assertTrue(purchase_config.open_taobao_purchase())
        self.assertEqual(open_url.call_args.args[0].toString(), target)

    def test_version_management_refresh_never_stacks_formal_buttons(self):
        window = QtWidgets.QMainWindow()
        window.edition = EDITIONS["gaokao"]
        window.license_entitlements = frozenset({"gaokao"})
        window.request_version_from_management = lambda _edition: None
        window.open_taobao_purchase = lambda: None
        window.get_purchase_machine_id = lambda: "EMPC3-LICENSED"
        window.activate_code_from_page = lambda _code: (True, "成功")
        window.show_user_notice_page = lambda: None
        view = VersionManagementView(window)
        view.resize(520, 760)
        view.show()
        self.app.processEvents()

        for _ in range(4):
            view.refresh()
            self.app.processEvents()
            QtCore.QCoreApplication.sendPostedEvents(
                None, QtCore.QEvent.Type.DeferredDelete)

        formal_buttons = [
            button for button in view.findChildren(QtWidgets.QPushButton)
            if button.objectName().startswith("btn_manage_formal_")
        ]
        self.assertEqual(len(formal_buttons), 5)
        gaokao_buttons = [
            button for button in formal_buttons
            if button.objectName() == "btn_manage_formal_gaokao"
        ]
        self.assertEqual(len(gaokao_buttons), 1)
        self.assertIn("当前已解锁", gaokao_buttons[0].text())
        self.assertNotIn("}}QPushButton", gaokao_buttons[0].styleSheet())
        view.close()
        window.close()

    def test_inline_activation_uses_page_code_without_legacy_dialog(self):
        window = main.EngMasterApplication.__new__(main.EngMasterApplication)
        QtWidgets.QMainWindow.__init__(window)
        window.license_entitlements = frozenset()
        window.has_formal_license = False
        window.get_purchase_machine_id = lambda: "EMPC3-TEST-MACHINE"
        window.version_management_widget = None
        window.stack = QtWidgets.QStackedWidget()
        payload = {
            "product": main.LICENSE_PRODUCT_ID,
            "machine_id": "EMPC3-TEST-MACHINE",
            "version": main.LICENSE_FORMAT_VERSION,
            "entitlements": ["gaokao"],
        }
        with mock.patch.object(
            main, "verify_activation_code", return_value=(True, payload)
        ), mock.patch.object(main, "save_license_file") as save_license, mock.patch.object(
            main, "show_activation_dialog"
        ) as legacy_dialog:
            ok, message = window.activate_code_from_page("EM3-TEST")

        self.assertTrue(ok)
        self.assertIn("激活成功", message)
        self.assertEqual(window.license_entitlements, frozenset({"gaokao"}))
        save_license.assert_called_once()
        legacy_dialog.assert_not_called()
        window.close()

    def test_licensed_trial_entry_also_opens_in_app_version_management(self):
        window = main.EngMasterApplication.__new__(main.EngMasterApplication)
        QtWidgets.QMainWindow.__init__(window)
        window.has_formal_license = True
        window.license_entitlements = frozenset({"gaokao"})
        window.show_version_management = mock.Mock()
        window.request_trial_activation()
        window.show_version_management.assert_called_once_with()
        window.close()

    def test_licensed_trial_center_only_links_to_purchase_management(self):
        window = QtWidgets.QMainWindow()
        window.edition = TRIAL_EDITIONS["trial_gaokao"]
        window.has_formal_license = True
        window.request_trial_level_switch = lambda _edition: None
        requested = []
        window.request_trial_activation = lambda: requested.append(True)
        view = TrialCenterView(window)
        purchase_button = view.findChild(
            QtWidgets.QPushButton, "btn_trial_go_purchase")
        self.assertIsNotNone(purchase_button)
        self.assertIsNone(view.findChild(
            QtWidgets.QLineEdit, "purchase_machine_id"))
        purchase_button.click()
        self.assertEqual(requested, [True])
        view.close()
        window.close()

    def test_formal_version_selector_enters_matching_trial_without_second_popup(self):
        def choose_trial(dialog):
            trial_entry = dialog.findChild(QtWidgets.QPushButton, "btn_select_trial")
            self.assertIsNotNone(trial_entry)
            trial_entry.click()
            return QtWidgets.QDialog.DialogCode.Accepted

        with mock.patch.object(QtWidgets.QDialog, "exec", choose_trial):
            selected = main.show_edition_selection_dialog(
                "gaokao", entitlements={"gaokao"})
        self.assertEqual(selected.edition_id, "trial_gaokao")

    def test_real_trial_window_loads_center_and_hides_non_word_pages(self):
        settings = _MemorySettings({"guides/quick_overview_seen_v1": True})
        with tempfile.TemporaryDirectory() as data_dir, mock.patch.dict(
            os.environ, {"ENGMASTER_DATA_DIR": data_dir}
        ), mock.patch.object(main, "_app_settings", return_value=settings):
            self.app.license_active = False
            self.app.license_entitlements = frozenset()
            window = main.EngMasterApplication("trial_zhongkao")
            deadline = time.monotonic() + 15
            while not (window.vocab_loader_done and window.self_register_loader_done):
                self.app.processEvents()
                if time.monotonic() > deadline:
                    self.fail("trial window did not finish loading")
                time.sleep(0.01)
            self.app.processEvents()
            self.assertTrue(window.is_trial)
            self.assertEqual(window.lbl_current_edition.text(), "初中英语免费体验版（30词）")
            self.assertEqual(window.btn_free_trial.text(), "免费体验")
            self.assertEqual(window.btn_switch_edition.text(), "正式版管理与购买")
            self.assertTrue(window.btn_free_trial.isEnabled())
            self.assertEqual(len(window.vocab_ctrl.vocabulary), 30)
            self.assertIs(window.stack.currentWidget(), window.word_list_widget)
            self.assertIsNone(window.trial_center_widget)
            self.assertEqual(window.lbl_learning_section.text(), "体验版学习功能")
            self.assertIn("免费体验版", window.trial_mode_banner.text())
            self.assertIn("30词体验版", window.ui_root.findChild(
                QtWidgets.QPushButton, "btn_nav_core_vocab").text())
            self.assertIn("最多30词体验版", window.ui_root.findChild(
                QtWidgets.QPushButton, "btn_nav_self_register").text())
            phrase_button = window.ui_root.findChild(
                QtWidgets.QPushButton, "btn_nav_phrase_challenge")
            self.assertFalse(phrase_button.isHidden())
            window.show_phrase_irregular_challenge()
            self.assertEqual(len(window.phrase_irregular_challenge_widget.all_phrases), 20)
            self.assertEqual(len(window.phrase_irregular_challenge_widget.irregulars), 15)
            window.close()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
