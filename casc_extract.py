import _casc, os
from pathlib import Path

inst = _casc.open(r"D:\StarCraft II")
OUT = Path(r"E:\Code\sc2\Work\casc_export")
OUT.mkdir(parents=True, exist_ok=True)

files = {
    "core_gamestrings": r"mods\core.sc2mod\zhcn.sc2data\localizeddata\gamestrings.txt",
    "core_objectstrings": r"mods\core.sc2mod\zhcn.sc2data\localizeddata\objectstrings.txt",
    "core_triggerstrings": r"mods\core.sc2mod\zhcn.sc2data\localizeddata\triggerstrings.txt",
    "core_conversationstrings": r"mods\core.sc2mod\zhcn.sc2data\localizeddata\conversationstrings.txt",
    "core_errors": r"mods\core.sc2mod\zhcn.sc2data\localizeddata\errors.txt",
    "liberty_triggerstrings": r"campaigns\liberty.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    "swarm_triggerstrings": r"campaigns\swarm.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    "void_triggerstrings": r"campaigns\void.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    "libertystory_triggerstrings": r"campaigns\libertystory.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    "swarmstory_triggerstrings": r"campaigns\swarmstory.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    "voidstory_triggerstrings": r"campaigns\voidstory.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    "swarmstoryutil_triggerstrings": r"campaigns\swarmstoryutil.sc2mod\zhcn.sc2data\localizeddata\triggerstrings.txt",
    "swarmstoryutil_gamestrings": r"campaigns\swarmstoryutil.sc2mod\zhcn.sc2data\localizeddata\gamestrings.txt",
    "swarmstoryutil_objectstrings": r"campaigns\swarmstoryutil.sc2mod\zhcn.sc2data\localizeddata\objectstrings.txt",
}

for label, name in files.items():
    try:
        r = _casc.open_file(inst, name)
        ok = r[0] if isinstance(r, tuple) else r
        if not ok:
            print("MISS", label)
            continue
        fh = r[1]
        res = _casc.read_file(fh)
        data = res[1] if isinstance(res, tuple) else res
        _casc.close_file(fh)
        out = OUT / (label + ".txt")
        out.write_bytes(data)
        nlines = data.decode("utf-8-sig", errors="replace").count("\n")
        print("OK", label, len(data), "bytes,", nlines, "lines ->", out.name)
    except Exception as e:
        print("ERR", label, type(e).__name__, e)

_casc.close(inst)
print("done")
