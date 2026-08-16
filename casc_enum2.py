import _casc

inst = _casc.open(r"D:\StarCraft II")

def enum(mask, cap=200):
    out = []
    h = _casc.find_first_file(inst, mask)
    while h is not None and isinstance(h, tuple) and h[0]:
        out.append(h[1])
        if len(out) >= cap:
            break
        h = _casc.find_next_file(inst)
    return out

# test loop on a broad mask
r = enum("*triggerstrings.txt", cap=200)
print("total *triggerstrings.txt matches (cap 200):", len(r))
for m in r:
    print("  ", m["filename"], m["file_size"])

_casc.close(inst)
