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
DEFAULT_ENGLISH_OBJECT = (
    WORK
    / "localized_output"
    / "Editor"
    / "合作本地化文件（英文）"
    / "ObjectStrings.txt"
)
DEFAULT_ENGLISH_GAME = DEFAULT_ENGLISH_OBJECT.with_name("GameStrings.txt")
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
# Official and legacy editor tables use these proper nouns across multiple
# catalog kinds.  Keep them in the shared token layer so an Actor, Behavior,
# Abil, Effect, Validator and Model that references the same unit receives the
# same translation.  Values here are taken from existing Chinese catalog rows,
# not inferred from the internal asset code.
CATALOG_TOKEN_OVERRIDES = {
    "aleksander": "亚历山大号",
    "alkesander": "亚历山大号",
    "boombot": "破坏无人机",
    "choker": "扼喉怪",
    "hunterling": "猎杀体",
    "kaboomer": "炸弹怪",
    "remastered": "重制版",
    "slayer": "杀戮者",
    "spotter": "监控体",
    "stank": "腐尸怪",
    "tombstone": "墓碑",
    "user": "用户",
    "zertaul": "泽拉图",
}
CATALOG_PHRASE_OVERRIDES = {
    "user 1": "用户 1",
    "warpableanywhere": "可在任意位置折跃",
}
MANUAL_NAME_OVERRIDES = {
    "Actor/Name/ZeratulShadowCleave": "泽拉图-暗影顺劈",
    "Actor/Name/ZeratulShadowCleaveImpact": "泽拉图-暗影顺劈-冲击",
    "Actor/Name/ZeratulShadowCleaveImpactSound": "泽拉图-暗影顺劈-冲击音效",
    "Actor/Name/ZeratulShadowCleaveSound": "泽拉图-暗影顺劈-音效",
    "Abil/Name/ZeratulShadowCleave": "泽拉图-暗影顺劈",
    "Effect/Name/ZeratulShadowCleaveDamage": "泽拉图-暗影顺劈-伤害",
    "Effect/Name/ZeratulShadowCleaveSearch": "泽拉图-暗影顺劈-搜索",
    "Effect/Name/ZeratulShadowCleaveSet": "泽拉图-暗影顺劈-效果集合",
    "Model/Name/ZeratulShadowCleave": "泽拉图-暗影顺劈",
    "Model/Name/ZeratulShadowCleaveImpact": "泽拉图-暗影顺劈-冲击",
    "Validator/Name/ZeratulShadowCleaveTargetsInArea": "泽拉图-暗影顺劈-范围内有目标",
    "Behavior/Name/PitAlarakLifeRegen": "深渊阿拉纳克-生命恢复",
    "Behavior/Name/PrimalSlashStun": "原始切割-眩晕",
    "Behavior/EditorPrefix/PitAlarakLifeRegen": "深渊阿拉纳克 -",
    "Behavior/EditorPrefix/PylonPowerSourceAlly": "水晶塔 -",
    "Abil/Name/KarassFeedback": "卡拉斯-反馈",
    "Abil/Name/ZeratulZealotWhirlwind": "泽拉图-狂热者-旋风",
    "Behavior/Name/Inspiration_Jaina_ArmorBuff": "激励-吉安娜-护甲增益",
    "Behavior/Name/Inspiration_Jaina_AttackBuff": "激励-吉安娜-攻击增益",
    "Behavior/Name/TychusOdinBarrageCannonsSlow": "泰凯斯-奥丁-弹幕加农炮-减速",
    "Behavior/Name/ZeratulBlackHole": "泽拉图-黑洞",
    "Behavior/Name/ZeratulDarkArchonMindControl": "泽拉图-黑暗执政官-精神控制",
}
ENGLISH_ENTRY_OVERRIDES = {
    # These two rows are already concatenated in Blizzard's supplied English
    # tables.  Split their intended values here so the malformed source can
    # neither leak into an alias nor overwrite the following key.
    "Behavior/Name/PitAlarakLifeRegen": "Pit Alarak Life Regen",
    "Behavior/Name/PrimalSlashStun": "Primal Slash Stun",
    "Behavior/EditorPrefix/PitAlarakLifeRegen": "Pit Alarak -",
    "Behavior/EditorPrefix/PylonPowerSourceAlly": "Pylon -",
}
DISPLAY_ALIAS_PREFIX = "@display:"
TRIGGER_NAME_OVERRIDES = {
    "TOD": "时段",
    "d": "技术触发器 d",
    "Ambt - Register": "Ambt-注册",
    "Aegr - Elune's Grace - Register": "Aegr-艾露恩的恩典-注册",
    "Adev - Register": "Adev-注册",
    "Amfl - Register": "Amfl-注册",
    "AUts - Register": "AUts-注册",
    "Upkeep": "维护费",
    "Override": "覆盖",
    "F5": "F5 技术触发器",
    "lootshow": "显示战利品",
    "lootdelete": "删除战利品",
    "setdiff": "设置难度",
    "victorys": "胜利处理",
    "lootgrant": "授予战利品",
    "energylinkdebug1": "能量链接调试 1",
    "energylinkdebug2": "能量链接调试 2",
    "PP_FootageRecording": "PP-镜头录制",
    "TS_FootageRecording": "TS-镜头录制",
    "ZS_FootageRecording": "ZS-镜头录制",
    "DEBUGDELETEME": "调试-待删除",
}
REQUIRED_RESOURCE_ALIASES = {
    (
        "Stukov Infested - Stukov Infested Infested Civilian Leap Land Dust"
    ): "StukovInfestedInfestedCivilianLeapLandDust",
    (
        "Void Shard Void Shard Damage Field (Impact FX)"
    ): "VoidShardACDamageFieldImpactFX",
    "ZeratulShadowCleave": "ZeratulShadowCleave",
}
REQUIRED_DEPENDENCY_ALIASES = {
    "Hunterling Attack Start": ("Actor", "HunterlingAttackStart"),
    "Primal Slash Stun": ("Behavior", "PrimalSlashStun"),
    "Blink Slayer": ("Abil", "BlinkSlayer"),
    "Hunterling Claws Damage": ("Effect", "HunterlingClawsDamage"),
    "In Range Of Leap Target Point": ("Validator", "InRangeOfLeapTargetPoint"),
    "Hunterling Air Death": ("Model", "HunterlingAirDeath"),
}
CJK = re.compile(r"[\u3400-\u9fff]")
EMBEDDED_CATALOG_KEY = re.compile(
    r"(?:Actor|Behavior|Abil|Effect|Validator|Model)/"
    r"(?:Name|EditorPrefix|EditorSuffix)/[^=\r\n]+="
)
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
    # A few legacy catalog rows remove separators entirely when converting a
    # model path to a display token (``SOA_MatrixOverload`` ->
    # ``SOAMatrixOverload``).  Keep that compact spelling too; it is harmless
    # because the hook still requires an exact key/value pair in this table.
    compact = re.sub(r"[\s_-]+", "", text_compact_acronyms)
    aliases = {basename, text_compact_acronyms, text, compact}
    lowered = text.lower()
    for prefix in ("terrain object ", "terrainobject ", "model "):
        if lowered.startswith(prefix):
            aliases.add(text[len(prefix) :])
    return {re.sub(r"\s+", " ", alias).strip() for alias in aliases if alias.strip()}


