# -*- coding: utf-8 -*-
"""Apply the polish dictionaries to every value in OfficialDependencyNames.tsv.

Rewrites the whole table in place (id + @display sections, @model lines kept
untouched).  Idempotent: a second run over polished data changes nothing, so
it can be re-run safely after a CASC regeneration.

Usage:
    python -X utf8 tools/apply_polish.py            # apply
    python -X utf8 tools/apply_polish.py --report   # apply + write residue report
"""
import re
import sys
from collections import Counter

sys.path.insert(0, r"e:\Code\sc2\Work\sc2ed_dpifix\tools")
from polish_terms import (UNIT_ZH, NAME_ZH, WAR3_ZH, WORD_ZH, PHRASE_FIX,
                          VALUE_FIX, is_code)

TSV = r"e:\Code\sc2\Work\sc2ed_dpifix\packages\hook\OfficialDependencyNames.tsv"
OUT_UNMATCHED = r"e:\Code\sc2\Work\sc2ed_dpifix\tools\polish_unmatched.txt"

# tokens considered for dictionary lookup: ascii alnum runs led by a letter
# (hyphens excluded so "250mm-180" is never swallowed whole).
TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9@']*")
CJK = re.compile(r"[一-鿿]")
CJK_GAP = re.compile(r"(?<=[一-鿿。：，、])\s+(?=[一-鿿。：，、])")
CJK_DASH = re.compile(r"(?<=[一-鿿。：，、])\s*-\s*-(?=[一-鿿。：，、])")
SPACE_DASH = re.compile(r"\s+\-")
MULTI_DASH = re.compile(r"\-{3,}")
TRAIL = re.compile(r"[\s\-]+$")
PARTS = re.compile(r"[A-Z][a-z]*|[a-z]+|[0-9]+")


def lookup(word: str):
    """Dictionary priority: names > war3 > units > words."""
    for d in (NAME_ZH, WAR3_ZH, UNIT_ZH, WORD_ZH):
        if word in d:
            return d[word]
    return None


def translate_token(word: str):
    zh = lookup(word)
    if zh is not None:
        return zh
    if is_code(word):
        return word
    # split CamelCase / digit decorations: "Planets00" -> 行星00,
    # "DataMine" -> 数据地雷, "MP03010" -> kept (code part)
    parts = PARTS.findall(word)
    if parts and "".join(parts) == word:
        out, ok = [], True
        for p in parts:
            if p.isdigit():
                out.append(p)
                continue
            zh = lookup(p)
            if zh is None and is_code(p):
                out.append(p)
            elif zh is not None:
                out.append(zh)
            else:
                ok = False
                break
        if ok:
            return "".join(out)
    return None  # unmatched


ARROW = ""

def polish(value: str, unmatched: Counter):
    value = value.replace("->", ARROW)
    if value in VALUE_FIX:
        return VALUE_FIX[value]
    for bad, good in PHRASE_FIX.items():
        if bad in value:
            value = value.replace(bad, good)
    # never touch rich-text markup (paths, <img> tags)
    if "<" in value or "path=" in value:
        return value
    if not CJK.search(value):
        return value  # pure-ascii structural values stay verbatim

    def repl(m):
        w = m.group(0)
        zh = translate_token(w)
        if zh is None:
            unmatched[w] += 1
            return w
        return zh

    value = TOKEN.sub(repl, value)
    # spacing cleanup between chinese segments
    value = CJK_GAP.sub("", value)
    value = CJK_DASH.sub("-", value)
    value = SPACE_DASH.sub("-", value)
    value = MULTI_DASH.sub("-", value)
    value = re.sub(r"(?<=[一-鿿])-\s+", "-", value)
    value = TRAIL.sub("", value)
    return value.replace(ARROW, "->")


def main():
    apply = "--report" in sys.argv or True
    unmatched = Counter()
    changed = 0
    total = 0
    out_lines = []
    with open(TSV, encoding="utf-8") as fh:
        for line in fh.read().splitlines():
            if not line or line.startswith("#") or "\t" not in line:
                out_lines.append(line)
                continue
            key, _, value = line.partition("\t")
            total += 1
            if key.startswith("@model:"):
                out_lines.append(line)
                continue
            new = polish(value, unmatched)
            if new != value:
                changed += 1
            out_lines.append(f"{key}\t{new}")

    with open(TSV, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out_lines) + "\n")

    with open(OUT_UNMATCHED, "w", encoding="utf-8") as fh:
        for w, n in unmatched.most_common():
            fh.write(f"{n}\t{w}\n")

    print(f"values={total} changed={changed} unmatched-tokens={len(unmatched)}")


if __name__ == "__main__":
    main()
