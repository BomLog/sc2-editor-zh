import _casc
from pathlib import Path

inst = _casc.open(r"D:\StarCraft II")
OUT = Path(r"E:\Code\sc2\Work\casc_export")
files = {
    "core_editorcatalogstrings": r"mods\core.sc2mod\zhcn.sc2data\localizeddata\editor\editorcatalogstrings.txt",
    "core_editorcategorystrings": r"mods\core.sc2mod\zhcn.sc2data\localizeddata\editor\editorcategorystrings.txt",
    "core_editorstrings": r"mods\core.sc2mod\zhcn.sc2data\localizeddata\editor\editorstrings.txt",
}
for label, name in files.items():
    r = _casc.open_file(inst, name)
    ok = r[0] if isinstance(r, tuple) else r
    if not ok:
        print("MISS", label)
        continue
    fh = r[1]
    res = _casc.read_file(fh)
    data = res[1] if isinstance(res, tuple) else res
    _casc.close_file(fh)
    (OUT / (label + ".txt")).write_bytes(data)
    print("OK", label, len(data))
_casc.close(inst)
