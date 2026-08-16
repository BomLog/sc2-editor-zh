import _casc

inst = _casc.open(r"D:\StarCraft II")
ok, fh = _casc.open_file(inst, "mods\\core.sc2mod\\zhcn.sc2data\\localizeddata\\gamestrings.txt")
print("open_file ->", ok, fh)
r = _casc.read_file(fh)
print("read_file type:", type(r), "len:", len(r) if hasattr(r, '__len__') else '?')
print("repr:", repr(r))
for i, x in enumerate(r):
    print("  [%d] type=%s repr=%r" % (i, type(x).__name__, x if not isinstance(x, (bytes, bytearray)) else x[:80]))
_casc.close_file(fh)
_casc.close(inst)
