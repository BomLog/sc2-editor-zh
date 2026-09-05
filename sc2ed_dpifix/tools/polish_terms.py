# -*- coding: utf-8 -*-
"""Full-table polish dictionaries for the SC2 editor localization.

applied by tools/apply_polish.py to every value in OfficialDependencyNames.tsv
(id + @display sections).  Rules are idempotent: once a value is polished the
same pass leaves it unchanged, so re-running after a CASC regen is safe.

Buckets:
  UNIT_ZH      english token -> official zhCN term (checked against in-table usage)
  NAME_ZH      proper nouns / easter-egg characters
  WAR3_ZH      Warcraft-3 easter-egg unit vocabulary
  WORD_ZH      common english words left over by machine composition
  PHRASE_FIX   bad substring -> good replacement (word salad, function-word munges)
  VALUE_FIX    exact whole value -> fixed value (irrecoverable salads)
  KEEP_*       tokens intentionally left as-is (codes, retained abbreviations)
"""
import re

# ---------------------------------------------------------------- units
UNIT_ZH = {
    # protoss units / buildings (terms verified against table: 光影议会/黑暗圣坛/吸纳舱/分裂池...)
    "Zealot": "狂热者", "Stalker": "追猎者", "Sentry": "哨兵", "Adept": "使徒",
    "DarkTemplar": "黑暗圣堂武士", "HighTemplar": "高阶圣堂武士", "Templar": "圣堂武士",
    "Archon": "执政官", "DarkArchon": "黑暗执政官", "Immortal": "不朽者",
    "Colossus": "巨像", "Colossi": "巨像", "Disruptor": "干扰者", "Phoenix": "凤凰",
    "VoidRay": "虚空辉光舰", "Oracle": "预言者", "Tempest": "风暴战舰", "Carrier": "航母",
    "Mothership": "母舰", "Observer": "观察者", "WarpPrism": "折跃棱镜", "Probe": "探机",
    "Nexus": "枢纽", "PhotonCannon": "光子炮", "ShieldBattery": "护盾充能器",
    "Pylon": "水晶塔", "Gateway": "传送门", "WarpGate": "折跃门",
    "CyberneticsCore": "控制核心", "TwilightCouncil": "光影议会", "Forge": "锻炉",
    "Photon": "光子", "Assimilator": "吸纳舱", "RoboticsFacility": "机械台",
    "RoboticsSupportBay": "机械研究所", "TemplarArchive": "圣堂武士文献馆",
    "DarkShrine": "黑暗圣坛", "FleetBeacon": "舰队航标", "Forcefield": "力场",
    "Phasesmith": "相位匠", "Megalith": "巨石碑", "Tesseract": "四维巨石碑",
    "Monolith": "巨石碑", "WarpIn": "折跃", "Phasing": "相位", "Psionic": "灵能",
    # terran
    "Marine": "陆战队员", "Firebat": "喷火兵", "Marauder": "掠夺者", "Reaper": "死神",
    "Ghost": "幽灵", "Spectre": "幽灵特工", "Specter": "幽灵特工", "Battlecruiser": "战列巡航舰",
    "CommandCenter": "指挥中心", "OrbitalCommand": "轨道指挥中心",
    "PlanetaryFortress": "行星要塞", "SupplyDepot": "补给站", "Refinery": "精炼厂",
    "Barracks": "兵营", "Factory": "重工厂", "Starport": "星港",
    "EngineeringBay": "工程站", "Armory": "军械库", "MissileTurret": "导弹塔",
    "SensorTower": "传感器塔", "Bunker": "地堡", "TechLab": "科技实验室",
    "Reactor": "反应堆", "Cyclone": "旋风", "WidowMine": "寡妇雷", "Liberator": "解放者",
    "Viking": "维京战机", "Medivac": "医疗运输机", "Raven": "渡鸦", "Banshee": "女妖",
    "Thor": "雷神", "Hellion": "恶火", "Hellbat": "恶蝠", "SiegeTank": "攻城坦克",
    "Odin": "奥丁", "Dominate": "支配", "Grenade": "手雷", "Barrage": "弹幕",
    "Titan": "泰坦", "Transformer": "变形体", "Afterburner": "加力燃烧",
    "SpecialistDepot": "专精仓库", "AssaultDepot": "突击仓库", "Outpost": "前哨站",
    "ShootingDrone": "射击无人机", "Munition": "弹药", "Nanite": "纳米",
    "Transfusion": "输血", "Infestation": "感染", "Unpowered": "已断电",
    # zerg
    "Zergling": "跳虫", "Baneling": "爆虫", "Roach": "蟑螂", "Hydralisk": "刺蛇",
    "Infestor": "感染虫", "SwarmHost": "虫群宿主", "Locust": "蝗虫", "Ultralisk": "雷兽",
    "Overlord": "王虫", "Overseer": "眼虫", "Mutalisk": "飞龙", "Corruptor": "腐化者",
    "BroodLord": "虫群领主", "Broodling": "巢虫", "Viper": "飞蛇", "Queen": "虫后",
    "Devolve": "退化", "SpawningPool": "分裂池", "EvolutionChamber": "进化室",
    "RoachWarren": "蟑螂窝", "BanelingNest": "爆虫巢", "InfestationPit": "感染坑",
    "Spire": "尖塔", "GreaterSpire": "巨型尖塔", "UltraliskCavern": "雷兽窟",
    "Hatchery": "孵化场", "Lair": "兽穴", "Hive": "巢穴", "Nydus": "坑道",
    "Creep": "菌毯", "Transfusion": "输血",
    # generic combat / effect vocabulary
    "Beacon": "信标", "ReviveBeacon": "复活信标", "Portrait": "头像",
    "Projection": "投影", "Epilogue": "终章", "Celebration": "庆祝", "Room": "房间",
    "Heavens": "天堂", "Planets": "行星", "Trigger": "触发器", "Cannon": "火炮",
    "Prototype": "原型", "Devolve": "退化", "Ray": "射线", "Spinner": "旋臂",
    "Arrival": "抵达", "Redirect": "重定向", "Revealer": "显形者", "Duel": "决斗",
    "Uncloaked": "已显形", "Detector": "侦测器", "Diffusion": "扩散",
    "Armageddon": "末日审判", "Extinction": "灭绝", "Constriction": "束缚",
    "Nuclear": "核弹", "Thief": "窃贼", "Trapped": "被困", "Unstoppable": "势不可挡",
    "Unfinished": "未完工", "Unlimited": "无限", "Possessed": "被附身",
    "Suppressed": "被压制", "Recalled": "已召回", "Recalling": "召回中",
    "Activated": "已激活", "Dragged": "被拖拽", "Stopped": "已停止",
    "Raising": "升起", "Flagged": "已标记", "Warped": "已折跃", "Fired": "已开火",
    "Melt": "熔毁", "Spill": "泼溅", "Splat": "泼溅", "Blob": "团块",
    "Suplex": "过肩摔", "Uppercut": "上勾拳", "Karma": "业报", "Malignant": "恶性",
    "Sanitization": "净化", "Conductor": "导流体", "Prevention": "阻止",
    "Shooting": "射击", "Research": "研究", "Intro": "开场", "Combat": "战斗",
    "Construct": "构造体", "Platform": "平台", "Shop": "商店", "Roof": "屋顶",
    "Block": "阻挡", "Buy": "购买", "Fix": "修复", "Gear": "装备", "Kit": "装备包",
    "Load": "装载", "Unload": "卸载", "Transport": "运输", "Seeker": "追踪者",
    "Specialization": "专精", "Upgrade": "升级", "Tier": "层级", "Vet": "老兵",
    "Legendary": "传奇", "Minimum": "最小", "Maximum": "最大", "Equal": "等于",
    "Assign": "分配", "Markers": "标记", "Visual": "视觉", "Graphic": "图形",
    "Voice": "语音", "Tooltip": "悬浮说明", "Starfield": "星空", "Border": "边缘",
    "Wheel": "车轮", "Pedestal": "基座", "Spot": "地点", "Bottle": "瓶子",
    "Particles": "粒子", "Fluid": "流体", "Oil": "燃油", "Rad": "辐射",
    "Vulcan": "火神", "Strike": "打击", "Outlaw": "亡命徒", "Cavalry": "骑兵",
    "Grunt": "兽人步兵", "Civilian": "平民", "Civ": "平民", "Kid": "小孩",
    "Leg": "腿", "Biodome": "生物穹顶", "Skirt": "裙摆", "Braids": "辫子",
    "Sideways": "侧向", "Mapwide": "全图", "Psy": "灵能", "Vignette": "暗角",
    "Shakurus": "夏库拉斯", "Time": "时间", "Way": "路径", "Out": "结束",
    "Log": "日志", "Locks": "锁定", "Prep": "准备", "Center": "中心",
    "Kicker": "弹跳", "Headed": "头", "Sun": "太阳", "Facing": "朝向",
    "Flowing": "流动", "Stasis": "静滞", "Blast": "爆发", "Penetrating": "穿透",
    "Shot": "射击", "Gale": "强风", "Aura": "光环", "Entropic": "熵",
    "Dummy": "虚拟", "Slip": "潜行", "Heatbutt": "头槌", "Lizzard": "蜥蜴",
    "Trapper": "诱捕者", "felstalker": "邪能潜猎兽", "Flyerling": "幼飞龙",
    "Dominator": "支配者", "Trapper": "诱捕者",
    # retained-but-composed words that still deserve zh in-place
    "Ragdoll": "布娃娃", "Warp": "折跃", "Prism": "棱镜", "Blink": "闪现",
    "Validate": "验证", "Covered": "已覆盖", "Purification": "净化",
    "Suppression": "压制", "Crystal": "水晶", "Incap": "失能", "Dest": "摧毁",
    "Faction": "派系", "Equipped": "已装备", "Customization": "自定义",
    "Deco": "装饰", "Engineering": "工程", "Grenadier": "掷弹兵",
    "Cyber": "网络", "Operative": "特工", "DoT": "持续伤害", "Cords": "缆线",
    "Bay": "库房", "Net": "网络", "War": "战争", "Cap": "上限", "Lab": "实验室",
    "Tag": "标签", "Man": "男人", "Win": "胜利", "Sky": "天空", "Ice": "寒冰",
    "Run": "奔跑", "Fan": "风扇", "Gas": "瓦斯", "Jet": "喷气", "Rig": "钻台",
    "Golden": "黄金", "Remastered": "重制版", "Webby": "威比", "Umbra": "暗影",
    "Ihanrii": "伊汗瑞", "Rohanna": "罗哈娜", "Warfields": "沃菲尔德",
    "Precusor": "先兆", "Supress": "压制", "Sanitization": "净化",
    "Shredder": "碎地机", "Office": "办公室", "Conductor": "导流体",
    "Regen": "恢复", "Recall": "紧急召回", "Sanitizer": "净化者",
    "Hut": "棚屋", "Hunter": "猎手", "hunters": "猎手",
    "Essence": "精华", "Evolution": "进化", "Dominated": "被支配",
    "Owned": "拥有", "Move": "移动", "Moves": "移动",
    "Old": "旧版", "old": "旧版",
}

