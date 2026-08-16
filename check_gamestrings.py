import collections
from pathlib import Path

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

p = Path(r"D:\StarCraft II\Editor\LocalizedData\GameStrings.txt")
keys = set()
dup = 0
bad = 0
nochinese = 0
total = 0
for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if not line or line.lstrip().startswith("//"):
        continue
    if "=" not in line:
        bad += 1
        continue
    k, v = line.split("=", 1)
    total += 1
    if k in keys:
        dup += 1
    keys.add(k)
    body = v.split("///", 1)[0].split("//", 1)[0].strip()
    if not hascjk(body):
        nochinese += 1
print(f"GameStrings.txt: lines={total} unique_keys={len(keys)} dup={dup} malformed={bad} no_chinese={nochinese}")
# spot check appended actor entries
for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if line.startswith(("Actor/Name/ACss=", "Actor/Name/AFOD=", "Effect/Name/DUWEAP=", "CWeapon=", "Validator/Name/Burrowing=")):
        print("   ", line[:80])