def resource_key(value: str) -> str:
    """Canonical key used by OfficialResourceNames.tsv and the native hook."""
    return " ".join(value.strip().lower().split())


def join_display_parts(*parts: str) -> str:
    """Join editor display-name pieces while preserving punctuation."""
    return re.sub(r"\s+", " ", " ".join(part.strip() for part in parts if part.strip())).strip()


def generated_name(value: str) -> bool:
    """Return whether a Chinese catalog value is only a generated type label."""
    visible = visible_value(value)
    labels = "|".join(re.escape(label) for label in KIND_LABELS.values())
    return bool(re.match(rf"^(?:{labels})\s*-\s*[A-Za-z]", visible))


def translated_display_value(
    source: str, translator: Engine, field: str
) -> tuple[str, bool]:
    """Translate an editor display fragment and retain its punctuation role."""
    source = visible_value(source).strip()
    translated, complete = translator.translate(source)
    if not CJK.search(translated):
        return source, False
    if field == "EditorPrefix" and source.endswith("-") and not translated.endswith("-"):
        translated = translated.rstrip() + " -"
    if field == "EditorSuffix" and source.startswith("(") and source.endswith(")"):
        translated = f"({translated})"
    return translated, bool(complete)


def improve_trigger_names(path: Path, translator: Engine) -> dict[str, object]:
    """Replace generated ``触发器 - English`` names when tokens are translatable."""
    lines = path.read_text(encoding="utf-8-sig", errors="strict").splitlines()
    placeholder = re.compile(r"^触发器\s*-\s*(.+?)\s*$")
    changed = 0
    complete = 0
    unresolved: list[dict[str, str]] = []
    output: list[str] = []
    for line in lines:
        if not line.startswith("Trigger/Name/") or "=" not in line:
            output.append(line)
            continue
        key, value = line.split("=", 1)
        visible, separator, reference = value.partition(" /// ")
        match = placeholder.fullmatch(visible.strip())
        if not match:
            output.append(line)
            continue
        source = reference.strip() if separator and reference.strip() else match.group(1)
        translated = TRIGGER_NAME_OVERRIDES.get(source, "")
        if translated:
            is_complete = True
        else:
            translated, is_complete = translator.translate(source)
        if CJK.search(translated) and translated.strip() != visible.strip():
            value = translated.strip()
            if separator:
                value += f" /// {reference.strip()}"
            output.append(f"{key}={value}")
            changed += 1
            complete += int(is_complete)
        else:
            output.append(line)
            unresolved.append({"key": key, "source": source})
    if changed:
        path.write_text("\n".join(output) + "\n", encoding="utf-8", newline="")
    return {
        "generatedPlaceholders": changed + len(unresolved),
        "improved": changed,
        "fullyTranslated": complete,
        "unresolvedTechnicalNames": len(unresolved),
        "unresolvedSamples": unresolved[:50],
    }


