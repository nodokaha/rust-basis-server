# Official Basis conformance checks

This repository does not treat hand-written Rust expectations as proof of Basis compatibility.
The `upstream-conformance` workflow checks a pinned snapshot of the official
`BasisVR/Basis` repository and uses an assertion from its own C# test suite as the
wire-format oracle.

## What is checked

1. The verifier reads `AdminRequest.cs` from the pinned official source and checks the
   numeric values of the five protocol-57 admin modes.
2. It reads the expected byte array from
   `BasisServerTests/Security/SecurityListAndLockManagerTests.cs` in the official
   `SendLockStateToPeer_WritesTheAppendOnlyWireLayout` test.
3. It compares that extracted byte array with the committed fixture
   `crates/basis-transport/tests/fixtures/upstream_global_lock_state.hex`.
4. CI runs the official C# test itself, then runs the Rust test that serializes `GlobalLocks`
   and compares the result byte-for-byte with the same fixture.

The official source revision is pinned in
`scripts/verify_upstream_basis_contract.py`. This makes CI reproducible and ensures an
upstream change cannot silently rewrite the expected behavior.

## Updating the upstream reference

When intentionally following a newer official Basis revision:

1. Review the upstream changes to `AdminRequest.cs` and the official lock-state test.
2. Update `UPSTREAM_SHA` in the verifier and the checkout ref in
   `.github/workflows/upstream-conformance.yml` to the same commit.
3. Run the verifier with `--write` against that checkout to regenerate the fixture.
4. Run the official C# test and Rust comparison test. Review the fixture diff; do not accept it
   automatically if the wire contract changed unexpectedly.

This is a focused executable conformance check, not a claim that the entire Rust server has
feature parity with the official C# server. Additional protocol areas should be added only when
there is a corresponding authoritative upstream test or explicit protocol contract to compare.
