#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成/更新演算体汉化词典 l10n_dict.json(已存在则只补新键, 不覆盖人工修改)。"""
import io
import json
import os

OUT = r"e:\Code\sc2\Work\l10n_dict.json"

SUFFIX = {
    # 用途 / 部件
    "Model": "模型", "Sound": "音效", "Splat": "泼溅图", "Shadow": "阴影",
    "Impact": "轰击", "Launch": "发射", "Range": "范围", "Anim": "动画",
    "Macro": "宏", "Beam": "光束", "Missile": "导弹", "Death": "死亡",
    "Birth": "出生", "Attack": "攻击", "Hit": "命中", "Start": "开始",
    "Stop": "停止", "Loop": "循环", "Cursor": "指针", "Icon": "图标",
    "Portrait": "头像", "Light": "光源", "Flames": "火焰", "Flame": "火焰",
    "Smoke": "烟雾", "Dust": "尘土", "Blood": "血液", "Debris": "碎屑",
    "Explosion": "爆炸", "Wireframe": "线框", "Selection": "选择",
    "Status": "状态", "Bar": "条", "Ring": "环", "Glow": "辉光",
    "Trail": "拖尾", "Ragdoll": "布娃娃", "Decal": "贴花",
    "Texture": "纹理", "Overlay": "覆盖层", "Quad": "四边形",
    "Segment": "分段", "Radius": "半径", "Point": "点",
    # 行为 / 流程
    "Placement": "放置", "Preview": "预览", "Upgrade": "升级",
    "Build": "建造", "Construction": "建造进程", "Queue": "队列",
    "Warp": "折跃", "Burrow": "钻地", "Unburrow": "出土",
    "Morph": "变形", "UnMorph": "变形还原", "Transform": "变形",
    "Cancel": "取消", "Create": "创建", "Remove": "移除",
    "Destroy": "毁灭", "Destroyed": "已毁灭", "Spawn": "生成",
    "Summon": "召唤", "Channel": "引导", "Teleport": "传送",
    "Transition": "过渡", "Move": "移动", "Land": "降落",
    "Lift": "升空", "Flying": "飞行", "Sleep": "休眠",
    "Wake": "唤醒", "Hover": "悬浮", "Idle": "空闲", "Fire": "开火",
    "Set": "设置", "Clear": "清除", "Toggle": "切换",
    "On": "开启", "Off": "关闭", "Confirm": "确认",
    "Search": "搜索", "Query": "查询", "Detect": "探测",
    "Reveal": "显形", "Cloak": "隐形", "Force": "强制",
    # 数据类别
    "Effect": "效果", "Effects": "效果", "Ability": "技能", "Abil": "技能",
    "Behavior": "行为", "Validator": "验证器", "Actor": "演算体",
    "Unit": "单位", "Hero": "英雄", "Item": "物品", "Weapon": "武器",
    "Turret": "炮塔", "Button": "按钮", "Observer": "侦测器",
    # 属性
    "Buff": "增益", "Debuff": "减益", "Aura": "光环",
    "Splash": "溅射", "Damage": "伤害", "Heal": "治疗",
    "Shield": "护盾", "Armor": "护甲", "Energy": "能量",
    "Target": "目标", "Area": "区域",
    # 场景 / 地形
    "Ambient": "环境", "Doodad": "装饰物", "Terrain": "地形",
    "TerrainObject": "地形对象", "Water": "水面", "Creep": "菌毯",
    "Nydus": "坑道", "Tumor": "孢肿", "Cliff": "悬崖",
    "Foliage": "植被", "Tree": "树", "Rock": "岩石", "Wall": "墙",
    "Bridge": "桥", "Tower": "塔", "Building": "建筑",
    "Buildings": "建筑", "CityBuilding": "城市建筑", "City": "城市",
    "Snow": "积雪", "Jungle": "丛林", "Temple": "神庙",
    "Cavern": "洞穴", "Fog": "迷雾", "Curtain": "帷幕",
    "SpacePlatform": "空间平台", "InhibitorZone": "抑制场",
    "StasisTube": "静滞舱", "Site": "场地", "Base": "基地",
    "Orbit": "轨道", "Orbiter": "轨道器", "Starship": "星舰",
    "Ark": "方舟", "Lab": "实验室", "Logo": "徽标",
    # 界面 / 调试
    "UI": "界面", "Panel": "面板", "Info": "信息", "Debug": "调试",
    "Test": "测试", "Demo": "演示", "Harness": "控制组",
    "Guide": "引导", "Visual": "视觉", "Banker": "存储库",
    # 修饰
    "Tiny": "微型", "Small": "小型", "Medium": "中型",
    "Large": "大型", "Huge": "巨型", "High": "高", "Low": "低",
    "Up": "上", "Down": "下", "Pre": "预", "Post": "后",
    "With": "带", "NoEvents": "无事件", "Addition": "追加",
    "Local": "局部", "Omni": "全向", "Level": "等级",
    "Red": "红", "Blue": "蓝", "Green": "绿", "Yellow": "黄",
    "Team": "队伍", "Player": "玩家", "Ally": "友方", "Enemy": "敌方",
    "Campaign": "战役", "Coop": "合作", "Multi": "对战", "Story": "故事",
    "Action": "动作", "Command": "指令", "AntiGrav": "反重力",
    "Defenders": "防御者", "Colonist": "殖民者",
    # 高频补充(据 --unknown 统计)
    "Void": "虚空", "Mutator": "突变因子", "Tank": "坦克",
    "Air": "对空", "Ground": "对地", "Siege": "攻城",
    "Caster": "施法者", "Infested": "被感染", "Space": "空间",
    "Collapsible": "可倒塌", "Destructible": "可破坏",
    "Field": "场", "Platform": "平台", "Black": "黑",
    "Special": "特殊", "Power": "能量", "Mine": "地雷",
    "Left": "左", "Right": "右", "Out": "外", "In": "内",
    "Offset": "偏移", "Port": "港", "Gluescreen": "过场界面",
    "Boost": "加速", "Powerup": "增强道具", "Attachment": "附着",
    "Release": "释放", "Spirit": "灵体", "Puddle": "水洼",
    "Knockback": "击退", "Hologram": "全息", "Projector": "投影器",
    "Pipes": "管道", "Exhaust": "排气", "Sewers": "下水道",
    "Compound": "建筑群", "Assault": "突击", "Fighter": "战机",
    "Front": "前", "Back": "后", "Top": "顶", "Bottom": "底",
    "Inner": "内", "Outer": "外", "Center": "中心",
    "Fade": "淡出", "Blend": "混合", "Swap": "交换",
    "Hide": "隐藏", "Show": "显示", "Show1": "显示1",
    "Enable": "启用", "Disable": "禁用",
    "Charge": "充能", "Recharge": "再充能", "Drain": "抽取",
    "Rotation": "旋转", "Scale": "缩放", "Tint": "染色",
    "Trophy": "奖杯", "Flag": "旗帜", "Banner": "横幅",
    "Portal": "传送门", "Gate": "门", "Door": "门",
    "Crystal": "水晶", "Mineral": "矿物", "Gas": "瓦斯",
    "Rich": "富集", "Depleted": "枯竭", "Harvest": "采集",
    "Veterancy": "老兵", "Kill": "击杀", "Revive": "复活",
    "Stun": "眩晕", "Slow": "减速", "Root": "定身",
    "Vision": "视野", "Sight": "视野", "Detector": "探测器",
    "Emitter": "发射器", "Generator": "发生器",
}

