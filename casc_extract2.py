import _casc
from pathlib import Path

inst = _casc.open(r"D:\StarCraft II")
OUT = Path(r"E:\Code\sc2\Work\casc_export")
OUT.mkdir(parents=True, exist_ok=True)

# (label, path-prefix, is_campaign)
mods = [
    ("core", r"mods\core.sc2mod", False),
    ("liberty", r"mods\liberty.sc2mod", False),
    ("libertymulti", r"mods\libertymulti.sc2mod", False),
    ("swarm", r"mods\swarm.sc2mod", False),
    ("swarmmulti", r"mods\swarmmulti.sc2mod", False),
    ("void", r"mods\void.sc2mod", False),
    ("voidmulti", r"mods\voidmulti.sc2mod", False),
    ("camp_liberty", r"campaigns\liberty.sc2campaign", True),
    ("camp_swarm", r"campaigns\swarm.sc2campaign", True),
    ("camp_void", r"campaigns\void.sc2campaign", True),
    ("camp_libertystory", r"campaigns\libertystory.sc2campaign", True),
    ("camp_swarmstory", r"campaigns\swarmstory.sc2campaign", True),
    ("camp_voidstory", r"campaigns\voidstory.sc2campaign", True),
    ("camp_swarmstoryutil", r"campaigns\swarmstoryutil.sc2mod", False),
]

for label, prefix, is_camp in mods:
    for ftype in ["triggerstrings", "gamestrings", "objectstrings"]:
        name = prefix + "\\zhcn.sc2data\\localizeddata\\" + ftype + ".txt"
        try:
            r = _casc.open_file(inst, name)
            ok = r[0] if isinstance(r, tuple) else r
            if not ok:
                continue
            fh = r[1]
            res = _casc.read_file(fh)
            data = res[1] if isinstance(res, tuple) else res
            _casc.close_file(fh)
            out = OUT / f"{label}_{ftype}.txt"
            out.write_bytes(data)
            print("OK ", out.name, len(data))
        except Exception as e:
            print("ERR", name, type(e).__name__, e)

_casc.close(inst)
print("done")
