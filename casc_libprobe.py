from pathlib import Path
from collections import Counter
import _casc

EXT = Path(r"D:\StarCraft II\Editor\LocalizedData\TriggerStrings.txt")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

# library prefix of untranslated external trigger entries
c = Counter()
for line in EXT.read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if not line or line.lstrip().startswith("//") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    body = v.split("///", 1)[0].split("//", 1)[0].strip()
    if not body or hascjk(body):
        continue
    # category-prefixed still counts (X - English)
    if " - " in body:
        tail = body.split(" - ", 1)[1]
        if hascjk(tail):
            continue
    # extract library prefix: <LibName>/<Field>/<lib_XXXX_hash>
    seg = k.split("/")
    name = seg[-1] if seg else k
    if "_" in name and name.startswith("lib_"):
        parts = name.split("_")
        lib = parts[0] + "_" + parts[1] if len(parts) >= 2 else name
        c[lib] += 1
    else:
        c["(no-lib-prefix)"] += 1

print("=== untranslated trigger entries by library prefix ===")
for lib, n in c.most_common(40):
    print(f"  {lib:24s} {n}")

# probe more mods for triggerstrings
print("\n=== probe additional mods ===")
inst = _casc.open(r"D:\StarCraft II")
mods = [
    "mods\\liberty.sc2mod", "mods\\libertymulti.sc2mod",
    "mods\\swarm.sc2mod", "mods\\swarmmulti.sc2mod",
    "mods\\void.sc2mod", "mods\\voidmulti.sc2mod",
    "mods\\starcoop.sc2mod", "mods\\war3.sc2mod", "mods\\heroes.sc2mod",
    "campaigns\\novacampaign.sc2campaign",
    "campaigns\\novastory.sc2campaign",
    "campaigns\\prologue.sc2campaign",
    "campaigns\\swarmstory.sc2campaign",
    "mods\\core.sc2mod",
]
for m in mods:
    name = m + "\\zhcn.sc2data\\localizeddata\\triggerstrings.txt"
    try:
        r = _casc.open_file(inst, name)
        ok = r[0] if isinstance(r, tuple) else r
        print(("  EXISTS " if ok else "  miss   "), name)
    except Exception as e:
        print("  ERR    ", name, type(e).__name__)
_casc.close(inst)
