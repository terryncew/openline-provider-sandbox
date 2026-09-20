"""Pre-contact qualification of the repair vectors (Q1/Q2/Q3).

Disposition-only evaluation: steps 1-4 of the profile's fixed check order.
No state mutation, no effect committed for vectors.

Preregistered:
  V1-valid-revocation    -> REVOCATION_ADMITTABLE   (Q1)
  V2-invalid-pairing     -> REFUSE DECISION_NOT_AUTHORITATIVE (Q2)
  V3-neighbor-commit     -> GRANT_PATH              (Q3)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from b_cleanroom.receiver import Config, Receiver  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

PINNED_ISSUER_KEY = "9647b78a4f5423024f83de0c12fbe9ec5275e8d23a2fda83014d43cdf89fd176"
PINNED_POLICY_HASH = "dd73adab77159b7a3bafbd9c0deb1953d798f071143011464fb3e8bce0e40d01"

EXPECTED = {
    "V1-valid-revocation": ("REVOCATION_ADMITTABLE", "PAIRING_TERMINAL_REVOCATION"),
    "V2-invalid-pairing": ("REFUSE", "DECISION_NOT_AUTHORITATIVE"),
    "V3-neighbor-commit": ("GRANT_PATH", "PAIRING_GRANT"),
}


def main() -> int:
    vectors_dir = Path(__file__).resolve().parents[1] / "vectors"
    receiver = Receiver(
        Config(
            pinned_issuer_key=PINNED_ISSUER_KEY,
            pinned_policy_hash=PINNED_POLICY_HASH,
            signing_key=Ed25519PrivateKey.generate(),
        ),
        state_dir=Path("/tmp/interop-002-b-vecstate"),
    )
    failures = []
    for tag, (want_disp, want_reason) in EXPECTED.items():
        text = (vectors_dir / f"{tag}-receipt.json").read_text(encoding="utf-8")
        got = receiver.evaluate_prefix(text)
        status = (
            "PASS"
            if (got["disposition"], got["reason"]) == (want_disp, want_reason)
            else "FAIL"
        )
        print(f"{tag}: {status} got={got['disposition']}/{got['reason']}")
        # Q4 support: B's independent canonical recomputation must match the
        # recorded payload_hash exactly.
        receipt = json.loads(text)
        from b_cleanroom.canon import canonical_bytes
        import hashlib

        body = {k: v for k, v in receipt.items() if k not in ("payload_hash", "signature")}
        recomputed = hashlib.sha256(canonical_bytes(body)).hexdigest()
        canon_ok = recomputed == receipt["payload_hash"]
        print(f"  canonical recompute match: {canon_ok}")
        if status != "PASS" or not canon_ok:
            failures.append(tag)
    if failures:
        print(f"VECTOR QUALIFICATION FAILED: {failures}")
        return 1
    print("VECTOR QUALIFICATION: 3/3 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
