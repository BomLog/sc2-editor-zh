#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""批量词条 第三批 —— 被误判为代号的真英文词 + 20 次以下长尾。
FORCE 里的键强制覆盖(用来纠正之前"原样保留"的错误)。
"""
import io
import json

DICT = r"e:\Code\sc2\Work\l10n_dict.json"

# 之前被 KEEP 规则误留成原文的真英文词, 强制改成中文
FORCE = {
    "East": "东", "West": "西", "North": "北", "South": "南",
    "Easy": "简单", "Echo": "回声", "Edge": "边缘", "Edit": "编辑",
    "Eel": "鳗", "Eggs": "卵", "Ele": "元素", "Elec": "电",
    "Elm": "榆", "Emp": "EMP", "Eng": "引擎", "Ent": "树人",
    "Enum": "枚举", "Epic": "史诗", "Eta": "伊塔", "Euro": "欧陆",
    "Evac": "撤离", "Evis": "剖膛", "Exo": "外骨骼", "Exp": "经验",
    "Ext": "外部", "Eyes": "眼", "Hack": "入侵", "Halo": "光环",
    "Hat": "帽", "Hay": "干草", "Haze": "霾", "Hazy": "朦胧",
    "Hear": "听闻", "Heat": "热", "Hell": "地狱", "Helm": "头盔",
    "Hemi": "半", "Herc": "大力神", "Hex": "妖术", "Hey": "嘿",
    "Hint": "提示", "Hire": "雇用", "Hiss": "嘶声", "Hits": "命中",
    "Holy": "神圣", "Home": "家园", "Hood": "罩", "Hoof": "蹄",
    "Hook": "钩", "Hose": "软管", "Howl": "嚎叫", "Hull": "船体",
    "Humn": "人类", "Hurl": "投掷", "Hvy": "重型", "Name": "名称",
    "Neo": "新", "Neon": "霓虹", "Net": "网", "News": "新闻",
    "Next": "下一", "None": "无", "Nor": "或非", "Norm": "标准",
    "Note": "便条", "Now": "现在", "Null": "空", "Oil": "石油",
    "Old": "旧", "Opac": "不透明度", "Orbs": "宝珠", "Ouch": "哎哟",
    "Ult": "终极", "Undo": "撤销", "Uni": "通用", "Urn": "骨灰坛",
    "Ursa": "熊", "User": "用户", "Uses": "使用次数", "Mar": "玛尔",
    "Dom": "自治领", "Nova1": "诺娃1",
    "diffuse": "漫反射", "emp": "EMP", "eye": "眼", "has": "拥有",
    "head": "头", "her": "她", "hits": "命中", "loop": "循环",
    "norm": "标准", "normal": "普通", "nova": "诺娃", "nuke": "核弹",
    "off": "关", "open": "打开", "uber": "超级", "low": "低",
    "research": "研究", "upgrade1": "升级1", "upgrade2": "升级2",
    "briefing": "任务简报", "newsreport": "新闻报道",
    "location": "位置", "video": "视频", "cmd": "命令",
    "covertops": "隐秘行动", "terranarmory": "人类军械库",
    "scboy": "scboy",
}

WORDS = {
    # 长尾: 20 次以下
    "Ghost": "幽灵", "Druidofthe": "德鲁伊", "Revivable": "可复活",
    "Facing": "朝向", "Morphing": "变形中", "Ripple": "涟漪",
    "Starter": "初始", "Expire": "到期", "Harass": "骚扰",
    "Type": "类型", "Symb": "共生", "Capacity": "容量",
    "Backpack": "背包", "Patrol": "巡逻", "Summer": "夏季",
    "Gnoll": "豺狼人", "Reverb": "混响", "Resistant": "抗性",
    "Replenish": "补充", "Abolish": "消除", "Agility": "敏捷",
    "Ill": "疾病", "Bullet": "子弹", "Animate": "活化",
    "Turtle": "龟", "Cen": "半人马", "Ordnance": "军械",
    "Entangle": "缠绕", "Totem": "图腾", "Change": "变更",
    "Exploration": "探索", "Crater": "弹坑", "Drift": "漂移",
    "Penetrating": "穿透", "Fleetwide": "全舰队", "Corrupted": "腐化",
    "Footstep": "脚步", "Cap": "上限", "Containment": "收容",
    "Deadly": "致命", "Fish": "鱼", "Khaydarin": "凯达琳",
    "Objective": "目标", "Current": "当前", "Premium": "高级",
    "Support": "支援", "Michael": "迈克尔", "Possession": "夺魂",
    "Whirlwind": "旋风", "Concentrated": "集中", "Voodoo": "巫毒",
    "Invisibility": "隐形", "Travel": "传送", "Visor": "护目镜",
    "Searchlight": "探照灯", "Clan": "氏族", "Rough": "粗糙",
    "Enhanced": "强化", "Snake": "蛇", "Color": "颜色",
    "Behemoth": "巨兽", "Kasai": "卡萨伊", "Plasma": "等离子",
    "Call": "召唤", "Walker": "行者", "Thorn": "刺", "Pick": "选取",
    "Third": "第三", "Transient": "瞬态", "Busy": "忙碌",
    "Immune": "免疫", "Immunity": "免疫", "Immuneto": "免疫",
    "Vanguard": "先锋", "Collector": "收藏家", "Edition": "版本",
    "Murloc": "鱼人", "Uproot": "拔起", "Underground": "地下",
    "Classic": "经典", "Personal": "个人", "Cold": "冰冷",
    "Evasion": "闪避", "Burning": "燃烧", "Polymorph": "变形术",
    "Obsidian": "黑曜石", "Disenchant": "解除法术", "Reckless": "鲁莽",
    "Key": "钥匙", "Side": "侧", "Cliffs": "悬崖", "Railgun": "磁轨炮",
    "Amorphous": "无形", "Armorcloud": "护甲云", "Rumble": "轰鸣",
    "State": "状态", "Nebula": "星云", "Ultimate": "终极",
    "Resurgence": "复苏", "Direct": "直接", "Face": "面",
    "Arcs": "弧", "Library": "图书馆", "Escape": "逃脱",
    "Allow": "允许", "Copy": "复制", "Lances": "长枪",
    "Initialize": "初始化", "Immortality": "不朽", "Centaur": "半人马",
    "Brand": "烙印", "Villager": "村民", "Dies": "死亡",
    "Wedges": "楔形", "Critical": "致命", "Resurrection": "复活",
    "Shots": "射击", "Liquid": "液体", "Tranquility": "宁静",
    "Region": "区域", "Gem": "宝石", "Cart": "车", "Heart": "心",
    "Response": "回应", "Constant": "恒定", "Multiplayer": "多人",
    "Crack": "裂痕", "Cracks": "裂痕", "Cracked": "破裂",
    "Conduit": "导管", "Trim": "镶边", "Trims": "镶边",
    "Tornadoes": "旋风", "Docking": "停靠", "Sweep": "扫荡",
    "Maelstrom": "大漩涡", "Natural": "自然", "Virus": "病毒",
    "Breaker": "破坏者", "Moving": "移动中", "Harpy": "鹰身女妖",
    "Koto": "古筝", "Best": "最佳", "Escorts": "护卫",
    "Imperial": "帝国", "Propagate": "传播", "Punisher": "惩罚者",
    "Dialog": "对话框", "Scouting": "侦察", "Ascension": "扬升",
    "Clap": "掌声", "Banish": "放逐", "Pilot": "驾驶员",
    "Data": "数据", "Dominance": "支配", "Reentry": "再入",
    "Brazier": "火盆", "Empowered": "已强化", "Asteroid": "小行星",
    "Helper": "辅助", "Strafer": "扫射机", "Piece": "件",
    "Plants": "植物", "Concrete": "混凝土", "Flood": "洪流",
    "Scanner": "扫描器", "Subway": "地铁", "Central": "中央",
    "Hornet": "黄蜂", "Tap": "轻击", "Unity": "统一",
    "Commando": "突击队", "Unique": "唯一", "Being": "存在",
    "Inject": "注入", "Mandate": "授权", "Cooldowns": "冷却",
    "Gravitic": "重力", "Jessica": "杰西卡", "Scripted": "脚本",
    "Tendril": "触须", "Reinforced": "强化", "Glyph": "符文",
    "Feral": "野性", "Drunken": "醉拳", "Colony": "巢群",
    "Wormhole": "虫洞", "Book": "书", "Detonate": "引爆",
    "Dome": "穹顶", "Wander": "游荡", "Felblaze": "邪焰",
    "Kills": "击杀数", "Play": "播放", "Explosive": "爆炸",
    "Curb": "路缘", "Attached": "已附着", "Clouds": "云",
    "Angled": "斜角", "Origin": "原点", "Blinding": "致盲",
    "Barrel": "桶", "Windy": "多风", "Replenishment": "补充",
    "Clockwork": "机械", "Supplies": "补给", "Bones": "骨",
    "Magical": "魔法", "Broadside": "舷炮", "Channeled": "引导",
    "Galleon": "帆船", "Kaiser": "凯撒", "Wyrm": "巨龙",
    "Static": "静态", "Before": "之前", "Fate": "命运",
    "Moveto": "移动至", "Ion": "离子", "Ares": "阿瑞斯",
    "Eternity": "永恒", "Thanks": "感谢", "Zurvan": "祖尔万",
    "Whoosh": "呼啸", "Flashback": "闪回", "Targetis": "目标为",
    "Contour": "轮廓", "Skins": "皮肤", "Chest": "箱",
    "Invitational": "邀请赛", "Inventory": "物品栏", "Reborn": "重生",
    "Cat": "猫", "Collapsed": "已倒塌", "Arcane": "秘法",
    "Couple": "对", "Thorny": "多刺", "Ancestral": "先祖",
    "Diabolus": "迪亚布罗斯", "Footprint2x2": "占地2x2",
    "Wedges4x4": "楔形4x4", "Stetellite": "斯台特卫星",
    "Ghost1": "幽灵1", "Ghost2": "幽灵2", "Revivable0": "可复活0",
    "Revivable2": "可复活2", "Immortal": "不朽者",
    "Hellion": "恶火", "Chest1": "箱1", "Chest3": "箱3",
}


def main():
    with io.open(DICT, encoding="utf-8") as f:
        d = json.load(f)
    sfx, prop = d["suffix"], d["proper"]
    f_n = 0
    for k, v in FORCE.items():
        prop.pop(k, None)
        if sfx.get(k) != v:
            f_n += 1
        sfx[k] = v
    n = 0
    for k, v in WORDS.items():
        if k not in sfx and k not in prop:
            sfx[k] = v
            n += 1
    with io.open(DICT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("强制修正 %d, 新增 %d -> suffix=%d proper=%d"
          % (f_n, n, len(sfx), len(prop)))


if __name__ == "__main__":
    main()
