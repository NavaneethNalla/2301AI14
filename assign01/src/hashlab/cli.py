"""
hashlab.cli
===========
Command-line interface for the hashlab tool.
Provides commands:
  text            - Hash UTF-8 text string
  hex             - Hash raw hexadecimal byte string
  file            - Hash file via O(1) memory chunk streaming
  avalanche       - Flip single bit and report digest Hamming distance
  canonical-json  - Canonicalize JSON and hash deterministic bytes
  demo-differences- Demonstrate hash divergence on visually similar inputs
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import unicodedata

from hashlab.core import (
    canonicalize_obj,
    flip_bit,
    flip_bit_in_file_stream,
    hamming_distance,
    hash_bytes,
    hash_file,
    parse_canonical_json,
    parse_hex,
    to_canonical_json_bytes,
)


def print_hash_diagnostics(total_bytes: int, sha256_hex: str, sha256_b64: str) -> None:
    """Prints diagnostics in the exact required format."""
    print(f"bytes: {total_bytes}")
    print(f"sha256: {sha256_hex}")
    print(f"base64: {sha256_b64}")


def cmd_text(args: argparse.Namespace) -> int:
    raw_bytes = args.string.encode("utf-8")
    length, sha256_hex, sha256_b64 = hash_bytes(raw_bytes)
    print_hash_diagnostics(length, sha256_hex, sha256_b64)
    return 0


def cmd_hex(args: argparse.Namespace) -> int:
    try:
        raw_bytes = parse_hex(args.hex_string)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    length, sha256_hex, sha256_b64 = hash_bytes(raw_bytes)
    print_hash_diagnostics(length, sha256_hex, sha256_b64)
    return 0


def cmd_file(args: argparse.Namespace) -> int:
    try:
        length, sha256_hex, sha256_b64 = hash_file(args.path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print_hash_diagnostics(length, sha256_hex, sha256_b64)
    return 0


def cmd_avalanche(args: argparse.Namespace) -> int:
    sources = [args.text is not None, args.hex is not None, args.file is not None]
    if sum(sources) != 1:
        print("Error: Exactly one of --text, --hex, or --file must be specified.", file=sys.stderr)
        return 1

    try:
        if args.file is not None:
            _, orig_hex, _ = hash_file(args.file)
            orig_digest = bytes.fromhex(orig_hex)
            _, mutated_digest = flip_bit_in_file_stream(args.file, args.bit)
        else:
            if args.text is not None:
                raw_bytes = args.text.encode("utf-8")
            else:
                raw_bytes = parse_hex(args.hex)

            orig_digest = hashlib.sha256(raw_bytes).digest()
            mutated_bytes = flip_bit(raw_bytes, args.bit)
            mutated_digest = hashlib.sha256(mutated_bytes).digest()

        changed_bits = hamming_distance(orig_digest, mutated_digest)
        print(f"changed_bits_in_digest: {changed_bits}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_canonical_json(args: argparse.Namespace) -> int:
    try:
        canonical_bytes = parse_canonical_json(args.input)
        length, sha256_hex, sha256_b64 = hash_bytes(canonical_bytes)
        print_hash_diagnostics(length, sha256_hex, sha256_b64)
        return 0
    except Exception as e:
        print(f"Error parsing/canonicalizing JSON: {e}", file=sys.stderr)
        return 1


def cmd_demo_differences(args: argparse.Namespace) -> int:
    print("=" * 70)
    print("DEMONSTRATION: SENSITIVITY OF CRYPTOGRAPHIC HASHES TO INPUT BYTES")
    print("=" * 70)

    # 1. Newline differences
    print("\n1. Line Ending Differences (LF vs CRLF vs No Newline)")
    print("-" * 70)
    samples = [
        ("No newline", b"Alice pays Bob 10"),
        ("LF newline (\\n)", b"Alice pays Bob 10\n"),
        ("CRLF newline (\\r\\n)", b"Alice pays Bob 10\r\n"),
    ]
    for label, b in samples:
        h = hashlib.sha256(b).hexdigest()
        print(f"  [{label:<22}] len={len(b):<2} bytes={b.hex()} -> sha256={h}")

    # 2. Unicode normalization (NFC vs NFD)
    print("\n2. Unicode Normalization (NFC vs NFD)")
    print("-" * 70)
    nfc_str = "café"  # NFC: 'e' with acute as single codepoint U+00E9
    nfd_str = unicodedata.normalize("NFD", nfc_str)  # 'e' + U+0301 combining acute
    nfc_bytes = nfc_str.encode("utf-8")
    nfd_bytes = nfd_str.encode("utf-8")
    print(f"  Visual string: '{nfc_str}' vs '{nfd_str}' (Strings equal in Python? {nfc_str == nfd_str})")
    print(f"  [NFC (precomposed)]     len={len(nfc_bytes)} bytes={nfc_bytes.hex()} -> sha256={hashlib.sha256(nfc_bytes).hexdigest()}")
    print(f"  [NFD (decomposed)]      len={len(nfd_bytes)} bytes={nfd_bytes.hex()} -> sha256={hashlib.sha256(nfd_bytes).hexdigest()}")
    print(f"  [Canonical JSON norm]   Normalizing to NFC guarantees identical hashes!")

    # 3. JSON Integer vs String
    print("\n3. JSON Integer vs String Type Ambiguity")
    print("-" * 70)
    int_obj = {"amount": 10}
    str_obj = {"amount": "10"}
    int_bytes = to_canonical_json_bytes(int_obj)
    str_bytes = to_canonical_json_bytes(str_obj)
    print(f"  [JSON Integer 10]       bytes={int_bytes.decode('utf-8')} -> sha256={hashlib.sha256(int_bytes).hexdigest()}")
    print(f"  [JSON String '10']      bytes={str_bytes.decode('utf-8')} -> sha256={hashlib.sha256(str_bytes).hexdigest()}")

    # 4. JSON Key Order and Whitespace
    print("\n4. Raw JSON Key Order and Whitespace vs Canonical JSON")
    print("-" * 70)
    raw_1 = b'{\n  "recipient": "Bob",\n  "amount": 10\n}'
    raw_2 = b'{"amount": 10, "recipient": "Bob"}'
    canon_1 = parse_canonical_json(raw_1.decode("utf-8"))
    canon_2 = parse_canonical_json(raw_2.decode("utf-8"))
    print(f"  Raw 1 sha256:        {hashlib.sha256(raw_1).hexdigest()}")
    print(f"  Raw 2 sha256:        {hashlib.sha256(raw_2).hexdigest()} (Different due to whitespace & ordering!)")
    print(f"  Canonical 1 sha256:  {hashlib.sha256(canon_1).hexdigest()}")
    print(f"  Canonical 2 sha256:  {hashlib.sha256(canon_2).hexdigest()} (Identical: {canon_1.decode('utf-8')})")
    print("=" * 70)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hashlab",
        description="Cryptographic hashing, byte diagnostics, and canonicalization tool.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # text
    p_text = subparsers.add_parser("text", help="Hash UTF-8 text string.")
    p_text.add_argument("string", help="String to hash")
    p_text.set_defaults(func=cmd_text)

    # hex
    p_hex = subparsers.add_parser("hex", help="Hash hexadecimal byte string.")
    p_hex.add_argument("hex_string", help="Hexadecimal string to decode and hash")
    p_hex.set_defaults(func=cmd_hex)

    # file
    p_file = subparsers.add_parser("file", help="Hash file using fixed 64 KB streaming buffers.")
    p_file.add_argument("path", help="Path to file")
    p_file.set_defaults(func=cmd_file)

    # avalanche
    p_avalanche = subparsers.add_parser("avalanche", help="Analyze avalanche effect by flipping 1 bit.")
    p_avalanche.add_argument("--text", help="Input text string")
    p_avalanche.add_argument("--hex", help="Input hexadecimal byte string")
    p_avalanche.add_argument("--file", help="Input file path")
    p_avalanche.add_argument("--bit", type=int, required=True, help="0-indexed bit to flip (MSB-first)")
    p_avalanche.set_defaults(func=cmd_avalanche)

    # canonical-json
    p_canon = subparsers.add_parser("canonical-json", help="Canonicalize JSON and hash UTF-8 bytes.")
    p_canon.add_argument("input", help="JSON string or path to JSON file")
    p_canon.set_defaults(func=cmd_canonical_json)

    # demo-differences
    p_demo = subparsers.add_parser("demo-differences", help="Demonstrate differences for visually similar inputs.")
    p_demo.set_defaults(func=cmd_demo_differences)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

