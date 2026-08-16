import _casc

inst = _casc.open(r"D:\StarCraft II")
h = _casc.find_first_file(inst, "*zhcn*localizeddata*triggerstrings.txt")
print("first:", repr(h)[:300])
if isinstance(h, tuple):
    ptr, meta = h
    print("meta:", meta)
    # try signatures for next
    for desc, fn in [
        ("next(inst)", lambda: _casc.find_next_file(inst)),
        ("next(inst, ptr)", lambda: _casc.find_next_file(inst, ptr)),
        ("next(ptr, inst)", lambda: _casc.find_next_file(ptr, inst)),
    ]:
        try:
            r = fn()
            print(desc, "->", repr(r)[:300])
        except Exception as e:
            print(desc, "ERR", type(e).__name__, e)
_casc.close(inst)
