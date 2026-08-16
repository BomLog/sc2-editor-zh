import json
from pathlib import Path

plan = json.loads(Path(r"E:\Code\sc2\Work\translate_plan.json").read_text(encoding="utf-8"))
strs = plan["to_translate"]
BATCH = 350
n = 0
for i in range(0, len(strs), BATCH):
    chunk = strs[i:i + BATCH]
    Path(rf"E:\Code\sc2\Work\trans_input_{n:02d}.json").write_text(
        json.dumps(chunk, ensure_ascii=False, indent=1), encoding="utf-8")
    n += 1
print("chunks =", n, "strings =", len(strs))
