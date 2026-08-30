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
DEFAULT_ORIGINAL_OVERLAY = (
    WORK
    / "localized_output"
    / "编辑器翻译包2024.6.6"
    / "Editor"
    / "LocalizedData"
    / "ObjectStrings.txt"
)
DEFAULT_OUTPUT = HERE / "l10n" / "OfficialDependencyNames.tsv"
DEFAULT_RESOURCE_OUTPUT = HERE / "l10n" / "OfficialResourceNames.tsv"
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


def visible_value(value: str) -> str:
    """Return the displayed part before an optional English reference comment."""
    return value.split(" //", 1)[0].rstrip()


def resource_aliases(value: str) -> set[str]:
    """Return the spellings used by the model/resource tree for a basename.

    ModelData.xml uses both CamelCase object ids and asset paths.  The editor's
    resource tree presents the basename with spaces (and, for terrain objects,
    drops the ``TerrainObject`` prefix), so keep all of those forms in one
    canonical table.  The hook lowercases and collapses whitespace before
    looking up a key.
    """
    # Keep the source basename as-is as well as the human-readable spelling.
    # The resource tree has two call paths: ModelData-backed rows generally
    # pass a spaced display name, while a number of preview/selection rows
    # pass the catalog object id verbatim (for example
    # ``UnitSelectionLeft``).  The native hook canonicalizes only case and
    # whitespace, so dropping the original CamelCase token makes those rows
    # impossible to translate even when Model/Name already has Chinese text.
    basename = value.replace("/", "\\").rsplit("\\", 1)[-1]
    basename = re.sub(r"\.[^.\\]+$", "", basename)
    if not basename:
        return set()

    text = basename.replace("_", " ").replace("-", " ")
    # The editor uses both acronym spellings: ``ACDamage`` is common in
    # localized catalog rows, while other views split it as ``AC Damage``.
    # Preserve the intermediate pass before applying the acronym boundary
    # rule so both forms are available to the native hook.
    text_compact_acronyms = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text_compact_acronyms)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return set()
    aliases = {basename, text_compact_acronyms, text}
    lowered = text.lower()
    for prefix in ("terrain object ", "terrainobject ", "model "):
        if lowered.startswith(prefix):
            aliases.add(text[len(prefix) :])
    return {re.sub(r"\s+", " ", alias).strip() for alias in aliases if alias.strip()}


def resource_key(value: str) -> str:
    """Canonical key used by OfficialResourceNames.tsv and the native hook."""
    return " ".join(value.strip().lower().split())


