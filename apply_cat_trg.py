import json, shutil, time
from pathlib import Path

CAT = Path(r"D:\StarCraft II\Editor\EditorCategoryStrings.txt")
TRG = Path(r"D:\StarCraft II\Editor\LocalizedData\TriggerStrings.txt")

cat_map = {
    "EDSTR_CATEGORY_DataGroup_Buff": "增益",
    "EDSTR_CATEGORY_GROUP_Buff": "增益",
    "EDSTR_CATEGORY_GROUP_Tileset": "地形组",
    "EDSTR_CATEGORY_LightGroup_C3PortraitsUnitsProtoss": "战争宝箱 III\\头像\\单位\\星灵",
    "EDSTR_CATEGORY_LightGroup_C3PortraitsUnitsTerran": "战争宝箱 III\\头像\\单位\\人类",
    "EDSTR_CATEGORY_LightGroup_C3PortraitsUnitsZerg": "战争宝箱 III\\头像\\单位\\虫族",
    "EDSTR_CATEGORY_LightGroup_C3UI": "战争宝箱 III\\UI",
    "EDSTR_CATEGORY_LightGroup_C4PortraitsBuildingsProtoss": "战争宝箱 IV\\头像\\建筑\\星灵",
    "EDSTR_CATEGORY_LightGroup_C4PortraitsBuildingsTerran": "战争宝箱 IV\\头像\\建筑\\人类",
    "EDSTR_CATEGORY_LightGroup_C4PortraitsBuildingsZerg": "战争宝箱 IV\\头像\\建筑\\虫族",
    "EDSTR_CATEGORY_LightGroup_C4UI": "战争宝箱 IV\\UI",
    "EDSTR_CATEGORY_LightGroup_C5PortraitsUnitsProtoss": "战争宝箱 V\\头像\\单位\\星灵",
    "EDSTR_CATEGORY_LightGroup_C5PortraitsUnitsTerran": "战争宝箱 V\\头像\\单位\\人类",
    "EDSTR_CATEGORY_LightGroup_C5PortraitsUnitsZerg": "战争宝箱 V\\头像\\单位\\虫族",
    "EDSTR_CATEGORY_LightGroup_C5UI": "战争宝箱 V\\UI",
    "EDSTR_CATEGORY_LightGroup_C6PortraitsBuildingsProtoss": "战争宝箱 VI\\头像\\建筑\\星灵",
    "EDSTR_CATEGORY_LightGroup_C6PortraitsBuildingsTerran": "战争宝箱 VI\\头像\\建筑\\人类",
    "EDSTR_CATEGORY_LightGroup_C6PortraitsBuildingsZerg": "战争宝箱 VI\\头像\\建筑\\虫族",
    "EDSTR_CATEGORY_LightGroup_C6UI": "战争宝箱 VI\\UI",
}

trg_map = {
    "Effect/Name/CEffectAddTrackedUnit": ("Default Effect (CEffectAddTrackedUnit)", "默认效果 (CEffectAddTrackedUnit)"),
    "Effect/Name/CEffectEnumTrackedUnits": ("Default Effect (CEffectEnumTrackedUnits)", "默认效果 (CEffectEnumTrackedUnits)"),
}

def apply_file(path, is_trg):
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="replace")
    nl = "\r\n" if "\r\n" in text else "\n"
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(f"{path.name}.bak.final_{ts}")
    shutil.copy2(path, bak)
    out = []
    changed = 0
    for line in text.split("\n"):
        core = line[:-1] if line.endswith("\r") else line
        if core and not core.lstrip().startswith("//") and "=" in core:
            k, v = core.split("=", 1)
            if is_trg:
                if k in trg_map and v == trg_map[k][0]:
                    core = f"{k}={trg_map[k][1]} /// {trg_map[k][0]}"
                    changed += 1
            else:
                if k in cat_map:
                    core = f"{k}={cat_map[k]}"
                    changed += 1
        out.append(core)
    new_bytes = nl.join(out).encode("utf-8")
    if has_bom:
        new_bytes = b"\xef\xbb\xbf" + new_bytes
    path.write_bytes(new_bytes)
    print(f"{path.name}: changed={changed}, backup={bak.name}")

apply_file(CAT, False)
apply_file(TRG, True)
