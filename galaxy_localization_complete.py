import json, re, shutil, time, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
ROOT=Path(r"D:\StarCraft II\Editor")
CACHE=Path(r"E:\Code\sc2\Work\galaxy_localization_cache.json")
REPORT=Path(r"E:\Code\sc2\Work\galaxy_localization_report.json")
OBJECT=ROOT/"LocalizedData"/"ObjectStrings.txt"
TRIGGER=ROOT/"LocalizedData"/"TriggerStrings.txt"
OC={"Actor":"演算体","Behavior":"行为","Effect":"效果","Mover":"移动器","Validator":"验证器"}
TC={"Category":"类别","CustomScript":"自定义脚本","FunctionDef":"函数","Label":"标签","Library":"库","ParamDef":"参数","Preset":"预设","PresetValue":"预设值","Structure":"结构体","SubFuncType":"子函数","Trigger":"触发器","Variable":"变量"}
CJK=re.compile(r"[\u3400-\u9fff]"); ALPHA=re.compile(r"[A-Za-z]"); CAMEL=re.compile(r"(?<=[a-z])(?=[A-Z])")
SEP=re.compile(r"\n__DSHSEP_(\d{4})__\n")
TERMS={"ability":"技能","actor":"演算体","actors":"演算体","behavior":"行为","behaviors":"行为","category":"类别","effect":"效果","effects":"效果","function":"函数","library":"库","mover":"移动器","parameter":"参数","player":"玩家","preset":"预设","scope":"作用域","trigger":"触发器","unit":"单位","units":"单位","validator":"验证器","validators":"验证器","variable":"变量"}
def entry(line):
 return None if not line or line.lstrip().startswith("//") or "=" not in line else line.split("=",1)
def cat(key): return key.split("/",1)[0] if "/" in key else ""
def source(value): return value.split("///",1)[0].strip()
def identifier(value):
 return (not value or not ALPHA.search(value) or bool(re.fullmatch(r"[A-Za-z]{1,5}\d*",value)) or bool(re.fullmatch(r"[A-Z0-9_@./-]+",value)) or (" " not in value and "_" not in value and not CAMEL.search(value) and len(value)<=12))
def glossary(value):
 parts=re.split(r'(~[^~]+~|<[^>]+>|"[^"\n]*")',value)
 for i in range(0,len(parts),2):
  for a,b in TERMS.items(): parts[i]=re.sub(rf"\b{re.escape(a)}\b",b,parts[i],flags=re.I)
 return "".join(parts).strip()
def request(values):
 payload="".join((f"\n__DSHSEP_{i:04d}__\n" if i else "")+v for i,v in enumerate(values))
 query=urllib.parse.urlencode({"client":"gtx","sl":"en","tl":"zh-CN","dt":"t","q":payload})
 req=urllib.request.Request("https://translate.googleapis.com/translate_a/single?"+query,headers={"User-Agent":"Mozilla/5.0"})
 err=None
 for attempt in range(5):
  try:
   data=json.loads(urllib.request.urlopen(req,timeout=30).read().decode())
   text="".join(x[0] for x in data[0]); parts=SEP.split(text); out=[parts[0]]+[parts[i+1] for i in range(1,len(parts),2)]
   if len(out)!=len(values): raise ValueError(f"separator mismatch {len(out)}/{len(values)}")
   return [glossary(x.replace("\n"," ")) for x in out]
  except Exception as ex: err=ex; time.sleep(1.5*(attempt+1))
 raise RuntimeError(err)
def collect(targets):
 out=[]; seen=set()
 for path,cats in targets:
  for line in path.read_text(encoding="utf-8-sig").splitlines():
   e=entry(line)
   if not e: continue
   k,v=e; s=source(v)
   if cat(k) in cats and not CJK.search(v) and s and ALPHA.search(s) and not identifier(s) and s not in seen:
    seen.add(s); out.append(s)
 return out
def parse_map(path):
 out={}
 for line in path.read_text(encoding="utf-8-sig").splitlines():
  e=entry(line)
  if e: out[e[0]]=e[1]
 return out
