"""Canonical JSON per olp-wire-canon SPEC.md section 3
(`olp-canonical-json-int-v1`), written from the spec text only.

- accepted: null, booleans, strings, integers in
  [-9007199254740991, 9007199254740991], arrays, objects
- floats and non-finite numbers are forbidden
- object keys MUST be ASCII strings; sorted by ascending ASCII code point
- duplicate keys MUST be rejected by the parser before canonicalization
- no insignificant whitespace
- non-ASCII string characters encoded with lowercase JSON \\u escapes
- shortest JSON escapes for quote, reverse solidus, standard control escapes
- final byte sequence is ASCII
"""

from __future__ import annotations

import json

_INT_MIN = -(2**53 - 1)
_INT_MAX = 2**53 - 1


class CanonicalValueError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise CanonicalValueError(f"non-finite constant forbidden: {value}")


def _no_dupes(pairs: list[tuple[str, object]]) -> dict:
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise CanonicalValueError(f"duplicate key rejected: {key!r}")
        out[key] = value
    return out


def parse_strict(text: str) -> object:
    """Strict JSON parse: duplicate keys and non-finite constants rejected."""
    return json.loads(
        text,
        object_pairs_hook=_no_dupes,
        parse_constant=_reject_constant,
    )


def _check_keys_ascii(value: object) -> None:
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalValue  # unreachable; parser guarantees str
            try:
                key.encode("ascii")
            except UnicodeEncodeError as exc:
                raise CanonicalValueError(f"non-ASCII object key: {key!r}") from exc
            _check_keys_ascii(value[key])
    elif isinstance(value, list):
        for item in value:
            _check_keys_ascii(item)


class CanonicalValue(CanonicalValueError):
    pass


def _encode_string(text: str) -> str:
    # json.dumps with ensure_ascii=True emits lowercase \uXXXX escapes for
    # non-ASCII, shortest escapes (\n, \t, \", \\) for the standard set, and
    # \u00xx (lowercase hex) for other controls. That is exactly the spec's
    # string encoding.
    return json.dumps(text, ensure_ascii=True, separators=(",", ":"))


def _encode(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if not (_INT_MIN <= value <= _INT_MAX):
            raise CanonicalValueError(f"integer out of safe range: {value}")
        return str(value)
    if isinstance(value, float):
        raise CanonicalValueError("floats forbidden in canonical JSON")
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        _check_keys_ascii(value)
        # Python str ordering is by Unicode code point; for ASCII keys this
        # is exactly ascending ASCII code-point order per the spec.
        items = sorted(value.items(), key=lambda kv: kv[0])
        return "{" + ",".join(
            _encode_string(key) + ":" + _encode(item_value)
            for key, item_value in items
        ) + "}"
    raise CanonicalValueError(f"unsupported value type: {type(value).__name__}")


def canonical_bytes(value: object) -> bytes:
    """Canonical JSON byte sequence (ASCII)."""
    return _encode(value).encode("ascii")
