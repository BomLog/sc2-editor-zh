import shutil
from datetime import datetime
from pathlib import Path

path = Path(r"D:\StarCraft II\Editor\LocalizedData\ObjectStrings.txt")

TRANS = {
    "UNITTYPEPLAGUED": "单位类型-被感染",
    "UNITTYPEPOISONED": "单位类型-中毒",
    "UNITTYPEPOLYMORPHED": "单位类型-被变形",
    "UNITTYPESNARED": "单位类型-被减速",
    "UPKEEPHIGH": "高维护费",
    "UPKEEPLOW": "低维护费",
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
            if eid in TRANS:
                out.append(f"{k}={TRANS[eid]}")
                changed += 1
                print(f"  {k} -> {TRANS[eid]}")
                continue
    out.append(line)

b = path.with_name(path.name + f".bak.validator2_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(path, b)
path.write_text(nl.join(out) + (nl if raw.endswith(("\n", "\r")) else ""), encoding="utf-8", newline="")
print("changed:", changed, "backup:", b.name)
