"""
AlgoRacers — Session 17: Content Addressing & CID Utilities
Module: blockchain/scripts/cid_utils.py
===========================================================
Pure Python deterministic multihash and CIDv1 (base32) computation.
Follows IPFS multiformats specification:
  - Hash Function: SHA-256 (0x12)
  - Digest Length: 32 bytes (0x20)
  - Codec: Raw (0x55) or DAG-PB (0x70)
  - Multibase: Base32 lowercase ('b' prefix)
"""

import hashlib
import json
import base64
from typing import Dict, Any, Tuple

# Base32 lowercase alphabet (RFC 4648 without padding)
BASE32_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"

def compute_sha256(content: bytes) -> bytes:
    """Returns the 32-byte SHA-256 digest."""
    return hashlib.sha256(content).digest()

def encode_base32_no_padding(data: bytes) -> str:
    """Encodes raw bytes into base32 lowercase without padding."""
    # Standard base32 uppercase with padding
    b32_str = base64.b32encode(data).decode("ascii").lower()
    return b32_str.rstrip("=")

def compute_cid_v1(content: bytes, codec: int = 0x55) -> str:
    """
    Computes a deterministic CIDv1 base32 string for the given content.
    Header structure:
      - CID version: 0x01
      - Codec: 0x55 (raw) or 0x70 (dag-pb)
      - Multihash code: 0x12 (SHA-256)
      - Multihash length: 0x20 (32 bytes)
      - Digest: 32 bytes
    Prefix: 'b' for base32 lowercase multibase
    """
    digest = compute_sha256(content)
    multihash = bytes([0x12, 0x20]) + digest
    cid_bytes = bytes([0x01, codec]) + multihash
    return "b" + encode_base32_no_padding(cid_bytes)

def canonical_json_bytes(data: Dict[str, Any]) -> bytes:
    """
    Serializes a dictionary into canonical UTF-8 JSON bytes:
      - Keys sorted alphabetically
      - Compact separators (',', ':')
      - No trailing newlines or extra whitespace
    """
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

def verify_cid(content: bytes, expected_cid: str, codec: int = 0x55) -> bool:
    """Verifies that the content reproduces the exact expected CID."""
    computed = compute_cid_v1(content, codec=codec)
    return computed == expected_cid