PROPER = {
    "Protoss": "星灵", "Terran": "人类", "Zerg": "异虫",
    "Ouros": "欧罗斯", "Zerus": "泽鲁斯", "Moebius": "莫比斯",
    "Daelaam": "戴拉姆", "Purifier": "净化者", "Nerazim": "涅拉齐姆",
    "Khalai": "卡莱", "Hybrid": "混合体", "Sentinel": "哨卫",
    "HotS": "虫群之心", "Mecha": "机甲", "Naga": "泽尔纳加",
    "Xel": "泽尔", "Umojan": "乌莫扬", "UmojanLab": "乌莫扬实验室",
    "Amon": "阿蒙", "Kerrigan": "凯瑞甘", "Raynor": "雷诺",
    "Artanis": "阿塔尼斯", "Zeratul": "泽拉图", "Nova": "诺娃",
    "Tychus": "泰凯斯", "Stukov": "斯托科夫", "Zagara": "扎加拉",
    "Abathur": "阿巴瑟", "Alarak": "阿拉纳克", "Vorazun": "沃拉尊",
    "Karax": "卡拉克斯", "Dehaka": "德哈卡", "Fenix": "菲尼克斯",
    "Swann": "斯旺", "Stetmann": "斯台特曼", "Mengsk": "蒙斯克",
    "Horner": "霍纳", "Tal": "塔达林", "Han": "汉", "SCV": "SCV",
}

NOTE = ("演算体汉化词典。suffix=用途/修饰词, proper=专有名词。"
        "可自由增补, 生成器每次读取; 重跑本脚本只补新键, 不覆盖你改过的值。")


def main():
    data = {"suffix": {}, "proper": {}, "_note": NOTE}
    if os.path.isfile(OUT):
        with io.open(OUT, encoding="utf-8") as f:
            old = json.load(f)
        data["suffix"] = dict(old.get("suffix", {}))
        data["proper"] = dict(old.get("proper", {}))
    added = 0
    for k, v in SUFFIX.items():
        if k not in data["suffix"]:
            data["suffix"][k] = v
            added += 1
    for k, v in PROPER.items():
        if k not in data["proper"]:
            data["proper"][k] = v
            added += 1
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("词典已写: %s  suffix=%d proper=%d  本次新增=%d"
          % (OUT, len(data["suffix"]), len(data["proper"]), added))


if __name__ == "__main__":
    main()
