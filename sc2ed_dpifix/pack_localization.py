#!/usr/bin/env python3
"""Build a deduplicated LZMA bundle for the localization release assets."""

import hashlib
import json
import lzma
import os
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
L10N = HERE / "l10n"
OUTPUT = L10N / "bundle"
RESOURCE_PATHS = (
    "SC2EditorDependencyL10n.dll",
    "OfficialDependencyNames.tsv",
    "EditorCatalogStrings.txt",
    "EditorCategoryStrings.txt",
    "EditorStrings.txt",
    "LocalizedData/GameStrings.txt",
    "LocalizedData/ObjectStrings.txt",
    "LocalizedData/TriggerStrings.txt",
    "LocalizedData/GameStringsProduct.txt",
    "LocalizedData/ObjectStringsProduct.txt",
)


def source_path(relative):
    if relative in RESOURCE_PATHS[:2]:
        return L10N / relative
    return L10N / "Editor" / Path(relative)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compress(source, target):
    with source.open("rb") as unpacked, lzma.open(target, "wb", preset=9) as packed:
        shutil.copyfileobj(unpacked, packed, length=1024 * 1024)


def main():
    version = (HERE / "VERSION").read_text(encoding="ascii").strip()
    temporary = OUTPUT.with_name(OUTPUT.name + ".tmp")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    records = []
    raw_bytes = 0
    try:
        for relative in RESOURCE_PATHS:
            source = source_path(relative)
            if not source.is_file():
                raise SystemExit(f"missing localization resource: {source}")
            digest = sha256(source)
            size = source.stat().st_size
            blob = f"{digest}.xz"
            packed = temporary / blob
            if not packed.exists():
                compress(source, packed)
            records.append(
                {
                    "path": relative,
                    "size": size,
                    "sha256": digest,
                    "blob": blob,
                }
            )
            raw_bytes += size
        hook = source_path(RESOURCE_PATHS[0]).read_bytes()
        marker = f"SC2ED_DPIFIX_L10N_HOOK_VERSION={version}".encode("ascii")
        if not hook.startswith(b"MZ") or marker not in hook:
            raise SystemExit("hook DLL version does not match VERSION")
        manifest = {"format": 1, "version": version, "resources": records}
        with (temporary / "manifest.json").open(
            "w", encoding="utf-8", newline="\n"
        ) as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        os.replace(temporary, OUTPUT)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    packed_bytes = sum(path.stat().st_size for path in OUTPUT.iterdir())
    print(
        json.dumps(
            {
                "version": version,
                "resources": len(records),
                "uniqueBlobs": len({record["blob"] for record in records}),
                "rawBytes": raw_bytes,
                "packedBytes": packed_bytes,
                "ratio": round(packed_bytes / raw_bytes, 4),
                "output": str(OUTPUT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