def ac_display_stems(english_name: str, parent_names: set[str]) -> set[str]:
    """Reproduce the resource tree's special ``AC`` presentation spelling.

    Cooperative models sometimes use an internal ``AC`` token and repeat the
    leading group in the tree.  A model such as
    ``VoidShardACDamageFieldImpactFX`` is consequently rendered as
    ``Void Shard Void Shard Damage Field (Impact FX)``.  Derive the stem from
    the official English name instead of hard-coding individual model ids.
    """
    parent_words = {
        word.lower()
        for parent_name in parent_names
        for alias in resource_aliases(parent_name)
        for word in alias.split()
    }
    stems: set[str] = set()
    for alias in resource_aliases(english_name):
        words = alias.split()
        for index, word in enumerate(words):
            if word.upper() != "AC" or not words[:index] or index + 1 >= len(words):
                continue
            category = words[:index]
            leaf = words[:index] + words[index + 1 :]
            while leaf and leaf[-1].lower() in parent_words:
                leaf.pop()
            if leaf:
                stems.add(" ".join(leaf))
                stems.add(" ".join(category + leaf))
    return stems


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
    parser.add_argument(
        "--english-object",
        type=Path,
        default=DEFAULT_ENGLISH_OBJECT,
        help="English ObjectStrings used to reproduce resource-tree display aliases",
    )
    parser.add_argument(
        "--english-game",
        type=Path,
        default=DEFAULT_ENGLISH_GAME,
        help="English GameStrings used to reproduce all catalog display aliases",
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
    model_parents: dict[str, set[str]] = collections.defaultdict(set)
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
                    parent = element.get("parent")
                    if parent:
                        model_parents[object_id].add(parent)
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
    english_object = (
        read_entries(args.english_object) if args.english_object.is_file() else {}
    )
    english_game = (
        read_entries(args.english_game) if args.english_game.is_file() else {}
    )
    english_strings = {**english_game, **english_object, **ENGLISH_ENTRY_OVERRIDES}
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

    translator = Engine()
    translator.tokmap.update(CATALOG_TOKEN_OVERRIDES)
    translator.phrase.update(CATALOG_PHRASE_OVERRIDES)
    official_kind_ids = {
        (str(row["kind"]), str(row["id"])) for row in latest.values()
    }
    catalog_string_ids = set(official_kind_ids)
    for key in product:
        parts = key.split("/", 2)
        if len(parts) == 3 and parts[0] in KINDS and parts[1] in {
            "Name",
            "EditorPrefix",
            "EditorSuffix",
        }:
            catalog_string_ids.add((parts[0], parts[2]))
    catalog_improvements: dict[str, dict[str, str | bool]] = {}
    catalog_improvements_by_kind: collections.Counter[str] = collections.Counter()
    catalog_unresolved_generated: list[dict[str, str]] = []
    for kind, object_id in sorted(catalog_string_ids):
        for field in ("Name", "EditorPrefix", "EditorSuffix"):
            key = f"{kind}/{field}/{object_id}"
            current = product.get(key, "")
            if not generated_name(current):
                continue
            source = english_strings.get(key, "")
            source_fallback = not bool(source.strip())
            if source_fallback:
                source = object_id
            translated, complete = translated_display_value(
                source, translator, field
            )
            if CJK.search(translated) and source_fallback:
                if field == "EditorPrefix" and not translated.rstrip().endswith("-"):
                    translated = translated.rstrip() + " -"
                elif field == "EditorSuffix":
                    translated = f"({translated.strip('()')})"
            if CJK.search(translated) and not generated_name(translated):
                if product[key] != translated:
                    product[key] = translated
                    catalog_improvements[key] = {
                        "previous": current,
                        "value": translated,
                        "completeTokenTranslation": complete,
                        "sourceFallback": source_fallback,
                    }
                    catalog_improvements_by_kind[f"{kind}/{field}"] += 1
            else:
                catalog_unresolved_generated.append(
                    {"key": key, "value": current, "source": source}
                )

    manual_changed = 0
    for key, value in MANUAL_NAME_OVERRIDES.items():
        if product.get(key) != value:
            product[key] = value
            manual_changed += 1
    embedded_catalog_rows = [
        {"key": key, "value": value}
        for key, value in product.items()
        if EMBEDDED_CATALOG_KEY.search(value)
    ]
    if embedded_catalog_rows:
        raise ValueError(
            f"concatenated catalog rows remain: {embedded_catalog_rows[:20]}"
        )
    product_baseline_path = args.product.with_name(
        args.product.name + ".bak.before_official_dependencies"
    )
    product_baseline = (
        read_entries(product_baseline_path)
        if product_baseline_path.exists()
        else dict(product)
    )
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

    if additions or overlay_changed or manual_changed or catalog_improvements:
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
    } | set(MANUAL_NAME_OVERRIDES) | set(catalog_improvements)
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
    resource_expected: dict[str, set[str]] = collections.defaultdict(set)
    resource_exact_object_values: dict[str, set[str]] = collections.defaultdict(set)
    resource_alias_sources: collections.Counter[str] = collections.Counter()

    def add_resource_alias(
        alias: str, value: str, priority: int, source_kind: str
    ) -> bool:
        if not alias or "##" in alias or not CJK.search(visible_value(value)):
            return False
        resource_candidates[resource_key(alias)].append(
            (priority, -int(generated_name(value)), value)
        )
        resource_alias_sources[source_kind] += 1
        return True

    def add_alias_source(
        source: str, value: str, priority: int, source_kind: str
    ) -> None:
        basename = source.replace("/", "\\").rsplit("\\", 1)[-1]
        basename = re.sub(r"\.[^.\\]+$", "", basename)
        exact_key = resource_key(basename)
        for alias in resource_aliases(source):
            alias_key = resource_key(alias)
            # If a synthetic compact/spaced spelling collides with a real
            # source spelling, the exact source must win.
            specificity = 2 if alias_key == exact_key else 0
            if add_resource_alias(
                alias, value, priority + specificity, source_kind
            ):
                resource_expected[alias_key].add(value)
                if source_kind == "objectId" and alias_key == exact_key:
                    resource_exact_object_values[alias_key].add(value)

    def add_model_resource(
        object_id: str, value: str, id_priority: int, file_priority: int
    ) -> None:
        if not CJK.search(visible_value(value)):
            return
        add_alias_source(object_id, value, id_priority, "objectId")
        for file_value in model_files.get(object_id, ()):
            add_alias_source(file_value, value, file_priority, "modelFile")

    def english_model_name(object_id: str) -> str:
        return visible_value(
            english_object.get(f"Model/Name/{object_id}", "")
            or english_object.get(f"Actor/Name/{object_id}", "")
        ).strip()

    def english_parent_names(object_id: str) -> set[str]:
        names: set[str] = set()
        for parent_id in model_parents.get(object_id, ()):
            name = english_model_name(parent_id)
            if name:
                names.add(name)
                continue
            # Parent rows without a string binding are rendered from the
            # CamelCase catalog id.
            names.update(
                alias
                for alias in resource_aliases(parent_id)
                if " " in alias or alias == parent_id
            )
        return names

    def add_model_display_aliases(object_id: str, value: str) -> None:
        name = english_model_name(object_id)
        if not name or not CJK.search(visible_value(value)):
            return
        prefix = visible_value(
            english_object.get(f"Model/EditorPrefix/{object_id}", "")
            or english_object.get(f"Actor/EditorPrefix/{object_id}", "")
        ).strip()
        suffix = visible_value(
            english_object.get(f"Model/EditorSuffix/{object_id}", "")
            or english_object.get(f"Actor/EditorSuffix/{object_id}", "")
        ).strip()
        parents = english_parent_names(object_id)

        # The official English Name is an independent render path from the
        # object id and model basename.
        add_alias_source(name, value, 36, "englishName")
        if prefix:
            add_alias_source(
                join_display_parts(prefix, name), value, 38, "editorPrefix"
            )
        if suffix:
            add_alias_source(
                join_display_parts(name, suffix), value, 38, "editorSuffix"
            )
        if prefix and suffix:
            add_alias_source(
                join_display_parts(prefix, name, suffix),
                value,
                39,
                "editorPrefixSuffix",
            )

        stems = {name} | ac_display_stems(name, parents)
        for parent_name in parents:
            annotation = f"({parent_name})"
            for stem in stems:
                add_alias_source(
                    join_display_parts(stem, annotation),
                    value,
                    37,
                    "parentAnnotation",
                )
                if prefix:
                    add_alias_source(
                        join_display_parts(prefix, stem, annotation),
                        value,
                        39,
                        "prefixParentAnnotation",
                    )

    # Most model declarations use Model/Name, but the editor's actor-backed
    # preview models (notably the Purifier guide visuals) only have an
    # Actor/Name translation.  Restrict this fallback to IDs that are actually
    # declared as model/resource objects so actor catalog names do not flood
    # the resource table or win unrelated collisions.
    model_ids = set(model_files) | resource_model_ids
    product_model_names = {
        key[len("Model/Name/") :]: value
        for key, value in product.items()
        if key.startswith("Model/Name/")
    }

    def choose_model_translation(object_id: str) -> str:
        model_value = product_model_names.get(object_id, "")
        actor_value = product.get(f"Actor/Name/{object_id}", "")
        choices = [
            (model_value, 1),
            (actor_value, 0),
        ]
        return max(
            choices,
            key=lambda row: (
                int(bool(CJK.search(visible_value(row[0])))),
                int(not generated_name(row[0])),
                -len(re.findall(r"[A-Za-z]", visible_value(row[0]))),
                row[1],
            ),
        )[0]

    model_translation_values = {
        object_id: choose_model_translation(object_id)
        for object_id in set(product_model_names) | model_ids
    }
    resource_untranslated_model_ids = [
        object_id
        for object_id in sorted(model_ids)
        if not CJK.search(visible_value(model_translation_values[object_id]))
    ]
    for object_id, value in sorted(model_translation_values.items()):
        add_model_resource(object_id, value, 40, 30)
        add_model_display_aliases(object_id, value)

    resource_resolved = {
        alias: max(rows, key=lambda row: (row[0], row[1], -len(row[2]), row[2]))[2]
        for alias, rows in resource_candidates.items()
    }
    resource_missing_aliases = [
        alias for alias in resource_expected if alias not in resource_resolved
    ]
    resource_mismatched_aliases = [
        {
            "alias": alias,
            "expectedValues": sorted(resource_expected[alias]),
            "resolvedValue": resource_resolved[alias],
        }
        for alias in resource_resolved
        if alias in resource_expected
        and resource_resolved[alias] not in resource_expected[alias]
    ]
    resource_exact_object_mismatches = [
        {
            "alias": alias,
            "expectedValue": next(iter(values)),
            "resolvedValue": resource_resolved.get(alias, ""),
        }
        for alias, values in resource_exact_object_values.items()
        if len(values) == 1
        and resource_resolved.get(alias, "") != next(iter(values))
    ]
    if resource_exact_object_mismatches:
        raise ValueError(
            "exact model object aliases lost collision precedence: "
            f"{resource_exact_object_mismatches[:20]}"
        )
    required_resource_alias_audit = []
    for alias, object_id in REQUIRED_RESOURCE_ALIASES.items():
        alias_key = resource_key(alias)
        expected_value = model_translation_values.get(object_id, "")
        resolved_value = resource_resolved.get(alias_key, "")
        required_resource_alias_audit.append(
            {
                "alias": alias,
                "objectId": object_id,
                "expectedValue": expected_value,
                "resolvedValue": resolved_value,
                "matched": bool(expected_value and resolved_value == expected_value),
            }
        )
    failed_required_resource_aliases = [
        row for row in required_resource_alias_audit if not row["matched"]
    ]
    if failed_required_resource_aliases:
        raise ValueError(
            "required resource aliases failed: "
            f"{failed_required_resource_aliases}"
        )
    args.resource_output.parent.mkdir(parents=True, exist_ok=True)
    with args.resource_output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# SC2 model/resource tree basename aliases; UTF-8\n")
        for alias in sorted(resource_resolved):
            handle.write(f"{alias}\t{resource_resolved[alias].rstrip()}\n")

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

    # The common fallback callback is shared by Actor, Behavior, Abil,
    # Effect, Validator and Model catalogs.  Besides raw object ids, some
    # views pass the localized presentation text assembled from the English
    # Name/EditorPrefix/EditorSuffix rows.  Store canonical, unambiguous
    # display aliases in the dependency table under a reserved prefix.
    dependency_alias_candidates: dict[
        str, list[tuple[int, str, str, str]]
    ] = collections.defaultdict(list)
    dependency_alias_sources: collections.Counter[str] = collections.Counter()
    dependency_aliases_by_kind: collections.Counter[str] = collections.Counter()
    official_names_without_chinese: list[dict[str, str]] = []

    def add_dependency_alias(
        source: str,
        value: str,
        priority: int,
        source_kind: str,
        kind: str,
    ) -> None:
        if not source or not CJK.search(visible_value(value)):
            return
        for alias in resource_aliases(source):
            key = resource_key(alias)
            if not key or any(char in key for char in "\t\r\n"):
                continue
            dependency_alias_candidates[key].append(
                (priority, value, source_kind, kind)
            )
            dependency_alias_sources[source_kind] += 1

    for kind, object_id in sorted(official_kind_ids):
        key = f"{kind}/Name/{object_id}"
        value = product.get(key, "")
        if not CJK.search(visible_value(value)):
            official_names_without_chinese.append(
                {"kind": kind, "id": object_id, "key": key, "value": value}
            )
            continue
        add_dependency_alias(object_id, value, 100, "objectId", kind)
        name = visible_value(english_strings.get(key, "")).strip()
        if not name:
            continue
        prefix = visible_value(
            english_strings.get(f"{kind}/EditorPrefix/{object_id}", "")
        ).strip()
        suffix = visible_value(
            english_strings.get(f"{kind}/EditorSuffix/{object_id}", "")
        ).strip()
        add_dependency_alias(name, value, 40, "englishName", kind)
        add_dependency_alias(
            join_display_parts(KIND_LABELS[kind], "-", name),
            value,
            50,
            "localizedKindName",
            kind,
        )
        if prefix:
            add_dependency_alias(
                join_display_parts(prefix, name),
                value,
                60,
                "editorPrefix",
                kind,
            )
        if suffix:
            add_dependency_alias(
                join_display_parts(name, suffix),
                value,
                60,
                "editorSuffix",
                kind,
            )
        if prefix and suffix:
            add_dependency_alias(
                join_display_parts(prefix, name, suffix),
                value,
                70,
                "editorPrefixSuffix",
                kind,
            )

    dependency_display_aliases: dict[str, str] = {}
    ambiguous_dependency_aliases: list[dict[str, object]] = []
    for alias, rows in dependency_alias_candidates.items():
        priority = max(row[0] for row in rows)
        strongest = [row for row in rows if row[0] == priority]
        values = {row[1] for row in strongest}
        if len(values) != 1:
            ambiguous_dependency_aliases.append(
                {
                    "alias": alias,
                    "priority": priority,
                    "candidates": [
                        {
                            "value": value,
                            "source": source_kind,
                            "kind": kind,
                        }
                        for _priority, value, source_kind, kind in strongest
                    ],
                }
            )
            continue
        dependency_display_aliases[alias] = next(iter(values))
        dependency_aliases_by_kind.update(row[3] for row in strongest)

    required_dependency_alias_audit = []
    for alias, (kind, object_id) in REQUIRED_DEPENDENCY_ALIASES.items():
        expected_value = product.get(f"{kind}/Name/{object_id}", "")
        resolved_value = dependency_display_aliases.get(resource_key(alias), "")
        required_dependency_alias_audit.append(
            {
                "alias": alias,
                "kind": kind,
                "objectId": object_id,
                "expectedValue": expected_value,
                "resolvedValue": resolved_value,
                "matched": bool(expected_value and resolved_value == expected_value),
            }
        )
    failed_required_dependency_aliases = [
        row for row in required_dependency_alias_audit if not row["matched"]
    ]
    if failed_required_dependency_aliases:
        raise ValueError(
            "required dependency aliases failed: "
            f"{failed_required_dependency_aliases}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# SC2 official CASC dependency fallback names; UTF-8\n")
        for object_id in sorted(resolved, key=lambda value: (value.lower(), value)):
            handle.write(f"{object_id}\t{resolved[object_id].rstrip()}\n")
        for alias in sorted(dependency_display_aliases):
            handle.write(
                f"{DISPLAY_ALIAS_PREFIX}{alias}\t"
                f"{dependency_display_aliases[alias].rstrip()}\n"
            )

    trigger_improvement = improve_trigger_names(
        WORK / "localized_output" / "TriggerStrings.txt", translator
    )
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
        for key in (
            "allOfficialKeys",
            "targetKeys",
            "missingKeys",
            "targetValuesWithoutChinese",
            "missingWithZhCN",
            "missingWithEnUS",
        ):
            if key in audit:
                trigger_summary[key] = audit[key]
        incomplete_trigger_sources = {
            key: int(audit.get(key, 0))
            for key in (
                "targetValuesWithoutChinese",
                "missingWithZhCN",
                "missingWithEnUS",
            )
            if int(audit.get(key, 0))
        }
        if incomplete_trigger_sources:
            raise ValueError(
                f"official trigger strings remain incomplete: {incomplete_trigger_sources}"
            )

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
        "dependencyDisplayAliases": len(dependency_display_aliases),
        "dependencyDisplayAliasAudit": {
            "officialKindObjects": len(official_kind_ids),
            "officialNamesWithoutChinese": len(official_names_without_chinese),
            "untranslatedSamples": official_names_without_chinese[:50],
            "candidateAliasKeys": len(dependency_alias_candidates),
            "resolvedAliasKeys": len(dependency_display_aliases),
            "ambiguousAliasKeysSkipped": len(ambiguous_dependency_aliases),
            "aliasesByKind": dict(dependency_aliases_by_kind),
            "candidateRowsBySource": dict(dependency_alias_sources),
            "requiredAliases": required_dependency_alias_audit,
            "failedRequiredAliases": len(failed_required_dependency_aliases),
            "ambiguousSamples": ambiguous_dependency_aliases[:50],
        },
        "resourceAliases": len(resource_resolved),
        "resourceAliasConflicts": sum(
            1 for rows in resource_candidates.values() if len({row[2] for row in rows}) > 1
        ),
        "resourceAliasAudit": {
            "modelObjectIds": len(model_ids),
            "modelReferenceValues": sum(len(values) for values in model_files.values()),
            "modelParentReferences": sum(
                len(values) for values in model_parents.values()
            ),
            "modelIdsWithoutChineseName": len(resource_untranslated_model_ids),
            "untranslatedModelSamples": resource_untranslated_model_ids[:50],
            "englishObjectAvailable": bool(english_object),
            "englishModelNames": sum(
                bool(english_model_name(object_id))
                for object_id in model_translation_values
            ),
            "aliasCandidatesBySource": dict(resource_alias_sources),
            "expectedAliasKeys": len(resource_expected),
            "missingAliasKeys": len(resource_missing_aliases),
            "mismatchedAliasKeys": len(resource_mismatched_aliases),
            "exactObjectAliasKeys": len(resource_exact_object_values),
            "ambiguousExactObjectAliasKeys": sum(
                len(values) > 1 for values in resource_exact_object_values.values()
            ),
            "exactObjectAliasMismatches": len(resource_exact_object_mismatches),
            "missingSamples": resource_missing_aliases[:50],
            "mismatchedSamples": resource_mismatched_aliases[:50],
            "requiredAliases": required_resource_alias_audit,
            "failedRequiredAliases": len(failed_required_resource_aliases),
        },
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
        "manualNameOverrides": {
            "rows": len(MANUAL_NAME_OVERRIDES),
            "changedProductRows": manual_changed,
        },
        "generatedCatalogImprovements": {
            "improvedRows": len(catalog_improvements),
            "improvedByKind": dict(catalog_improvements_by_kind),
            "unresolvedTechnicalRows": len(catalog_unresolved_generated),
            "unresolvedByKindAndField": dict(
                collections.Counter(
                    "/".join(row["key"].split("/", 2)[:2])
                    for row in catalog_unresolved_generated
                )
            ),
            "unresolvedSamples": sorted(
                catalog_unresolved_generated,
                key=lambda row: (-len(row["source"]), row["key"]),
            )[:50],
        },
        "sourceStringsSynced": synced_tables,
        "parseFailures": len(parse_failures),
        "invalidRows": len(invalid_rows),
        "triggerStrings": trigger_summary,
        "triggerNameImprovements": trigger_improvement,
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
