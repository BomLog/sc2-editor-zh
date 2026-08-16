#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""看某个词出现在哪些对象 ID 里, 用来判断是真英文词还是 war3 四字代号。
用法: python l10n_ctx.py East Edge Halo
"""
import io
import os
import re
import sys
import glob

DRAFT = r"e:\Code\sc2\Work\_draft"


def main():
    want = sys.argv[1:]
    hits = {w: [] for w in want}
    for fp in glob.glob(os.path.join(DRAFT, "*.txt")):
        cat = os.path.basename(fp)[:-4]
        for line in io.open(fp, encoding="utf-8"):
            if "\t" not in line:
                continue
            oid = line.split("\t")[0].strip()
            for w in want:
                if w in oid and len(hits[w]) < 6:
                    hits[w].append(cat + ":" + oid)
    for w in want:
        print(w, "->", ", ".join(hits[w]) or "(未出现)")


if __name__ == "__main__":
    main()
