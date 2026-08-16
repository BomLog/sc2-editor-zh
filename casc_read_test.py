import _casc, sys

inst = _casc.open(r"D:\StarCraft II")

def read_one(name):
    ok, fh = _casc.open_file(inst, name)
    if not ok:
        print("open failed:", name)
        return None
    data = _casc.read_file(fh)
    _casc.close_file(fh)
    return data

# 1) read the core zhcn gamestrings and print a sample
data = read_one("mods\\core.sc2mod\\zhcn.sc2data\\localizeddata\\gamestrings.txt")
print("gamestrings.txt bytes:", None if data is None else len(data))
if data:
    txt = data.decode("utf-8-sig", errors="replace")
    lines = txt.splitlines()
    print("lines:", len(lines))
    for l in lines[:8]:
        print("  ", l)

# 2) enumerate all zhcn localizeddata string files with correct handler chaining
print("=== enumerate *zhcn*localizeddata*.txt ===")
h = _casc.find_first_file(inst, "*zhcn*localizeddata*.txt")
count = 0
hh = h
while hh is not None and hh != 0:
    ptr, meta = hh
    print("  ", meta.get("filename"), meta.get("file_size"), "local" if meta.get("exists_locally") else "cdns")
    count += 1
    hh = _casc.find_next_file(ptr)
try:
    _casc.find_close(h[0] if isinstance(h, tuple) else h)
except Exception as e:
    print("find_close err", e)
print("total zhcn localizeddata txt files:", count)

_casc.close(inst)
