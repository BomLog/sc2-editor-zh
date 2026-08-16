#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
批量词条 —— 按 _tokens.txt 词频从高到低人工翻译, 合并进 l10n_dict.json。
只补新键, 不覆盖已有值(所以可以反复跑)。

分组:
  WORDS   普通词/用途词 -> suffix
  NAMES   专有名词(人名/地名/势力/主播名)-> proper
  KEEP    保持原样的缩写与代号(不翻, 但标记为已识别, 不再计入残留)
"""
import io
import json
import os

DICT = r"e:\Code\sc2\Work\l10n_dict.json"

WORDS = {
    # ---- 逻辑/结构词(Requirement / Validator 里大量出现) ----
    "Count": "计数", "Complete": "完成", "Only": "仅", "Or": "或", "Not": "非",
    "And": "与", "Have": "拥有", "Has": "拥有", "Is": "是", "Of": "的",
    "At": "于", "To": "至", "By": "由", "For": "用于", "The": "",
    "Any": "任意", "All": "全部", "So": "故", "Do": "执行", "Use": "使用",
    "Better": "更优", "Greater": "更高", "Lesser": "较低", "More": "更多",
    "Need": "需要", "Needed": "需要", "Yes": "是", "No": "否",
    "Queued": "已排队", "Under": "低于", "Over": "高于", "Non": "非",
    "Total": "总计", "Sum": "合计", "Half": "半", "Full": "完整",
    "Max": "最大", "Min": "最小", "Initial": "初始", "Final": "最终",
    "First": "第一", "Second": "第二", "One": "一", "Two": "二", "Nine": "九",
    "Primary": "主", "Secondary": "副", "Alternate": "备用", "Alt": "备用",
    "Extra": "额外", "Bonus": "加成", "Free": "免费", "Self": "自身",
    "Active": "激活", "Empty": "空", "Fake": "虚假", "Real": "真实",
    "Random": "随机", "Custom": "自定义", "Generic": "通用", "Special": "特殊",
    "New": "新", "Add": "添加", "Apply": "应用", "Modify": "修改",
    "Check": "检查", "Filter": "筛选", "Filters": "筛选", "Select": "选取",
    "Choice": "选项", "Order": "命令", "Issue": "下达", "Event": "事件",
    "Source": "源", "Object": "对象", "Obj": "目标", "Alias": "别名",
    "Part": "部件", "Parts": "部件", "Group": "组", "Table": "表",
    "Pattern": "模式", "Mode": "模式", "Rank": "等级", "Tier": "阶",
    "Rate": "速率", "Cost": "花费", "Value": "值", "Amount": "数量",
    "Chance": "概率", "Duration": "持续时间", "Delay": "延迟",
    "Timer": "计时器", "Timed": "定时", "Time": "时间", "Cooldown": "冷却",
    "Countdown": "倒计时", "Progress": "进度", "Done": "完成",
    "Fail": "失败", "Lose": "失败", "Lost": "已失去", "Found": "已找到",
    "Victory": "胜利", "Defeat": "失败", "Survive": "存活",
    "Start": "开始", "Starting": "起始", "Early": "早期", "End": "结束",
    "Finish": "完成", "Return": "返回", "Restore": "恢复", "Reset": "重置",
    "Pause": "暂停", "Paused": "已暂停", "Resumed": "已恢复",
    "Open": "打开", "Opened": "已打开", "Close": "关闭", "Closed": "已关闭",
    "Lock": "锁定", "Locked": "已锁定", "Unlock": "解锁",
    "Used": "已使用", "Given": "已给予", "Capped": "已达上限",
    "Interrupt": "打断", "Cancel": "取消", "Switch": "切换",
    "Increase": "提升", "Reduction": "削减", "Efficiency": "效率",
    "Yield": "产出", "Store": "存储", "Carry": "携带", "Mix": "混音",
    "Look": "查看", "Display": "显示", "Show": "显示", "Hide": "隐藏",
    "Text": "文本", "Image": "图像", "Icon": "图标", "Menu": "菜单",
    "Screen": "界面", "Screens": "界面", "Panel": "面板", "Help": "帮助",
    "Learn": "学习", "What": "什么", "Where": "何处",

    # ---- 战斗 / 技能 ----
    "Attack": "攻击", "Attacks": "攻击", "Melee": "近战", "Ranged": "远程",
    "Damage": "伤害", "Damaged": "已受损", "Blast": "爆破", "Burst": "爆发",
    "Strike": "打击", "Strikes": "打击", "Shot": "射击", "Shoot": "射击",
    "Barrage": "弹幕", "Artillery": "火炮", "Cannons": "火炮",
    "Missiles": "导弹", "Rocket": "火箭", "Rockets": "火箭",
    "Grenade": "手雷", "Grenades": "手雷", "Bomb": "炸弹", "Bombing": "轰炸",
    "Explo": "爆炸", "Detonation": "引爆", "Shockwave": "冲击波",
    "Laser": "激光", "Ray": "射线", "Bolt": "闪电束", "Lightning": "闪电",
    "Storm": "风暴", "Storms": "风暴", "Thunder": "雷霆",
    "Thunderous": "雷鸣", "Wind": "风", "Rain": "雨", "Frost": "冰霜",
    "Frozen": "冰冻", "Burn": "燃烧", "Flamethrower": "喷火器",
    "Firebreath": "火焰吐息", "Breath": "吐息", "Acid": "酸液",
    "Caustic": "腐蚀性", "Corrosive": "腐蚀", "Toxic": "剧毒",
    "Poison": "毒素", "Plague": "瘟疫", "Blight": "枯萎",
    "Slime": "黏液", "Bile": "胆液", "Spore": "孢子", "Spores": "孢子",
    "Fungal": "菌类", "Growth": "生长", "Vines": "藤蔓",
    "Entangling": "缠绕", "Snare": "陷网", "Trap": "陷阱",
    "Roots": "根须", "Thorns": "尖刺", "Spike": "尖刺", "Spiked": "带刺",
    "Claw": "利爪", "Blade": "刀刃", "Blades": "刀刃", "Knives": "飞刀",
    "Glaive": "利刃", "Bladestorm": "剑刃风暴", "Swipe": "横扫",
    "Stab": "突刺", "Bash": "猛击", "Stomp": "践踏", "Push": "推进",
    "Pusher": "推进器", "Bounce": "弹跳", "Leap": "跃击", "Jump": "跳跃",
    "Jumper": "跳跃器", "Dash": "冲刺", "Charges": "充能",
    "Chain": "连锁", "Arrows": "箭矢", "Rifle": "步枪", "Shotgun": "霰弹枪",
    "Sniper": "狙击手", "Gunner": "枪手", "Munitions": "弹药",
    "Payload": "载荷", "Warhead": "弹头", "Silence": "沉默",
    "Stun": "眩晕", "Snipe": "狙杀", "Eviscerate": "剖膛",
    "Immolation": "献祭", "Searing": "灼烧", "Chaos": "混乱",
    "Unholy": "邪恶", "Evil": "邪恶", "Hostile": "敌对", "Friendly": "友好",
    "Allied": "友方", "Neutral": "中立", "Threat": "威胁",
    "Defense": "防御", "Defensive": "防御", "Barrier": "屏障",
    "Shields": "护盾", "Armors": "护甲", "Plates": "装甲板",
    "Invulnerability": "无敌", "Absorb": "吸收", "Empower": "强化",
    "Haste": "急速", "Rapid": "急速", "Slow": "减速", "Regen": "恢复",
    "Regeneration": "恢复", "Healing": "治疗", "Mend": "修补",
    "Repaired": "已修理", "Respawn": "重生", "Revive": "复活",
    "Reincarnation": "转生", "Die": "死亡", "Dead": "死亡",
    "Corpse": "尸体", "Wreckage": "残骸", "Wrecked": "已损毁",
    "Rubble": "碎砾", "Scrap": "废料", "Ruined": "废墟",
    "Broken": "破损", "Scorched": "焦土", "Crashing": "坠毁",
    "Collapsing": "倒塌", "Takeover": "接管", "Purge": "清除",
    "Destruction": "破坏", "Killer": "击杀者", "Kill": "击杀",
    "Overload": "过载", "Unstable": "不稳定", "Volatile": "易爆",
    "Crit": "暴击", "Strength": "力量", "Endurance": "耐力",
    "Fury": "怒气", "Bloodlust": "嗜血", "Warcry": "战吼",
    "Roar": "咆哮", "Guard": "守卫", "Stand": "驻守", "Hold": "保持",
    "Holding": "保持", "Escort": "护送", "Rescued": "已营救",
    "Superiority": "优势", "Champion": "勇士", "Heroic": "英雄",
    "Master": "大师", "Mastery": "精通", "Prestige": "威望",
    "Talent": "天赋", "Feat": "功勋", "Achievement": "成就",
    "Promotion": "晋升", "Veterancy": "老兵",

    # ---- 单位 / 兵种 / 载具 ----
    "Commander": "指挥官", "Trooper": "士兵", "Infantry": "步兵",
    "Merc": "雇佣兵", "Mercenary": "雇佣兵", "Worker": "工人",
    "Workers": "工人", "Miner": "矿工", "Harvester": "采集者",
    "Guardian": "守护者", "Keeper": "守护者", "Warden": "守望者",
    "Ranger": "游侠", "Rider": "骑手", "Raider": "掠夺者",
    "Destroyer": "毁灭者", "Dominator": "支配者", "Warbringer": "战争使者",
    "Seeker": "追猎者", "Tracker": "追踪者", "Hound": "猎犬",
    "Bot": "机器人", "Robot": "机器人", "Robotics": "机械",
    "Mech": "机甲", "Mechanic": "机械师", "Mechanical": "机械",
    "Vehicle": "载具", "Tripod": "三足机", "Servo": "伺服",
    "Construct": "构造体", "Golem": "魔像", "Monster": "怪物",
    "Beast": "野兽", "Worm": "巨虫", "Wurm": "亚龙", "Serpent": "巨蛇",
    "Dragon": "巨龙", "Giant": "巨人", "Elemental": "元素",
    "Angel": "天使", "Elf": "精灵", "Nightelf": "暗夜精灵",
    "Elven": "精灵", "Troll": "巨魔", "Goblin": "地精", "Junker": "破烂客",
    "Pirate": "海盗", "Bully": "恶霸", "Officer": "军官",
    "Doctor": "博士", "Priestess": "女祭司", "Witch": "巫医",
    "Tinkerer": "修补匠", "Brewmaster": "酒仙", "Druid": "德鲁伊",
    "Mage": "法师", "Wiz": "术士", "Lord": "领主", "King": "国王",
    "Royal": "皇家", "Council": "议会", "Leaders": "领袖",
    "Army": "部队", "Forces": "部队", "Fleet": "舰队", "Squad": "小队",
    "Ship": "舰船", "Cruiser": "巡洋舰", "Vessel": "舰船",
    "Transport": "运输", "Flyer": "飞行器", "Bomber": "轰炸机",
    "Jet": "喷气", "Airstrike": "空袭", "Airlift": "空运",
    "Cluster": "集群", "Swarm": "虫群", "Brood": "虫群",
    "Broodlings": "小狗", "Cocoon": "蛹", "Symbiote": "共生体",
    "Host": "宿主", "Parasite": "寄生虫", "Parasitic": "寄生",
    "Crawler": "爬虫", "Spine": "脊针", "Creeper": "菌毯",
    "Biomass": "生物质", "Essence": "精华", "Gene": "基因",
    "Evolve": "进化", "Evolution": "进化", "Evo": "进化",
    "Metamorphosis": "变形", "Morphed": "已变形", "Morphto": "变形为",
    "Primal": "原生", "Ancient": "远古", "Sliver": "裂片",
    "Tyrannozor": "暴虐龙", "Apocalisk": "天启虫", "Gorgon": "蛇发女妖",
    "Widow": "寡妇", "Warhound": "战犬", "Interceptors": "拦截机",
    "Drill": "钻机", "Nest": "巢", "Den": "巢穴", "Pool": "池",
    "Warren": "兽穴", "Academy": "学院", "Armory": "军械库",
    "Depot": "补给站", "Bay": "舱", "Dock": "码头", "Docked": "已停靠",
    "Station": "站", "Facility": "设施", "Engineering": "工程",
    "Production": "生产", "Supply": "补给", "Cargo": "货物",
    "Crate": "板条箱", "Crates": "板条箱", "Parcel": "包裹",
    "Pod": "舱", "Pods": "舱", "Tube": "管", "Capsule": "舱",

    # ---- 资源 / 经济 ----
    "Minerals": "晶矿", "Mineral": "晶矿", "Vespene": "瓦斯",
    "Geyser": "气泉", "Gold": "金", "Credits": "点数", "Econ": "经济",
    "Food": "食物", "Lumber": "木材", "Metal": "金属", "Stone": "石",
    "Terrazine": "泰伦晶矿", "Biscuit": "饼干", "Trade": "交易",
    "Exhausted": "已耗尽", "Depleted": "枯竭", "Bounty": "赏金",

    # ---- 科技 / 升级 ----
    "Tech": "科技", "Upgrades": "升级", "Upgraded": "已升级",
    "Improved": "改良", "Advanced": "高级", "Super": "超级",
    "Equipment": "装备", "Eq": "装备", "Gadget": "装置",
    "Matrix": "矩阵", "Network": "网络", "Networked": "已联网",
    "Battery": "充能器", "Charged": "已充能", "Recharge": "再充能",
    "Solar": "太阳能", "Thermal": "热能", "Fusion": "聚变",
    "Electric": "电", "Magnetic": "磁", "Graviton": "重力子",
    "Temporal": "时间", "Chrono": "时空", "Phase": "相位",
    "Phasing": "相位", "Prism": "棱镜", "Lens": "透镜",
    "Sonar": "声纳", "Sensor": "传感器", "Detection": "探测",
    "Detector": "探测器", "Sighted": "已发现", "Vision": "视野",
    "Cloaked": "已隐形", "Cloaking": "隐形", "Unpowered": "无能量供应",
    "Controller": "控制器", "Control": "控制", "Ncontrol": "控制",
    "Automation": "自动化", "Auto": "自动", "Manual": "手动",

    # ---- 地形 / 场景 / 建筑 ----
    "Structure": "建筑", "Citybuilding": "城市建筑", "Hall": "大厅",
    "Town": "城镇", "Village": "村庄", "Capital": "首都",
    "Mansion": "宅邸", "Altar": "祭坛", "Tome": "典籍", "Rune": "符文",
    "Archway": "拱门", "Arch": "拱", "Pillar": "石柱", "Fence": "栅栏",
    "Walls": "墙", "Floor": "地板", "Ramp": "坡道", "Road": "道路",
    "Path": "路径", "Canal": "运河", "Elevator": "升降机",
    "Airlock": "气闸", "Courtyard": "庭院", "Pit": "坑",
    "Tunnel": "隧道", "Tunneling": "掘进", "Caverns": "洞穴",
    "Cave": "洞穴", "Mountain": "山", "Hill": "丘", "Rocks": "岩石",
    "Dirt": "泥土", "Grass": "草地", "Flora": "植被", "Plant": "植物",
    "Desert": "沙漠", "Winter": "冬季", "Moon": "月",
    "Night": "夜", "Day": "日", "Sky": "天空", "Planet": "行星",
    "Sea": "海", "Aquatic": "水生", "Abandoned": "废弃",
    "Floating": "漂浮", "Rotating": "旋转", "Extending": "伸展",
    "Diagonal": "对角", "Horizontal": "水平", "Vertical": "垂直",
    "Straight": "直", "Thin": "细", "Tall": "高", "Wide": "宽",
    "Mid": "中", "Far": "远", "Nearby": "附近", "Distance": "距离",
    "Corner": "角", "Column": "列", "Marker": "标记",
    "Sign": "标牌", "Signs": "标牌", "Figurine": "小雕像",
    "Fireworks": "烟火", "Crowd": "人群", "Ambience": "环境音",
    "Amb": "环境", "Background": "背景", "Ambient": "环境",
    "Traffic": "交通", "Car": "汽车", "Tram": "有轨电车",
    "Train": "训练", "Training": "训练", "Wrangler": "牧马人",

    # ---- 音频 / 视觉 / 引擎 ----
    "Sound": "音效", "Stereo": "立体声", "Speakermix": "扬声器混音",
    "Foley": "拟音", "Theme": "主题曲", "Cine": "过场", "Cutscene": "过场动画",
    "Intro": "开场", "Outro": "结尾", "Video": "视频", "Briefing": "任务简报",
    "Debrief": "任务总结", "Narrator": "旁白", "Responses": "回应",
    "Communication": "通讯", "Comm": "通讯", "Genericphrases": "通用语句",
    "Holo": "全息", "Hologram": "全息", "Flash": "闪光",
    "Lights": "灯光", "Glow": "辉光", "Cloud": "云", "Fog": "迷雾",
    "Dust": "尘土", "Steam": "蒸汽", "Vent": "排气口", "Thud": "闷响",
    "Ack": "应答", "Alert": "警报", "Warning": "警告", "Ping": "标记",
    "Click": "点击", "Directional": "定向", "Directed": "定向",
    "Fade": "淡出", "Mirror": "镜像", "Rotate": "旋转",
    "Scale": "缩放", "Height": "高度", "Long": "长", "Short": "短",
    "Big": "大", "Deep": "深", "Heavy": "重型", "Massive": "重型",
    "Mono": "单声道", "Hdr": "HDR", "Vx": "特效", "Fx": "特效",

    # ---- 游戏模式 / 元素 ----
    "Game": "游戏", "Map": "地图", "Match": "对局", "League": "联赛",
    "Season": "赛季", "Challenge": "挑战", "Challengescombined": "挑战合集",
    "Tutorial": "教程", "Prologue": "序章", "Mission": "任务",
    "Expedition": "远征", "Campaign": "战役", "Battle": "战斗",
    "War": "战争", "Battleground": "战场", "Arena": "竞技场",
    "Solo": "单人", "Single": "单人", "Coop": "合作",
    "Mutation": "突变", "Mutator": "突变因子", "Mutant": "变异体",
    "Bundle": "捆绑包", "Collection": "合集", "Pack": "包",
    "Reward": "奖励", "Trophy": "奖杯", "Emoticon": "表情",
    "Skin": "皮肤", "Deluxe": "豪华", "Console": "控制台",
    "Profile": "档案", "Bnet": "战网", "Cheat": "秘籍",
    "Ops": "行动", "Op": "行动", "Covert": "隐秘", "Tactical": "战术",
    "Utility": "功能", "Mod": "模组", "Meta": "元", "Sports": "竞技",
    "Gaming": "游戏", "Turkey": "火鸡", "Boom": "轰",
    "Bombing1": "轰炸1", "Wave": "波次", "Waves": "波次",
    "Spawner": "生成器", "Spawning": "生成", "Summoned": "已召唤",
    "Persistent": "持续", "Instant": "瞬间", "Fast": "快速",
    "Quick": "快速", "Double": "双", "Single1": "单1",
    "Acceleration": "加速", "Speed": "速度", "Fly": "飞行",
    "Walk": "行走", "Landing": "着陆", "Transit": "运输",
    "Calldown": "呼叫", "Recall": "召回", "Recalling": "召回中",
    "Drop": "投放", "Deployed": "已部署", "Deploy": "部署",
    "Unload": "卸载", "Load": "装载", "Stack": "叠加",
    "Sieged": "攻城模式", "Burrowed": "已钻地", "Uprooted": "已拔起",
    "Lowered": "已降下", "Raised": "已升起", "Attach": "附着",
    "Combine": "合并", "Merge": "合并", "Transfer": "转移",
    "Delivery": "投送", "Link": "链接", "Grip": "抓握",
    "Grab": "抓取", "Carry1": "携带1", "Body": "躯体", "Tail": "尾",
    "Eye": "眼", "Arm": "臂", "Cell": "细胞", "Life": "生命",
    "Mana": "法力", "Psi": "灵能", "Mind": "心智", "Neural": "神经",
    "Spells": "法术", "Abilities": "技能", "Magic": "魔法",
    "Cast": "施法", "Channeling": "引导中", "Disruption": "干扰",
    "Inhibitor": "抑制器", "Interference": "干扰",
    "Purification": "净化", "Purify": "净化",
}

NAMES = {
    # 人物
    "Hyperion": "许珀里翁", "Xanthos": "桑索斯", "Aleksander": "亚历山大",
    "Reigel": "雷格尔", "Grom": "格罗姆", "Hellscream": "地狱咆哮",
    "Murvar": "穆瓦", "Jarban": "贾班", "Dakrun": "达克伦",
    "Kaldalis": "卡尔达利斯", "Glevig": "格莱维格", "Taldarin": "塔达林",
    "Clolarion": "克洛拉瑞恩", "Morian": "莫里安", "Folsom": "福尔松",
    "Davis": "戴维斯", "Mojo": "魔咒", "Gary": "加里", "Mira": "米拉",
    "Sara": "萨拉", "Valerian": "瓦莱里安", "Nef": "耐法",
    "Lordaeron": "洛丹伦", "Sgt": "中士", "Mr": "先生",
    # 地名 / 势力
    "Char": "查尔", "Korhal": "克哈", "Braxis": "布拉希斯",
    "Tarsonis": "塔桑尼斯", "Zhakul": "扎库尔", "Shir": "希尔",
    "Belshir": "贝尔希尔", "Bel": "贝尔", "Zion": "锡安",
    "Twilight": "黄昏", "Frontiers": "边疆", "Liberty": "自由",
    "Xelnaga": "泽尔纳加", "Kel": "凯尔", "Adun": "阿顿",
    "Warcraft": "魔兽争霸", "War3": "魔兽争霸3", "Hots": "虫群之心",
    "Prison": "监狱", "World": "世界", "Earth": "地球",
    "Junkyard": "废料场", "Park": "公园", "Science": "科研",
    # 主播 / 社区名(保留音译或原名)
    "Webby": "Webby", "Lowko": "Lowko", "Nathanias": "Nathanias",
    "Tastosis": "Tastosis", "Day9": "Day9", "Alex007": "Alex007",
    "Scboy": "scboy", "Jeon": "Jeon", "Kim": "Kim", "Sheng": "Sheng",
    "Pomf": "Pomf", "Qo": "Qo", "Thos": "Thos", "Uls": "Uls",
    "Ols": "Ols", "Nin": "Nin", "Omi": "Omi", "Das": "Das",
}

# 保持原样但视为已识别(缩写 / 内部代号 / 素材前缀)
KEEP = ["ac", "cmd", "vp", "war3", "covertops", "terranarmory", "location",
        "video", "cliff0", "cliff1", "Ttw", "Ttc", "Nvc", "Ncl", "Ocl",
        "Nlm", "Rrk", "Acef", "Uim", "Ndc", "Hfs", "Hex", "Mag", "Mv",
        "Ao", "Ra", "Va", "Um", "Pn", "Eq2", "5dot1", "EVENT", "PLAYER",
        "FOLEY", "Sar", "Robo", "Explo1", "Nine1"]


def main():
    with io.open(DICT, encoding="utf-8") as f:
        d = json.load(f)
    sfx, prop = d.setdefault("suffix", {}), d.setdefault("proper", {})
    n_w = n_n = n_k = 0
    for k, v in WORDS.items():
        if k not in sfx:
            sfx[k] = v
            n_w += 1
    for k, v in NAMES.items():
        if k not in prop:
            prop[k] = v
            n_n += 1
    for k in KEEP:
        if k not in prop and k not in sfx:
            prop[k] = k
            n_k += 1
    with io.open(DICT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("合并完成: +%d 普通词, +%d 专名, +%d 保留代号" % (n_w, n_n, n_k))
    print("现有 suffix=%d, proper=%d" % (len(sfx), len(prop)))


if __name__ == "__main__":
    main()
