import json
from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")
plan = json.loads((WORK / "opaque_plan.json").read_text(encoding="utf-8"))
ids = plan["to_translate"]
BATCH = 350
n = 0
for i in range(0, len(ids), BATCH):
    chunk = ids[i:i + BATCH]
    (WORK / f"opaque_input_{n:02d}.json").write_text(
        json.dumps(chunk, ensure_ascii=False, indent=1), encoding="utf-8")
    n += 1
print("chunks:", n, "ids:", len(ids))
