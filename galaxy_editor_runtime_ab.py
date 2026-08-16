import json, shutil, subprocess, time
from pathlib import Path
root=Path(r"D:\StarCraft II\Editor\LocalizedData")
work=Path(r"E:\Code\sc2\Work")
exe=r"D:\StarCraft II\Support64\SC2Editor_x64.exe"
files=["ObjectStrings.txt","TriggerStrings.txt"]
backups={"ObjectStrings.txt":root/"ObjectStrings.txt.bak.autofill_20260815_211720","TriggerStrings.txt":root/"TriggerStrings.txt.bak.autofill_20260815_211720"}
saved={}
result={}
def launch(label):
 p=subprocess.Popen([exe],cwd=r"D:\StarCraft II")
 deadline=time.time()+20
 while time.time()<deadline and p.poll() is None: time.sleep(0.25)
 alive=p.poll() is None
 if alive:
  p.terminate()
  try: p.wait(5)
  except subprocess.TimeoutExpired: p.kill(); p.wait(5)
 return {"pid":p.pid,"alive_after_20s":alive,"exit_code":None if alive else p.returncode}
try:
 for name in files:
  temp=work/(name+".runtime_test_current")
  shutil.copy2(root/name,temp); saved[name]=temp
  shutil.copy2(backups[name],root/name)
 result["original_backup"]=launch("original_backup")
 for name in files: shutil.copy2(saved[name],root/name)
 result["localized_current"]=launch("localized_current")
finally:
 for name in files:
  if name in saved and saved[name].exists(): shutil.copy2(saved[name],root/name); saved[name].unlink()
Path(r"E:\Code\sc2\Work\galaxy_editor_runtime_ab.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
