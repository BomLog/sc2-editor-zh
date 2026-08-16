import json
from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

merged = json.loads((WORK / "translations.json").read_text(encoding="utf-8"))

added = 0
for p in sorted(WORK.glob("trans_output_*.json")) + sorted(WORK.glob("trans_zh_*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    for s, v in d.items():
        # skip: source already contains Chinese (already-localized, leave untouched)
        if hascjk(s):
            continue
        if isinstance(v, str) and hascjk(v) and s not in merged:
            merged[s] = v
            added += 1

(WORK / "translations.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
print("total translations:", len(merged), "(added", added, ")")
