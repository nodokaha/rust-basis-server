# Official Basis conformance checks

This repository does not treat hand-written Rust expectations as proof of Basis compatibility.
CI checks a pinned snapshot of the official `BasisVR/Basis` repository and keeps the upstream
C# regression suite separate from direct Rust-vs-official contract comparisons.

## What is checked

1. CI checks out the official Basis source at the pinned commit
   `d8b718d4fb6a16e6f2339d4431ffd1212d97c69d`.
2. The verifier reads `AdminRequest.cs` and checks the numeric values of the five
   protocol-57 admin modes (101–105).
3. It reads the expected byte array from
   `BasisServerTests/Security/SecurityListAndLockManagerTests.cs` in the official
   `SendLockStateToPeer_WritesTheAppendOnlyWireLayout` test and compares it with the
   committed Rust-side fixture.
4. CI runs the **entire** `BasisServerTests.csproj` test suite in a Microsoft .NET 10 SDK
   container. It does not modify the pinned upstream source. The job constrains the visible
   processor count to four and injects xUnit runner configuration into the temporary checkout
   to disable collection-level parallelism. This addresses the hosted-runner failures observed
   at this revision (processor-budget over-allocation and a collection-mutation race) while
   retaining the full test set.
5. A separate job runs the Rust `basis-transport` test that serializes `GlobalLocks` and
   compares the result byte-for-byte with the fixture extracted from the official C# test.
   This job is independent, so a failure in the upstream C# suite cannot prevent the Rust
   fixture comparison from running.
6. The normal Rust CI independently runs `cargo test --workspace --locked` on Linux,
   Windows, and macOS, plus the server black-box compatibility suite on all three platforms.

The published `ghcr.io/basisvr/basis-server` image is a runtime image, not a .NET SDK image:
it is intended to run the server and does not contain the source test project or test runner.
Therefore it is not used to execute `BasisServerTests.csproj`. A runtime-image-based
interoperability test would be a separate layer and must exchange real protocol traffic with the
Rust server; merely starting the official container would not establish protocol parity.

The full upstream C# suite is a regression gate for the official implementation. It does not
by itself prove that every Rust feature has parity: direct Rust-vs-upstream comparisons are
added only where the official test provides an authoritative observable contract. The existing
black-box Rust server tests cover startup/configuration, permissions seeding, logging, HTTP
health/REST behavior, world lifecycle, UDP server-info, and connection rejects.

## Updating the upstream reference

When intentionally following a newer official Basis revision:

1. Review the upstream changes to `AdminRequest.cs` and the official lock-state test.
2. Update `UPSTREAM_SHA` in the verifier and the checkout ref in
   `.github/workflows/ci.yml` to the same commit.
3. Run the verifier with `--write` against that checkout to regenerate the fixture. Review the
   fixture diff; do not accept it automatically if the wire contract changed unexpectedly.
4. Run the complete official C# test project and Rust comparison test.

This suite is broader than a single protocol test, but it is not a claim that the entire Rust
server has feature parity with the official C# server. New Rust-vs-upstream checks should be
added by feature area whenever there is a corresponding authoritative upstream test or
explicit protocol contract to compare.
