#!/usr/bin/env python3
"""Verify Rust wire behavior against the pinned official Basis C# test contract.

The fixture is extracted from BasisServerTests, not re-authored here. The script
also reads the official AdminRequestMode enum so protocol IDs cannot silently drift.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

UPSTREAM_SHA = "d8b718d4fb6a16e6f2339d4431ffd1212d97c69d"
ADMIN_ENUM = Path("Basis Server/BasisNetworkCore/Serializable/Permissions/AdminRequest.cs")
RESTRICTION_ENUM = Path("Basis Server/BasisNetworkCore/Identity/BasisUserRestrictionMode.cs")
LOCK_TEST = Path("Basis Server/BasisServerTests/Security/SecurityListAndLockManagerTests.cs")
FIXTURE = Path("crates/basis-transport/tests/fixtures/upstream_global_lock_state.hex")

EXPECTED_MODES = {
    "GlobalToggleAvatarHosting": 101,
    "GlobalToggleVideoClips": 102,
    "SetGlobalImageMaxResolution": 103,
    "SetGlobalVideoClipMaxSize": 104,
    "SetGlobalVideoClipMaxPerPlayer": 105,
}


def read(root: Path, path: Path) -> str:
    return (root / path).read_text(encoding="utf-8-sig")


def enum_values(source: str, name: str) -> dict[str, int]:
    match = re.search(
        rf"\\benum\\s+{re.escape(name)}\\s*(?::\\s*\\w+)?\\s*\\{{(.*?)^\\s*\\}}",
        source,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError(f"official enum {name} not found")
    result: dict[str, int] = {}
    next_value = 0
    for raw_line in match.group(1).splitlines():
        line = raw_line.split("//", 1)[0].strip().rstrip(",").strip()
        if not line:
            continue
        item = re.fullmatch(r"([A-Za-z_]\\w*)(?:\\s*=\\s*(\\d+))?", line)
        if not item:
            raise ValueError(f"cannot parse {name} enum line: {raw_line!r}")
        key, explicit = item.groups()
        value = int(explicit) if explicit is not None else next_value
        result[key] = value
        next_value = value + 1
    return result


def official_lock_state_bytes(root: Path) -> tuple[dict[str, int], list[int]]:
    admin = enum_values(read(root, ADMIN_ENUM), "AdminRequestMode")
    restriction = enum_values(read(root, RESTRICTION_ENUM), "BasisUserRestrictionMode")
    for name, expected in EXPECTED_MODES.items():
        actual = admin.get(name)
        if actual != expected:
            raise ValueError(f"{name}: official enum is {actual}, expected {expected}")

    source = read(root, LOCK_TEST)
    start = source.find("SendLockStateToPeer_WritesTheAppendOnlyWireLayout")
    if start < 0:
        raise ValueError("official append-only lock-state test not found")
    end = source.find("\\n    [Fact]", start)
    method = source[start:] if end < 0 else source[start:end]
    array = re.search(
        r"Assert\\.Equal\\(new byte\\[\\]\\s*\\{(.*?)\\},\\s*payload\\);",
        method,
        re.DOTALL,
    )
    if not array:
        raise ValueError("official lock-state expected byte array not found")

    tokens = [
        token.strip()
        for token in re.sub(r"//[^\\n]*", "", array.group(1)).replace("\\n", " ").split(",")
        if token.strip()
    ]
    values: list[int] = []
    for token in tokens:
        if token == "(byte)AdminRequestMode.GlobalGetLockState":
            values.append(admin["GlobalGetLockState"])
        elif token == "(byte)BasisUserRestrictionMode.AllowList":
            values.append(restriction["AllowList"])
        elif re.fullmatch(r"0[xX][0-9A-Fa-f]+", token):
            values.append(int(token, 16))
        elif token.isdecimal():
            values.append(int(token))
        else:
            raise ValueError(f"unsupported expression in official byte fixture: {token!r}")
    return admin, values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--write", action="store_true", help="replace the checked-in fixture")
    args = parser.parse_args()

    root = args.upstream_root.resolve()
    actual_sha = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual_sha != UPSTREAM_SHA:
        raise ValueError(
            f"Basis checkout is {actual_sha}, expected pinned upstream {UPSTREAM_SHA}; "
            "review the upstream change before updating the pin"
        )

    modes, values = official_lock_state_bytes(root)
    fixture = FIXTURE
    expected = " ".join(f"{value:02x}" for value in values) + "\\n"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    if args.write:
        fixture.write_text(expected, encoding="ascii")
        print(f"updated {fixture} from official Basis tests at {UPSTREAM_SHA}")
    else:
        if not fixture.exists():
            raise ValueError(f"missing fixture: {fixture}; run with --write")
        checked_in = " ".join(fixture.read_text(encoding="ascii").split()) + "\\n"
        if checked_in != expected:
            raise ValueError(
                "official Basis test contract changed; inspect upstream diff and update "
                "the fixture intentionally with --write"
            )
        print(
            f"official contract verified: {len(values)} bytes; "
            f"AdminRequestMode IDs 101-105; upstream {UPSTREAM_SHA}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"upstream conformance verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
