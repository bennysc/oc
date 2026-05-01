#!/usr/bin/env python3
"""Structural validation for the packwiz manifest.

Run from the repo root:

    python scripts/validate-pack.py

Exits 0 on success, 1 on the first failure with a human-readable error.
This is complementary to ``packwiz refresh`` -- packwiz proves hashes are
internally consistent; this script proves the surrounding metadata is shaped
correctly (required fields, valid sides, no orphans, no jar collisions, etc.).
"""

from __future__ import annotations

import hashlib
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VALID_SIDES = {"client", "server", "both"}
VALID_HASH_FORMATS = {"sha1", "sha256", "sha512", "md5", "murmur2"}
VALID_DOWNLOAD_MODES = {"url", "metadata:curseforge", "metadata:modrinth"}

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pack_toml() -> dict:
    pack_path = REPO / "pack.toml"
    if not pack_path.exists():
        fail("pack.toml is missing")
        return {}
    pack = load_toml(pack_path)

    for key in ("name", "author", "version", "pack-format"):
        if not pack.get(key):
            fail(f"pack.toml: missing required top-level key {key!r}")

    pf = pack.get("pack-format", "")
    if not pf.startswith("packwiz:"):
        fail(f"pack.toml: pack-format {pf!r} does not start with 'packwiz:'")

    index = pack.get("index", {})
    for key in ("file", "hash-format", "hash"):
        if not index.get(key):
            fail(f"pack.toml: missing [index].{key}")
    if index.get("hash-format") not in VALID_HASH_FORMATS:
        fail(f"pack.toml: [index].hash-format {index.get('hash-format')!r} is not a known format")

    idx_hash = index.get("hash", "")
    if index.get("hash-format") == "sha256" and len(idx_hash) != 64:
        fail(f"pack.toml: [index].hash is {len(idx_hash)} chars, expected 64 for sha256")

    versions = pack.get("versions", {})
    if not versions.get("minecraft"):
        fail("pack.toml: missing [versions].minecraft")
    if not versions.get("neoforge"):
        fail("pack.toml: missing [versions].neoforge (this pack is NeoForge-only)")

    index_file = REPO / index.get("file", "index.toml")
    if index_file.exists() and index.get("hash-format") == "sha256":
        actual = sha256_of(index_file)
        if actual != idx_hash:
            fail(
                f"pack.toml: [index].hash {idx_hash!r} does not match sha256({index_file.name}) "
                f"{actual!r} -- run 'packwiz refresh'"
            )
    return pack


def check_index_toml() -> dict:
    index_path = REPO / "index.toml"
    if not index_path.exists():
        fail("index.toml is missing")
        return {}
    index = load_toml(index_path)
    hash_format = index.get("hash-format", "sha256")
    if hash_format not in VALID_HASH_FORMATS:
        fail(f"index.toml: hash-format {hash_format!r} is not known")

    seen: set[str] = set()
    for entry in index.get("files", []):
        rel = entry.get("file")
        if not rel:
            fail("index.toml: [[files]] entry missing 'file'")
            continue
        if rel in seen:
            fail(f"index.toml: duplicate entry for {rel}")
        seen.add(rel)

        target = REPO / rel
        if not target.exists():
            fail(f"index.toml: references missing file {rel}")
            continue
        if hash_format == "sha256":
            actual = sha256_of(target)
            expected = entry.get("hash", "")
            if actual != expected:
                fail(
                    f"index.toml: hash for {rel} is {expected!r}, expected {actual!r} "
                    f"-- run 'packwiz refresh'"
                )
    return index


def check_mod_metafiles(index: dict) -> None:
    mods_dir = REPO / "mods"
    if not mods_dir.exists():
        return

    indexed = {e["file"] for e in index.get("files", []) if "file" in e}
    on_disk = sorted(p for p in mods_dir.rglob("*.pw.toml"))

    seen_filenames: dict[str, str] = {}
    for meta_path in on_disk:
        rel = meta_path.relative_to(REPO).as_posix()
        if rel not in indexed:
            fail(f"orphan metafile: {rel} exists on disk but is not in index.toml")

        meta = load_toml(meta_path)
        for key in ("name", "filename", "side"):
            if not meta.get(key):
                fail(f"{rel}: missing required key {key!r}")

        side = meta.get("side")
        if side and side not in VALID_SIDES:
            fail(f"{rel}: side {side!r} is not one of {sorted(VALID_SIDES)}")

        filename = meta.get("filename")
        if filename:
            prior = seen_filenames.get(filename)
            if prior:
                fail(f"{rel}: jar filename {filename!r} also declared by {prior}")
            else:
                seen_filenames[filename] = rel

        download = meta.get("download", {})
        if not download.get("hash"):
            fail(f"{rel}: [download].hash is empty")
        if download.get("hash-format") not in VALID_HASH_FORMATS:
            fail(f"{rel}: [download].hash-format {download.get('hash-format')!r} is not known")
        mode = download.get("mode", "url")
        if mode not in VALID_DOWNLOAD_MODES:
            fail(f"{rel}: [download].mode {mode!r} is not one of {sorted(VALID_DOWNLOAD_MODES)}")
        if mode == "url" and not download.get("url"):
            fail(f"{rel}: [download].mode='url' but no [download].url is set")


def main() -> int:
    pack = check_pack_toml()
    index = check_index_toml()
    check_mod_metafiles(index)

    if errors:
        print(f"validate-pack: {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    n_files = len(index.get("files", []))
    mc = pack.get("versions", {}).get("minecraft", "?")
    nf = pack.get("versions", {}).get("neoforge", "?")
    print(f"validate-pack: ok -- {n_files} indexed files, MC {mc} / NeoForge {nf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
