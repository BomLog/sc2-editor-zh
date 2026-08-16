from pathlib import Path
from collections import Counter

LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

for fname in ["ObjectStrings.txt", "TriggerStrings.txt"]:
    p = LDR / fname
    keys = set()
    dup = 0
    bad = 0
    nochinese = Counter()
    catprefixed = Counter()
    for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line or line.lstrip().startswith("//"):
            continue
        if "=" not in line:
            bad += 1
            continue
        k, v = line.split("=", 1)
        if k in keys:
            dup += 1
        keys.add(k)
        body = v.split("///", 1)[0].split("//", 1)[0].strip()
        c = k.split("/", 1)[0] if "/" in k else ""
        if not hascjk(body):
            nochinese[c] += 1
        elif " - " in body and not hascjk(body.split(" - ", 1)[-1]):
            catprefixed[c] += 1
    print(f"{fname}: keys={len(keys)} dup={dup} malformed={bad}")
    print("  remaining_no_chinese:", dict(nochinese))
    print("  remaining_catprefixed:", dict(catprefixed))
