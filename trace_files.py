import json, subprocess, time
from pathlib import Path

DIRS = [
    Path(r"D:\StarCraft II\Editor\LocalizedData"),
    Path(r"D:\StarCraft II\Editor"),
]
files = []
for d in DIRS:
    for p in d.iterdir():
        if p.is_file():
            files.append(p)

# baseline (do NOT read contents; stat only)
def snapshot():
    return {str(p): p.stat().st_atime_ns for p in files if p.exists()}

before = snapshot()
# launch editor
exe = r"D:\StarCraft II\Support64\SC2Editor_x64.exe"
proc = subprocess.Popen([exe], cwd=r"D:\StarCraft II")
try:
    time.sleep(60)
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
        changed.append((p, before[p], t))
changed.sort(key=lambda x: -x[2])
print("files whose LastAccessTime changed (editor read them):")
for p, b, a in changed:
    print("  ", Path(p).name, "in", Path(p).parent.name)
Path(r"E:\Code\sc2\Work\file_trace1.json").write_text(
    json.dumps({"changed": [{"path": p, "before": b, "after": a} for p, b, a in changed]},
               ensure_ascii=False, indent=2), encoding="utf-8")
print("total changed:", len(changed), "of", len(files))
