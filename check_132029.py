import json, re
from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")

for n in ["13", "20", "29"]:
    outp = WORK / f"trans_output_{n}.json"
    if not outp.exists():
        print(f"{n}: no output")
        continue
    tr = json.loads(outp.read_text(encoding="utf-8"))
    # find over-translated: source has no whitespace (single token) but translation differs
    over = [(s, v) for s, v in tr.items() if v != s and not re.search(r"\s", s)]
    # find under-translated: source has whitespace (descriptive) but translation unchanged
    under = [s for s, v in tr.items() if v == s and re.search(r"\s", s)]
    print(f"chunk {n}: total={len(tr)} over-translated-single-token={len(over)} under-translated-whitespace={len(under)}")
    for s, v in over[:10]:
        print(f"   OVER: {s} -> {v}")
    for s in under[:10]:
        print(f"   UNDER: {s}")
