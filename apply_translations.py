import json, shutil, re
from datetime import datetime
from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")
LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")

def hascjk(v):
    for ch in v:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

def esc(s):
    # escape placeholders/markup in the /// original comment (full-width)
    return s.translate(str.maketrans({"~": "～", "<": "＜", ">": "＞"}))

translations = json.loads((WORK / "translations.json").read_text(encoding="utf-8"))
plan = json.loads((WORK / "translate_plan.json").read_text(encoding="utf-8"))
entries = plan["entries"]

# group entries by file, preserving order
by_file = {}
for e in entries:
    by_file.setdefault(e["file"], []).append(e)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report = {"stamp": stamp, "backups": [], "applied": {}}

for fname, ents in by_file.items():
    path = LDR / fname
    raw = path.read_text(encoding="utf-8-sig")
    nl = "\r\n" if "\r\n" in raw else "\n"
    # build key -> entry map
    emap = {e["key"]: e for e in ents}
    out = []
    applied = 0
    for line in raw.splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            out.append(line)
            continue
        k, v = line.split("=", 1)
        e = emap.get(k)
        if e is None:
            out.append(line)
            continue
        s = e["source"]
        # skip already-localized sources (source containing Chinese must stay untouched)
        if hascjk(s):
            out.append(line)
            continue
        if e["mode"] == "translate":
            z = translations.get(s, "").strip()
            if not hascjk(z):
                z = f"{e['category']} - {s}"  # fallback
            if fname == "TriggerStrings.txt":
                new = f"{z} /// {esc(s)}"
            else:
                new = z
            out.append(f"{k}={new}")
            applied += 1
        else:  # prefix
            out.append(f"{k}={e['category']} - {s}")
            applied += 1
    b = path.with_name(path.name + f".bak.llm_{stamp}")
    shutil.copy2(path, b)
    report["backups"].append(str(b))
    path.write_text(nl.join(out) + (nl if raw.endswith(("\n", "\r")) else ""),
                    encoding="utf-8", newline="")
    report["applied"][fname] = applied
    print(f"{fname}: applied {applied} entries")

(WORK / "llm_apply_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
print("report -> llm_apply_report.json")
