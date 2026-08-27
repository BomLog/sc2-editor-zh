#!/usr/bin/env python3
"""Build the editor fallback-name table from official CASC dependencies."""

from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
WORK = HERE.parent
GAME = Path(r"D:\StarCraft II")
DEFAULT_PRODUCT = (
    WORK / "localized_output" / "Editor" / "LocalizedData" / "ObjectStringsProduct.txt"
)
DEFAULT_GAME_PRODUCT = DEFAULT_PRODUCT.with_name("GameStringsProduct.txt")
DEFAULT_OUTPUT = HERE / "l10n" / "OfficialDependencyNames.tsv"
DEFAULT_REPORT = HERE / "l10n" / "OfficialDependencyNames.report.json"
DEFAULT_ASSETS = HERE / "l10n" / "Editor"
DEFAULT_TRIGGER_AUDIT = WORK / "official_trigger_string_audit.json"
KINDS = ("Actor", "Behavior", "Abil", "Effect", "Validator", "Model")
KIND_PRIORITY = {kind: index for index, kind in enumerate(KINDS)}
KIND_LABELS = {
    "Actor": "演算体",
    "Behavior": "行为",
    "Abil": "技能",
    "Effect": "效果",
    "Validator": "验证器",
    "Model": "模型",
}
CJK = re.compile(r"[\u3400-\u9fff]")
ALLOWED_VISIBLE_ASCII_FIELD = re.compile(
    r"^(?:\*|[A-Z]|[23]D|PU72516J|SSAO|Id|ID|AI|CUE|CCPA|DNA|"
    r"PCM (?:8|16|24|32|FLOAT)|WCS 20\d\d|20\d\d WCS|"
    r"~Case\.|~UpgradeWeapon\.)$"
)

sys.path.insert(0, str(WORK))
sys.path.insert(0, str(WORK / "dds_viewer"))
from casc_reader import Casc  # noqa: E402
from l10n_engine import Engine  # noqa: E402


def local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def catalog_kind(tag: str) -> str | None:
    body = local_tag(tag)
    if not body.startswith("C"):
        return None
    body = body[1:]
    if body.startswith("ActorSupport"):
        return None
    for kind in KINDS:
        if body.startswith(kind):
            return kind
    return None


def direct_name(element: ET.Element) -> str | None:
    for child in element:
        if local_tag(child.tag) == "Name":
            return child.get("value", "")
    return None


def dependency_root(path: str) -> str | None:
    parts = path.lower().replace("/", "\\").split("\\")
    if not parts or parts[0] not in {"mods", "campaigns"}:
        return None
    for index, part in enumerate(parts[1:], start=1):
        if part.endswith((".sc2mod", ".sc2campaign")):
            return "\\".join(parts[: index + 1])
    return None


def decode(blob: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return blob.decode(encoding)
        except UnicodeDecodeError:
            continue
    return blob.decode("utf-8", errors="replace")


def read_entries(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig", errors="strict").splitlines():
        if "=" not in line or line.lstrip().startswith("//"):
            continue
        key, value = line.split("=", 1)
        entries[key] = value
    return entries


def write_entries(path: Path, entries: dict[str, str]) -> None:
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in entries.items()) + "\n",
        encoding="utf-8",
        newline="",
    )


def audit_editor_fields(path: Path) -> dict[str, object]:
    entries = 0
    allowed = 0
    untranslated: list[dict[str, object]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig", errors="strict").splitlines(), start=1
    ):
        if "=" not in line or line.lstrip().startswith("//"):
            continue
        key, value = line.split("=", 1)
        visible = value.split(" //", 1)[0].rstrip()
        entries += 1
        if CJK.search(visible):
            continue
        if ALLOWED_VISIBLE_ASCII_FIELD.fullmatch(visible):
            allowed += 1
            continue
        untranslated.append({"line": line_number, "key": key, "value": visible})
    return {
        "entries": entries,
        "allowedTechnicalValues": allowed,
        "unexpectedVisibleValuesWithoutChinese": len(untranslated),
        "unexpectedRows": untranslated,
    }


def candidate_score(kind: str, object_id: str, value: str) -> tuple[int, ...]:
    contains_id = object_id.lower() in value.lower()
    ascii_letters = len(re.findall(r"[A-Za-z]", value))
    return (
        int(not contains_id),
        -ascii_letters,
        len(CJK.findall(value)),
        -KIND_PRIORITY[kind],
        -len(value),
    )


