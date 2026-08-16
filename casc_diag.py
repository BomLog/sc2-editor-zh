from pathlib import Path

EXP = Path(r"E:\Code\sc2\Work\casc_export")
EXT_TRIG = Path(r"D:\StarCraft II\Editor\LocalizedData\TriggerStrings.txt")

def parse(path):
    d = {}
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k] = v
    return d

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

ext = parse(EXT_TRIG)
core = parse(EXP / "core_triggerstrings.txt")

# FunctionDef/Name keys comparison
ext_fn = {k for k in ext if k.startswith("FunctionDef/Name/")}
core_fn = {k for k in core if k.startswith("FunctionDef/Name/")}
print("external FunctionDef/Name:", len(ext_fn))
print("official core FunctionDef/Name:", len(core_fn))
print("overlap:", len(ext_fn & core_fn))
print("external-only:", len(ext_fn - core_fn))
print("core-only:", len(core_fn - ext_fn))

# of the overlap, how many external are untranslated?
ext_fn_untrans = {k for k in ext_fn if not hascjk(ext[k])}
print("external FunctionDef/Name untranslated:", len(ext_fn_untrans))
print("untranslated that exist in official core:", len(ext_fn_untrans & core_fn))

# samples of external-only vs core-only
print("\nexternal-only samples:")
for k in sorted(ext_fn - core_fn)[:10]:
    print("   ", k, "=", ext[k][:40])
print("core-only samples:")
for k in sorted(core_fn - ext_fn)[:10]:
    print("   ", k, "=", core[k][:40])

# library prefix breakdown
from collections import Counter
def lib_of(k):
    # FunctionDef/Name/lib_XXXX_hash
    parts = k.split("/")
    name = parts[-1] if parts else k
    if "_" in name:
        pre = name.split("_")[0] + "_" + name.split("_")[1] if len(name.split("_")) > 1 else name
        return pre
    return name[:12]
ec = Counter(lib_of(k) for k in ext_fn_untrans)
cc = Counter(lib_of(k) for k in core_fn)
print("\nexternal untranslated FunctionDef/Name lib prefixes:")
for k, n in ec.most_common(20):
    print("   ", k, n)
print("official core FunctionDef/Name lib prefixes:")
for k, n in cc.most_common(20):
    print("   ", k, n)
