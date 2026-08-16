import json, shutil
from datetime import datetime
from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")
LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

# 1) merge opaque_zh_*.json -> opaque_translations.json
merged = {}
for p in sorted(WORK.glob("opaque_zh_*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    for s, v in d.items():
        if hascjk(v):
            merged.setdefault(s, v)
(WORK / "opaque_translations.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
print("opaque_translations.json:", len(merged), "entries")

# 2) apply: replace "类别 - ID" with the translation where available
path = LDR / "ObjectStrings.txt"
raw = path.read_text(encoding="utf-8-sig")
nl = "\r\n" if "\r\n" in raw else "\n"
out = []
applied = 0
for line in raw.splitlines():
    if "=" not in line:
        out.append(line)
        continue
    k, v = line.split("=", 1)
    parts = k.split("/")
    cat = parts[0] if parts else ""
    field = parts[1] if len(parts) > 1 else ""
    if field != "Name":
        out.append(line)
        continue
    body = v.split("///", 1)[0].split("//", 1)[0].strip()
    if " - " not in body:
        out.append(line)
        continue
    head, tail = body.split(" - ", 1)
    head = head.strip()
    if not hascjk(head):
        out.append(line)
        continue
    tail = tail.strip()
    if not tail or hascjk(tail):
        out.append(line)
        continue
    z = merged.get(tail, "")
    if z and hascjk(z):
        out.append(f"{k}={z}")
        applied += 1
    else:
        out.append(line)

b = path.with_name(path.name + f".bak.opaque_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(path, b)
path.write_text(nl.join(out) + (nl if raw.endswith(("\n", "\r")) else ""), encoding="utf-8", newline="")
print("applied:", applied, "backup:", b.name)
