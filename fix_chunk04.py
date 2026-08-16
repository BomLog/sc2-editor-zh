import json
from pathlib import Path

WORK = Path(r"E:\Code\sc2\Work")

# exact corrected translations for chunk 04 (whitespace phrases only)
CORRECT = {
    "CM_Abort Mission": "CM_Abort 任务",
    "CM_Apply Tychus Rage Buffs": "CM_Apply 泰凯斯狂怒增益",
    "CM_Dehaka Glevig Timer Adjustments": "CM_Dehaka 格利维格计时器调整",
    "CM_Dehaka Learn": "CM_Dehaka 学习",
    "CM_Dehaka Revive Heal Only Once": "CM_Dehaka 复活仅治疗一次",
    "CM_DehakaMammoth Breath Look At Start": "CM_DehakaMammoth 吐息注视开始",
    "CM_DehakaMammoth Breath Look At Stop": "CM_DehakaMammoth 吐息注视停止",
    "CM_DehakaRevive Eat Button Clicked": "CM_DehakaRevive 进食按钮已点击",
    "CM_DehakaRevive Timer Adjustments": "CM_DehakaRevive 计时器调整",
    "CM_DropPodCreateZergBuilding_Don't Wait": "CM_DropPodCreateZergBuilding_Don't 等待",
    "CM_Fenix_Champion Building ReBuilt": "CM_Fenix_Champion 建筑已重建",
    "CM_Fenix_Champion Potential Voluteer Trained": "CM_Fenix_Champion 潜在志愿者已训练",
    "CM_Fenix_Champion Timers": "CM_Fenix_Champion 计时器",
    "CM_Fenix_Champion Upgrade Researched": "CM_Fenix_Champion 升级已研发",
}

# 1) regenerate trans_output_04.json correctly (14 translated + 336 unchanged)
src = json.loads((WORK / "trans_input_04.json").read_text(encoding="utf-8"))
out = {s: CORRECT.get(s, s) for s in src}
(WORK / "trans_output_04.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
n_zh = sum(1 for k, v in out.items() if v != k)
print(f"regenerated trans_output_04.json: total={len(out)} translated={n_zh} unchanged={len(out)-n_zh}")

# 2) fix translations.json: remove ALL chunk-04 source keys, then re-add the 14 corrected ones
tr = json.loads((WORK / "translations.json").read_text(encoding="utf-8"))
before = len(tr)
for s in src:
    tr.pop(s, None)
after_remove = len(tr)
for s, v in CORRECT.items():
    tr[s] = v
(WORK / "translations.json").write_text(json.dumps(tr, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"translations.json: {before} -> removed chunk04 ({after_remove}) -> +14 = {len(tr)}")
