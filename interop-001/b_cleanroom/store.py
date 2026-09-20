"""B's state machinery: hash-chained evidence journal, standing ledger,
one-use consumption registry. Independent implementation written from the
frozen interop profile (kill-switch EVIDENCE.md semantics, B's own layout).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from .canon import canonical_json
from .envelope import sha256_hex

GENESIS = "GENESIS"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ChainStore:
    """Append-only hash-chained JSONL store. Each record binds the previous
    record's hash. Monotonic seq; no wall-clock ordering."""

    def __init__(self, path: str):
        self.path = path
        self._seq = 0
        self._prev = GENESIS
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    self._seq = rec["seq"]
                    self._prev = rec["record_hash"]

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        self._seq += 1
        body = {
            "seq": self._seq,
            "prev": self._prev,
            "observed_at": _utcnow(),
            **record,
        }
        body["record_hash"] = sha256_hex(canonical_json(body))
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(body, sort_keys=True) + "\n")
        self._prev = body["record_hash"]
        return body

    def verify_chain(self) -> tuple[bool, str]:
        prev = GENESIS
        seq = 0
        if not os.path.exists(self.path):
            return True, "empty"
        with open(self.path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                seq += 1
                if rec.get("seq") != seq or rec.get("prev") != prev:
                    return False, f"chain break at line {lineno}"
                check = {k: v for k, v in rec.items() if k != "record_hash"}
                if sha256_hex(canonical_json(check)) != rec.get("record_hash"):
                    return False, f"hash mismatch at line {lineno}"
                prev = rec["record_hash"]
        return True, f"ok seq={seq}"

    def records(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not os.path.exists(self.path):
            return out
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out


class ConsumedRegistry:
    """Set of consumed one-use authorization hashes (the signed
    one_use_code_hash values themselves)."""

    def __init__(self, path: str):
        self.path = path
        self._set: set[str] = set()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                self._set = {ln.strip() for ln in fh if ln.strip()}

    def is_consumed(self, code_hash: str) -> bool:
        return code_hash in self._set

    def consume(self, code_hash: str) -> None:
        if code_hash in self._set:
            raise ValueError("double consumption attempt")
        self._set.add(code_hash)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(code_hash + "\n")
