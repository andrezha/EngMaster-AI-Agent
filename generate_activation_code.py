import argparse
import base64
import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives.serialization import load_pem_private_key


PRODUCT_ID = "engmaster-ai-agent"
DEFAULT_PRIVATE_KEY_PATH = os.getenv("LICENSE_PRIVATE_KEY_PATH", "").strip()


def get_machine_id():
    import platform
    import sys
    import uuid

    material = ""
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                material = "windows-machine-guid-v2|" + str(machine_guid).strip().lower()
        except Exception:
            pass

    if not material:
        parts = [platform.node(), platform.system(), platform.machine(), str(uuid.getnode())]
        material = "fallback-machine-v2|" + "|".join(
            str(part).strip().lower() for part in parts if str(part).strip()
        )

    digest = hashlib.sha256((f"EngMaster-AI-Agent|{material}").encode("utf-8")).hexdigest().upper()
    compact = digest[:32]
    return "-".join(compact[i:i + 8] for i in range(0, len(compact), 8))


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
    print("activation_code=", make_em2_code(machine_id, private_key_path))


if __name__ == "__main__":
    main()
