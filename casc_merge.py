import json, shutil, re
from datetime import datetime
from pathlib import Path

EXP = Path(r"E:\Code\sc2\Work\casc_export")
LDR = Path(r"D:\StarCraft II\Editor\LocalizedData")
WORK = Path(r"E:\Code\sc2\Work")

CAT_WORDS = ["演算体","行为","效果","移动器","验证器","触发器","函数","变量","参数","预设",
             "预设值","结构体","子函数","类别","库","标签","自定义脚本","技能","单位","模型",
             "音效","需求","按钮","物品","掉落","升级","用户","纹理","灯光","足迹","奖励",
             "蓄能器","成就","军队单位","军队类别","军队升级","附着方式","银行条件","捆绑包",
             "镜头","卡片","角色","对话","对话状态","数据收集","英雄","英雄技能","英雄属性",
             "物品类别","动力学","位置","地图","目标","预加载","种族","混响","计分结果","计分值",
             "皮肤","皮肤包","原声带","战术","目标排序","地形纹理","炮塔"]

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

def body_of(v):
    return re.split(r"\s*(?://|///)\s*", v, 1)[0].strip()

def needs_fill(v):
    b = body_of(v)
    if not b:
        return True
    if not hascjk(b):
        return True
    for w in CAT_WORDS:
        if b.startswith(w + " - "):
            tail = b[len(w) + 3:]
            if tail and not hascjk(tail):
                return True
    return False

# build official dictionaries from ALL extracted files
# order: core first, then melee mods, then campaigns (later override)
order_trig = ["core_triggerstrings", "liberty_triggerstrings", "libertymulti_triggerstrings",
              "swarm_triggerstrings", "swarmmulti_triggerstrings", "void_triggerstrings",
              "voidmulti_triggerstrings", "camp_liberty_triggerstrings", "camp_swarm_triggerstrings",
              "camp_void_triggerstrings", "camp_libertystory_triggerstrings",
              "camp_swarmstory_triggerstrings", "camp_voidstory_triggerstrings",
              "camp_swarmstoryutil_triggerstrings"]
order_obj = []
for prefix in ["core", "liberty", "libertymulti", "swarm", "swarmmulti", "void", "voidmulti",
               "camp_liberty", "camp_swarm", "camp_void", "camp_libertystory",
               "camp_swarmstory", "camp_voidstory", "camp_swarmstoryutil"]:
    order_obj.append(prefix + "_gamestrings")
    order_obj.append(prefix + "_objectstrings")

trig_official = {}
for stem in order_trig:
    p = EXP / (stem + ".txt")
    if p.exists():
        d = parse(p)
        for k, v in d.items():
            if hascjk(v):
                trig_official[k] = v

obj_official = {}
for stem in order_obj:
    p = EXP / (stem + ".txt")
    if p.exists():
        d = parse(p)
        for k, v in d.items():
            if hascjk(v):
                obj_official[k] = v

print("official trigger keys (with Chinese):", len(trig_official))
print("official object keys (with Chinese):", len(obj_official))

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report = {"stamp": stamp, "backups": [], "filled": {}}

for fname, official in [("TriggerStrings.txt", trig_official),
                        ("ObjectStrings.txt", obj_official)]:
    path = LDR / fname
    raw = path.read_text(encoding="utf-8-sig")
    nl = "\r\n" if "\r\n" in raw else "\n"
    out = []
    filled = 0
    skipped_no_official = 0
    samples = []
    for line in raw.splitlines():
        if not line or line.lstrip().startswith("//") or "=" not in line:
            out.append(line)
            continue
        k, v = line.split("=", 1)
        if needs_fill(v):
            ov = official.get(k)
            if ov is not None and hascjk(ov):
                out.append(f"{k}={ov}")
                filled += 1
                if len(samples) < 20:
                    samples.append({"key": k, "before": v[:60], "after": ov[:60]})
            else:
                out.append(line)
                skipped_no_official += 1
        else:
            out.append(line)
    b = path.with_name(path.name + f".bak.cascmerge_{stamp}")
    shutil.copy2(path, b)
    report["backups"].append(str(b))
    new_content = nl.join(out) + (nl if raw.endswith(("\n", "\r")) else "")
    path.write_text(new_content, encoding="utf-8", newline="")
    report["filled"][fname] = {"filled": filled, "needed_but_no_official": skipped_no_official}
    print(f"\n{fname}: filled={filled}  needed_but_no_official={skipped_no_official}")
    for s in samples[:20]:
        print("   +", s["key"], "\n       ", s["before"], "\n     ->", s["after"])

report_path = WORK / "casc_merge_report.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nreport ->", report_path)
