import json, sys
from pathlib import Path

SPILL = Path(sys.argv[1])
WORK = Path(r"E:\Code\sc2\Work")

raw = SPILL.read_text(encoding="utf-8", errors="replace")
body = raw[raw.find("Return value:") + len("Return value:"):]
if "[truncated:" in body:
    body = body[:body.index("[truncated:")]
# repair truncated JSON: drop incomplete trailing lines, then close the object
lines = body.split("\n")
while lines and not lines[-1].rstrip().endswith('",') and lines[-1].strip() != "{":
    lines.pop()
repaired = "\n".join(lines).rstrip()
if repaired.endswith(","):
    repaired = repaired[:-1]
repaired += "\n}"
data = json.loads(repaired)
print("recovered complete entries:", len(data))

merged = json.loads((WORK / "translations.json").read_text(encoding="utf-8"))
added = 0
for s, v in data.items():
    if isinstance(v, str) and v != s and s not in merged:
        merged[s] = v
        added += 1
(WORK / "translations.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
print("added", added, "-> translations.json now", len(merged))
