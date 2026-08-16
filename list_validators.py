import re
from pathlib import Path

LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

def hasalpha(v):
    return bool(re.search(r"[A-Za-z]", v))

# validators needing translation
print("=== validators: category-prefixed or mixed English ===")
vals = []
for line in (LDR / "ObjectStrings.txt").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if line.startswith("Validator/Name/"):
        k, v = line.split("=", 1)
        body = v.split("///", 1)[0].split("//", 1)[0].strip()
        if body.startswith("验证器 - "):
            vals.append((k, body))
print("category-prefixed validators:", len(vals))
for k, b in vals:
    print("   ", k, "=", b)
