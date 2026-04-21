from __future__ import annotations

import hashlib


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest().upper()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest().upper()
