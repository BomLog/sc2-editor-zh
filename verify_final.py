import re, collections
from pathlib import Path

LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")

for fname in ["ObjectStrings.txt", "TriggerStrings.txt"]:
    p = LDR / fname
    raw = p.read_bytes()
    txt = raw.decode("utf-8", errors="replace")
    # 1) no replacement chars
    repl = txt.count("\ufffd")
    # 2) placeholder integrity: in translated body (before ///), placeholder tokens ~x~ must be intact
    bad_placeholder = 0
    for line in txt.splitlines():
        if "=" not in line:
            continue
        v = line.split("=", 1)[1]
        body = v.split("///", 1)[0]
        # find unbalanced/odd ~ count in body (placeholders come in pairs)
        if body.count("~") % 2 != 0:
            bad_placeholder += 1
    print(f"{fname}: utf8_replacement_chars={repl} unbalanced_tilde_bodies={bad_placeholder}")

# spot-check a few applied entries
print("\n=== spot check TriggerStrings ===")
n = 0
for line in (LDR / "TriggerStrings.txt").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if line.startswith("FunctionDef/Grammar/lib_Ntve_00000387") or line.startswith("Trigger/Name/lib_Lbty_3942F304"):
        print("  ", line[:120])
        n += 1
    if n >= 4:
        break
print("\n=== spot check ObjectStrings ===")
n = 0
for line in (LDR / "ObjectStrings.txt").read_text(encoding="utf-8-sig", errors="replace").splitlines():
    if line.startswith("Validator/Name/Burrowing") or line.startswith("Actor/Name/ACss"):
        print("  ", line[:80])
        n += 1
    if n >= 3:
        break
