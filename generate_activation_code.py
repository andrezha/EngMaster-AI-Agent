import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.serialization import load_pem_private_key


PRODUCT_ID = "engmaster-vocabulary-platform"
FORMAL_EDITION_IDS = ("zhongkao", "gaokao", "cet4", "cet6", "kaoyan")
RELEASED_EDITION_IDS = ("gaokao",)
DEFAULT_PRIVATE_KEY_PATH = os.getenv("LICENSE_PRIVATE_KEY_PATH", "").strip()


def get_machine_id():
    # Keep local test generation identical to the customer application's
    # hardware-first EMPC3 identifier implementation.
    from main import get_machine_id as get_application_machine_id

    return get_application_machine_id()


def _load_private_numbers(private_key_path: Path):
    private_key = load_pem_private_key(private_key_path.read_bytes(), password=None)
    return private_key.private_numbers()


def make_em2_code(machine_id: str, private_key_path: Path) -> str:
    machine_id = machine_id.strip().upper()
    private_numbers = _load_private_numbers(private_key_path)
    payload = f"{PRODUCT_ID}|{machine_id}|v2".encode("utf-8")
    digest_int = int.from_bytes(hashlib.sha256(payload).digest(), "big")
    sig_int = pow(digest_int, private_numbers.d, private_numbers.public_numbers.n)
    sig_bytes = sig_int.to_bytes((private_numbers.public_numbers.n.bit_length() + 7) // 8, "big")
    return "EM2-" + base64.urlsafe_b64encode(sig_bytes).decode("ascii").rstrip("=")


def make_em3_code(machine_id: str, entitlements, private_key_path: Path) -> str:
    machine_id = machine_id.strip().upper().replace(" ", "")
    requested = {
        item.strip().lower()
        for value in entitlements
        for item in str(value).split(",")
        if item.strip()
    }
    unknown = requested - set(FORMAL_EDITION_IDS)
    if unknown:
        raise ValueError(f"未知版本：{', '.join(sorted(unknown))}")
    unavailable = requested - set(RELEASED_EDITION_IDS)
    if unavailable:
        raise ValueError(
            "当前 V1.0 只开放高考英语正式授权；以下版本仍在开发中："
            + ", ".join(sorted(unavailable)))
    ordered = [item for item in FORMAL_EDITION_IDS if item in requested]
    if not ordered:
        raise ValueError("至少需要一个版本权限。")
    payload = {
        "product": PRODUCT_ID,
        "machine_id": machine_id,
        "version": 3,
        "entitlements": ordered,
        "issued_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    payload_bytes = json.dumps(
        payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    private_numbers = _load_private_numbers(private_key_path)
    digest_int = int.from_bytes(hashlib.sha256(payload_bytes).digest(), "big")
    sig_int = pow(digest_int, private_numbers.d, private_numbers.public_numbers.n)
    sig_bytes = sig_int.to_bytes(
        (private_numbers.public_numbers.n.bit_length() + 7) // 8, "big")
    return f"EM3-{_b64encode(payload_bytes)}.{_b64encode(sig_bytes)}"


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def private_key_public_numbers(private_key_path: Path):
    private_numbers = _load_private_numbers(private_key_path)
    public_numbers = private_numbers.public_numbers
    return public_numbers.n, public_numbers.e


def parse_args():
    parser = argparse.ArgumentParser(description="Generate an EM2 machine-bound activation code.")
    parser.add_argument("machine_id", nargs="?", help="Customer machine ID shown in the activation window.")
    parser.add_argument(
        "--private-key",
        default=DEFAULT_PRIVATE_KEY_PATH,
        help="Path to private.pem. You can also set LICENSE_PRIVATE_KEY_PATH.",
    )
    parser.add_argument(
        "--editions",
        nargs="+",
        default=["gaokao"],
        help="Cumulative formal permissions: zhongkao gaokao cet4 cet6 kaoyan.",
    )
    parser.add_argument(
        "--legacy-em2",
        action="store_true",
        help="Generate the old gaokao-only EM2 code (compatibility/testing only).",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Generate a code for this computer, useful only for local testing.",
    )
    parser.add_argument(
        "--print-public",
        action="store_true",
        help="Print the public key numbers that must match the client app.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.private_key:
        raise SystemExit("请用 --private-key 指定 private.pem，或先设置 LICENSE_PRIVATE_KEY_PATH 环境变量。")
    private_key_path = Path(args.private_key)

    if args.print_public:
        public_n, public_e = private_key_public_numbers(private_key_path)
        print("public_n=", public_n)
        print("public_e=", public_e)
        return

    machine_id = get_machine_id() if args.local else (args.machine_id or "")
    if not machine_id:
        raise SystemExit("请传入客户机器码；如需给本机测试，请使用 --local。")

    print("machine_id=", machine_id.strip().upper())
    if args.legacy_em2:
        code = make_em2_code(machine_id, private_key_path)
    else:
        code = make_em3_code(machine_id, args.editions, private_key_path)
    print("activation_code=", code)


if __name__ == "__main__":
    main()
