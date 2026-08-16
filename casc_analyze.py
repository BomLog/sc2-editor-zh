import json, re
from pathlib import Path
from collections import Counter

EXP = Path(r"E:\Code\sc2\Work\casc_export")
WORK = Path(r"E:\Code\sc2\Work")

def parse(path):
    d = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k] = v
    return d

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

# load extracted files
extracted = {}
for p in sorted(EXP.glob("*.txt")):
    d = parse(p)
    extracted[p.stem] = d
    # category breakdown
    cats = Counter()
    for k in d:
        cats[k.split("/", 1)[0] if "/" in k else "(none)"] += 1
    print("=== %s: %d keys" % (p.stem, len(d)))
    for c, n in cats.most_common(12):
        print("    %s: %d" % (c, n))

# check overlap with external untranslated keys
plan = json.loads((WORK / "translate_plan.json").read_text(encoding="utf-8"))
untrans = plan["entries"]

# map each extracted file's keys for lookup
print("\n=== overlap of untranslated external keys with official files ===")
by_file = Counter()
found_total = 0
missing = []
for e in untrans:
    key = e["key"]
    hit = None
    for stem, d in extracted.items():
        if key in d and hascjk(d[key]):
            hit = stem
            break
    if hit:
        by_file[hit] += 1
        found_total += 1
    else:
        missing.append(key)

print("untranslated entries:", len(untrans))
print("found in official:", found_total)
print("still missing:", len(missing))
for stem, n in by_file.most_common():
    print("  from", stem, ":", n)
print("missing sample:")
for k in missing[:30]:
    print("   ", k)