def sync_assets(asset_root: Path, work: Path) -> dict[str, int]:
    sources = {
        "EditorCatalogStrings.txt": work / "localized_output" / "EditorCatalogStrings.txt",
        "EditorCategoryStrings.txt": work / "localized_output" / "EditorCategoryStrings.txt",
        "EditorStrings.txt": work / "localized_output" / "EditorStrings.txt",
        "LocalizedData/GameStrings.txt": work / "localized_output" / "GameStrings.txt",
        "LocalizedData/ObjectStrings.txt": work / "localized_output" / "ObjectStrings.txt",
        "LocalizedData/TriggerStrings.txt": work / "localized_output" / "TriggerStrings.txt",
        "LocalizedData/GameStringsProduct.txt": (
            work / "localized_output" / "Editor" / "LocalizedData" / "GameStringsProduct.txt"
        ),
        "LocalizedData/ObjectStringsProduct.txt": (
            work / "localized_output" / "Editor" / "LocalizedData" / "ObjectStringsProduct.txt"
        ),
    }
    sizes: dict[str, int] = {}
    for relative, source in sources.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        target = asset_root / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        sizes[relative] = target.stat().st_size
    return sizes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, default=GAME)
    parser.add_argument("--product", type=Path, default=DEFAULT_PRODUCT)
    parser.add_argument("--game-product", type=Path, default=DEFAULT_GAME_PRODUCT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--trigger-audit", type=Path, default=DEFAULT_TRIGGER_AUDIT)
    args = parser.parse_args()

    casc = Casc()
    casc.open(str(args.game))
    latest: dict[tuple[str, str, str], dict[str, str | None]] = {}
    classes: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    parse_failures: list[str] = []
    xml_files = 0
    declarations = 0
    try:
        for path in casc.list_paths((".xml",)):
            low = path.lower().replace("/", "\\")
            root = dependency_root(low)
            if not root or "gamedata" not in low:
                continue
            try:
                document = ET.fromstring(decode(casc.read(path)))
            except Exception:
                parse_failures.append(path)
                continue
            xml_files += 1
            for element in document:
                kind = catalog_kind(element.tag)
                object_id = element.get("id")
                if not kind or not object_id:
                    continue
                class_name = local_tag(element.tag)
                declarations += 1
                classes[(kind, object_id)].add(class_name)
                latest[(root, kind, object_id)] = {
                    "dependency": root,
                    "kind": kind,
                    "id": object_id,
                    "class": class_name,
                    "name": direct_name(element),
                    "path": path,
                }
    finally:
        casc.close()

    missing = [row for row in latest.values() if not row["name"]]
    product = read_entries(args.product)
    product_baseline_path = args.product.with_name(
        args.product.name + ".bak.before_official_dependencies"
    )
    product_baseline = (
        read_entries(product_baseline_path)
        if product_baseline_path.exists()
        else dict(product)
    )
    translator = Engine()
    additions: dict[str, dict[str, str | bool]] = {}
    candidates: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    invalid_rows: list[dict[str, str]] = []
    for source in missing:
        row = {key: str(value or "") for key, value in source.items()}
        kind = row["kind"]
        object_id = row["id"]
        string_key = f"{kind}/Name/{object_id}"
        if any(char in object_id for char in "\t\r\n"):
            invalid_rows.append({**row, "reason": "unsafeObjectId"})
            continue
        value = product.get(string_key, "")
        if not CJK.search(value):
            value, complete = translator.translate(object_id)
            if not CJK.search(value):
                value = f"{KIND_LABELS[kind]} - {object_id}"
                complete = False
            product[string_key] = value
            additions[string_key] = {
                "value": value,
                "completeTokenTranslation": bool(complete),
            }
        if any(char in value for char in "\t\r\n"):
            invalid_rows.append({**row, "reason": "unsafeTranslation"})
            continue
        candidates[object_id].append(
            {
                "dependency": row["dependency"],
                "kind": kind,
                "class": row["class"],
                "key": string_key,
                "value": product[string_key],
            }
        )

    if additions:
        backup = product_baseline_path
        if not backup.exists():
            shutil.copy2(args.product, backup)
        write_entries(args.product, product)
    shutil.copy2(args.product, args.game_product)

    selected_keys = {
        row["key"] for rows in candidates.values() for row in rows
    }
    generated_keys = {
        key for key in selected_keys if not CJK.search(product_baseline.get(key, ""))
    }
    generated_complete = 0
    for key in generated_keys:
        object_id = key.split("/", 2)[-1]
        _translated, complete = translator.translate(object_id)
        generated_complete += int(complete)
    synced_tables: dict[str, int] = {}
    for table_path in (
        WORK / "localized_output" / "GameStrings.txt",
        WORK / "localized_output" / "ObjectStrings.txt",
    ):
        table = read_entries(table_path)
        changed = 0
        for key in selected_keys:
            if table.get(key) != product[key]:
                table[key] = product[key]
                changed += 1
        if changed:
            backup = table_path.with_name(
                table_path.name + ".bak.before_official_dependencies"
            )
            if not backup.exists():
                shutil.copy2(table_path, backup)
            write_entries(table_path, table)
        synced_tables[str(table_path)] = changed

    resolved: dict[str, str] = {}
    conflicts: list[dict[str, object]] = []
    for object_id, rows in candidates.items():
        chosen = max(
            rows,
            key=lambda row: candidate_score(row["kind"], object_id, row["value"]),
        )
        resolved[object_id] = chosen["value"]
        values = {row["value"] for row in rows}
        if len(values) > 1:
            conflicts.append(
                {
                    "id": object_id,
                    "chosenKind": chosen["kind"],
                    "chosenKey": chosen["key"],
                    "chosenValue": chosen["value"],
                    "candidates": rows,
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# SC2 official CASC dependency fallback names; UTF-8\n")
        for object_id in sorted(resolved, key=lambda value: (value.lower(), value)):
            handle.write(f"{object_id}\t{resolved[object_id]}\n")

    field_audit = audit_editor_fields(
        WORK / "localized_output" / "EditorCatalogStrings.txt"
    )
    if field_audit["unexpectedVisibleValuesWithoutChinese"]:
        rows = field_audit["unexpectedRows"]
        raise ValueError(f"untranslated visible editor fields: {rows[:10]}")
    asset_sizes = sync_assets(args.assets, WORK)
    trigger_summary: dict[str, object] = {}
    if args.trigger_audit.exists():
        audit = json.loads(args.trigger_audit.read_text(encoding="utf-8"))
        for key in ("allOfficialKeys", "targetKeys", "missingKeys", "targetValuesWithoutChinese"):
            if key in audit:
                trigger_summary[key] = audit[key]

    by_dependency = collections.Counter(row["dependency"] for row in missing)
    bindings_by_kind = collections.Counter(row["kind"] for rows in candidates.values() for row in rows)
    class_conflicts = sum(1 for values in classes.values() if len(values) > 1)
    report = {
        "source": "official CASC mods and campaigns only",
        "game": str(args.game),
        "xmlFiles": xml_files,
        "declarations": declarations,
        "dependencyObjects": len(latest),
        "missingNameBindings": sum(len(rows) for rows in candidates.values()),
        "uniqueRuntimeIds": len(resolved),
        "bindingsByKind": dict(bindings_by_kind),
        "bindingsByDependency": dict(sorted(by_dependency.items())),
        "duplicateRuntimeIds": sum(1 for rows in candidates.values() if len(rows) > 1),
        "duplicateIdsWithDifferentTranslations": len(conflicts),
        "globalClassConflicts": class_conflicts,
        "productStringsAdded": len(generated_keys),
        "productStringsAddedThisRun": len(additions),
        "productStringsFullyTranslated": generated_complete,
        "sourceStringsSynced": synced_tables,
        "parseFailures": len(parse_failures),
        "invalidRows": len(invalid_rows),
        "triggerStrings": trigger_summary,
        "output": str(args.output),
        "outputBytes": args.output.stat().st_size,
        "projectAssets": asset_sizes,
        "editorFieldAudit": field_audit,
        "differentTranslationRows": conflicts,
        "parseFailurePaths": parse_failures,
        "invalidRowDetails": invalid_rows,
    }
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = dict(report)
    summary.pop("differentTranslationRows")
    summary.pop("parseFailurePaths")
    summary.pop("invalidRowDetails")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
