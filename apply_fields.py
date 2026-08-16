import json, re, shutil, time
from pathlib import Path

SRC = Path(r"D:\StarCraft II\Editor\EditorCatalogStrings.txt")
plan = json.load(open(r"E:\Code\sc2\Work\field_plan.json", encoding="utf-8"))
trans = json.load(open(r"E:\Code\sc2\Work\field_translations.json", encoding="utf-8"))

# Targeted fixes (terminology consistency)
fixes = {
    "瓦莱里安": "瓦伦里安",
    "霍纳到雷诺": "霍纳对雷诺",
    "中立之眼": "中性（眼睛）",
    "单人": "独奏",
    "射程": "远程",
    "每种情况的效果": "每个分支的效果",
    "效果的分支贯穿": "效果的分支穿透",
    "优良": "卓越",
    "次级": "次级",  # keep
    "金色": "金色",
}
submaster = re.compile("^子母线")  # 子母线 -> 子主控

def polish(v):
    for a, b in fixes.items():
        if v == a:
            v = b
    if submaster.match(v):
        v = "子主控" + v[3:]
    # remove space between CJK and digits (伤害 1 -> 伤害1, 目标 01 -> 目标01)
    v = re.sub(r"([\u3400-\u9fff]) (\d)", r"\1\2", v)
    return v

trans = {k: polish(v) for k, v in trans.items()}

raw = SRC.read_bytes()
has_bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8-sig", errors="replace")
nl = "\r\n" if "\r\n" in text else "\n"

# Backup
ts = time.strftime("%Y%m%d_%H%M%S")
bak = SRC.with_name(f"{SRC.name}.bak.fields_{ts}")
shutil.copy2(SRC, bak)
print("backup:", bak)

lines = text.split("\n")  # keep \r at end if CRLF handled below
changed = 0
total_replacements = 0
out = []
body_map = {}  # body -> set of keys seen
for line in lines:
    s = line
    had_cr = s.endswith("\r")
    core = s[:-1] if had_cr else s
    if not core or core.lstrip().startswith("//") or "=" not in core:
        out.append(core)
        continue
    k, v = core.split("=", 1)
    vstrip = v.rstrip()
    if vstrip in trans and trans[vstrip] != vstrip:
        core = k + "=" + trans[vstrip]
        total_replacements += 1
        changed += 1
        body_map.setdefault(vstrip, []).append(k)
    out.append(core)

new_text = nl.join(out)
new_bytes = new_text.encode("utf-8")
if has_bom:
    new_bytes = b"\xef\xbb\xbf" + new_bytes
SRC.write_bytes(new_bytes)

# Verification
nokeys = 0
dup = {}
seen_keys = set()
bad = 0
for line in new_text.splitlines():
    if not line or line.lstrip().startswith("//") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    if k in seen_keys:
        dup[k] = dup.get(k, 0) + 1
    seen_keys.add(k)
    v = v.rstrip()
    if not re.search(r"[\u3400-\u9fff]", v):
        nokeys += 1
    if "\ufffd" in line:
        bad += 1

result = {
    "lines": len(out),
    "keys": len(seen_keys),
    "duplicate_keys": len(dup),
    "replacement_chars": bad,
    "lines_replaced": total_replacements,
    "unique_bodies_replaced": len(body_map),
    "remaining_no_chinese_values": nokeys,
}
json.dump(result, open(r"E:\Code\sc2\Work\field_apply_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))

# Bodies still untranslated
missing = set(plan["to_translate"]) - set(trans)
print("\nmissing bodies:", len(missing))
for m in sorted(missing):
    print("  ", repr(m))
