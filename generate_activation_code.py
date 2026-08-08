import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives.serialization import load_pem_private_key


PRODUCT_ID = "engmaster-vocabulary-platform"
FORMAL_EDITION_IDS = ("zhongkao", "gaokao", "cet4", "cet6", "kaoyan")
RELEASED_EDITION_IDS = ("gaokao",)
DEFAULT_PRIVATE_KEY_PATH = os.getenv("LICENSE_PRIVATE_KEY_PATH", "").strip()
DEFAULT_ORDER_REGISTRY_PATH = Path(os.getenv(
    "ENGMASTER_ORDER_REGISTRY",
    str(Path(__file__).resolve().parent / ".license_generator_work" /
        "internal_orders.json"),
))


def normalize_order_number(value: str) -> str:
    order_number = str(value or "").strip()
    if not order_number:
        raise ValueError("订单号不能为空。")
    return order_number


def _load_order_registry(registry_path: Path) -> list:
    if not registry_path.exists():
        return []
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("内部订单登记文件格式错误。")
    return data


def _write_order_registry(registry_path: Path, orders: list):
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = registry_path.with_suffix(registry_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(orders, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(registry_path)


def create_internal_order(order_type: str, note: str, registry_path: Path) -> dict:
    normalized_type = re.sub(r"[^A-Z0-9]", "", str(order_type).upper())
    if not 2 <= len(normalized_type) <= 12:
        raise ValueError("内部订单类型需为2至12位英文字母或数字，例如 TEST、FRIEND。")
    now = datetime.datetime.now(datetime.timezone.utc)
    orders = _load_order_registry(registry_path)
    existing_numbers = {
        str(item.get("order_number", "")) for item in orders
        if isinstance(item, dict)}
    while True:
        suffix = f"{secrets.randbelow(1_000_000):06d}"
        order_number = f"{now:%Y%m%d%H%M%S}{suffix}"
        if order_number not in existing_numbers:
            break
    record = {
        "order_number": order_number,
        "order_type": normalized_type,
        "note": str(note or "").strip(),
        "status": "issued",
        "created_at": now.isoformat(timespec="seconds"),
        "activation_count": 0,
    }
    orders.append(record)
    _write_order_registry(registry_path, orders)
    return record


def find_internal_order(order_number: str, registry_path: Path):
    normalized = normalize_order_number(order_number)
    for record in _load_order_registry(registry_path):
        if (isinstance(record, dict) and
                str(record.get("order_number", "")).upper() == normalized):
            return record
    return None


def record_internal_order_activation(
        order_number: str, machine_id: str, entitlements, registry_path: Path):
    orders = _load_order_registry(registry_path)
    normalized = normalize_order_number(order_number)
    for record in orders:
        if (isinstance(record, dict) and
                str(record.get("order_number", "")).upper() == normalized):
            record["status"] = "activation_generated"
            record["activation_count"] = int(record.get("activation_count", 0)) + 1
            record["last_machine_id"] = machine_id.strip().upper()
            record["last_entitlements"] = list(entitlements)
            record["last_activation_at"] = datetime.datetime.now(
                datetime.timezone.utc).isoformat(timespec="seconds")
            _write_order_registry(registry_path, orders)
            return
    raise ValueError("内部订单号不存在于客服登记文件中。")


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


def make_em3_code(
        machine_id: str, entitlements, private_key_path: Path,
        order_number: str = "") -> str:
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
    if order_number:
        payload["order_number"] = normalize_order_number(order_number)
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
    parser.add_argument(
        "--create-internal-order",
        metavar="TYPE",
        help="Create and register a support order, e.g. TEST or FRIEND.",
    )
    parser.add_argument(
        "--order-note",
        default="",
        help="Internal note saved with a newly created EMO order.",
    )
    parser.add_argument(
        "--list-internal-orders",
        action="store_true",
        help="List internal orders from the private support registry.",
    )
    parser.add_argument(
        "--order-registry",
        default=str(DEFAULT_ORDER_REGISTRY_PATH),
        help="Private JSON registry used by support for internal orders.",
    )
    parser.add_argument(
        "--order-number",
        default="",
        help="Taobao or support-provided order number to sign into EM3.",
    )
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    registry_path = Path(args.order_registry)
    if args.create_internal_order:
        record = create_internal_order(
            args.create_internal_order, args.order_note, registry_path)
        print("internal_order_number=", record["order_number"])
        print("registry=", registry_path.resolve())
        return
    if args.list_internal_orders:
        orders = _load_order_registry(registry_path)
        if not orders:
            print("No internal orders found.")
            return
        for record in orders:
            print(
                record.get("order_number", ""),
                record.get("status", ""),
                record.get("note", ""),
            )
        print("registry=", registry_path.resolve())
        return
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
    order_number = normalize_order_number(args.order_number) if args.order_number else ""
    internal_order = (
        find_internal_order(order_number, registry_path) if order_number else None)
    if args.legacy_em2:
        if order_number:
            raise SystemExit("旧版 EM2 不能记录订单号，请生成 EM3 激活码。")
        code = make_em2_code(machine_id, private_key_path)
    else:
        code = make_em3_code(
            machine_id, args.editions, private_key_path,
            order_number=order_number)
        if internal_order:
            record_internal_order_activation(
                order_number, machine_id, args.editions, registry_path)
    if order_number:
        print("order_number=", order_number)
    print("activation_code=", code)


if __name__ == "__main__":
    main()
