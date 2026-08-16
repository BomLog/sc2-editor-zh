import shutil
from datetime import datetime
from pathlib import Path

LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")
GAME = LDR / "GameStrings.txt"
OBJ = LDR / "ObjectStrings.txt"

def parse(path):
    d = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k] = v
    return d

game = parse(GAME)
obj = parse(OBJ)

# object-only keys = in ObjectStrings but NOT in GameStrings
only = {k: v for k, v in obj.items() if k not in game}
print("object-only keys to append to GameStrings.txt:", len(only))

# append them to GameStrings.txt (preserving original formatting)
raw = GAME.read_text(encoding="utf-8-sig")
nl = "\r\n" if "\r\n" in raw else "\n"
# ensure single trailing newline
raw = raw.rstrip("\r\n")
lines = raw.splitlines()

# order: append object-only entries sorted by key (stable)
new_entries = [f"{k}={only[k]}" for k in sorted(only)]
print("sample appended:")
for e in new_entries[:10]:
    print("   ", e[:100])

b = GAME.with_name(GAME.name + f".bak.mergeobj_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(GAME, b)
out = nl.join(lines + [""] + new_entries) + nl
GAME.write_text(out, encoding="utf-8", newline="")
print("backup:", b.name)
print("GameStrings.txt keys now:", len(lines) + len(new_entries))
