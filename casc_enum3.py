import _casc

# inspect signatures
for fn in ['open', 'find_first_file', 'find_next_file', 'find_close', 'open_file', 'read_file', 'close_file']:
    f = getattr(_casc, fn)
    print(fn, "sig:", getattr(f, '__text_signature__', None), "| ann:", getattr(f, '__annotations__', None))

inst = _casc.open(r"D:\StarCraft II")

def enum(mask, cap=60):
    out = []
    h = _casc.find_first_file(inst, mask)
    while h is not None and isinstance(h, tuple) and h[0]:
        out.append(h[1])
        if len(out) >= cap:
            break
        nxt = _casc.find_next_file(inst)
        h = nxt
    return out

for mask in ["*.txt", "*gamestrings.txt", "*objectstrings.txt"]:
    r = enum(mask, cap=60)
    print("mask", mask, "-> count", len(r))
    for m in r[:5]:
        print("   ", m["filename"], m["file_size"])

_casc.close(inst)
