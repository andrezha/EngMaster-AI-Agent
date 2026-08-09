import base64
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

import main


MACHINE_ID = "11111111-22222222-33333333-44444444"


def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _fake_em3(entitlements):
    payload = {
        "product": main.LICENSE_PRODUCT_ID,
        "machine_id": MACHINE_ID,
        "version": 3,
        "entitlements": list(entitlements),
        "issued_at": "2026-08-01T00:00:00+00:00",
    }
    payload_bytes = json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    # Tests patch the public exponent to 1, so the digest itself is a valid
    # deterministic signature without putting the seller's private key here.
    signature = hashlib.sha256(payload_bytes).digest()
    return f"EM3-{_b64(payload_bytes)}.{_b64(signature)}", payload


class LicenseEntitlementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def test_legal_notice_contains_general_vocabulary_scope_statement(self):
        notice = main.get_legal_notice_text()
        self.assertIn(main.VOCABULARY_SCOPE_NOTICE, notice)
        self.assertIn("国家英语课程标准", notice)
        self.assertIn("相关英语考试大纲", notice)
        self.assertIn("并非教育主管部门、学校或考试机构官方指定软件", notice)
        self.assertIn("关于、版权与许可", notice)

    def test_public_copyright_and_data_notices_are_formal_and_bounded(self):
        copyright_notice = main.get_copyright_notice_text()
        data_notice = main.get_third_party_data_notice_text()
        self.assertIn("开发者署名：EngMaster", copyright_notice)
        self.assertIn("不在本说明中宣称已经取得", copyright_notice)
        self.assertIn("第三方开放许可证", copyright_notice)
        self.assertIn("Open English WordNet 2025", data_notice)
        self.assertIn("CC BY 4.0", data_notice)
        self.assertIn("ECDICT", data_notice)
        self.assertIn("Moby Words II", data_notice)
        self.assertIn("Tatoeba CC0", data_notice)
        documents = main.load_public_license_documents()
        self.assertEqual(len(documents), 4)
        self.assertIn("Creative Commons Attribution 4.0", documents["OEWN与WordNet完整许可"])
        self.assertIn("WordNet 3.0 Copyright 2006", documents["Princeton WordNet许可"])
        self.assertIn("Permission is hereby granted", documents["ECDICT MIT许可证"])
        self.assertIn("Third-Party Data Notices", documents["第三方数据声明"])

    def test_em3_signed_permissions_are_verified_and_tampering_fails(self):
        code, _payload = _fake_em3(["gaokao", "cet4"])
        with mock.patch.object(main, "LICENSE_PUBLIC_E", 1):
            ok, verified = main.verify_activation_code(code, MACHINE_ID)
            self.assertTrue(ok)
            self.assertEqual(verified["entitlements"], ["gaokao", "cet4"])

            payload_part, signature_part = code[4:].split(".", 1)
            changed = json.loads(main._license_b64decode(payload_part).decode("utf-8"))
            changed["entitlements"].append("cet6")
            changed_bytes = json.dumps(
                changed, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            tampered = f"EM3-{_b64(changed_bytes)}.{signature_part}"
            tampered_ok, _message = main.verify_activation_code(tampered, MACHINE_ID)
            self.assertFalse(tampered_ok)

    def test_unknown_or_empty_permissions_are_rejected(self):
        for permissions in ([], ["unknown-edition"]):
            code, _payload = _fake_em3(permissions)
            with mock.patch.object(main, "LICENSE_PUBLIC_E", 1):
                ok, _message = main.verify_activation_code(code, MACHINE_ID)
            self.assertFalse(ok)

    def test_future_permission_is_ignored_without_losing_known_permissions(self):
        code, _payload = _fake_em3(["gaokao", "toefl"])
        with mock.patch.object(main, "LICENSE_PUBLIC_E", 1):
            ok, verified = main.verify_activation_code(code, MACHINE_ID)
        self.assertTrue(ok)
        self.assertEqual(verified["entitlements"], ["gaokao"])

    def test_legacy_em2_code_remains_valid_as_gaokao_only(self):
        payload = f"{main.LICENSE_PRODUCT_ID}|{MACHINE_ID}|v2".encode("utf-8")
        code = "EM2-" + _b64(hashlib.sha256(payload).digest())
        with mock.patch.object(main, "LICENSE_PUBLIC_E", 1):
            ok, verified = main.verify_activation_code(code, MACHINE_ID)
        self.assertTrue(ok)
        self.assertEqual(verified["entitlements"], ["gaokao"])

    def test_license_file_persists_signed_entitlements(self):
        code, payload = _fake_em3(["zhongkao", "cet6"])
        with tempfile.TemporaryDirectory() as temp_dir:
            path = str(Path(temp_dir) / "licensing.dat")
            with mock.patch.object(main, "LICENSE_PUBLIC_E", 1):
                main.save_license_file(
                    path, MACHINE_ID, code, license_payload=payload)
                loaded = main.load_license_state(path, MACHINE_ID)
            stored = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(
            main._license_entitlements_from_payload(loaded),
            frozenset({"zhongkao", "cet6"}),
        )
        self.assertEqual(stored["entitlements"], ["zhongkao", "cet6"])

    def test_selector_shows_all_versions_but_blocks_locked_ones(self):
        inspected = {}

        def choose(dialog):
            buttons = {
                edition_id: dialog.findChild(
                    QtWidgets.QPushButton, f"btn_select_{edition_id}")
                for edition_id in main.FORMAL_EDITION_IDS
            }
            inspected["texts"] = {key: button.text() for key, button in buttons.items()}
            inspected["upgrade"] = dialog.findChild(
                QtWidgets.QPushButton, "btn_upgrade_license")
            buttons["cet4"].click()
            buttons["gaokao"].click()
            return QtWidgets.QDialog.DialogCode.Accepted

        with mock.patch.object(QtWidgets.QDialog, "exec", choose), mock.patch.object(
            QtWidgets.QMessageBox, "information", return_value=QtWidgets.QMessageBox.StandardButton.Ok
        ) as notice:
            selected = main.show_edition_selection_dialog(
                "gaokao", include_trial=True, entitlements={"gaokao"})

        self.assertEqual(selected.edition_id, "gaokao")
        self.assertIn("🔓 已解锁", inspected["texts"]["gaokao"])
        self.assertIn("开发中", inspected["texts"]["cet4"])
        self.assertIsNone(inspected["upgrade"])
        notice.assert_called_once()


if __name__ == "__main__":
    unittest.main()