# ------------------------------------------------------------ proper nouns
NAME_ZH = {
    "Zeratul": "泽拉图", "Tychus": "泰凯斯", "Nova": "诺娃", "Karax": "凯拉克斯",
    "Artanis": "阿塔尼斯", "Vorazun": "沃拉尊", "Alarak": "阿拉纳克",
    "Stetmann": "斯台特曼", "Horner": "霍纳", "Mengsk": "蒙斯克", "Abathur": "阿巴瑟",
    "Kerrigan": "凯瑞甘", "Dehaka": "德哈卡", "Zagara": "扎加拉", "Fenix": "菲尼克斯",
    "Raynor": "雷诺", "Swann": "斯旺", "Malash": "马拉什", "Amon": "埃蒙",
    "Duran": "杜兰", "Narud": "纳鲁德", "Selendis": "塞兰迪斯", "Rohanna": "罗哈娜",
    "Jaina": "吉安娜", "Grom": "格罗姆", "Dutch": "杜奇", "Debra": "黛布拉",
    "Greene": "格林", "Gary": "加里", "GARY": "加里", "Warfield": "沃菲尔德",
    "Talandar": "塔兰达尔", "Mohandar": "莫汉达尔", "Urun": "尤兰",
    "Rokhan": "沃坎", "Volazun": "沃拉尊", "Egon": "艾贡", "Kate": "凯特",
    "Lockwell": "洛克威尔", "Davis": "戴维斯", "Valerian": "瓦伦里安",
    "Ihanrii": "伊汗瑞", "XelNaga": "萨尔纳加", "Adun": "亚顿",
    "TerraTron": "泰拉创", "Albion": "奥比昂", "Khalai": "卡拉莱",
    "Telbrus": "特尔布鲁斯",
}

