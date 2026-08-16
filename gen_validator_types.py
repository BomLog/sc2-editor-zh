#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate missing CValidator ENTRYTYPE entries for EditorCatalogStrings.txt"""
import os

# All 100 CValidator subtypes with Chinese translations
VALIDATOR_TYPES = {
    "CValidator": "验证器",
    "CValidatorCombine": "组合",
    "CValidatorCondition": "条件",
    "CValidatorEffect": "效果",
    "CValidatorEffectCompareDodged": "效果比较-已闪避",
    "CValidatorEffectCompareEvaded": "效果比较-已回避",
    "CValidatorEffectTreeUserData": "效果树-用户数据",
    "CValidatorFunction": "函数",
    "CValidatorGameCommanderActive": "游戏-指挥官激活",
    "CValidatorGameCompareTerrain": "游戏比较-地形",
    "CValidatorGameCompareTimeOfDay": "游戏比较-时间",
    "CValidatorLocation": "位置",
    "CValidatorLocationArc": "位置-弧形",
    "CValidatorLocationCompareCliffLevel": "位置比较-悬崖等级",
    "CValidatorLocationComparePower": "位置比较-能量源",
    "CValidatorLocationCompareRange": "位置比较-距离",
    "CValidatorLocationCreep": "位置-菌毯",
    "CValidatorLocationCrossChasm": "位置-跨越深渊",
    "CValidatorLocationCrossCliff": "位置-跨越悬崖",
    "CValidatorLocationEnumArea": "位置-枚举区域",
    "CValidatorLocationInPlayableMapArea": "位置-在可游玩区域内",
    "CValidatorLocationPathable": "位置-可寻路",
    "CValidatorLocationPlacement": "位置-放置",
    "CValidatorLocationShrub": "位置-灘木",
    "CValidatorLocationType": "位置-类型",
    "CValidatorLocationVision": "位置-视野",
    "CValidatorPlayer": "玩家",
    "CValidatorPlayerAlliance": "玩家-联盟",
    "CValidatorPlayerCompareDifficulty": "玩家比较-难度",
    "CValidatorPlayerCompareFoodAvailable": "玩家比较-可用补给",
    "CValidatorPlayerCompareFoodUsed": "玩家比较-已用补给",
    "CValidatorPlayerCompareRace": "玩家比较-种族",
    "CValidatorPlayerCompareResource": "玩家比较-资源",
    "CValidatorPlayerCompareResult": "玩家比较-结果",
    "CValidatorPlayerCompareType": "玩家比较-类型",
    "CValidatorPlayerRequirement": "玩家-所需条件",
    "CValidatorUnit": "单位",
    "CValidatorUnitAI": "单位-AI",
    "CValidatorUnitAbil": "单位-技能",
    "CValidatorUnitAlliance": "单位-联盟",
    "CValidatorUnitBehaviorState": "单位-行为状态",
    "CValidatorUnitCombatAI": "单位-战斗AI",
    "CValidatorUnitCompareAIAreaEvalRatio": "单位比较-AI区域评估比率",
    "CValidatorUnitCompareAbilLevel": "单位比较-技能等级",
    "CValidatorUnitCompareAttackPriority": "单位比较-攻击优先级",
    "CValidatorUnitCompareBehaviorCount": "单位比较-行为计数",
    "CValidatorUnitCompareCargo": "单位比较-装载量",
    "CValidatorUnitCompareChargeUsed": "单位比较-充能使用",
    "CValidatorUnitCompareCooldown": "单位比较-冷却时间",
    "CValidatorUnitCompareDamageDealtTime": "单位比较-造成伤害时间",
    "CValidatorUnitCompareDamageTakenTime": "单位比较-受到伤害时间",
    "CValidatorUnitCompareDeath": "单位比较-死亡",
    "CValidatorUnitCompareField": "单位比较-字段",
    "CValidatorUnitCompareHeight": "单位比较-高度",
    "CValidatorUnitCompareKillCount": "单位比较-击杀数",
    "CValidatorUnitCompareMarkerCount": "单位比较-标记计数",
    "CValidatorUnitCompareMoverPhase": "单位比较-移动阶段",
    "CValidatorUnitCompareOrderCount": "单位比较-命令数",
    "CValidatorUnitCompareOrderTargetRange": "单位比较-命令目标距离",
    "CValidatorUnitComparePowerSourceLevel": "单位比较-能量源等级",
    "CValidatorUnitComparePowerUserLevel": "单位比较-能量用户等级",
    "CValidatorUnitCompareRallyPointCount": "单位比较-集结点数",
    "CValidatorUnitCompareResourceContents": "单位比较-资源容量",
    "CValidatorUnitCompareResourceHarvesters": "单位比较-资源采集者",
    "CValidatorUnitCompareSpeed": "单位比较-速度",
    "CValidatorUnitCompareVeterancyLevel": "单位比较-老兵等级",
    "CValidatorUnitCompareVital": "单位比较-生命值",
    "CValidatorUnitCompareVitality": "单位比较-活力",
    "CValidatorUnitDetected": "单位-已被侦测",
    "CValidatorUnitFilters": "单位-过滤器",
    "CValidatorUnitFlying": "单位-飞行中",
    "CValidatorUnitInWeaponRange": "单位-在武器射程内",
    "CValidatorUnitInventory": "单位-物品栏",
    "CValidatorUnitInventoryContainsItem": "单位-物品栏包含物品",
    "CValidatorUnitInventoryIsFull": "单位-物品栏已满",
    "CValidatorUnitKinetic": "单位-动能",
    "CValidatorUnitLastDamagePlayer": "单位-最后伤害玩家",
    "CValidatorUnitMissileNullified": "单位-飞弹已无效化",
    "CValidatorUnitMover": "单位-移动体",
    "CValidatorUnitOrder": "单位-命令",
    "CValidatorUnitOrderQueue": "单位-命令队列",
    "CValidatorUnitOrderTargetPathable": "单位-命令目标可寻路",
    "CValidatorUnitOrderTargetType": "单位-命令目标类型",
    "CValidatorUnitPathable": "单位-可寻路",
    "CValidatorUnitPathing": "单位-寻路中",
    "CValidatorUnitScanning": "单位-正在扫描",
    "CValidatorUnitState": "单位-状态",
    "CValidatorUnitType": "单位-类型",
    "CValidatorUnitWeaponAnimating": "单位-武器动画播放中",
    "CValidatorUnitWeaponFiring": "单位-武器开火中",
    "CValidatorUnitWeaponPlane": "单位-武器平面",
}

