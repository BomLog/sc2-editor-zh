from pathlib import Path
EXP = Path(r"E:\Code\sc2\Work\casc_export")
EXT_O = Path(r"D:\StarCraft II\Editor\LocalizedData\ObjectStrings.txt")

def parse(path, maxn=100000):
    d = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k] = v
        if len(d) >= maxn:
            break
    return d

# official liberty objectstrings keys
off = parse(EXP / "liberty_objectstrings.txt")
print("=== official liberty_objectstrings key samples ===")
for k in list(off)[:30]:
    print("  ", k, "=", off[k][:40])

# external objectstrings keys (Actor/Name sample + Validator/Name sample)
ext = parse(EXT_O)
print("\n=== external ObjectStrings Actor/Name samples ===")
n = 0
for k, v in ext.items():
    if k.startswith("Actor/Name/"):
        print("  ", k, "=", v[:40])
        n += 1
        if n >= 10:
            break

print("\n=== official keys containing 'ACss' or 'DUWEAP' or 'Burrowing' ===")
for stem in ["liberty_objectstrings", "camp_liberty_objectstrings", "core_objectstrings",
             "liberty_gamestrings", "camp_liberty_gamestrings", "core_gamestrings"]:
    p = EXP / (stem + ".txt")
    if not p.exists():
        continue
    d = parse(p)
    hits = [k for k in d if any(t in k for t in ["ACss", "DUWEAP", "Burrowing", "Validator/Name/IsFlying"])]
    print(f"  {stem}: {len(hits)} hits")
    for k in hits[:5]:
        print("      ", k, "=", d[k][:50])
