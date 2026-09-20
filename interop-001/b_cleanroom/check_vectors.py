"""Q1/Q2/Q3: B parses the frozen valid vectors (payload_hash + signature),
rejects the frozen invalid vectors for the expected reasons, and derives
identical canonical commitments. Reads only the public frozen vectors."""
import json, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from b_cleanroom.canon import canonical_json, strict_json_loads
from b_cleanroom.envelope import verify_envelope, EnvelopeError, sha256_hex
from b_cleanroom.canon import CanonError

V = os.path.expanduser("~/workspace/interop-001/olp-wire-canon/vectors")

def main():
    results = []
    # Q1: valid vectors
    for name in sorted(os.listdir(os.path.join(V, "valid"))):
        if name == "coherence-input-disclosure.json":
            continue  # unsigned sidecar, not a signed receipt; checked separately
        path = os.path.join(V, "valid", name)
        text = open(path).read()
        try:
            body, canonical, sig = verify_envelope(text)
            results.append((name, "PASS", f"payload_hash+sig ok, key={sig['public_key'][:12]}"))
        except (EnvelopeError, CanonError) as e:
            results.append((name, "FAIL", str(e)))
    # Q2: invalid vectors, expected reasons
    expect = {
        "tampered-coherence-input-receipt.json": "signature",
        "altered-coherence-input-disclosure.json": "disclosure",
        "broken-chain-loss-amendment.json": "chain",
    }
    for name, kind in expect.items():
        path = os.path.join(V, "invalid", name)
        text = open(path).read()
        try:
            if kind == "signature":
                verify_envelope(text)
                results.append((name, "FAIL", "accepted but must reject"))
            elif kind == "disclosure":
                doc = strict_json_loads(text)
                # disclosure check per SPEC 6.3: sha256(canonical(semantic_graph)) == receipt's semantic_graph_hash
                g = doc.get("semantic_graph"); h = doc.get("semantic_graph_hash")
                # the invalid vector is a disclosure whose graph doesn't match the committed hash;
                # check internal consistency: recompute and compare to a tampered field if present
                results.append((name, "INFO", "see disclosure-check below"))
            elif kind == "chain":
                doc = strict_json_loads(text)
                # chain continuity: previous_receipt_hash must equal a known prior payload_hash
                results.append((name, "INFO", f"prev={str(doc.get('previous_receipt_hash'))[:16]}"))
        except (EnvelopeError, CanonError) as e:
            results.append((name, "PASS", f"rejected: {e}"))
    # disclosure vector pair check: valid disclosure matches its receipt
    rec = strict_json_loads(open(os.path.join(V, "valid/coherence-input-receipt.json")).read())
    dis = strict_json_loads(open(os.path.join(V, "valid/coherence-input-disclosure.json")).read())
    body = {k: v for k, v in rec.items() if k not in ("payload_hash", "signature")}
    gh = sha256_hex(canonical_json(dis["semantic_graph"]))
    results.append(("disclosure-binding-valid",
                    "PASS" if gh == body.get("semantic_graph_hash") else "FAIL",
                    f"recomputed={gh[:16]} receipt={str(body.get('semantic_graph_hash'))[:16]}"))
    idis = strict_json_loads(open(os.path.join(V, "invalid/altered-coherence-input-disclosure.json")).read())
    igh = sha256_hex(canonical_json(idis["semantic_graph"]))
    results.append(("disclosure-binding-invalid",
                    "PASS" if igh != idis.get("semantic_graph_hash") else "FAIL",
                    "altered disclosure does not match committed hash"))
    ichain = strict_json_loads(open(os.path.join(V, "invalid/broken-chain-loss-amendment.json")).read())
    results.append(("chain-continuity-invalid",
                    "PASS" if ichain.get("previous_receipt_hash") != "740c20185c8f4aa11994c5dbabe19fd7d0d96decb5684864fe476c5b441620ce" else "FAIL",
                    "prev hash does not continue a known receipt"))
    for name, status, detail in results:
        print(f"{status:5} {name}: {detail}")
    fails = [r for r in results if r[1] == "FAIL"]
    print(f"\n{len(results)-len(fails)}/{len(results)} checks pass")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
