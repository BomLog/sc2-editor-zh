#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""批量词条 第二批 —— 覆盖 _tokens.txt 中频段(300 次 ~ 20 次)。"""
import io
import json
import re

DICT = r"e:\Code\sc2\Work\l10n_dict.json"

WORDS = {
    "Weapons": "武器", "Weapon": "武器", "Core": "核心", "Griffin": "狮鹫",
    "Griffon": "狮鹫", "Hot": "高温", "Orb": "宝珠", "Shard": "碎片",
    "Zone": "区域", "Female": "女性", "Male": "男性", "Orbital": "轨道",
    "Mass": "群体", "Glaze": "釉面", "Psionic": "灵能", "Work": "工作",
    "Vox": "语音", "Minor": "次要", "Major": "主要", "Footprint": "占地",
    "Aoe": "范围", "Glue": "粘合", "Physics": "物理", "Ward": "守卫",
    "Diamond": "钻石", "Chieftain": "酋长", "Chamber": "室",
    "White": "白色", "Black": "黑色", "Red": "红色", "Blue": "蓝色",
    "Green": "绿色", "Yellow": "黄色", "Purple": "紫色", "Silver": "白银",
    "Bronze": "青铜", "Photon": "光子", "Bio": "生物", "Permanent": "永久",
    "Boss": "首领", "Line": "线", "General": "通用", "Resource": "资源",
    "Canister": "罐", "Shooter": "射手", "Eradicator": "灭绝者",
    "Requirement": "需求", "Requirements": "需求", "Hammer": "锤",
    "Drakken": "德拉肯", "Buster": "破坏者", "Un": "非", "Cant": "无法",
    "Suit": "战衣", "Star": "星", "Form": "形态", "Pulse": "脉冲",
    "Enough": "足够", "Fan": "扇", "Place": "放置", "Wild": "野性",
    "Doom": "厄运", "Anti": "反", "Lance": "长枪", "Location": "位置",
    "Shock": "震荡", "Rail": "轨道", "Engine": "引擎", "Wolf": "狼",
    "Mines": "地雷", "Thrower": "投掷器", "Fuel": "燃料",
    "Stinger": "毒刺", "Rift": "裂隙", "Launcher": "发射器",
    "Launchers": "发射器", "Alpha": "阿尔法", "Med": "医疗",
    "Mover": "移动器", "Pad": "平台", "Can": "可", "Bypass": "绕过",
    "Dry": "干燥", "Race": "种族", "Forward": "前进", "Exit": "出口",
    "Fall": "坠落", "Falling": "坠落", "Bricks": "砖", "Art": "美术",
    "Shell": "弹壳", "Targeted": "已指定目标", "Targets": "目标",
    "Talon": "利爪", "Crane": "起重机", "Validators": "验证器",
    "Doodads": "装饰物", "Forged": "锻造", "Bad": "劣", "Good": "优",
    "Pop": "爆裂", "Strongest": "最强", "Scrambler": "干扰器",
    "Bird": "鸟", "Spear": "长矛", "Uber": "超级", "Numbers": "数字",
    "Winner": "获胜者", "Win": "获胜", "Hole": "洞", "Hardened": "硬化",
    "Earthquake": "地震", "Decay": "衰变", "Nano": "纳米",
    "Blossom": "绽放", "Activate": "激活", "Steal": "窃取",
    "Dodge": "闪避", "Basic": "基础", "Archangel": "大天使",
    "Harvestable": "可采集", "Pathing": "寻路", "Prevent": "阻止",
    "Glass": "玻璃", "Entrance": "入口", "Init": "初始化",
    "Mining": "采矿", "Negative": "负", "Positive": "正",
    "Received": "已接收", "Venom": "毒液", "Faerie": "小精灵",
    "Decoy": "诱饵", "Magrail": "磁轨", "Circle": "圆",
    "Volcano": "火山", "Planetary": "行星", "Track": "轨迹",
    "Tracking": "追踪", "Catalyst": "催化剂", "Wire": "线缆",
    "Animation": "动画", "Puke": "喷吐", "Cybernetics": "控制核心",
    "Block": "阻挡", "Blocker": "阻挡物", "Suppress": "压制",
    "System": "系统", "Periodic": "周期", "Pandaren": "熊猫人",
    "Bear": "熊", "Warlock": "术士", "Fight": "战斗",
    "Fireball": "火球", "Swoop": "俯冲", "Inferno": "地狱火",
    "Hawk": "鹰", "Emergency": "紧急", "Node": "节点",
    "Window": "窗口", "Lantern": "灯笼", "Pen": "栏", "Banshees": "女妖",
    "Hatch": "舱门", "Armored": "重甲", "Billboard": "广告牌",
    "Nuclear": "核", "Incubation": "孵化", "Sapper": "工兵",
    "Mule": "矿骡", "Chase": "追击", "Minion": "仆从",
    "Bubble": "气泡", "Steel": "钢", "Slash": "斩击", "Round": "轮",
    "Stretch": "拉伸", "Recalled": "已召回", "Servos": "伺服",
    "Doors": "门", "Door": "门", "Assimilation": "同化",
    "Attacking": "攻击中", "Attacker": "攻击者", "Too": "过于",
    "Trueshot": "强击", "Rage": "狂怒", "Annihilation": "歼灭",
    "Crushing": "碾压", "Crashed": "已坠毁", "Per": "每",
    "Warpgate": "折跃门", "Sparks": "火花", "Unbuildable": "不可建造",
    "Regenerative": "再生", "Pile": "堆", "Spires": "尖塔",
    "Throne": "王座", "Barricade": "路障", "Purpose": "用途",
    "Fun": "趣味", "Pitch": "音调", "Very": "极", "Parent": "父级",
    "Lizard": "蜥蜴", "Hanger": "机库", "Eat": "吞食",
    "Factor": "因子", "Template": "模板", "From": "来自",
    "Fountain": "泉", "Props": "道具", "Decals": "贴花",
    "Cage": "笼", "Box": "箱", "Disabler": "禁用器",
    "Streak": "连胜", "Luck": "幸运", "Score": "得分",
    "Defend": "防守", "Terrans": "人类", "Bang": "爆响",
    "Increased": "已提升", "Pull": "牵引", "Enter": "进入",
    "Carrion": "腐肉", "Expand": "扩张", "Dissection": "解剖",
    "Camera": "镜头", "Badge": "徽章", "Plating": "镀层",
    "Foot": "足", "Prismatic": "棱光", "Ursadak": "乌萨达克",
    "Fear": "恐惧", "Arc": "弧", "Reheight": "重设高度",
    "Havoc": "浩劫", "Trait": "特性", "Needle": "针",
    "Download": "下载", "Insane": "疯狂", "Thrasher": "鞭笞者",
    "Industrial": "工业", "Nature": "自然", "Restoration": "恢复",
    "Counter": "计数器", "Bush": "灌木", "Waterfall": "瀑布",
    "Barrels": "桶", "Propagator": "增殖者", "Flatbed": "平板车",
    "Frame": "帧", "Whale": "鲸", "Hurricane": "飓风",
    "Trip": "行程", "Well": "井", "Leash": "牵引",
    "Bombers": "轰炸机", "Iterate": "迭代", "Dynamic": "动态",
    "Sounds": "音效", "Avatar": "化身", "Vampiric": "吸血",
    "Three": "三", "Sweetener": "增味", "Horn": "号角",
    "Anniversary": "周年", "Sewer": "下水道", "Interior": "内部",
    "Street": "街道", "Intimidating": "威吓", "Conjoined": "连体",
    "Repulser": "斥力场", "Tick": "刻", "Piercing": "穿刺",
    "Startport": "星港", "Acquire": "获取", "Near": "靠近",
    "Slave": "奴隶", "Transmissions": "通讯", "Phrase": "语句",
    "Generate": "生成", "Frag": "破片", "Creation": "创建",
    "Cover": "掩护", "Shepherds": "牧者", "Ogre": "食人魔",
    "Mending": "修补", "Cinematic": "过场", "Icons": "图标",
    "Loot": "战利品", "Wyvern": "双足飞龙", "Kinetic": "动能",
    "Backup": "支援", "Convo": "对话", "Interact": "交互",
    "Shared": "共享", "Restock": "补货", "Dispel": "驱散",
    "Autocast": "自动施法", "Make": "制作", "Starfall": "星辰坠落",
    "Gift": "礼物", "Experimental": "实验", "Envelope": "包络",
    "Ear": "耳", "Wings": "翼", "Machine": "机械", "Firing": "开火",
    "Security": "安保", "Military": "军事", "Transformation": "变形",
    "Hand": "手", "Hellfire": "地狱火", "Claim": "占领",
    "Trees": "树", "Tree": "树", "Skull": "颅骨", "Reverse": "反向",
    "Collect": "收集", "Canopy": "顶篷",
    # 20 次以下但常见的补充
    "Ability": "技能", "Aura": "光环", "Slot": "槽位", "Stage": "阶段",
    "Level": "等级", "Point": "点", "Points": "点数", "Range": "范围",
    "Radius": "半径", "Target": "目标", "Unit": "单位", "Units": "单位",
    "Player": "玩家", "Players": "玩家", "Team": "队伍", "Enemy": "敌方",
    "Enemies": "敌方", "Ally": "友方", "Base": "基地", "Building": "建筑",
    "Buildings": "建筑", "Tower": "塔", "Turret": "炮塔", "Gun": "枪",
    "Guns": "枪", "Armor": "护甲", "Shield": "护盾", "Health": "生命值",
    "Energy": "能量", "Heal": "治疗", "Buff": "增益", "Debuff": "减益",
    "Death": "死亡", "Birth": "出生", "Spawn": "生成", "Move": "移动",
    "Movement": "移动", "Idle": "待机", "Stop": "停止", "Turn": "转向",
    "Impact": "撞击", "Launch": "发射", "Missile": "导弹",
    "Beam": "光束", "Explosion": "爆炸", "Fire": "火焰", "Flame": "火焰",
    "Ice": "冰", "Water": "水", "Earth": "地", "Air": "空中",
    "Ground": "地面", "Light": "轻甲", "Small": "小", "Medium": "中",
    "Large": "大", "Huge": "巨型", "Hero": "英雄", "Boss1": "首领1",
    "Elite": "精英", "Veteran": "老兵", "Rookie": "新兵",
    "Leader": "领袖", "Ruler": "统治者", "Queen": "女王",
    "Overlord": "王虫", "Prince": "王子", "Emperor": "皇帝",
    "Empire": "帝国", "Dominion": "自治领", "Rebel": "反抗军",
    "Raynor": "雷诺", "Swann": "斯旺", "Nova": "诺娃",
    "Stukov": "斯托科夫", "Fenix": "菲尼克斯", "Artanis": "阿塔尼斯",
    "Zagara": "扎加拉", "Abathur": "阿巴瑟", "Alarak": "阿拉纳克",
    "Vorazun": "沃拉尊", "Karax": "卡拉克斯", "Zeratul": "泽拉图",
    "Kerrigan": "凯瑞甘", "Tychus": "泰凯斯", "Dehaka": "德哈卡",
    "Mengsk": "蒙斯克", "Tassadar": "塔萨达", "Selendis": "赛兰迪斯",
    "Rohana": "罗哈娜", "Amon": "阿蒙", "Narud": "纳鲁德",
    "Horner": "霍纳", "Tosh": "托什", "Hanson": "汉森",
    "Warfield": "沃菲尔德", "Valerian1": "瓦莱里安1",
}

