import collections
from pathlib import Path

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

def parse(path):
    d = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k] = v.strip()
    return d

ext = Path(r"D:\StarCraft II\Editor\EditorCatalogStrings.txt")
casc = Path(r"E:\Code\sc2\Work\casc_export\core_editorcatalogstrings.txt")
d_ext = parse(ext)
d_casc = parse(casc)
print("external keys:", len(d_ext), "  casc keys:", len(d_casc))

# untranslated external entries
untrans = {k: v for k, v in d_ext.items() if not hascjk(v)}
print("untranslated external:", len(untrans))

# overlap: does casc have Chinese for these?
found = 0
missing = 0
by_kind = collections.Counter()
samples_found = []
for k, v in untrans.items():
    cv = d_casc.get(k)
    if cv and hascjk(cv):
        found += 1
        kind = k.split("_", 2)[1] if k.startswith("EDSTR_") else "?"
        by_kind[kind] += 1
        if len(samples_found) < 20:
            samples_found.append((k, v, "->", cv))
    else:
        missing += 1

print("casc has Chinese for:", found)
print("casc missing/English:", missing)
for kind, n in by_kind.most_common():
    print("   ", kind, n)
print("\n=== samples (external -> official) ===")
for k, v, _, cv in samples_found:
    print(f"  {k}\n      {v}\n    ->{cv}")
