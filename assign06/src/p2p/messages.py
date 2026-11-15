"""
p2p.messages
============
Versioned P2P protocol messages and length-prefixed safe framing.
Maximum message size: 1 MB (1,048,576 bytes).
"""

from __future__ import annotations

import asyncio
import json
import struct
from typing import Any, Dict, Optional

MAX_MESSAGE_SIZE = 1048576  # 1 MB framing cap
PROTOCOL_VERSION = 1


def frame_message(msg_dict: Dict[str, Any]) -> bytes:
    """
    Serializes a message dictionary to UTF-8 JSON with a 4-byte big-endian length prefix.
    """
    payload = json.dumps(msg_dict, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError(f"Payload size {len(payload)} exceeds maximum allowed {MAX_MESSAGE_SIZE} bytes.")
    return struct.pack(">I", len(payload)) + payload


async def read_framed_message(reader: asyncio.StreamReader) -> Optional[Dict[str, Any]]:
    """
    Safely reads a length-prefixed framed message from an asyncio stream.
    Enforces the 1 MB size limit before loading the payload into memory.
    Returns parsed dictionary, or None on clean EOF.
    """
    try:
        prefix = await reader.readexactly(4)
    except (asyncio.IncompleteReadError, ConnectionResetError):
        return None

    msg_len = struct.unpack(">I", prefix)[0]
    if msg_len > MAX_MESSAGE_SIZE:
        raise ValueError(f"Frame length {msg_len} exceeds maximum allowed {MAX_MESSAGE_SIZE} bytes.")
    if msg_len == 0:
        return {}

    try:
        raw_payload = await reader.readexactly(msg_len)
    except asyncio.IncompleteReadError as e:
        raise ConnectionError("Stream closed while reading framed payload.") from e

    try:
        return json.loads(raw_payload.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Malformed JSON payload in framed message: {e}") from e

