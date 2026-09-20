"""B's state machinery: hash-chained evidence journal, standing ledger,
one-use consumption registry. B's own layout; no OpenLine code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .canon import canonical_bytes


class Store:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.journal_path = state_dir / "journal.jsonl"
        self.standing_path = state_dir / "standing.json"
        self.consumed_path = state_dir / "consumed.json"
        if not self.journal_path.exists():
            self.journal_path.write_text("", encoding="utf-8")

    # -- journal ---------------------------------------------------------
    def _last_hash(self) -> str:
        prev = "GENESIS"
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                prev = json.loads(line)["record_hash"]
        return prev

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        seq = sum(
            1 for _ in self.journal_path.read_text(encoding="utf-8").splitlines() if _.strip()
        ) + 1
        entry = {"seq": seq, "prev_hash": self._last_hash(), **record}
        entry["record_hash"] = hashlib.sha256(canonical_bytes(entry)).hexdigest()
        with self.journal_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def verify_chain(self) -> tuple[bool, str]:
        prev = "GENESIS"
        seq = 0
        for line in self.journal_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            seq += 1
            if entry.get("seq") != seq or entry.get("prev_hash") != prev:
                return False, f"chain break at seq {seq}"
            record_hash = entry.pop("record_hash")
            if hashlib.sha256(canonical_bytes(entry)).hexdigest() != record_hash:
                return False, f"hash mismatch at seq {seq}"
            entry["record_hash"] = record_hash
            prev = record_hash
        return True, "OK"

    # -- standing ledger ---------------------------------------------------
    def _load_json(self, path: Path, default: Any) -> Any:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return default

    def standing_head(self, action_identity: str) -> dict[str, Any] | None:
        ledger = self._load_json(self.standing_path, {})
        entries = ledger.get(action_identity, [])
        return entries[-1] if entries else None

    def admit_standing(self, action_identity: str, entry: dict[str, Any]) -> None:
        ledger = self._load_json(self.standing_path, {})
        ledger.setdefault(action_identity, []).append(entry)
        self.standing_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")

    # -- one-use registry ----------------------------------------------------
    def is_consumed(self, code_hash: str) -> bool:
        return code_hash in self._load_json(self.consumed_path, [])

    def consume(self, code_hash: str) -> None:
        consumed = self._load_json(self.consumed_path, [])
        consumed.append(code_hash)
        self.consumed_path.write_text(json.dumps(consumed, indent=2) + "\n")