def build_tm():
 tm={}
 pairs=[(ROOT/"合作本地化文件（英文）"/"GameStrings.txt",ROOT/"LocalizedData"/"GameStrings.txt"),(ROOT/"合作本地化文件（英文）"/"ObjectStrings.txt",OBJECT),(ROOT/"合作本地化文件（英文）"/"TriggerStrings.txt",TRIGGER)]
 for ep,zp in pairs:
  en=parse_map(ep); zh=parse_map(zp)
  for k,v in en.items():
   z=zh.get(k,"")
   if v.strip() and CJK.search(z): tm.setdefault(v.strip(),source(z))
 for path in (ROOT/"LocalizedData"/"GameStrings.txt",OBJECT,TRIGGER):
  for v in parse_map(path).values():
   if "///" in v:
    z,e=v.split("///",1); z=z.strip(); e=e.strip()
    if e and CJK.search(z): tm.setdefault(e,z)
 return tm
def fill_cache(cache,sources,tm):
 for s in sources:
  if s in cache: continue
  z=tm.get(s,"")
  if not z:
   candidate=glossary(s)
   z=candidate if CJK.search(candidate) else ""
  cache[s]=z
 CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding="utf-8")

def rewrite(path,cats,cache,original):
 raw=path.read_text(encoding="utf-8-sig"); nl="\r\n" if "\r\n" in raw else "\n"; out=[]; changed=Counter(); samples=[]
 for line in raw.splitlines():
  e=entry(line)
  if not e: out.append(line); continue
  k,v=e; c=cat(k)
  if c not in cats or CJK.search(v): out.append(line); continue
  s=source(v); z=cache.get(s,"").strip()
  if not CJK.search(z): z=f"{cats[c]} - {s or v.strip()}"
  if original and s:
    source_tokens=Counter(re.findall(r"~[A-Za-z][A-Za-z0-9_]*~|<[^>]+>",s))
    translated_tokens=Counter(re.findall(r"~[A-Za-z][A-Za-z0-9_]*~|<[^>]+>",z))
    if source_tokens!=translated_tokens: z=f"{cats[c]} - {s}"
    safe=s.translate(str.maketrans({"~":"～","<":"＜",">":"＞"}))
    z=f"{z} /// {safe}"
  out.append(f"{k}={z}"); changed[c]+=1
  if len(samples)<30: samples.append({"key":k,"before":v,"after":z})
 path.write_text(nl.join(out)+(nl if raw.endswith(("\n","\r")) else ""),encoding="utf-8",newline="")
 return dict(changed),samples
def audit(path,cats):
 keys=set(); dup=0; bad=0; left=Counter()
 for line in path.read_text(encoding="utf-8-sig").splitlines():
  e=entry(line)
  if not e:
   if line and not line.lstrip().startswith("//") and "=" not in line: bad+=1
   continue
  k,v=e; dup+=k in keys; keys.add(k); c=cat(k)
  if c in cats and not CJK.search(v): left[c]+=1
 return {"keys":len(keys),"duplicates":dup,"malformed_noncomment_lines":bad,"remaining_without_chinese":dict(left)}
def main():
 targets=[(OBJECT,OC),(TRIGGER,TC)]; sources=collect(targets); cache=json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
 tm=build_tm(); print(f"sources={len(sources)} cached={len(cache)} tm={len(tm)}"); fill_cache(cache,sources,tm)
 stamp=datetime.now().strftime("%Y%m%d_%H%M%S"); backups=[]
 for path,_ in targets:
  b=path.with_name(path.name+f".bak.autofill_{stamp}"); shutil.copy2(path,b); backups.append(str(b))
 oc,os=rewrite(OBJECT,OC,cache,False); tc,ts=rewrite(TRIGGER,TC,cache,True)
 report={"generated_at":datetime.now().isoformat(timespec="seconds"),"backups":backups,"changed":{"ObjectStrings.txt":oc,"TriggerStrings.txt":tc},"audit":{"ObjectStrings.txt":audit(OBJECT,OC),"TriggerStrings.txt":audit(TRIGGER,TC)},"samples":{"ObjectStrings.txt":os,"TriggerStrings.txt":ts}}
 REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