# Already existing in the file
EXISTING = {
    "CValidatorCompareTrackedUnitsCount",
    "CValidatorGameCompareTimeEvent",
    "CValidatorIsUnitTracked",
    "CValidatorPlayerFood",
    "CValidatorUnitArmor",
    "CValidatorUnitBehaviorStackAlias",
    "CValidatorUnitCompareAbilSkillPoint",
    "CValidatorUnitCompareAbilStage",
    "CValidatorUnitTestWeaponType",
}

def main():
    # Generate new entries
    new_lines = []
    for cls in sorted(VALIDATOR_TYPES.keys()):
        if cls not in EXISTING:
            name = VALIDATOR_TYPES[cls]
            new_lines.append(f"EDSTR_ENTRYTYPE_{cls}={name}  //\u6570\u636e\u7c7b\u578b\u9a8c\u8bc1\u5668>\u7c7b\u578b>{name}")

    print(f"Generated {len(new_lines)} new Validator ENTRYTYPE entries")

    # Read existing EditorCatalogStrings.txt
    catalog_path = r"D:\StarCraft II\Editor\EditorCatalogStrings.txt"
    with open(catalog_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    # Find the last CValidator entry and insert after it
    insert_marker = "EDSTR_ENTRYTYPE_CValidatorUnitTestWeaponType"
    if insert_marker in content:
        idx = content.index(insert_marker)
        line_end = content.index("\n", idx) + 1
        new_block = "\n-------\u9a8c\u8bc1\u5668\u7c7b\u578b(\u8865\u5168)-------\n" + "\n".join(new_lines) + "\n"
        content = content[:line_end] + new_block + content[line_end:]
    else:
        content += "\n\n-------\u9a8c\u8bc1\u5668\u7c7b\u578b(\u8865\u5168)-------\n" + "\n".join(new_lines) + "\n"

    # Write back with BOM (original file has BOM)
    with open(catalog_path, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(content)

    print(f"Updated {catalog_path}")
    print(f"Total entries added: {len(new_lines)}")

if __name__ == "__main__":
    main()
