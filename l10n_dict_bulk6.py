#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""批量词条 第六批 —— 最终长尾扫荡。"""
import io
import json

DICT = r"e:\Code\sc2\Work\l10n_dict.json"

WORDS = {
    "Runed": "符文", "Lords": "领主", "Arachnathid": "蛛魔",
    "Archnathid": "蛛魔", "Guldans": "古尔丹的", "Sanctum": "圣所",
    "Tyrannosaur": "暴虐龙", "Sandbags": "沙袋", "Boosters": "助推器",
    "Guass": "高斯", "death": "死亡", "Teammatery": "队伍精通",
    "Aligntment": "阵营", "Cradle": "摇篮", "FINISH": "完成",
    "Persistant": "持续", "Leastest": "最少", "Higher": "更高",
    "Perdition": "毁灭", "Mooch": "蹭", "Dummy2": "假人2",
    "Dummy1": "假人1", "Templar2": "圣堂2", "Yamato3": "大和炮3",
    "Swell": "膨胀", "Spears": "长矛", "Battlestations": "战斗岗位",
    "Detetor": "探测器", "Augment": "增强", "Seaweed": "海藻",
    "Barbed": "带刺", "Destruct": "自毁", "Marked": "已标记",
    "Reinforcements": "增援", "Strafe": "扫射", "Straf": "扫射",
    "Aerial": "空中", "Shackles": "枷锁", "Voidray": "虚空射线",
    "Record": "记录", "Stolen": "被盗", "Threshold": "阈值",
    "Zerglings": "小狗", "Queens": "女王", "Inherit": "继承",
    "Tourny": "锦标赛", "Palmtree": "棕榈树", "Rocker": "摇杆",
    "Faces": "面", "Reanimator": "复活器", "Butcher": "屠夫",
    "Killwall": "致命墙", "Cattail": "香蒲", "Stones": "石块",
    "Continuous": "持续", "Wheelbarrel": "手推车", "Resorts": "度假村",
    "Hotels": "旅馆", "Reliquary": "圣物匣", "Tendrils": "触须",
    "Corpses": "尸体", "Carcasses": "残骸", "Statues": "雕像",
    "Watermelon": "西瓜", "Football": "橄榄球", "Scaffold": "脚手架",
    "Sealed": "密封", "Hexgrid": "六角网格", "Report": "报告",
    "Fallen": "堕落", "Curbs": "路缘", "Severed": "断裂",
    "Forearm": "前臂", "Communications": "通讯", "Warstomp": "战争践踏",
    "Clumps": "丛", "Dumpster": "垃圾箱", "Luggage": "行李",
    "Overdrive": "超载", "Baseball": "棒球", "Waterfalls": "瀑布",
    "Welder": "焊工", "Stalagmite": "石笋", "Edges": "边缘",
    "School": "学校", "Bridges": "桥", "Inactive": "未激活",
    "Preordain": "预定", "Pathingand": "寻路和", "Strobe": "频闪",
    "Inverted": "反转", "Spinning": "旋转", "Fueling": "加油",
    "Pointy": "尖锐", "Debris4x4": "碎片4x4", "Debris2x6": "碎片2x6",
    "Roach2": "蟑螂2",
    # 更多长尾
    "servo": "伺服", "tuskar": "海象人", "Clockwerk": "发条",
    "Swtnr": "增味", "MKIIAA": "MK2AA", "EAXON": "EAXON",
    "SEASON": "赛季", "WARCHEST": "战争宝箱", "FXDOM": "特效领域",
    "HHSCV": "HHSCV", "Thor250mm": "雷神250mm",
    "Vortexd": "漩涡D", "Epilogue01": "终章01",
    "Epilogue02": "终章02", "Epilogue03": "终章03",
    "Taldarim01": "塔达里姆01", "Taldarim02": "塔达里姆02",
    "Blocker1x1": "阻挡物1x1", "Blocker2x2": "阻挡物2x2",
    "Footprint4x4": "占地4x4", "250mm": "250mm",
    "Marine2": "枪兵2", "Hellbat02": "地狱蝙蝠02",
    "Wedges8x6": "楔形8x6", "Wedges6x6": "楔形6x6",
    "Wedges8x4": "楔形8x4", "330mm": "330mm",
    "Room01": "房间01", "Room02": "房间02", "Room03": "房间03",
    "Room04": "房间04", "Room05": "房间05", "Room09": "房间09",
    "Room11": "房间11", "Room16": "房间16", "Room17": "房间17",
    "Room18": "房间18",
    "EVENT": "事件", "PLAYER": "玩家", "FOLEY": "拟音",
    "stich1": "缝合1", "stich2": "缝合2", "stich3": "缝合3",
    "shot03": "射击03",
    # 额外杂项
    "Hotkey": "热键", "Submerge": "潜入", "Topbar": "顶栏",
    "Jaeden": "加伊登", "Batrider": "蝙蝠骑士",
}


def main():
    with io.open(DICT, encoding="utf-8") as f:
        d = json.load(f)
    sfx, prop = d["suffix"], d["proper"]
    n = 0
    for k, v in WORDS.items():
        if k not in sfx and k not in prop:
            sfx[k] = v
            n += 1
    with io.open(DICT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("+%d 词 -> suffix=%d proper=%d" % (n, len(sfx), len(prop)))


if __name__ == "__main__":
    main()
