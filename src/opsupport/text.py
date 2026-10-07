"""Turkish text helpers for reading the customer's confirmation."""

from __future__ import annotations

import re

_FOLD = str.maketrans("çğıöşü", "cgiosu")
YES = ("evet", "onay", "tamam", "olur", "kabul", "isterim", "yapin", "yap")
NO = ("hayir", "vazgec", "istemiyorum", "istemem", "iptal", "olmaz", "olmasin", "degil", "sonra", "yapma", "onaylamiyorum")


def fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").lower().translate(_FOLD)


def is_affirmative(text: str) -> bool:
    """True only for a clear yes. Questions, refusals and mixed messages do not count."""
    t = fold(text)
    if "?" in t or any(re.search(rf"\b{w}", t) for w in NO):
        return False
    return any(re.search(rf"\b{w}", t) for w in YES)
