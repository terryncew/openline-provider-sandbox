"""Live case runner for INDEPENDENT-INTEROP-002.

Usage:
  run_case.py --case <tag> --receipt <receipt.json> [--action <action.json>]
              --state-dir <dir> --key-file <b_signing.key> --out <result.json>

Runs the full profile section 7 pipeline for one presented receipt and
writes the observed disposition + effect evidence. Exits nonzero if the
provider path fails (fail-loud).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from b_cleanroom.receiver import Config, Receiver  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

PINNED_ISSUER_KEY = "9647b78a4f5423024f83de0c12fbe9ec5275e8d23a2fda83014d43cdf89fd176"
PINNED_POLICY_HASH = "dd73adab77159b7a3bafbd9c0deb1953d798f071143011464fb3e8bce0e40d01"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--action", default=None)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    key_path = Path(args.key_file)
    if key_path.exists():
        signing_key = Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(key_path.read_text().strip())
        )
    else:
        signing_key = Ed25519PrivateKey.generate()
        key_path.write_text(signing_key.private_bytes_raw().hex())

    receiver = Receiver(
        Config(
            pinned_issuer_key=PINNED_ISSUER_KEY,
            pinned_policy_hash=PINNED_POLICY_HASH,
            signing_key=signing_key,
        ),
        state_dir=Path(args.state_dir),
    )
    receipt_text = Path(args.receipt).read_text(encoding="utf-8")
    presented = None
    if args.action:
        presented = json.loads(Path(args.action).read_text(encoding="utf-8"))

    result = receiver.decide(receipt_text, presented)
    serializable = {
        "decision": result["decision"],
        "reason": result["reason"],
        "effect": result.get("effect"),
        "b_signing_pubkey": receiver.config.signing_pubkey_hex,
    }
    if result.get("trace_receipt") is not None:
        out_trace = Path(args.out).with_name(Path(args.out).stem + "-trace-receipt.json")
        out_trace.write_text(
            json.dumps(result["trace_receipt"], indent=2, sort_keys=True) + "\n"
        )
        serializable["trace_receipt_file"] = out_trace.name
        serializable["trace_payload_hash"] = result["trace_receipt"]["payload_hash"]
    Path(args.out).write_text(json.dumps(serializable, indent=2, sort_keys=True) + "\n")
    print(json.dumps(serializable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
