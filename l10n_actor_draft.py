#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
演算体(Actor)汉化草稿生成器 —— 银河编辑器内部 mod。

原理: 演算体 ID = 「某个已有官方译名的对象 ID」+「用途后缀」,
例如 HighTemplarPsiStormModel = 高阶圣堂武士 + 灵能风暴 + 模型。
所以:
  1. 从 CASC 各 mod 的 zhCN GameStrings 收官方译名, 建 ID -> 中文 词表;
  2. 从 OB 汉化包已译的演算体反推「后缀 -> 中文」的既有风格, 与 l10n_dict.json 合并;
  3. 缺译 ID 按 CamelCase 切词, 在词边界上做最长匹配, 逐段翻译;
  4. 输出草稿 + 置信度, 人工过一遍再并入 Editor\LocalizedData\ObjectStrings.txt。

用法:
  python l10n_actor_draft.py                     # 全部 mod
  python l10n_actor_draft.py core liberty        # 指定 mod
  python l10n_actor_draft.py --unknown           # 只列未识别高频词(用于补词典)
"""
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
PACK = os.path.join(GAME, "Editor", "LocalizedData", "ObjectStrings.txt")
DICT = os.path.join(WORK, "l10n_dict.json")
DRAFT = os.path.join(WORK, "_actor_draft.txt")
SEP = "\\"

# 官方 GameStrings 里同名 ID 撞车时的类别优先级
CAT_PRI = ["Unit", "Abil", "Effect", "Behavior", "Weapon", "Upgrade",
           "Button", "Model", "Actor", "Item", "Hero", "Doodad", "Sound"]

# 中性片段: 全大写缩写(AS/MP/SI/LM)、单字母变体标记、带编号的重复项(Attack1)
NEUTRAL = re.compile(r"^(?:[A-Z]{1,4}\d*|[A-Za-z]+\d+)$")


def GOOD_NAME(s):
    """排除带 UI 标记 / 换行 / 过长的条目, 这类不是干净的对象名。"""
    if len(s) > 24 or "<" in s or "\n" in s or "%" in s:
        return False
    return True


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
    """CamelCase / 下划线 / 数字切词, 大写缩写(如 UI/SCV/HotS)整段保留。"""
    return re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+", s)


def clean_name(v):
    """剥掉部分 mod 里的 '中文 /// English' 双语尾巴与首尾空白。"""
    return v.split("///")[0].strip()


def actor_ids(xml_text):
    try:
        root = ET.fromstring(xml_text)
        return [el.get("id") for el in root
                if el.tag.startswith("C") and "Actor" in el.tag and el.get("id")]
    except ET.ParseError:
        return re.findall(r'<C\w*Actor\w*\b[^>]*?\bid="([^"]+)"', xml_text)


def mod_label(path):
    parts = path.split(SEP)
    segs = [p for p in parts if p.endswith(".sc2mod")]
    if not segs:
        return parts[1] if len(parts) > 1 else path
    return segs[-1][: -len(".sc2mod")]


class Translator:
    """按 CamelCase 词边界做最长匹配的分段翻译器。"""

    def __init__(self, lex, sfx, proper):
        self.lex = lex          # 对象 ID -> 官方中文
        self.sfx = sfx          # 后缀词 -> 中文
        self.proper = proper    # 专有名词 -> 中文
        # 词表也建成「切词后拼接」的索引, 保证匹配落在词边界上
        self.lex_tok = {}
        for k, v in lex.items():
            self.lex_tok.setdefault(tuple(camel(k)), v)

    def render(self, aid):
        """-> (草稿, 置信度)  high=全部命中 / low=有未识别片段 / none=没吃到对象名"""
        toks = camel(aid)
        parts, hit_obj, unknown = [], False, 0
        i = 0
        while i < len(toks):
            matched = False
            # 1) 最长匹配官方对象名(>=1 段, 优先长的)
            for n in range(min(len(toks) - i, 8), 0, -1):
                key = tuple(toks[i:i + n])
                if n == 1 and len(key[0]) <= 2:
                    continue                      # 单个极短片段不当对象名
                v = self.lex_tok.get(key)
                if v:
                    parts.append(v)
                    hit_obj = True
                    i += n
                    matched = True
                    break
            if matched:
                continue
            tok = toks[i]
            # 带尾号的片段(Attack1)先剥号再查, 译文保留编号
            m = re.match(r"^([A-Za-z]+?)(\d+)$", tok)
            stem, num = (m.group(1), m.group(2)) if m else (tok, "")
            if tok in self.proper:
                parts.append(self.proper[tok])
            elif tok in self.sfx:
                parts.append(self.sfx[tok])
            elif num and stem in self.sfx:
                parts.append(self.sfx[stem] + num)
            elif num and stem in self.proper:
                parts.append(self.proper[stem] + num)
            elif tok.isdigit() or NEUTRAL.match(tok):
                parts.append(tok)                 # 编号 / 变体标记, 原样保留且不计未识别
            else:
                parts.append(tok)                 # 保留原文, 计为未识别
                unknown += 1
            i += 1
        # 首段是对象名时用「-」分隔用途, 贴合 OB 包既有风格
        if hit_obj and len(parts) > 1:
            out = parts[0] + "-" + "".join(parts[1:])
        else:
            out = "".join(parts)
        conf = "none" if not hit_obj else ("high" if unknown == 0 else "low")
        return out, conf


def learn_suffix(pack, tr):
    """从已译演算体反推后缀习惯用法: id 去掉对象名后的单段尾巴 -> 译文尾巴。"""
    pair = collections.defaultdict(collections.Counter)
    for aid, zh in pack.items():
        if not has_cjk(zh):
            continue
        toks = camel(aid)
        base_zh, used = None, 0
        for n in range(min(len(toks), 8), 0, -1):
            v = tr.lex_tok.get(tuple(toks[:n]))
            if v:
                base_zh, used = v, n
                break
        if not base_zh or not zh.startswith(base_zh):
            continue
        tail_toks = toks[used:]
        tail_zh = zh[len(base_zh):].lstrip("-— ")
        if len(tail_toks) == 1 and tail_zh and has_cjk(tail_zh):
            pair[tail_toks[0]][tail_zh] += 1
    return {k: c.most_common(1)[0][0] for k, c in pair.items() if sum(c.values()) >= 2}


def load_all(only):
    c = cr.Casc()
    c.open(GAME)
    txts = c.list_paths((".xml", ".txt"))

    lex, pri = {}, {}
    for p in (x for x in txts if x.endswith("gamestrings.txt") and "zhcn" in x):
        for line in dec(c.read(p)).splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            bits = k.split("/")
            if len(bits) != 3 or bits[1] != "Name" or not has_cjk(v):
                continue
            cat, oid = bits[0], bits[2]
            name = clean_name(v)
            if not name or not has_cjk(name) or not GOOD_NAME(name):
                continue
            # 被改过的 balancemulti* 系列降权, 官方 mod 优先
            rank = CAT_PRI.index(cat) if cat in CAT_PRI else len(CAT_PRI)
            if "balancemulti" in p:
                rank += 100
            if oid not in lex or rank < pri.get(oid, 999):
                lex[oid], pri[oid] = name, rank

    pack = {}
    for line in dec(open(PACK, "rb").read()).splitlines():
        if line.startswith("Actor/Name/") and "=" in line:
            k, v = line.split("=", 1)
            pack[k[len("Actor/Name/"):]] = v.split("\t")[0].strip()

    by_mod = collections.OrderedDict()
    for p in sorted(x for x in txts if x.endswith("actordata.xml") and x.startswith("mods")):
        m = mod_label(p)
        if only and m.lower() not in only:
            continue
        by_mod.setdefault(m, set()).update(actor_ids(dec(c.read(p))))
    return lex, pack, by_mod


def main():
    args = [a for a in sys.argv[1:]]
    unknown_mode = "--unknown" in args
    only = {a.lower() for a in args if not a.startswith("--")}

    with io.open(DICT, encoding="utf-8") as f:
        d = json.load(f)
    sfx, proper = dict(d["suffix"]), dict(d["proper"])

    lex, pack, by_mod = load_all(only)
    tr = Translator(lex, sfx, proper)
    learned = learn_suffix(pack, tr)
    for k, v in learned.items():
        sfx.setdefault(k, v)
    tr = Translator(lex, sfx, proper)

    done = {k for k, v in pack.items() if has_cjk(v)}

    if unknown_mode:
        unk = collections.Counter()
        for ids in by_mod.values():
            for aid in ids:
                if aid in done:
                    continue
                for tok in camel(aid):
                    if tok in sfx or tok in proper or tok in lex or tok.isdigit():
                        continue
                    unk[tok] += 1
        print("未识别片段 Top80(补进 l10n_dict.json 可提升置信度):")
        for k, n in unk.most_common(80):
            print("  %-24s %d" % (k, n))
        return

    stats = collections.Counter()
    with io.open(DRAFT, "w", encoding="utf-8") as w:
        w.write("// 演算体汉化草稿 —— 自动生成, 人工校对后并入\n")
        w.write("//   " + os.path.join(GAME, "Editor", "LocalizedData", "ObjectStrings.txt") + "\n")
        w.write("// 置信度 high=对象名+后缀全命中 / low=含未识别英文 / none=未命中对象名\n")
        w.write("// 词表 %d 条, 后缀 %d 条(其中自学 %d 条), 专名 %d 条\n\n"
                % (len(lex), len(sfx), len(learned), len(proper)))
        for m, ids in by_mod.items():
            todo = sorted(i for i in ids if i not in done)
            if not todo:
                continue
            w.write("\n// ===== %s  待补 %d / 共 %d =====\n" % (m, len(todo), len(ids)))
            for aid in todo:
                text, conf = tr.render(aid)
                stats[conf] += 1
                w.write("Actor/Name/%s=%s\t// %s\n" % (aid, text, conf))
    total = sum(stats.values())
    print("草稿已出: %s" % DRAFT)
    print("待补 %d 条 —— high %d (%.0f%%) / low %d / none %d"
          % (total, stats["high"], 100.0 * stats["high"] / max(total, 1),
             stats["low"], stats["none"]))
    print("自学后缀 %d 条, 词表 %d 条" % (len(learned), len(lex)))


if __name__ == "__main__":
    main()
