"""
AlgoRacers — Session 17: Backend IPFS & CID Utilities
Module: services/ipfs_utils.py
=====================================================
Cryptographic content addressing, canonical serialization, and multi-gateway resolution.
"""

import hashlib
import json
import base64
from typing import Dict, Any, List

DEFAULT_IPFS_GATEWAYS = [
    "https://ipfs.io/ipfs/",
    "https://dweb.link/ipfs/",
    "https://cloudflare-ipfs.com/ipfs/",
    "https://gateway.pinata.cloud/ipfs/"
]

def compute_sha256_hex(content: bytes) -> str:
    """Returns SHA-256 hex digest."""
    return hashlib.sha256(content).hexdigest()

def compute_cid_v1(content: bytes, codec: int = 0x55) -> str:
    """Computes a deterministic CIDv1 base32 string."""
    digest = hashlib.sha256(content).digest()
    multihash = bytes([0x12, 0x20]) + digest
    cid_bytes = bytes([0x01, codec]) + multihash
    b32_str = base64.b32encode(cid_bytes).decode("ascii").lower().rstrip("=")
    return "b" + b32_str

def canonical_json_bytes(data: Dict[str, Any]) -> bytes:
    """Deterministic UTF-8 JSON serialization with sorted keys and compact separators."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

def resolve_ipfs_gateway_url(ipfs_uri: str, gateway_base: str = DEFAULT_IPFS_GATEWAYS[0]) -> str:
    """Converts an ipfs:// URI into an HTTP gateway URL."""
    if not ipfs_uri.startswith("ipfs://"):
        return ipfs_uri
    path = ipfs_uri.replace("ipfs://", "")
    return f"{gateway_base.rstrip('/')}/{path.lstrip('/')}"
