import json, re
from pathlib import Path

LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")
WORK = Path(r"E:\Code\sc2\Work")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

CATS = {
    "Actor": "演算体", "Behavior": "行为", "Effect": "效果", "Mover": "移动器",
    "Validator": "验证器", "Weapon": "武器", "Unit": "单位", "Abil": "技能",
    "Model": "模型", "Sound": "音效", "Button": "按钮", "Requirement": "需求",
    "Item": "物品", "Loot": "掉落", "Upgrade": "升级", "User": "用户",
    "Tactical": "战术", "Preload": "预加载", "DataCollection": "数据收集",
    "Footprint": "足迹", "Light": "灯光", "Texture": "纹理", "TerrainTex": "地形纹理",
    "Conversation": "对话", "ConversationState": "对话状态", "Character": "角色",
    "Achievement": "成就", "AchievementTerm": "成就术语", "Reward": "奖励",
    "Skin": "皮肤", "SkinPack": "皮肤包", "ScoreValue": "计分值", "ScoreResult": "计分结果",
    "Objective": "目标", "ArmyCategory": "军队类别", "ArmyUnit": "军队单位",
    "ArmyUpgrade": "军队升级", "AttachMethod": "附着方式", "BankCondition": "银行条件",
    "Bundle": "捆绑包", "Camera": "镜头", "Card": "卡片", "Hero": "英雄",
    "HeroAbil": "英雄技能", "HeroStat": "英雄属性", "ItemClass": "物品类别",
    "Kinetic": "动力学", "Location": "位置", "Map": "地图", "Race": "种族",
    "Reverb": "混响", "Soundtrack": "原声带", "TargetSort": "目标排序", "Turret": "炮塔",
    "Accumulator": "蓄能器",
}

entries = []          # {file, key, category, id}
to_translate = {}     # unique id -> category (first seen)
for line in (LDR / "ObjectStrings.txt").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" not in line:
        continue
    k, v = line.split("=", 1)
    parts = k.split("/")
    cat = parts[0] if parts else ""
    field = parts[1] if len(parts) > 1 else ""
    if cat not in CATS or field != "Name":
        continue
    body = v.split("///", 1)[0].split("//", 1)[0].strip()
    if " - " not in body:
        continue
    head, tail = body.split(" - ", 1)
    head = head.strip()
    if not hascjk(head):
        continue
    tail = tail.strip()
    if not tail or hascjk(tail):
        continue
    entries.append({"key": k, "category": CATS[cat], "id": tail})
    to_translate.setdefault(tail, CATS[cat])

plan = {
    "unique_ids": len(to_translate),
    "to_translate": sorted(to_translate.keys()),
    "id_category": to_translate,
    "entries": entries,
}
(WORK / "opaque_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print("unique opaque ids:", len(to_translate))
print("total entries:", len(entries))
# sample
for s in sorted(to_translate.keys())[:40]:
    print("   ", s, "->", to_translate[s])
