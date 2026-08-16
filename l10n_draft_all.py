#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
全类别汉化草稿生成器 —— 银河编辑器内部 mod 的所有数据对象名。

原理同 l10n_actor_draft.py: 对象 ID = 「已有官方译名的对象」+「用途/修饰后缀」,
按 CamelCase / 下划线词边界做最长匹配, 逐段翻译。
本脚本把范围从 Actor 扩到全部 75 个类别(Sound/Model/Effect/Requirement/...)。

用法:
  python l10n_draft_all.py --tokens            # 列出所有未识别词(按词频), 用于补词典
  python l10n_draft_all.py --tokens --min 3    # 只看出现 >=3 次的
  python l10n_draft_all.py                     # 生成草稿到 _draft\<类别>.txt
  python l10n_draft_all.py --cat Actor Sound   # 只做指定类别
"""
import argparse
import collections
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

WORK = r"e:\Code\sc2\Work"
sys.path.insert(0, os.path.join(WORK, "dds_viewer"))
import casc_reader as cr  # noqa: E402

GAME = r"D:\StarCraft II"
PACK_DIR = os.path.join(GAME, "Editor", "LocalizedData")
DICT = os.path.join(WORK, "l10n_dict.json")
OUTDIR = os.path.join(WORK, "_draft")
SEP = "\\"

CAT_PRI = ["Unit", "Abil", "Effect", "Behavior", "Weapon", "Upgrade",
           "Button", "Model", "Actor", "Item", "Hero", "Doodad", "Sound"]

NEUTRAL = re.compile(r"^(?:[A-Z]{1,4}\d*|[A-Za-z]{1,2}\d+)$")
TOKEN = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+")


def dec(b):
    for e in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return b.decode(e)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def camel(s):
    return TOKEN.findall(s)


def clean_name(v):
    return v.split("///")[0].strip()


def good_name(s):
    return bool(s) and len(s) <= 24 and "<" not in s and "%" not in s and "\n" not in s


class Translator:
    def __init__(self, lex, sfx, proper):
        self.lex = lex
        self.sfx = sfx
        self.proper = proper
        self.lex_tok = {}
        for k, v in lex.items():
            self.lex_tok.setdefault(tuple(camel(k)), v)

    def lookup_tok(self, tok):
        """单片段查表, 支持尾号剥离(Attack1 -> 攻击1)。 -> (译文, 是否识别)"""
        if tok in self.proper:
            return self.proper[tok], True
        if tok in self.sfx:
            return self.sfx[tok], True
        m = re.match(r"^([A-Za-z]+?)(\d+)$", tok)
        if m:
            stem, num = m.group(1), m.group(2)
            if stem in self.proper:
                return self.proper[stem] + num, True
            if stem in self.sfx:
                return self.sfx[stem] + num, True
        if tok.isdigit() or NEUTRAL.match(tok):
            return tok, True          # 编号/缩写: 原样保留, 不算未识别
        return tok, False

    def render(self, oid):
        toks = camel(oid)
        parts, hit_obj, unknown = [], False, 0
        i = 0
        while i < len(toks):
            matched = False
            for n in range(min(len(toks) - i, 8), 0, -1):
                key = tuple(toks[i:i + n])
                if n == 1 and len(key[0]) <= 2:
                    continue
                v = self.lex_tok.get(key)
                if v:
                    parts.append(v)
                    hit_obj = True
                    i += n
                    matched = True
                    break
            if matched:
                continue
            text, ok = self.lookup_tok(toks[i])
            parts.append(text)
            if not ok:
                unknown += 1
            i += 1
        if hit_obj and len(parts) > 1:
            out = parts[0] + "-" + "".join(parts[1:])
        else:
            out = "".join(parts)
        conf = "none" if not hit_obj else ("high" if unknown == 0 else "low")
        if unknown == 0 and not hit_obj:
            conf = "high"             # 全部片段都翻出来了, 同样算可用
        return out, conf


def load_world(cats_filter):
    c = cr.Casc()
    c.open(GAME)
    allp = c.list_paths((".xml", ".txt"))

    lex, pri = {}, {}
    official = collections.defaultdict(dict)
    for p in (x for x in allp if x.endswith("gamestrings.txt") and "zhcn" in x):
        for line in dec(c.read(p)).splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            bits = k.split("/")
            if len(bits) != 3 or bits[1] != "Name":
                continue
            name = clean_name(v)
            if not has_cjk(name):
                continue
            cat, oid = bits[0], bits[2]
            official[cat][oid] = name
            if not good_name(name):
                continue
            rank = CAT_PRI.index(cat) if cat in CAT_PRI else len(CAT_PRI)
            if "balancemulti" in p:
                rank += 100
            if oid not in lex or rank < pri.get(oid, 999):
                lex[oid], pri[oid] = name, rank

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
                val = v.split("\t")[0].strip()
                pack[bits[0]][bits[2]] = val
                if has_cjk(val) and good_name(val) and bits[2] not in lex:
                    lex[bits[2]] = val      # 汉化包译名也进词表

    known = sorted(set(official) | set(pack), key=len, reverse=True)
    ids = collections.defaultdict(set)
    for p in sorted(x for x in allp if (x.startswith("mods") or x.startswith("campaigns")) and x.endswith("data.xml")):
        try:
            root = ET.fromstring(dec(c.read(p)))
        except Exception:
            continue
        for el in root:
            oid = el.get("id")
            if not oid or not el.tag.startswith("C"):
                continue
            body = el.tag[1:]
            cat = next((k for k in known if body.startswith(k)), None)
            if cat and (not cats_filter or cat in cats_filter):
                ids[cat].add(oid)
    return lex, official, pack, ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", action="store_true", help="只列未识别词")
    ap.add_argument("--min", type=int, default=1, help="--tokens 的最小词频")
    ap.add_argument("--cat", nargs="*", default=[], help="只处理指定类别")
    a = ap.parse_args()
    cats_filter = set(a.cat)

    with io.open(DICT, encoding="utf-8") as f:
        d = json.load(f)
    sfx, proper = dict(d["suffix"]), dict(d["proper"])

    lex, official, pack, ids = load_world(cats_filter)
    tr = Translator(lex, sfx, proper)

    def is_done(cat, oid):
        if has_cjk(official.get(cat, {}).get(oid, "")):
            return True
        return has_cjk(pack.get(cat, {}).get(oid, ""))

    if a.tokens:
        unk = collections.Counter()
        for cat, s in ids.items():
            for oid in s:
                if is_done(cat, oid):
                    continue
                for tok in camel(oid):
                    if tok in lex:
                        continue
                    _, ok = tr.lookup_tok(tok)
                    if not ok:
                        unk[tok] += 1
        rows = [(k, n) for k, n in unk.most_common() if n >= a.min]
        out = os.path.join(WORK, "_tokens.txt")
        with io.open(out, "w", encoding="utf-8") as w:
            w.write("# 未识别片段: %d 个不同词, 覆盖 %d 次出现\n"
                    % (len(rows), sum(n for _, n in rows)))
            for k, n in rows:
                w.write("%s\t%d\n" % (k, n))
        print("已出 %s —— %d 个不同词(>=%d 次), 合计出现 %d 次"
              % (out, len(rows), a.min, sum(n for _, n in rows)))
        return

    os.makedirs(OUTDIR, exist_ok=True)
    stats = collections.Counter()
    per_cat = []
    for cat in sorted(ids, key=lambda k: -len(ids[k])):
        todo = sorted(o for o in ids[cat] if not is_done(cat, o))
        if not todo:
            continue
        fp = os.path.join(OUTDIR, cat + ".txt")
        cs = collections.Counter()
        with io.open(fp, "w", encoding="utf-8") as w:
            w.write("// %s —— 自动汉化草稿 %d 条\n" % (cat, len(todo)))
            w.write("// 并入 Editor\\LocalizedData\\ObjectStrings.txt\n\n")
            for oid in todo:
                text, conf = tr.render(oid)
                cs[conf] += 1
                stats[conf] += 1
                w.write("%s/Name/%s=%s\t// %s\n" % (cat, oid, text, conf))
        per_cat.append((cat, len(todo), cs["high"], cs["low"], cs["none"]))

    total = sum(stats.values())
    print("草稿目录: %s" % OUTDIR)
    print("待补 %d 条 —— 全译 %d (%.1f%%) / 含英文残留 %d"
          % (total, stats["high"], 100.0 * stats["high"] / max(total, 1),
             stats["low"] + stats["none"]))
    for cat, n, h, lo, no in per_cat[:12]:
        print("  %-16s %6d  全译 %6d  残留 %6d" % (cat, n, h, lo + no))


if __name__ == "__main__":
    main()
