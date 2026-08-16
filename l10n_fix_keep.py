#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""分辨 "war3 四字代号" 与 "真英文词"。

war3 的对象 ID 就是 4 字代号本身(nadk / Ubal / AHex / hpea), 所以判据是:
  这个词单独构成整个 ID(去掉 @后缀 / 前导单字母 / 尾部数字)  -> 代号
  它跟别的词拼在一条更长的 ID 里(HomeLargeDoodad / CritNext)  -> 真英文词
两种都出现时按次数多的算。

判成真英文词的从 proper 摘出来待翻译; 判成代号的写回 proper 原样保留。
"""
import io
import json
import os
import re
import glob
import collections

DICT = r"e:\Code\sc2\Work\l10n_dict.json"
DRAFT = r"e:\Code\sc2\Work\_draft"
OUT = r"e:\Code\sc2\Work\_keep_audit.txt"

CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+")


def camel(s):
    return CAMEL.findall(s)


def main():
    with io.open(DICT, encoding="utf-8") as f:
        d = json.load(f)
    prop, sfx = d["proper"], d["suffix"]
    cand = set(k for k, v in prop.items() if k == v and len(k) >= 3)

    code = collections.Counter()
    word = collections.Counter()
    for fp in glob.glob(os.path.join(DRAFT, "*.txt")):
        for line in io.open(fp, encoding="utf-8"):
            if "\t" not in line:
                continue
            oid = line.split("\t")[0].split("/")[-1].split("=")[0]
            # 剥掉 @后缀
            core = oid.split("@")[0]
            toks = camel(core)
            # 剥掉尾部纯数字 token
            while toks and toks[-1].isdigit():
                toks.pop()
            # 剥掉前导单个大写字母(war3 技能/物品前缀 A / I ...)
            body = toks[1:] if (len(toks) > 1 and len(toks[0]) == 1
                                and toks[0].isupper()) else toks
            alone = body[0] if len(body) == 1 else None
            for t in set(toks):
                if t not in cand:
                    continue
                if t == alone:
                    code[t] += 1
                else:
                    word[t] += 1

    words, codes, unseen = [], [], []
    for t in sorted(cand):
        c, w = code[t], word[t]
        if c == 0 and w == 0:
            unseen.append(t)
        elif w > c:
            words.append((t, w, c))
        else:
            codes.append((t, c, w))

    for t, _, _ in words:
        del prop[t]
    with io.open(DICT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("== 判为真英文词(已从 proper 摘出, 待翻译) %d 个 ==\n" % len(words))
        f.write(" ".join("%s(%d/%d)" % x for x in words) + "\n\n")
        f.write("== 判为 war3 代号(保留原样) %d 个 ==\n" % len(codes))
        f.write(" ".join(t for t, _, _ in codes) + "\n\n")
        f.write("== 草稿中未出现 %d 个 ==\n" % len(unseen))
        f.write(" ".join(unseen) + "\n")
    print("真英文词 %d, 代号 %d, 未出现 %d -> %s"
          % (len(words), len(codes), len(unseen), OUT))
    print(" ".join(t for t, _, _ in words))


if __name__ == "__main__":
    main()
