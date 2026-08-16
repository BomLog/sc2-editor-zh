import collections
from pathlib import Path

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

p = Path(r"D:\StarCraft II\Editor\EditorCatalogStrings.txt")
total = collections.Counter()
nocz = collections.Counter()
samples = collections.defaultdict(list)
for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if not line or line.lstrip().startswith("//") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    # prefix = the EDSTR_xxx part (up to second underscore for sub-type, else first)
    # e.g. EDSTR_FIELDNAME_Abil_... -> EDSTR_FIELDNAME
    if k.startswith("EDSTR_"):
        prefix = k.split("_", 2)[1]  # e.g. FIELDNAME, ACTORSUBNAMEHINT, ...
        kind = "EDSTR_" + prefix
    else:
        kind = k.split("/")[0] if "/" in k else "(other)"
    total[kind] += 1
    v = v.strip()
    if not hascjk(v):
        nocz[kind] += 1
        if len(samples[kind]) < 10:
            samples[kind].append((k, v))

print("=== EditorCatalogStrings.txt untranslated (no Chinese) by kind ===")
for kind in sorted(total):
    t = total[kind]; n = nocz[kind]
    print(f"  {kind:28s} total={t:6d}  no_chinese={n:6d}")
print("\n=== samples ===")
for kind in sorted(samples):
    for k, v in samples[kind]:
        print(f"  {k} = {v[:70]}")
