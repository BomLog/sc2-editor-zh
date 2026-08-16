import shutil
from datetime import datetime
from pathlib import Path

path = Path(r"D:\StarCraft II\Editor\LocalizedData\ObjectStrings.txt")

# validator name translations (descriptive ones get real Chinese; opaque IDs keep category prefix)
VALIDATOR_TRANS = {
    "Burrowing": "潜地中",
    "Cloakable": "可隐身",
    "Flashbanged": "被闪光弹命中",
    "Raiseable": "可升起",
    "UNIT_TYPE_PLAGUED": "单位类型-被感染",
    "UNIT_TYPE_POISONED": "单位类型-中毒",
    "UNIT_TYPE_POLYMORPHED": "单位类型-被变形",
    "UNIT_TYPE_SNARED": "单位类型-被减速",
    "UPKEEP_HIGH": "高维护费",
    "UPKEEP_LOW": "低维护费",
    "Unrepairable": "不可修理",
    # opaque IDs: keep 验证器 - ID
    "AIgf": "验证器 - AIgf",
    "AIgu": "验证器 - AIgu",
    "ReqVali": "验证器 - ReqVali",
}

raw = path.read_text(encoding="utf-8-sig")
nl = "\r\n" if "\r\n" in raw else "\n"
out = []
changed = 0
for line in raw.splitlines():
    if line.startswith("Validator/Name/"):
        k, v = line.split("=", 1)
        body = v.split("///", 1)[0].split("//", 1)[0].strip()
        if body.startswith("验证器 - "):
            eid = body[len("验证器 - "):].strip()
            if eid in VALIDATOR_TRANS:
                out.append(f"{k}={VALIDATOR_TRANS[eid]}")
                changed += 1
                print(f"  {k} = {body} -> {VALIDATOR_TRANS[eid]}")
                continue
    out.append(line)

b = path.with_name(path.name + f".bak.validator_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(path, b)
path.write_text(nl.join(out) + (nl if raw.endswith(("\n", "\r")) else ""), encoding="utf-8", newline="")
print("changed validators:", changed)
print("backup:", b.name)
