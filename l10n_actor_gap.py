#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计银河编辑器「演算体(Actor)」汉化缺口。

数据来源:
  · CASC 内部 mod 的 base.sc2data/GameData/ActorData.xml  -> 演算体 ID 全表
  · CASC 内 <mod>/zhCN.SC2Data/LocalizedData/GameStrings.txt -> 官方已有译名
  · <游戏根>/Editor/LocalizedData/ObjectStrings.txt          -> OB 汉化包已覆盖的译名

输出: _gap.txt(总览) + _gap_todo.txt(可直接粘贴补翻的待办行)
"""
import collections
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

WORK = r"e:\Code\sc2\Work"
sys.path.insert(0, os.path.join(WORK, "dds_viewer"))
import casc_reader as cr  # noqa: E402

GAME = r"D:\StarCraft II"
PACK = os.path.join(GAME, "Editor", "LocalizedData", "ObjectStrings.txt")
SEP = "\\"


def dec(b):
    for e in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return b.decode(e)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def actor_ids(xml_text):
    """取 ActorData.xml 顶层各 C*Actor* 节点的 id(XML 解析, 回退正则)。"""
    try:
        root = ET.fromstring(xml_text)
        return [el.get("id") for el in root
                if el.tag.startswith("C") and "Actor" in el.tag and el.get("id")]
    except ET.ParseError:
        return re.findall(r'<C\w*Actor\w*\b[^>]*?\bid="([^"]+)"', xml_text)


def mod_label(path):
    """mods\a\b.sc2mod\... -> 最后一个 .sc2mod 段作为归属名。"""
    parts = path.split(SEP)
    segs = [p for p in parts if p.endswith(".sc2mod")]
    if not segs:
        return parts[1] if len(parts) > 1 else path
    name = segs[-1][: -len(".sc2mod")]
    if "maps" in parts:  # 战役子地图内嵌数据, 归到父 mod
        name += " (子地图)"
    return name


def main():
    c = cr.Casc()
    c.open(GAME)

    txts = c.list_paths((".xml", ".txt"))

    # 1) 演算体 ID 全表
    by_mod = collections.OrderedDict()
    for p in sorted(x for x in txts if x.endswith("actordata.xml") and x.startswith("mods")):
        got = actor_ids(dec(c.read(p)))
        by_mod.setdefault(mod_label(p), set()).update(got)

    # 2) 官方 zhCN 已有的 Actor/Name
    official = {}
    for p in (x for x in txts if x.endswith("gamestrings.txt") and "zhcn" in x):
        for line in dec(c.read(p)).splitlines():
            if line.startswith("Actor/Name/") and "=" in line:
                k, v = line.split("=", 1)
                official[k[len("Actor/Name/"):]] = v

    # 3) 汉化包覆盖情况
    pack = {}
    for line in dec(open(PACK, "rb").read()).splitlines():
        if line.startswith("Actor/Name/") and "=" in line:
            k, v = line.split("=", 1)
            pack[k[len("Actor/Name/"):]] = v

    done = {k for k, v in pack.items() if has_cjk(v)}
    hold = {k for k, v in pack.items() if not has_cjk(v)}      # 占位 id=id
    off_done = {k for k, v in official.items() if has_cjk(v)}

    all_ids = set().union(*by_mod.values()) if by_mod else set()
    covered = done | off_done
    missing = all_ids - covered - hold

    with io.open(os.path.join(WORK, "_gap.txt"), "w", encoding="utf-8") as w:
        w.write("演算体 ID 总数(内部 mod 去重) : %d\n" % len(all_ids))
        w.write("官方 zhCN 有译名             : %d\n" % len(off_done))
        w.write("汉化包已译                   : %d\n" % len(done))
        w.write("汉化包占位(id=id, 待翻)      : %d\n" % len(hold))
        w.write("完全未收录(连占位都没有)     : %d\n\n" % len(missing))
        w.write("%-34s %7s %7s %7s %7s\n" % ("mod", "演算体", "已译", "占位", "未收录"))
        w.write("-" * 68 + "\n")
        rows = [(m, len(s), len(s & covered), len(s & hold), len(s - covered - hold))
                for m, s in by_mod.items()]
        for r in sorted(rows, key=lambda x: -x[4]):
            w.write("%-34s %7d %7d %7d %7d\n" % r)

    # 待办清单: 占位的 + 完全未收录的, 按 mod 分组
    with io.open(os.path.join(WORK, "_gap_todo.txt"), "w", encoding="utf-8") as w:
        w.write("// 待补翻演算体 —— 直接复制到 Editor\\LocalizedData\\ObjectStrings.txt\n")
        w.write("// [占位] = 汉化包里已有 id=id 的行(改等号右侧��可)\n")
        w.write("// [新增] = 汉化包完全没有的行\n\n")
        for m, s in by_mod.items():
            todo = sorted((s & hold) | (s - covered - hold))
            if not todo:
                continue
            w.write("\n// ===== %s (%d 条) =====\n" % (m, len(todo)))
            for k in todo:
                w.write("Actor/Name/%s=%s\t// %s\n" % (k, k, "占位" if k in hold else "新增"))

    print("ok: _gap.txt / _gap_todo.txt")


if __name__ == "__main__":
    main()
