#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
全类别汉化缺口普查 —— 不止演算体, 覆盖内部 mod 所有数据类目录。

做法:
  1. 枚举 CASC 里 mods\**\GameData\*Data.xml, 按顶层节点标签(CUnit/CEffectDamage/...)
     反推字符串键类别(Unit/Effect/...);
  2. 与「官方 zhCN GameStrings」+「OB 汉化包 ObjectStrings.txt」对照;
  3. 输出 _scope.txt: 各类别 总数/已译/缺译, 以及键前缀映射校验。
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
PACK_DIR = os.path.join(GAME, "Editor", "LocalizedData")
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


def main():
    c = cr.Casc()
    c.open(GAME)
    allp = c.list_paths((".xml", ".txt"))

    # ---- 官方 zhCN 已有译名: 类别 -> {id: 中文} ----
    official = collections.defaultdict(dict)
    for p in (x for x in allp if x.endswith("gamestrings.txt") and "zhcn" in x):
        for line in dec(c.read(p)).splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            bits = k.split("/")
            if len(bits) == 3 and bits[1] == "Name" and has_cjk(v):
                official[bits[0]][bits[2]] = v.strip()

    # ---- OB 汉化包已有 ----
    pack = collections.defaultdict(dict)
    for fn in ("ObjectStrings.txt", "GameStrings.txt", "111GameStrings.txt"):
        fp = os.path.join(PACK_DIR, fn)
        if not os.path.isfile(fp):
            continue
        for line in dec(open(fp, "rb").read()).splitlines():
            if "=" not in line or line.startswith("//"):
                continue
            k, v = line.split("=", 1)
            bits = k.split("/")
            if len(bits) == 3 and bits[1] == "Name":
                pack[bits[0]][bits[2]] = v.split("\t")[0].strip()

    # ---- 内部 mod 数据类 ID 全表 ----
    known_cats = sorted(set(official) | set(pack), key=len, reverse=True)
    ids = collections.defaultdict(set)          # 类别 -> set(id)
    unmapped = collections.Counter()            # 无法归类的标签
    files = 0
    for p in sorted(x for x in allp
                    if x.startswith("mods") and re.search(r"data\.xml$", x)):
        try:
            txt = dec(c.read(p))
            root = ET.fromstring(txt)
        except (ET.ParseError, Exception):
            continue
        files += 1
        for el in root:
            oid = el.get("id")
            if not oid or not el.tag.startswith("C"):
                continue
            body = el.tag[1:]
            cat = next((k for k in known_cats if body.startswith(k)), None)
            if cat:
                ids[cat].add(oid)
            else:
                unmapped[el.tag] += 1

    rows = []
    for cat, s in ids.items():
        off = {i for i in s if i in official.get(cat, {})}
        pk = {i for i in s
              if has_cjk(pack.get(cat, {}).get(i, ""))}
        hold = {i for i in s
                if i in pack.get(cat, {}) and not has_cjk(pack[cat][i])}
        miss = s - off - pk - hold
        rows.append((cat, len(s), len(off), len(pk), len(hold), len(miss)))
    rows.sort(key=lambda r: -r[5])

    with io.open(os.path.join(WORK, "_scope.txt"), "w", encoding="utf-8") as w:
        w.write("解析 %d 个 *Data.xml, 归类出 %d 个类别\n\n" % (files, len(ids)))
        w.write("%-22s %8s %8s %8s %8s %8s\n"
                % ("类别", "总数", "官方译", "包已译", "占位", "缺译"))
        w.write("-" * 68 + "\n")
        tot = [0] * 5
        for cat, n, o, pk, h, m in rows:
            w.write("%-22s %8d %8d %8d %8d %8d\n" % (cat, n, o, pk, h, m))
            for i, v in enumerate((n, o, pk, h, m)):
                tot[i] += v
        w.write("-" * 68 + "\n")
        w.write("%-22s %8d %8d %8d %8d %8d\n" % ("合计", *tot))
        if unmapped:
            w.write("\n未归类标签 Top20(不影响主流程):\n")
            for t, n in unmapped.most_common(20):
                w.write("  %-40s %d\n" % (t, n))
    print("已出 _scope.txt")
    print("合计: 总数 %d / 官方译 %d / 包已译 %d / 占位 %d / 缺译 %d" % tuple(tot))


if __name__ == "__main__":
    main()
