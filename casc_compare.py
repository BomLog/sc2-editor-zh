from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")
EXP = WORK / "casc_export"
EXT_TRIG = Path(r"D:\StarCraft II\Editor\LocalizedData\TriggerStrings.txt")

def parse(path):
    d = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k] = v
    return d

ext = parse(EXT_TRIG)
lib = parse(EXP / "liberty_triggerstrings.txt")
core = parse(EXP / "core_triggerstrings.txt")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

# external untranslated Trigger/Name lib_Lbty keys
ext_lbty_untrans = {k: v for k, v in ext.items() if k.startswith("Trigger/Name/lib_Lbty_") and not hascjk(v)}
print("external Trigger/Name/lib_Lbty_ untranslated:", len(ext_lbty_untrans))
# official liberty Trigger/Name keys
lib_trigger = {k: v for k, v in lib.items() if k.startswith("Trigger/Name/")}
print("official liberty Trigger/Name total:", len(lib_trigger))

overlap = set(ext_lbty_untrans) & set(lib_trigger)
print("overlap:", len(overlap))

# sample some external untranslated and check if in official
print("\n=== external untranslated samples vs official ===")
for k in list(ext_lbty_untrans)[:15]:
    print("EXT ", k, "=", ext_lbty_untrans[k][:50])
    print("      in-official:", lib_trigger.get(k, "<MISSING>")[:50])

# what are the official liberty Trigger/Name keys like?
print("\n=== official liberty Trigger/Name samples ===")
for k in list(lib_trigger)[:15]:
    print("  ", k, "=", lib_trigger[k][:50])