# ------------------------------------------------- warcraft easter eggs
WAR3_ZH = {
    "War3": "魔兽争霸3", "war3": "魔兽争霸3", "Footman": "步兵", "Footprint": "足印",
    "Foot": "足印", "print": "印", "Ogre": "食人魔", "Troll": "巨魔",
    "Dark": "黑暗", "Shadow": "阴影", "Fel": "邪能", "Villager": "村民",
    "Voodoo": "巫毒", "Spirits": "之魂", "Spirit": "之魂", "Incinerate": "焚化",
    "Firelord": "炎魔", "Tinkerer": "修补匠", "Champion": "勇士",
    "Village": "村庄", "Mage": "法师", "Peasant": "农民", "Bandit": "强盗",
}

# ------------------------------------------- common leftover english words
WORD_ZH = {
    # function words (machine leftovers like "Is 泰凯斯 Command Center")
    "Is": "是", "is": "是", "Are": "是", "Not": "否", "no": "无", "No": "无",
    "Have": "拥有", "have": "拥有", "has": "拥有", "Has": "拥有",
    "dont": "未", "Dont": "未", "Doesnt": "未",
    "Than": "于", "than": "于", "Greater": "高于", "greater": "高于",
    "Less": "低于", "less": "低于", "Half": "一半", "half": "一半",
    "And": "与", "and": "与", "Or": "或", "or": "或", "With": "带",
    "with": "带", "Without": "无", "when": "当", "When": "当",
    "by": "由", "By": "由", "for": "为", "For": "为", "of": "之",
    "Of": "之", "the": "", "The": "", "to": "至",
    "in": "内", "In": "内", "on": "上", "On": "上", "at": "于",
    "never": "从不", "Never": "从不", "Always": "始终",
    # combat / attribute vocabulary
    "Full": "全满", "full": "全满", "Empty": "为空", "Low": "低",
    "High": "高", "Near": "邻近", "near": "邻近", "Far": "远离",
    "Used": "已用", "Cost": "花费", "factor": "因子", "Factor": "因子",
    "Text": "文本", "Model": "模型", "Cursor": "光标",
    "Damage": "伤害", "Heal": "治疗", "Regen": "恢复", "Mana": "法力",
    "Life": "生命", "Shield": "护盾", "Armor": "护甲", "Speed": "速度",
    "Attack": "攻击", "Weapon": "武器", "Kill": "击杀", "Death": "死亡",
    "Dead": "死亡", "Build": "建造", "Building": "建筑", "Built": "建造",
    "Under": "在下方", "ground": "地面", "Ground": "地面",
    "Auto": "自动", "Turret": "炮塔", "Turrets": "炮塔", "Cluster": "集群",
    "Rocket": "火箭", "Rockets": "火箭", "Level": "等级", "Charged": "已充能",
    "Charge": "充能", "Mine": "地雷", "Mines": "地雷", "Bomb": "炸弹",
    "Bombed": "被轰炸", "Bomber": "轰炸机", "Fire": "开火", "Launcher": "发射器",
    "Missile": "导弹", "Missiles": "导弹", "Spawn": "生成", "Spawns": "生成",
    "Target": "目标", "Targets": "目标", "arget": "目标",  # munge of Target
    "Check": "检查", "Validator": "验证器", "Validators": "验证器",
    "Delay": "延迟", "Duration": "持续时间", "Radius": "半径", "Area": "区域",
    "Search": "搜索", "Apply": "施加", "Applied": "已施加", "Behavior": "行为",
    "Behaviors": "行为", "Effect": "效果", "Effects": "效果", "Unit": "单位",
    "Units": "单位", "Player": "玩家", "Players": "玩家", "Hero": "英雄",
    "Heroes": "英雄", "Coop": "合作", "Command": "指令", "Commands": "指令",
    "Order": "命令", "Orders": "命令", "Cancel": "取消", "Create": "创建",
    "Restoring": "恢复", "phase": "相位", "gt": "大于", "gte": "大于等于",
    "lt": "小于", "lte": "小于等于", "Command": "指挥", "Commands": "指挥",
    "Destroy": "摧毁", "Destroyed": "已摧毁", "Launch": "发射", "Impact": "轰击",
    "Buff": "增益", "Debuff": "减益", "Stun": "眩晕", "Slow": "减速",
    "Root": "定身", "Silence": "沉默", "Cloak": "隐形", "Cloaked": "已隐形",
    "Decloak": "显形", "Snipe": "狙击", "Save": "保存", "Data": "数据",
    "Screen": "界面", "UI": "界面", "Main": "主", "Menu": "菜单", "City": "城市",
    "Tendril": "触须", "Supply": "补给", "Add": "添加", "Kinetic": "动能",
    "Rotating": "旋转", "Reveal": "显形", "Revealed": "已显形", "Heals": "治疗",
    "Weapon": "武器", "Sight": "视野", "Range": "射程", "Cooldown": "冷却",
    "Energy": "能量", "Health": "生命值", "Heath": "生命值",  # heath = typo of health
    "Push": "推进", "Pull": "拉拽", "Knock": "击退", "Back": "退",
    "Barrier": "屏障", "Beam": "射线", "Beams": "射线", "Blast": "爆发",
    "Blitz": "闪击", "Bombardment": "轰击", "Burst": "连发", "Caster": "施法者",
    "Channel": "引导", "Channeled": "引导中", "Charging": "充能中",
    "Circle": "圆形", "Cone": "锥形", "Cross": "十字", "Curve": "曲线",
    "Cutter": "切割机", "Drill": "钻机", "Drop": "空投", "Dropped": "已空投",
    "Drone": "无人机", "Drones": "无人机", "Elite": "精锐", "Enhanced": "强化",
    "Explode": "爆炸", "Exploded": "已爆炸", "Explosion": "爆炸",
    "Explosive": "爆炸物", "Fall": "坠落", "Falling": "坠落中", "Field": "力场",
    "Fields": "力场", "Flash": "闪光", "Flying": "飞行", "Fog": "战争迷雾",
    "Gate": "门", "Gates": "门", "Gravity": "重力", "Grid": "网格",
    "Hold": "驻守", "Holding": "驻守中", "Hole": "洞", "Hover": "悬浮",
    "Idle": "空闲", "Ignore": "忽略", "Improve": "改良", "Improved": "已改良",
    "Initial": "初始", "Inner": "内部", "Instant": "瞬时", "Item": "物品",
    "Items": "物品", "Jump": "跳跃", "Jumped": "已跳跃", "Keeper": "看守者",
    "Laser": "激光", "Lasers": "激光", "Layer": "层", "Leash": "束缚链",
    "Light": "光", "Lighting": "照明", "Loop": "循环", "Marker": "标记",
    "Mask": "遮罩", "Max": "最大", "Measure": "测量", "Mega": "巨型",
    "Mini": "迷你", "Mobile": "机动", "Morph": "变形", "Morphed": "已变形",
    "Morphing": "变形中", "Mount": "骑乘", "Move": "移动", "Moving": "移动中",
    "Never": "从不", "Neutral": "中立", "Night": "夜晚", "Nova": "诺娃",
    "Nuke": "核弹", "Objective": "目标物", "Offset": "偏移", "Orb": "宝珠",
    "Orbital": "轨道", "Other": "其他", "Outer": "外部", "Over": "结束",
    "Passive": "被动", "Patrol": "巡逻", "Pattern": "模式", "Pause": "暂停",
    "Per": "每", "Percent": "百分比", "Phase": "相位", "Pierce": "穿透",
    "Ping": "信号", "Place": "放置", "Placed": "已放置", "Plane": "平面",
    "Point": "点", "Points": "点", "Power": "能量", "Powered": "已通电",
    "Probe": "探机", "Prop": "道具", "Pure": "纯净", "Purple": "紫色",
    "Quick": "快速", "Random": "随机", "Rapid": "速射", "Rate": "速率",
    "Reactor": "反应堆", "Release": "释放", "Released": "已释放", "Remove": "移除",
    "Removed": "已移除", "Repair": "修理", "Repaired": "已修理", "Reply": "回复",
    "Reset": "重置", "Respawn": "重生", "Rest": "休息", "Retreat": "撤退",
    "Return": "返回", "Returned": "已返回", "Revive": "复活", "Rise": "升起",
    "Rising": "升起中", "Rock": "岩石", "Rocks": "岩石", "Roll": "翻滚",
    "Rotate": "旋转", "Rotates": "旋转", "Round": "回合", "Rush": "冲锋",
    "Scan": "扫描", "Scourge": "灾群", "Screen": "界面", "Sentry": "哨兵",
    "Set": "设置", "Sets": "设置", "Shock": "震击", "Shoot": "射击",
    "Shooter": "射手", "Show": "显示", "Shows": "显示", "Single": "单体",
    "Sink": "沉没", "Size": "大小", "Slash": "挥砍", "Slice": "切割",
    "Slide": "滑行", "Small": "小型", "Smash": "猛击", "Sound": "声音",
    "Spawned": "已生成", "Spawning": "生成中", "Spike": "尖刺", "Spikes": "尖刺",
    "Spin": "旋转", "Spinning": "旋转中", "Spirit": "之魂", "Spirits": "之魂",
    "Spray": "喷射", "Stack": "叠加", "Stacks": "叠加", "Stage": "阶段",
    "Stand": "站立", "Start": "开始", "Station": "站点", "Stasis": "静滞",
    "Stop": "停止", "Storage": "存储", "Storm": "风暴", "Strain": "品系",
    "Structure": "结构", "Structures": "结构", "Stun": "眩晕", "Summon": "召唤",
    "Summoned": "已召唤", "Summoning": "召唤中", "Support": "支援",
    "Surge": "涌动", "Swap": "交换", "Switch": "切换", "System": "系统",
    "Teleport": "传送", "Temp": "临时", "Test": "测试", "Throw": "投掷",
    "Thrown": "已投掷", "Timed": "限时", "Toggle": "切换", "Token": "标记物",
    "Total": "总计", "Tower": "塔", "Towers": "塔", "Trail": "轨迹",
    "Tram": "轨道车", "Trap": "陷阱", "Traps": "陷阱", "Travel": "行进",
    "Triple": "三重", "Turn": "转向", "Type": "类型", "Ultimate": "终极",
    "Unarmored": "无护甲", "Under": "在下方", "Up": "上", "Upgraded": "已升级",
    "Use": "使用", "Used": "已用", "Using": "使用中", "Utility": "效用",
    "Valor": "英勇", "Vault": "库房", "Vent": "通风口", "Vet": "老兵",
    "Vortex": "漩涡", "Wall": "墙", "Walls": "墙", "Ward": "守卫",
    "Wave": "波", "Waves": "波", "Whirlwind": "旋风", "Wide": "宽",
    "Wind": "风", "Wing": "机翼", "Wings": "机翼", "Wire": "线缆",
    "Within": "之内", "Work": "运作", "Working": "运作中", "Zone": "区域",
    "Zones": "区域",
}

