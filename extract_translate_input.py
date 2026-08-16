import json, re
from pathlib import Path

ROOT = Path(r"D:\StarCraft II\Editor\LocalizedData")
OBJ = ROOT / "ObjectStrings.txt"
TRIG = ROOT / "TriggerStrings.txt"
OUT = Path(r"E:\Code\sc2\Work\translate_plan.json")

OBJ_CATS = {
    "Abil": "技能", "Accumulator": "蓄能器", "Achievement": "成就",
    "AchievementTerm": "成就术语", "Actor": "演算体", "ArmyCategory": "军队类别",
    "ArmyUnit": "军队单位", "ArmyUpgrade": "军队升级", "AttachMethod": "附着方式",
    "BankCondition": "银行条件", "Behavior": "行为", "Bundle": "捆绑包",
    "Button": "按钮", "Camera": "镜头", "Card": "卡片", "Character": "角色",
    "Conversation": "对话", "ConversationState": "对话状态", "DataCollection": "数据收集",
    "Effect": "效果", "Footprint": "足迹", "Hero": "英雄", "HeroAbil": "英雄技能",
    "HeroStat": "英雄属性", "Item": "物品", "ItemClass": "物品类别", "Kinetic": "动力学",
    "Light": "灯光", "Location": "位置", "Loot": "掉落", "Map": "地图",
    "Model": "模型", "Mover": "移动器", "Objective": "目标", "Preload": "预加载",
    "Race": "种族", "Requirement": "需求", "Reverb": "混响", "Reward": "奖励",
    "ScoreResult": "计分结果", "ScoreValue": "计分值", "Skin": "皮肤",
    "SkinPack": "皮肤包", "Sound": "音效", "Soundtrack": "原声带", "Tactical": "战术",
    "TargetSort": "目标排序", "TerrainTex": "地形纹理", "Texture": "纹理",
    "Turret": "炮塔", "Unit": "单位", "Upgrade": "升级", "User": "用户",
    "Validator": "验证器", "Weapon": "武器",
}

TRIG_CATS = {
    "Category": "类别", "CustomScript": "自定义脚本", "FunctionDef": "函数",
    "Label": "标签", "Library": "库", "ParamDef": "参数", "Preset": "预设",
    "PresetValue": "预设值", "Structure": "结构体", "SubFuncType": "子函数",
    "Trigger": "触发器", "Variable": "变量",
}


def has_cjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False


def is_opaque_id(v):
    v = v.split("///", 1)[0].strip()
    if not v or not re.search(r"[A-Za-z]", v):
        return True
    if re.fullmatch(r"[A-Za-z]{1,5}\d*", v):
        return True
    if re.fullmatch(r"[A-Z0-9_@./-]+", v):
        return True
    if " " not in v and "_" not in v and not re.search(r"(?<=[a-z])(?=[A-Z])", v) and len(v) <= 12:
        return True
    return False


def entry(line):
    if not line or line.lstrip().startswith("//") or "=" not in line:
        return None
    return line.split("=", 1)


def source_of(v):
    return v.split("///", 1)[0].strip()


entries = []          # full plan entries
to_translate = {}     # unique descriptive source -> sample key

# 1) ObjectStrings: any value without Chinese in a known object category
for line in OBJ.read_text(encoding="utf-8-sig").splitlines():
    e = entry(line)
    if not e:
        continue
    k, v = e
    cat = k.split("/", 1)[0] if "/" in k else ""
    if cat not in OBJ_CATS:
        continue
    if has_cjk(v):
        continue
    s = source_of(v)
    if not s:
        continue
    if is_opaque_id(s):
        entries.append({"file": "ObjectStrings.txt", "key": k, "source": s,
                        "category": OBJ_CATS[cat], "mode": "prefix"})
    else:
        entries.append({"file": "ObjectStrings.txt", "key": k, "source": s,
                        "category": OBJ_CATS[cat], "mode": "translate"})
        to_translate.setdefault(s, k)

# 2) TriggerStrings: category-prefixed values (中文 - English /// ...) whose tail is descriptive
for line in TRIG.read_text(encoding="utf-8-sig").splitlines():
    e = entry(line)
    if not e:
        continue
    k, v = e
    cat = k.split("/", 1)[0] if "/" in k else ""
    if cat not in TRIG_CATS:
        continue
    body = v.split("///", 1)[0].strip()
    if " - " not in body:
        continue
    head, tail = body.split(" - ", 1)
    head = head.strip()
    if not has_cjk(head) or " " in head:
        continue  # not a category prefix
    tail = tail.strip()
    if not tail:
        continue
    if is_opaque_id(tail):
        continue  # already fine as category - ID
    entries.append({"file": "TriggerStrings.txt", "key": k, "source": tail,
                    "category": TRIG_CATS[cat], "mode": "translate"})
    to_translate.setdefault(tail, k)

# 3) TriggerStrings: still-untracked English values (no Chinese at all) in trigger categories
#    (should be none after autofill, but be safe)
for line in TRIG.read_text(encoding="utf-8-sig").splitlines():
    e = entry(line)
    if not e:
        continue
    k, v = e
    cat = k.split("/", 1)[0] if "/" in k else ""
    if cat not in TRIG_CATS:
        continue
    if has_cjk(v):
        continue
    s = source_of(v)
    if not s:
        continue
    if is_opaque_id(s):
        entries.append({"file": "TriggerStrings.txt", "key": k, "source": s,
                        "category": TRIG_CATS[cat], "mode": "prefix"})
    else:
        entries.append({"file": "TriggerStrings.txt", "key": k, "source": s,
                        "category": TRIG_CATS[cat], "mode": "translate"})
        to_translate.setdefault(s, k)

plan = {
    "unique_descriptive_sources": len(to_translate),
    "to_translate": sorted(to_translate.keys()),
    "entries": entries,
}
OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
print("unique_descriptive_sources =", len(to_translate))
print("total_entries =", len(entries))
print("translate_entries =", sum(1 for x in entries if x["mode"] == "translate"))
print("prefix_entries =", sum(1 for x in entries if x["mode"] == "prefix"))
# print a sample of descriptive sources
for s in sorted(to_translate.keys())[:40]:
    print("  SRC:", s)
