# Repair conformance vectors — INDEPENDENT-INTEROP-002

Frozen with the contract repair, before B was built. Admitted by the 002
preregistration as conformance material (not scientific contact).

- V1-valid-revocation: genuine A-issued (verdict=REJECTED, decision=DENY),
  commit_authorization null. payload_hash 5b8cbfbb06cd99ed7bb368c69bb0e7846871feef512846c82ac50f34ed8155bd
- V2-invalid-pairing: SYNTHETIC negative vector. V1's body re-signed by the
  experiment apparatus with verdict flipped to VERIFIED (decision stays DENY),
  valid signature under the pinned issuer key. The real gate never emits this
  pairing; it exists so the pairing check (not the signature check) is what
  refuses it.
- V3-neighbor-commit: genuine A-issued (verdict=VERIFIED, decision=COMMIT).
  payload_hash 7932a29cdee3647a06a1afb173e63eef0ddf9dfebbf0fe4d12ddad64564ccb13

All three carry valid signatures under the pinned issuer key
9647b78a4f5423024f83de0c12fbe9ec5275e8d23a2fda83014d43cdf89fd176.
Vector evaluation is disposition-only: no effect is committed for vectors.
Preregistered dispositions: V1 -> REVOCATION_ADMITTABLE, V2 -> REFUSE
DECISION_NOT_AUTHORITATIVE, V3 -> GRANT_PATH (pairing prefix only;
expiry/standing/replay are live-state checks, not asserted for vectors).