# ------------------------------------------------------- phrase-level fixes
PHRASE_FIX = {
    # machine word-salad compositions observed in the table
    "0Dot5": "0.5", "0dot5": "0.5", "Dot5": ".5",
    "吐息的开火": "火焰吐息", "吐息的冰霜": "冰霜吐息",
    "高于-先知": "眼虫-",
    "舱门是靠近虫后": "二级孵化场邻近虫后",
    "2nd-二级孵化场": "二级孵化场",
    "灰色遮罩巨魔": "黑暗巨魔",
    "温拓里尼射线": "激光钻机",
    "死亡时间结束": "死亡计时结束",
    "Spearof阿顿": "亚顿之矛", "Spearof": "亚顿之矛",
    "SSTerraTron": "SS泰拉创",
    "Tesseract-单声道-Lith": "四维巨石碑",
    "250mm-180毫米口径震击炮": "250毫米突袭炮",
    "已隐形-Reduce伤害应用行为": "已隐形-伤害降低-施加行为",
    "法力更高Than半": "法力高于一半",
    "施法者非内Combat": "施法者脱离战斗",
    "目标 Is Oil Bombed": "目标已被燃油轰炸",
    "Is 泰凯斯 Command Center": "是-泰凯斯指挥中心",
    "不要-Have250mm-火炮": "无250毫米火炮",
    "平民或Overseerand否": "平民或眼虫 且无",
    "拥有原型-Titan-升级": "拥有-泰坦原型-升级",
    "魔兽争霸3食人魔一Headed": "魔兽争霸3单头食人魔",
    "SCVAutoTurret": "SCV自动炮塔", "Jaina@Portrait": "吉安娜头像",
    "TerraTronSaw": "泰拉创锯", "或Overseerand拥有": "或眼虫 且拥有",
    # hunter munge: machine dict mapped Hunter->猎杀虫; official zhCN is 猎手
    "阴影猎杀虫": "暗影猎手",     # Shadow Hunter (War3 official)
    "猎杀虫": "猎手",             # Demon Hunter 恶魔猎手 / Hunter 猎手
    # "star fly by" salad
    "星飞行由已动画火焰": "星空飞掠-动画火焰",
    "星飞行由镜头": "星空飞掠-镜头",
    "星飞行由照明弹": "星空飞掠-照明弹",
    "星飞行由": "星空飞掠",
    "小型的大厅": "小型大厅",     # tiny great hall (War3)
    "剑圣-OLD": "旧版剑圣",       # blademaster old
    "启用Move2s": "启用移动2秒",  # enable move (2s) — parens lost in earlier pass
    "细胞Block": "细胞舱段",      # purifier cell block grid piece
}

