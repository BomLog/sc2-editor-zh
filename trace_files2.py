import json, subprocess, time
from pathlib import Path

WATCH = [
    Path(r"D:\StarCraft II\Editor\LocalizedData"),
    Path(r"D:\StarCraft II\Editor"),
    Path(r"D:\StarCraft II\Mods"),
    Path(r"D:\StarCraft II\SC2Data"),
    Path(r"E:\Code\sc2\Work\8v1bankedit\8v1map"),
    Path(r"E:\Code\sc2\Work\8v1bankedit\8v1map\Mods"),
]
files = []
for d in WATCH:
    if not d.exists():
        continue
    for p in d.rglob("*"):
        if p.is_file():
            files.append(p)

def snapshot():
    out = {}
    for p in files:
        try:
            out[str(p)] = p.stat().st_atime_ns
        except OSError:
            pass
    return out

before = snapshot()
exe = r"D:\StarCraft II\Support64\SC2Editor_x64.exe"
mapf = r"E:\Code\sc2\Work\8v1bankedit\8v1map\虫海-8vs1合众为一.SC2Map"
proc = subprocess.Popen([exe, mapf], cwd=r"D:\StarCraft II")
try:
    time.sleep(90)
finally:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(5)

after = snapshot()
changed = []
for p, t in after.items():
    if p in before and t != before[p]:
        rel = Path(p)
        changed.append((p, before[p], t))
changed.sort(key=lambda x: -x[2])
print("files read during map-open session:")
for p, b, a in changed:
    print("  ", p)
Path(r"E:\Code\sc2\Work\file_trace2.json").write_text(
    json.dumps({"changed": [{"path": p} for p, b, a in changed]}, ensure_ascii=False, indent=2), encoding="utf-8")
print("total changed:", len(changed))
