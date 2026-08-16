#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补丁：翻译 pack 中草稿未覆盖的 ~512 条纯英文条目。"""
import io, glob, os, json, re, shutil, datetime

PACK = r"D:\StarCraft II\Editor\LocalizedData\ObjectStrings.txt"
DRAFT_DIR = r"e:\Code\sc2\Work\_draft"
DICT = r"e:\Code\sc2\Work\l10n_dict.json"

with io.open(DICT, encoding="utf-8") as f:
    d = json.load(f)
sfx = d["suffix"]
prop = d["proper"]

# draft keys
draft_keys = set()
for fp in glob.glob(os.path.join(DRAFT_DIR, "*.txt")):
    for line in io.open(fp, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        body = line.split("\t")[0]
        if "=" in body:
            draft_keys.add(body.partition("=")[0].strip())

# 手工翻译: C类前缀
C_MANUAL = {
    "CAttachMethod": "附加方法",
    "CAttachMethodFilter": "附加方法-筛选",
    "CAttachMethodPattern": "附加方法-模式",
    "CAttachMethodProximity": "附加方法-邻近",
    "CAttachMethodRandom": "附加方法-随机",
    "CAttachMethodReduction": "附加方法-衰减",
    "CBankConditionCompare": "存储条件-比较",
    "CBankConditionCompareValueCount": "存储条件-比较值计数",
    "CBankConditionCompareValueSum": "存储条件-比较值总和",
    "CBeamAsyncLinear": "光束-异步线性",
    "CPreload": "预加载",
    "CPreloadActor": "预加载-演算体",
    "CPreloadConversation": "预加载-对话",
    "CPreloadModel": "预加载-模型",
    "CPreloadSound": "预加载-音效",
    "CPreloadUnit": "预加载-单位",
    "CRequirement": "需求",
    "CRequirementAllowAbil": "需求-允许技能",
    "CRequirementAllowBehavior": "需求-允许行为",
    "CRequirementAllowUnit": "需求-允许单位",
    "CRequirementAllowUpgrade": "需求-允许升级",
    "CRequirementAnd": "需求-且",
    "CRequirementConst": "需求-常量",
    "CRequirementCountAbil": "需求-技能计数",
    "CRequirementCountBehavior": "需求-行为计数",
    "CRequirementCountUnit": "需求-单位计数",
    "CRequirementCountUpgrade": "需求-升级计数",
    "CRequirementDiv": "需求-除",
    "CRequirementEq": "需求-等于",
    "CRequirementGT": "需求-大于",
    "CRequirementGTE": "需求-大于等于",
    "CRequirementLT": "需求-小于",
    "CRequirementLTE": "需求-小于等于",
    "CRequirementMod": "需求-取模",
    "CRequirementMul": "需求-乘",
    "CRequirementNE": "需求-不等于",
    "CRequirementNode": "需求节点",
    "CRequirementNot": "需求-非",
    "CRequirementOdd": "需求-奇数",
    "CRequirementOr": "需求-或",
    "CRequirementSum": "需求-总和",
    "CRequirementXor": "需求-异或",
    "CSound": "音效",
    "CValidator": "验证器",
    "CValidatorCombine": "验证器-组合",
    "CValidatorCondition": "验证器-条件",
    "CValidatorFunction": "验证器-函数",
    "CValidatorGameCompareTerrain": "验证器-游戏比较地形",
    "CValidatorGameCompareTimeOfDay": "验证器-游戏比较时间",
    "CValidatorLocation": "验证器-位置",
    "CValidatorLocationArc": "验证器-位置弧度",
    "CValidatorLocationCompareCliffLevel": "验证器-位置比较悬崖层级",
    "CValidatorLocationComparePower": "验证器-位置比较能量",
    "CValidatorLocationCompareRange": "验证器-位置比较距离",
    "CValidatorLocationCreep": "验证器-位置菌毯",
    "CValidatorLocationCrossChasm": "验证器-位置跨裂缝",
    "CValidatorLocationCrossCliff": "验证器-位置跨悬崖",
    "CValidatorLocationEnumArea": "验证器-位置枚举区域",
    "CValidatorLocationPathable": "验证器-位置可通行",
    "CValidatorLocationPlacement": "验证器-位置放置",
    "CValidatorLocationType": "验证器-位置类型",
    "CValidatorLocationVision": "验证器-位置视野",
    "CValidatorPlayer": "验证器-玩家",
    "CValidatorPlayerAlliance": "验证器-玩家联盟",
    "CValidatorPlayerCompareDifficulty": "验证器-玩家比较难度",
    "CValidatorPlayerCompareRace": "验证器-玩家比较种族",
    "CValidatorPlayerCompareResult": "验证器-玩家比较结果",
    "CValidatorPlayerCompareType": "验证器-玩家比较类型",
    "CValidatorPlayerRequirement": "验证器-玩家需求",
    "CValidatorUnit": "验证器-单位",
    "CValidatorUnitAI": "验证器-单位AI",
    "CValidatorUnitAbil": "验证器-单位技能",
    "CValidatorUnitBehaviorState": "验证器-单位行为状态",
    "CValidatorUnitCombatAI": "验证器-单位战斗AI",
    "CValidatorUnitCompareAIAreaEvalRatio": "验证器-单位比较AI区域评估比",
    "CValidatorUnitCompareAttackPriority": "验证器-单位比较攻击优先级",
    "CValidatorUnitCompareBehaviorCount": "验证器-单位比较行为计数",
    "CValidatorUnitCompareCargo": "验证器-单位比较载量",
    "CValidatorUnitCompareChargeUsed": "验证器-单位比较充能已用",
    "CValidatorUnitCompareDamageTakenTime": "验证器-单位比较受伤时间",
    "CValidatorUnitCompareDeath": "验证器-单位比较死亡",
    "CValidatorUnitCompareField": "验证器-单位比较字段",
    "CValidatorUnitCompareMarkerCount": "验证器-单位比较标记计数",
    "CValidatorUnitCompareMoverPhase": "验证器-单位比较移动阶段",
    "CValidatorUnitCompareOrderCount": "验证器-单位比较命令计数",
    "CValidatorUnitCompareOrderTargetRange": "验证器-单位比较命令目标距离",
    "CValidatorUnitComparePowerSourceLevel": "验证器-单位比较能量源等级",
    "CValidatorUnitComparePowerUserLevel": "验证器-单位比较能量使用者等级",
    "CValidatorUnitCompareResourceContents": "验证器-单位比较资源含量",
    "CValidatorUnitCompareResourceHarvesters": "验证器-单位比较采集者",
    "CValidatorUnitCompareSpeed": "验证器-单位比较速度",
    "CValidatorUnitCompareVeterancyLevel": "验证器-单位比较老兵等级",
    "CValidatorUnitCompareVital": "验证器-单位比较生命值",
    "CValidatorUnitCompareVitality": "验证器-单位比较生命力",
    "CValidatorUnitFilters": "验证器-单位过滤器",
    "CValidatorUnitFlying": "验证器-单位飞行",
    "CValidatorUnitInventory": "验证器-单位物品栏",
    "CValidatorUnitKinetic": "验证器-单位动能",
    "CValidatorUnitMover": "验证器-单位移动器",
    "CValidatorUnitOrder": "验证器-单位命令",
    "CValidatorUnitOrderQueue": "验证器-单位命令队列",
    "CValidatorUnitOrderTargetPathable": "验证器-单位命令目标可通行",
    "CValidatorUnitOrderTargetType": "验证器-单位命令目标类型",
    "CValidatorUnitPathable": "验证器-单位可通行",
    "CValidatorUnitTestWeaponType": "验证器-单位测试武器类型",
    "CValidatorUnitType": "验证器-单位类型",
}

# 特殊完整 key 翻译
SPECIAL = {
    "Validator/Name/IsFlying": "正在飞行",
    "Sound/Name/CSound": "音效",
    "Sound/Name/SC_Shell_Kerrigan_EyeFlare": "SC外壳-凯瑞甘眼光",
    "Sound/Name/Briefings": "任务简报",
    "Sound/Name/DevTV": "开发者TV",
    "Token/Tooltip/GenericAttack/effectAttack": "用于直接挂在武器上的纯伤害效果(代替效果发射和效果命中)",
    "LookAtType/NovaXanthosRailGunTurret": "诺娃赞瑟斯磁轨炮",
    "Model/Name/FX": "特效",
    "Model/Name/IGNORE": "忽略",
    "Model/Name/SM": "故事模式",
    "Model/Name/SMCAMERA": "故事模式镜头",
    "Model/Name/SMCHARACTER": "故事模式角色",
    "Model/Name/SMSET": "故事模式布景",
    "Game/Name/Dflt": "默认",
    "PhysicsMaterial/Name/Dirt": "泥土",
    "User/Name/Backgrounds": "背景",
    "User/Name/Clickable": "可点击",
    "User/Name/ConversationTimestamps": "对话时间戳",
}


def camel_split(name):
    """CamelCase longest-match tokenizer."""
    tokens = []
    i = 0
    all_dict = {}
    all_dict.update(sfx)
    all_dict.update(prop)

    while i < len(name):
        best = None
        best_len = 0
        for length in range(min(25, len(name) - i), 1, -1):
            sub = name[i:i + length]
            # Exact match
            if sub in all_dict:
                best = sub
                best_len = length
                break
            # Capitalized
            cap = sub[0].upper() + sub[1:] if len(sub) > 0 else sub
            if cap in all_dict:
                best = cap
                best_len = length
                break
        if best:
            tokens.append(best)
            i += best_len
        else:
            # Advance one "word" (to next uppercase or digit boundary)
            j = i + 1
            while j < len(name) and not (name[j].isupper() or (name[j].isdigit() and not name[j-1].isdigit())):
                j += 1
            tokens.append(name[i:j])
            i = j
    return tokens


def translate_name(name):
    """Translate a CamelCase ID using dictionary."""
    toks = camel_split(name)
    parts = []
    has_cjk = False
    for t in toks:
        if t.isdigit():
            parts.append(t)
            continue
        tr = None
        for variant in [t, t.capitalize(), t.lower(), t.upper()]:
            if variant in sfx:
                tr = sfx[variant]
                break
            if variant in prop:
                tr = prop[variant]
                break
        if tr:
            parts.append(tr)
            if any("\u4e00" <= c <= "\u9fff" for c in tr):
                has_cjk = True
        else:
            parts.append(t)
    if not has_cjk:
        return None
    # Join with dashes at CJK/ASCII boundaries
    out = []
    for p in parts:
        if not p:
            continue
        if out:
            prev = out[-1][-1]
            cur = p[0]
            if "\u4e00" <= prev <= "\u9fff" and cur.isascii() and cur.isalpha():
                out.append("-")
            elif prev.isascii() and prev.isalpha() and "\u4e00" <= cur <= "\u9fff":
                out.append("-")
        out.append(p)
    return "".join(out)


def main():
    # Read pack
    pack_text = io.open(PACK, encoding="utf-8-sig").read().replace("\r\n", "\n").replace("\r", "\n")
    pack_lines = pack_text.splitlines()

    # Collect entries to fix
    to_fix = {}
    for line in pack_lines:
        if not line.strip() or line.strip().startswith("//"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.split("\t")[0].strip()
        if any("\u4e00" <= ch <= "\u9fff" for ch in v):
            continue
        if k in draft_keys:
            continue

        # Try SPECIAL
        if k in SPECIAL:
            to_fix[k] = SPECIAL[k]
            continue

        _id = k.rsplit("/", 1)[-1] if "/" in k else k

        # Try C_MANUAL
        if _id in C_MANUAL:
            to_fix[k] = C_MANUAL[_id]
            continue

        # Try EditorSuffix entries: translate the suffix value
        if "/EditorSuffix/" in k and v.startswith("- "):
            suffix_id = v[2:].strip()
            tr = translate_name(suffix_id)
            if tr:
                to_fix[k] = "- " + tr
                continue

        # General translate
        tr = translate_name(_id)
        if tr:
            to_fix[k] = tr

    print("可修复: %d 条" % len(to_fix))

    # Backup
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = PACK + ".bak." + stamp
    shutil.copy2(PACK, bak)
    print("已备份: %s" % bak)

    # Apply
    new_lines = []
    fixed = 0
    for line in pack_lines:
        if "=" in line and not line.strip().startswith("//"):
            k = line.partition("=")[0].strip()
            if k in to_fix:
                new_lines.append("%s=%s" % (k, to_fix[k]))
                fixed += 1
                continue
        new_lines.append(line)

    # Detect BOM
    raw = open(PACK, "rb").read(3)
    enc = "utf-8-sig" if raw == b"\xef\xbb\xbf" else "utf-8"

    with io.open(PACK, "w", encoding=enc, newline="\r\n") as w:
        w.write("\n".join(new_lines) + "\n")

    print("已替换: %d 条" % fixed)

    # Show samples
    for k, v in list(to_fix.items())[:25]:
        print("  %s = %s" % (k, v))


if __name__ == "__main__":
    main()
