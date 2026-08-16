import _casc

inst = _casc.open(r"D:\StarCraft II")
candidates = [
    r"mods\core.sc2mod\zhcn.sc2data\localizeddata\editor\editorcatalogstrings.txt",
    r"mods\core.sc2mod\zhcn.sc2data\localizeddata\editor\editorcategorystrings.txt",
    r"mods\core.sc2mod\zhcn.sc2data\localizeddata\editor\editorstrings.txt",
    r"mods\core.sc2mod\base.sc2data\localizeddata\editor\editorcatalogstrings.txt",
    r"mods\core.sc2mod\base.sc2data\localizeddata\editor\editorcategorystrings.txt",
]
for name in candidates:
    try:
        r = _casc.open_file(inst, name)
        ok = r[0] if isinstance(r, tuple) else r
        print(("EXISTS" if ok else "miss  "), name)
    except Exception as e:
        print("ERR   ", name, type(e).__name__)
_casc.close(inst)
