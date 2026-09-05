"""Split unresolved residuals into unique bases; mark auto-resolvable ones."""
import re

TSV = r"e:\Code\sc2\Work\sc2ed_dpifix\packages\hook\OfficialDependencyNames.tsv"
UNRESOLVED = r"e:\Code\sc2\Work\sc2ed_dpifix\tools\unresolved.txt"
OUT_BASES = r"e:\Code\sc2\Work\sc2ed_dpifix\tools\unresolved_bases.txt"
OUT_AUTO = r"e:\Code\sc2\Work\sc2ed_dpifix\tools\unresolved_bases_auto.txt"
OUT_MANUAL = r"e:\Code\sc2\Work\sc2ed_dpifix\tools\unresolved_bases_manual.txt"

ids = {}
with open(TSV, encoding="utf-8") as fh:
    for line in fh:
        if line.startswith("#") or "\t" not in line:
            continue
        key, _, value = line.rstrip("\n").partition("\t")
        if not key.startswith("@display:"):
            ids[key.strip().lower().replace(" ", "")] = value

bases = {}
with open(UNRESOLVED, encoding="utf-8") as fh:
    for line in fh:
        text = line.rstrip("\n")
        if not text.strip():
            continue
        m = re.match(r"^(.*?)\s*((?:\([^()]*\)\s*)+)$", text)
        base = (m.group(1).strip() if m else text).strip()
        bases.setdefault(base, 0)
        bases[base] += 1

auto, manual = [], []
for base in sorted(bases):
    (auto if base.lower().replace(" ", "") in ids else manual).append(base)

with open(OUT_BASES, "w", encoding="utf-8") as fh:
    fh.write("\n".join(sorted(bases)) + "\n")
with open(OUT_AUTO, "w", encoding="utf-8") as fh:
    fh.write("\n".join(auto) + "\n")
with open(OUT_MANUAL, "w", encoding="utf-8") as fh:
    fh.write("\n".join(manual) + "\n")

print(f"unique bases={len(bases)} auto={len(auto)} manual={len(manual)}")
