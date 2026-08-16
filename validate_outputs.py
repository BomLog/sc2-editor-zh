import json
from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

for n in ["04", "13", "20", "29"]:
    inp = WORK / f"trans_input_{n}.json"
    outp = WORK / f"trans_output_{n}.json"
    if not outp.exists():
        print(f"{n}: MISSING output")
        continue
    try:
        src = json.loads(inp.read_text(encoding="utf-8"))
        tr = json.loads(outp.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"{n}: PARSE ERROR {e}")
        continue
    missing = [s for s in src if s not in tr]
    extra = [s for s in tr if s not in src]
    zh = sum(1 for v in tr.values() if isinstance(v, str) and hascjk(v))
    unchanged = sum(1 for s, v in tr.items() if v == s)
    print(f"{n}: src={len(src)} out={len(tr)} missing={len(missing)} extra={len(extra)} "
          f"chinese={zh} unchanged={unchanged}")
    if missing[:3]:
        print("   missing sample:", missing[:3])
    if extra[:3]:
        print("   extra sample:", extra[:3])
