import json
from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

# sample chunk 04 (fully translated) for quality
print("=== chunk 04 samples ===")
tr4 = json.loads((WORK / "trans_output_04.json").read_text(encoding="utf-8"))
for i, (k, v) in enumerate(tr4.items()):
    if i < 20:
        print(f"  {k} -> {v}")

# merge all 4 outputs' CHINESE entries into translations.json
merged = json.loads((WORK / "translations.json").read_text(encoding="utf-8"))
added = 0
for n in ["04", "13", "20", "29"]:
    p = WORK / f"trans_output_{n}.json"
    if not p.exists():
        continue
    tr = json.loads(p.read_text(encoding="utf-8"))
    for s, v in tr.items():
        if isinstance(v, str) and hascjk(v) and s not in merged:
            merged[s] = v
            added += 1
(WORK / "translations.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nmerged: added {added}, total now {len(merged)}")
