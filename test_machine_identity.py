import base64
import hashlib
import json
import unittest
from unittest import mock

import main


def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class MachineIdentityTests(unittest.TestCase):
    def test_oem_placeholders_are_rejected(self):
        for value in (
                "", "Default String", "To Be Filled By O.E.M.",
                "00000000", "FFFFFFFF", "System Serial Number"):
            self.assertEqual(main._normalize_hardware_id(value), "")

    def test_machine_id_contains_independent_hashed_components(self):
        hardware = {
            "system_uuid": "00112233445566778899AABBCCDDEEFF",
            "baseboard_serial": "BOARD123456",
            "system_serial": "SYSTEM654321",
        }
        with mock.patch.object(
                main, "_read_windows_smbios_ids", return_value=hardware), mock.patch.object(
                    main, "_read_windows_machine_guid", return_value="GUID123456"):
            machine_id = main.get_machine_id()
        parts = main._parse_machine_id(machine_id)
        self.assertEqual(set(parts), {"U", "B", "S", "G"})
        self.assertTrue(machine_id.startswith("EMPC3-U"))
        self.assertNotIn("BOARD123456", machine_id)

    def test_reinstall_matches_on_hardware_when_machine_guid_changes(self):
        before = "EMPC3-U1111111111111111-B2222222222222222-G3333333333333333"
        after = "EMPC3-U1111111111111111-B2222222222222222-G4444444444444444"
        self.assertTrue(main.machine_ids_match(before, after))

    def test_hardware_mismatch_is_not_hidden_by_same_machine_guid(self):
        first = "EMPC3-U1111111111111111-B2222222222222222-GAAAAAAAAAAAAAAAA"
        second = "EMPC3-U9999999999999999-B8888888888888888-GAAAAAAAAAAAAAAAA"
        self.assertFalse(main.machine_ids_match(first, second))

    def test_machine_guid_fallback_matches_when_hardware_is_unavailable(self):
        licensed = "EMPC3-U1111111111111111-GAAAAAAAAAAAAAAAA"
        restricted = "EMPC3-GAAAAAAAAAAAAAAAA"
        self.assertTrue(main.machine_ids_match(licensed, restricted))

    def test_signed_license_survives_windows_reinstall_component_change(self):
        licensed_id = "EMPC3-U1111111111111111-G2222222222222222"
        current_id = "EMPC3-U1111111111111111-G3333333333333333"
        payload = {
            "product": main.LICENSE_PRODUCT_ID,
            "machine_id": licensed_id,
            "version": main.LICENSE_FORMAT_VERSION,
            "entitlements": ["gaokao"],
        }
        payload_bytes = json.dumps(
            payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = hashlib.sha256(payload_bytes).digest()
        code = f"EM3-{_b64(payload_bytes)}.{_b64(signature)}"
        with mock.patch.object(main, "LICENSE_PUBLIC_E", 1):
            ok, verified = main.verify_activation_code(code, current_id)
        self.assertTrue(ok)
        self.assertEqual(verified["entitlements"], ["gaokao"])


if __name__ == "__main__":
    unittest.main()
