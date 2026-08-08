import json
import base64
import tempfile
import unittest
from pathlib import Path

import generate_activation_code as generator

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class InternalOrderTests(unittest.TestCase):
    def test_create_internal_order_is_persisted_and_findable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = Path(temp_dir) / "internal_orders.json"
            record = generator.create_internal_order(
                "test", "测试人员小王", registry)

            self.assertRegex(
                record["order_number"],
                r"^[0-9]{20}$")
            self.assertEqual(record["status"], "issued")
            self.assertEqual(record["note"], "测试人员小王")
            self.assertEqual(
                generator.find_internal_order(record["order_number"], registry),
                record)
            stored = json.loads(registry.read_text(encoding="utf-8"))
            self.assertEqual(stored, [record])

    def test_internal_order_activation_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = Path(temp_dir) / "internal_orders.json"
            record = generator.create_internal_order(
                "friend", "朋友授权", registry)
            generator.record_internal_order_activation(
                record["order_number"], "EMPC3-TEST", ["gaokao"], registry)
            updated = generator.find_internal_order(
                record["order_number"], registry)

            self.assertEqual(updated["status"], "activation_generated")
            self.assertEqual(updated["activation_count"], 1)
            self.assertEqual(updated["last_machine_id"], "EMPC3-TEST")
            self.assertEqual(updated["last_entitlements"], ["gaokao"])

    def test_order_number_validation(self):
        self.assertEqual(
            generator.normalize_order_number(" 1234 5678 "), "1234 5678")
        self.assertEqual(generator.normalize_order_number("0"), "0")
        self.assertEqual(
            generator.normalize_order_number(" 客服-TEST/001 "),
            "客服-TEST/001")
        for invalid in ("", "   "):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    generator.normalize_order_number(invalid)

    def test_em3_payload_contains_signed_order_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            private_key_path = Path(temp_dir) / "private.pem"
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048)
            private_key_path.write_bytes(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ))
            code = generator.make_em3_code(
                "EMPC3-TEST", ["gaokao"], private_key_path,
                order_number="202608040001")
            payload_part = code[4:].split(".", 1)[0]
            payload = json.loads(base64.urlsafe_b64decode(
                payload_part + "=" * (-len(payload_part) % 4)))

            self.assertEqual(
                payload["order_number"], "202608040001")


if __name__ == "__main__":
    unittest.main()
