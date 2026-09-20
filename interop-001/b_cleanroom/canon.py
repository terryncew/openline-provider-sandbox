"""olp-canonical-json-int-v1, implemented from olp-wire-canon SPEC.md section 3.

Domain: null, booleans, strings, arrays, objects, integers in
[-9007199254740991, 9007199254740991]. ASCII object keys. No floats.
Output: keys sorted by ascending ASCII code point, no insignificant
whitespace, non-ASCII as lowercase \\u escapes, shortest escapes for
quote/backslash/standard control escapes, final bytes ASCII.
"""

from __future__ import annotations

import json
from typing import Any

INT_MIN = -9007199254740991
INT_MAX = 9007199254740991


class CanonError(ValueError):
    pass


def _validate(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not (INT_MIN <= value <= INT_MAX):
            raise CanonError(f"integer out of canonical range: {value}")
        return
    if isinstance(value, float):
        raise CanonError("floats are forbidden in canonical JSON")
    if isinstance(value, str):
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate(item)
        return
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonError(f"non-string object key: {key!r}")
            try:
                key.encode("ascii")
            except UnicodeEncodeError:
                raise CanonError(f"non-ASCII object key: {key!r}")
        for item in value.values():
            _validate(item)
        return
    raise CanonError(f"unsupported type: {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    """Return the canonical byte representation (ASCII)."""
    _validate(value)
    # ensure_ascii=True -> non-ASCII as \uXXXX with lowercase hex and
    # surrogate pairs; separators remove whitespace; sort_keys orders by
    # code point (== ASCII order for ASCII keys); allow_nan=False bans
    # NaN/Infinity; Python uses shortest escapes for quote, backslash and
    # the standard control escapes, \u00xx (lowercase) otherwise.
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return text.encode("ascii")


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, val in pairs:
        if key in obj:
            raise CanonError(f"duplicate object key: {key!r}")
        obj[key] = val
    return obj


def strict_json_loads(text: str) -> Any:
    """Parse JSON, rejecting duplicate keys before canonicalization."""
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicates)
    except CanonError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface as CanonError
        raise CanonError(f"invalid JSON: {exc}") from exc
