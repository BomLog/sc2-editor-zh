import re, collections
from pathlib import Path

LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

CATS = {}
samples = collections.defaultdict(list)
for line in (LDR / "ObjectStrings.txt").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if "=" not in line:
        continue
    k, v = line.split("=", 1)
    body = v.split("///", 1)[0].split("//", 1)[0].strip()
    cat = k.split("/", 1)[0] if "/" in k else ""
    field = k.split("/")[1] if "/" in k and len(k.split("/")) > 1 else ""
    if field != "Name":
        continue
    if " - " in body:
        head, tail = body.split(" - ", 1)
        if hascjk(head) and not hascjk(tail):
            CATS[cat] = CATS.get(cat, 0) + 1
            if len(samples[cat]) < 15:
                samples[cat].append(tail)

print("=== category-prefixed Name entries (opaque IDs) ===")
for cat in sorted(CATS, key=lambda c: -CATS[c]):
    print(f"\n[{cat}] count={CATS[cat]}")
    for s in samples[cat]:
        print("   ", s)
