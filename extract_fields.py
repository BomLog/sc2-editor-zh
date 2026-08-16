import json
from pathlib import Path

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

p = Path(r"D:\StarCraft II\Editor\EditorCatalogStrings.txt")
entries = []
to_translate = {}
for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if not line or line.lstrip().startswith("//") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    v = v.rstrip("\r\n")
    if hascjk(v):
        continue
    body = v.split("///", 1)[0].strip()
    if not body:
        continue
    entries.append({"key": k, "value": v, "body": body})
    to_translate.setdefault(body, k)

plan = {
    "unique_bodies": len(to_translate),
    "to_translate": sorted(to_translate.keys()),
    "entries": entries,
}
Path(r"E:\Code\sc2\Work\field_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print("unique bodies:", len(to_translate), " total entries:", len(entries))
for s in sorted(to_translate.keys())[:60]:
    print("   ", repr(s))