def read_preferred_overlay(path: Path) -> dict[str, str]:
    """Read the original sparse package without letting appended English rows win.

    The 2024.6.6 package contains a few duplicate keys: some early rows are
    English placeholders and a later row is the hand-corrected Chinese value,
    while other sections have the reverse order.  For an overlay, the last
    visible Chinese value is the authoritative one; if no visible Chinese
    value exists, retain the last row for diagnostics but do not apply it.
    """
    values: dict[str, list[str]] = collections.defaultdict(list)
    for line in path.read_text(encoding="utf-8-sig", errors="strict").splitlines():
        if "=" not in line or line.lstrip().startswith("//"):
            continue
        key, value = line.split("=", 1)
        values[key].append(value)
    preferred: dict[str, str] = {}
    for key, rows in values.items():
        chinese = [row for row in rows if CJK.search(visible_value(row))]
        preferred[key] = chinese[-1] if chinese else rows[-1]
    return preferred


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
    parser.add_argument(
        "--original-overlay",
        type=Path,
        default=DEFAULT_ORIGINAL_OVERLAY,
        help="original sparse 2024.6.6 ObjectStrings overlay (Chinese rows win)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--resource-output", type=Path, default=DEFAULT_RESOURCE_OUTPUT
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--trigger-audit", type=Path, default=DEFAULT_TRIGGER_AUDIT)
    args = parser.parse_args()

    casc = Casc()
    casc.open(str(args.game))
    latest: dict[tuple[str, str, str], dict[str, str | None]] = {}
    classes: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    model_files: dict[str, set[str]] = collections.defaultdict(set)
    # ``CActorModel`` is cataloged as an Actor by the prefix-based kind
    # classifier, although its resource-tree label is backed by the same
    # model namespace as ``CModel``. Keep these IDs for the Actor/Name
    # fallback below (the PurifierGuideVisualQuad* rows are examples).
    resource_model_ids: set[str] = set()
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
                if class_name in {"CActorModel", "CModel"}:
                    resource_model_ids.add(object_id)
                if kind == "Model" or class_name == "CActorModel":
                    # The model tree can display the basename from ModelData.xml
                    # instead of the catalog id. Actor-backed models also point
                    # at a CModel through their ``Model`` child, so preserve
                    # those references as well; aliases are resolved after the
                    # Chinese Product overlay is applied below.
                    for child in element.iter():
                        child_tag = local_tag(child.tag)
                        if child_tag not in {
                            "Model",
                            "ModelFile",
                            "RequiredAnims",
                            "RequiredAnimsEx",
                        }:
                            continue
                        for attr in ("value", "FilePath", "File"):
                            file_value = child.get(attr)
                            if file_value:
                                model_files[object_id].add(file_value)
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
    overlay: dict[str, str] = {}
    overlay_applied = 0
    overlay_changed = 0
    overlay_missing = False
    if args.original_overlay.is_file():
        overlay = read_preferred_overlay(args.original_overlay)
        for key, value in overlay.items():
            if not CJK.search(visible_value(value)):
                continue
            overlay_applied += 1
            if product.get(key) != value:
                product[key] = value
                overlay_changed += 1
    else:
        overlay_missing = True
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

    if additions or overlay_changed:
        backup = product_baseline_path
        if not backup.exists():
            shutil.copy2(args.product, backup)
        write_entries(args.product, product)
    shutil.copy2(args.product, args.game_product)

    selected_keys = {
        row["key"] for rows in candidates.values() for row in rows
    }
    sync_keys = selected_keys | {
        key
        for key, value in overlay.items()
        if CJK.search(visible_value(value))
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
        for key in sync_keys:
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

    # Resource/model tree aliases are not catalog ids: the tree commonly
    # renders a spaced basename from ModelData.xml (for example
    # ``Space Platform Destructible Medium Doodad``). Keep a separate table so
    # the native resource hook can translate that path without changing the
    # editor's source files.
    resource_candidates: dict[str, list[tuple[int, int, str]]] = collections.defaultdict(list)

    def add_resource_alias(alias: str, value: str, priority: int) -> None:
        if not alias or "##" in alias or not CJK.search(visible_value(value)):
            return
        generated = int(value.startswith(("模型 - ", "妯″瀷 - ")))
        resource_candidates[resource_key(alias)].append((priority, -generated, value))

    def add_model_resource(
        object_id: str, value: str, id_priority: int, file_priority: int
    ) -> None:
        if not CJK.search(visible_value(value)):
            return
        for alias in resource_aliases(object_id):
            add_resource_alias(alias, value, id_priority)
        for file_value in model_files.get(object_id, ()):
            for alias in resource_aliases(file_value):
                add_resource_alias(alias, value, file_priority)

    # Most model declarations use Model/Name, but the editor's actor-backed
    # preview models (notably the Purifier guide visuals) only have an
    # Actor/Name translation.  Restrict this fallback to IDs that are actually
    # declared as model/resource objects so actor catalog names do not flood
    # the resource table or win unrelated collisions.
    model_ids = set(model_files) | resource_model_ids
    for key, value in product.items():
        if key.startswith("Model/Name/"):
            add_model_resource(key[len("Model/Name/") :], value, 40, 30)
    for object_id in sorted(model_ids):
        if not CJK.search(visible_value(product.get(f"Model/Name/{object_id}", ""))):
            add_model_resource(
                object_id,
                product.get(f"Actor/Name/{object_id}", ""),
                35,
                25,
            )

    resource_resolved = {
        alias: max(rows, key=lambda row: (row[0], row[1], -len(row[2]), row[2]))[2]
        for alias, rows in resource_candidates.items()
    }
    args.resource_output.parent.mkdir(parents=True, exist_ok=True)
    with args.resource_output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# SC2 model/resource tree basename aliases; UTF-8\n")
        for alias in sorted(resource_resolved):
            handle.write(f"{alias}\t{resource_resolved[alias]}\n")

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
        "resourceAliases": len(resource_resolved),
        "resourceAliasConflicts": sum(
            1 for rows in resource_candidates.values() if len({row[2] for row in rows}) > 1
        ),
        "bindingsByKind": dict(bindings_by_kind),
        "bindingsByDependency": dict(sorted(by_dependency.items())),
        "duplicateRuntimeIds": sum(1 for rows in candidates.values() if len(rows) > 1),
        "duplicateIdsWithDifferentTranslations": len(conflicts),
        "globalClassConflicts": class_conflicts,
        "productStringsAdded": len(generated_keys),
        "productStringsAddedThisRun": len(additions),
        "productStringsFullyTranslated": generated_complete,
        "originalOverlay": {
            "path": str(args.original_overlay),
            "available": not overlay_missing,
            "chineseRows": overlay_applied,
            "changedProductRows": overlay_changed,
        },
        "sourceStringsSynced": synced_tables,
        "parseFailures": len(parse_failures),
        "invalidRows": len(invalid_rows),
        "triggerStrings": trigger_summary,
        "output": str(args.output),
        "outputBytes": args.output.stat().st_size,
        "resourceOutput": str(args.resource_output),
        "resourceOutputBytes": args.resource_output.stat().st_size,
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
