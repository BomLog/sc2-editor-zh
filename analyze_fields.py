import collections
from pathlib import Path

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")

# Check ObjectStrings.txt and GameStrings.txt for untranslated entries by (category, field)
for fname in ["ObjectStrings.txt", "GameStrings.txt"]:
    p = LDR / fname
    stats = collections.Counter()   # (cat, field) -> total
    nocjk = collections.Counter()   # (cat, field) -> no_chinese
    samples = collections.defaultdict(list)
    for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        parts = k.split("/")
        cat = parts[0] if parts else ""
        field = parts[1] if len(parts) > 1 else "(none)"
        stats[(cat, field)] += 1
        body = v.split("///", 1)[0].split("//", 1)[0].strip()
        if not hascjk(body):
            nocjk[(cat, field)] += 1
            if len(samples[(cat, field)]) < 4:
                samples[(cat, field)].append((k, body))
    print(f"\n=== {fname}: untranslated by (category, field) ===")
    total_nocjk = 0
    for (cat, field) in sorted(nocjk, key=lambda x: -nocjk[x]):
        n = nocjk[(cat, field)]
        if n == 0:
            continue
        total_nocjk += n
        print(f"  {cat}/{field}: {n}")
    print(f"  TOTAL untranslated: {total_nocjk}")
    # sample non-Name fields
    for (cat, field) in sorted(samples, key=lambda x: -nocjk[x]):
        if field == "Name":
            continue
        for k, body in samples[(cat, field)][:3]:
            print(f"    SAMPLE {k} = {body[:60]}")