# ------------------------------------------------------- whole-value fixes
VALUE_FIX = {
}



# ------------------------------------------------------------ keep rules
def is_code(token: str) -> bool:
    """True for internal identifiers that must stay as-is.

    Covers the coop effect abbreviation families (ACc / ANrf / Aap / ANc1 ...),
    asset/model codes (SMX2, MP03), and short uppercase abbrevalue tokens.
    """
    if token in KEEP_UPPER:
        return True
    if re.fullmatch(r"[A-Z]{2,6}\d{0,3}", token):        # SMX2 / MP03 / PVP
        return True
    if re.fullmatch(r"[A-Za-z]{1,4}\d{1,4}[A-Za-z]{0,2}", token):  # Ex2 / Mk1 / L1 / WCS2017
        return True
    if re.fullmatch(r"[A-Z][a-z]{1,2}", token):          # Pn / Cwb / Ttw
        return True
    if re.fullmatch(r"[a-z][A-Z]", token):               # cU
        return True
    if re.fullmatch(r"[ACDEHIN]|AN[A-Za-z]{0,2}\d?|AC[A-Za-z]{0,2}\d?|AE[A-Za-z]{0,2}"
                    r"|AH[A-Za-z]{0,2}|AI[A-Za-z]{0,2}|AO[A-Za-z]{0,2}|AU[A-Za-z]{0,2}"
                    r"|AP[A-Za-z]{0,2}|AS[A-Za-z]?|A[a-z]{1,3}\d?", token):
        return True                                      # coop effect codes
    return False

KEEP_UPPER = {"SMX", "COOP", "SCV", "EMP", "DPS", "BFG", "WCS", "COD", "ATX",
              "LTE", "ULBR", "BLUR", "PVP", "ZZZ", "DOM", "GTE", "RCZ", "MKII",
              "SMTV", "SCCW", "HHMag", "YSw", "PHLM", "TVS", "DNA", "KD8",
              "Webby", "AOE", "AoE", "SS", "SOA", "PH", "Pn", "PnPEMP", "PnPAA", "DoT", "XThos"}

WHITESPACE_CJK = re.compile(r"(?<=[一-鿿。：，、])\s+(?=[一-鿿。：，、])")
TRAILING_SEP = re.compile(r"[\s\-]+$")