NAMES = {
    "Dalaran": "达拉然", "Hearthstone": "炉石", "Jinara": "吉娜拉",
    "Aiur": "艾尔", "Shakuras": "夏库拉斯", "Ulnar": "乌纳",
    "Moebius": "莫比乌斯", "Umoja": "乌莫贾", "Kaldir": "卡尔迪尔",
    "Skygeirr": "天矛", "Blizzcon": "暴雪嘉年华", "Blizzard": "暴雪",
    "Diablo": "暗黑破坏神", "Overwatch": "守望先锋",
    "Starcraft": "星际争霸", "Sc2": "星际争霸2",
}

# War3 四字代号 / 素材缩写 / 内部标识: 保持原样
KEEP_RE = [
    r"^[NnHhOoUuEe][a-z]{2,3}$",      # war3 objectid: Nhs Osh Uds Hca ...
    r"^Asp[0-9a-z]$",
]
KEEP = ["z", "e", "n", "p", "i", "c", "Mar", "Lp", "normal", "diffuse", "loop",
        "ebal", "Icl", "Ccl", "Cfs", "Nfs", "Nhs", "Osh", "Esh", "Nhw", "Ohw",
        "Uds", "Oob", "Aspp", "Asps", "Sra", "Ho", "Me", "Abof", "Nia", "Nab",
        "Cmp", "Ndh", "Udc", "Hca", "Asta", "Nba", "Ntm", "Cbf", "Osw", "Hblm",
        "Hamg", "Dom", "Nst", "Hmt", "Nrf", "Cbc", "Oae", "Chv", "Ows", "Npa",
        "Rrs", "Itp", "Ohx", "Aens", "Cdc", "Nfa", "Hfa", "Owk", "Imt", "Esv",
        "Ost", "Eah", "Nbf", "Ncs", "Nvc", "Uni", "Re", "Nic", "Osw1"]


def main():
    with io.open(DICT, encoding="utf-8") as f:
        d = json.load(f)
    sfx, prop = d["suffix"], d["proper"]
    n = 0
    for k, v in WORDS.items():
        if k not in sfx and k not in prop:
            sfx[k] = v
            n += 1
    m = 0
    for k, v in NAMES.items():
        if k not in prop and k not in sfx:
            prop[k] = v
            m += 1
    # 代号: 保留原样
    toks = [l.split("\t")[0] for l in
            io.open(r"e:\Code\sc2\Work\_tokens.txt", encoding="utf-8")
            .read().splitlines() if "\t" in l]
    keep = set(KEEP)
    pats = [re.compile(p) for p in KEEP_RE]
    for t in toks:
        for p in pats:
            if p.match(t):
                keep.add(t)
                break
    k = 0
    for t in sorted(keep):
        if t not in sfx and t not in prop:
            prop[t] = t
            k += 1
    with io.open(DICT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("+%d 词, +%d 专名, +%d 保留代号" % (n, m, k))
    print("suffix=%d proper=%d" % (len(sfx), len(prop)))


if __name__ == "__main__":
    main()
