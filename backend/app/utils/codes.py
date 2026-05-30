"""Short, human-friendly random codes (referral codes, etc.)."""
from __future__ import annotations

import secrets

# No ambiguous characters (0/O, 1/I/L).
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def random_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
