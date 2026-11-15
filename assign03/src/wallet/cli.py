"""
wallet.cli
==========
Command-line interface for the wallet tool.
Provides commands:
  keygen  - Generate new Ed25519 keypair and address
  address - Derive Base58Check address from a public key hex
  sign    - Sign a canonical transaction JSON with a private key
  verify  - Independently verify a signed transaction against rules
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from wallet.core import (
    DEFAULT_NETWORK_ID,
    b58check_decode,
    generate_keypair,
    pubkey_to_address,
    save_private_key_file,
    sign_transaction,
    verify_transaction,
)


def cmd_keygen(args: argparse.Namespace) -> int:
    priv, pub = generate_keypair()
    priv_bytes = priv.private_bytes_raw()
    pub_bytes = pub.public_bytes_raw()
    addr = pubkey_to_address(pub_bytes)

    if args.out:
        save_private_key_file(args.out, priv_bytes, pub_bytes, addr)
        print(f"Dev private key saved with 0600 permissions to: {args.out}", file=sys.stderr)
        print("WARNING: TEST ONLY - DO NOT USE ON MAINNET", file=sys.stderr)

    public_info = {
        "address": addr,
        "public_key_hex": pub_bytes.hex(),
        "network_id": DEFAULT_NETWORK_ID,
    }

    if args.pub_out:
        Path(args.pub_out).write_text(json.dumps(public_info, indent=2), encoding="utf-8")
        print(f"Public key info saved to: {args.pub_out}", file=sys.stderr)

    print(json.dumps(public_info, indent=2))
    return 0


def cmd_address(args: argparse.Namespace) -> int:
    try:
        clean_hex = args.pubkey.strip()
        if clean_hex.startswith("0x"):
            clean_hex = clean_hex[2:]
        pub_bytes = bytes.fromhex(clean_hex)
        addr = pubkey_to_address(pub_bytes)
        print(f"address: {addr}")
        return 0
    except Exception as e:
        print(f"Error deriving address: {e}", file=sys.stderr)
        return 1


def load_private_key_bytes(key_input: str) -> bytes:
    path = Path(key_input)
    if path.is_file():
        raw_text = path.read_text(encoding="utf-8")
        # Strip comments
        lines = [line for line in raw_text.splitlines() if not line.strip().startswith("#")]
        parsed = json.loads("".join(lines))
        hex_str = parsed.get("private_key_hex", "")
        return bytes.fromhex(hex_str)
    else:
        clean = key_input.strip()
        if clean.startswith("0x"):
            clean = clean[2:]
        return bytes.fromhex(clean)


def cmd_sign(args: argparse.Namespace) -> int:
    try:
        priv_bytes = load_private_key_bytes(args.key)
    except Exception as e:
        print(f"Error loading private key: {e}", file=sys.stderr)
        return 1

    tx_input = args.tx
    tx_path = Path(args.tx)
    if tx_path.is_file():
        tx_input = tx_path.read_text(encoding="utf-8")

    try:
        tx_data = json.loads(tx_input)
    except Exception as e:
        print(f"Error parsing transaction JSON: {e}", file=sys.stderr)
        return 1

    try:
        signed_tx = sign_transaction(priv_bytes, tx_data)
        out_json = json.dumps(signed_tx, indent=2)
        print(out_json)
        if args.out:
            Path(args.out).write_text(out_json, encoding="utf-8")
        return 0
    except Exception as e:
        print(f"Error signing transaction: {e}", file=sys.stderr)
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    stx_input = args.signed_tx
    stx_path = Path(args.signed_tx)
    if stx_path.is_file():
        stx_input = stx_path.read_text(encoding="utf-8")

    try:
        signed_data = json.loads(stx_input)
    except Exception as e:
        print(f"Error parsing signed transaction JSON: {e}", file=sys.stderr)
        return 1

    nonce_db = None
    if args.state_db:
        db_path = Path(args.state_db)
        if db_path.is_file():
            try:
                nonce_db = json.loads(db_path.read_text(encoding="utf-8"))
            except Exception:
                nonce_db = {}
        else:
            nonce_db = {}

    try:
        verify_transaction(
            signed_data,
            expected_network=args.network,
            nonce_tracker=nonce_db,
        )
        if args.state_db and nonce_db is not None:
            Path(args.state_db).write_text(json.dumps(nonce_db, indent=2), encoding="utf-8")

        print("TRANSACTION VERIFIED: Signature, address derivation, nonce, and contents are authentic.")
        return 0
    except Exception as e:
        print(f"VERIFICATION REJECTED: {e}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wallet",
        description="Educational cryptographic wallet CLI for toy chain.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # keygen
    p_kg = subparsers.add_parser("keygen", help="Generate Ed25519 keypair.")
    p_kg.add_argument("--out", help="Path to save private key file with 0600 permissions")
    p_kg.add_argument("--pub-out", help="Path to save public key info JSON")
    p_kg.set_defaults(func=cmd_keygen)

    # address
    p_addr = subparsers.add_parser("address", help="Derive address from public key.")
    p_addr.add_argument("--pubkey", required=True, help="32-byte public key hex")
    p_addr.set_defaults(func=cmd_address)

    # sign
    p_sign = subparsers.add_parser("sign", help="Sign transaction JSON.")
    p_sign.add_argument("--key", required=True, help="Private key file or 64 hex char string")
    p_sign.add_argument("--tx", required=True, help="Transaction JSON string or file path")
    p_sign.add_argument("--out", help="Path to save signed transaction JSON")
    p_sign.set_defaults(func=cmd_sign)

    # verify
    p_ver = subparsers.add_parser("verify", help="Verify signed transaction.")
    p_ver.add_argument("--signed-tx", required=True, help="Signed transaction JSON string or file path")
    p_ver.add_argument("--network", default=DEFAULT_NETWORK_ID, help="Expected network ID")
    p_ver.add_argument("--state-db", help="Path to JSON file tracking confirmed sender nonces")
    p_ver.set_defaults(func=cmd_verify)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

