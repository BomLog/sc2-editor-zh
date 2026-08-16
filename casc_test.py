import _casc

def try_path(path):
    print("=== open", path, "===")
    inst = _casc.open(path)
    print("  inst =", repr(inst))
    # try a few masks
    for mask in ["*", "*.txt", "*localizeddata*"]:
        try:
            h = _casc.find_first_file(inst, mask)
            print("  find_first_file(inst, %r) -> %r" % (mask, h))
            if h is not None and h != 0:
                # walk a few
                n = 0
                hh = h
                while hh not in (None, 0) and n < 5:
                    n += 1
                    print("      entry", n, "=", repr(hh))
                    hh = _casc.find_next_file(hh)
                _casc.find_close(h)
        except Exception as e:
            print("  find error (%r): %s: %s" % (mask, type(e).__name__, e))
    # try opening a known-ish file
    for name in ["mods/core.sc2mod/zhcn.sc2data/localizeddata/gamestrings.txt",
                 "mods\\core.sc2mod\\zhcn.sc2data\\localizeddata\\gamestrings.txt"]:
        try:
            fh = _casc.open_file(inst, name)
            print("  open_file(%r) -> %r" % (name, fh))
        except Exception as e:
            print("  open_file(%r) error: %s: %s" % (name, type(e).__name__, e))
    _casc.close(inst)

for p in [r"D:\StarCraft II", r"D:\StarCraft II\SC2Data"]:
    try_path(p)
