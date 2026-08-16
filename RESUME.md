# SC2 银河编辑器汉化 — 断点续做记忆 (RESUME)

> 工作目录：`E:\Code\sc2`，脚本目录：`E:\Code\sc2\Work`。
> **Git 仓库**：`E:\Code\sc2\Work` 已初始化并推送至 GitHub 私有仓库
> `https://github.com/BomLog/sc2-editor-zh`（gh CLI 已登录 BomLog；本机访问 GitHub 需代理
> `http://127.0.0.1:12334`，仓库内已配置 `http.proxy`/`https.proxy`，直接 `git push` 即可）。

## 1. 目标

用 IDA Pro MCP 逆向确认银河编辑器外部汉化导入机制，补齐所有未汉化的触发器/行为/效果/演算体/验证器/字段目录等编辑器数据，可复现导入与验证。**全部核心工作已完成**（见第 4 节）。

## 2. 已确认的关键事实（逆向结论，已写入 i64）

- 编辑器外部覆盖加载：`LoadGameDataAndLocalizedStringTables`(0x140AD2860) 加载 9 个文件：GameData.xml、Assets.txt、AssetsProduct.txt、GameHotkeys.txt、GameHotkeysProduct.txt、**GameStrings.txt**、ConversationStrings.txt、GameStringsProduct.txt、ObjectStringsProduct.txt。
- **ObjectStrings.txt 不在加载列表**（描述符 0x144C25E70 零引用）→ 这是"演算体翻译不生效"的根因。修复方式：把对象名条目合并进 **GameStrings.txt**（已做，45s 内存扫描实证生效）。
- 编辑器字符串包：`sub_1401D7910` 加载 `Editor\EditorStrings.txt`、`Editor\EditorCatalogStrings.txt`（字段目录）、`Editor\EditorCategoryStrings.txt`（类别目录），另加载 109 个 `LocalizedData/*Hints.txt`。路径相对游戏根目录，即 `D:\StarCraft II\Editor\*.txt`。
- `ExportEditorCatalogStrings`(0x14031E040) 是导出函数（写 `Data/Mods/Core.Mod/.Data/LocalizedData/Editor/...`），与加载无关。
- **TOKEN 格式串不可翻译**：`EDSTR_FIELDVALUE_CATALOGGAMELINK`（"TYPE - ID"）和 `EDSTR_LAYOUTFRAMEFORMAT`（"NAME [TYPE]"）中的 TYPE/ID/NAME 由代码逐字替换（sub_140781F10 调 sub_140117B40 做子串替换），必须保留英文原文。`EDSTR_LAYOUTFRAMETYPE_*` 是内部帧类型 ID，保留。
- 官方 zhCN CASC 数据不完整（swarmstory/voidstory 零中文、对象名英文），需 LLM 补译。
- 验证方法：启动 SC2Editor_x64.exe 等 **45 秒**（20 秒只提交 469MB、45 秒 1.9GB），遍历内存区扫描 UTF-8 中文探针。见 `verify_actor_fix2.py` / `verify_fields.py`。

## 3. 已完成进度（全部完成）

1. **逆向**：加载链路、资源路径、函数重命名+注释已写回 `D:\StarCraft II\Support64\SC2Editor_x64.exe.i64` 并保存。
2. **CASC 提取**：✅ 官方 zhCN 文件导出到 `casc_export\`。
3. **验证器**：✅ 14 条已翻（潜地中/可隐身/被闪光弹命中/可升起等）。
4. **触发器**：✅ `TriggerStrings.txt` 60801 键全部汉化（0 条无中文；含最后 2 条 `默认效果 (CEffectAddTrackedUnit) /// Default Effect (CEffectAddTrackedUnit)`）。
5. **对象名（演算体/武器/技能/行为/效果等）**：✅ ObjectStrings.txt 199388 键 0 无中文；**关键修复**：15004 条对象专属键已并入 GameStrings.txt（199422 键，0 重复/0 坏字符），内存扫描实证生效（"演算体 - ACss"/"默认武器"/"潜地中"/"技能 - AAns" 等全部命中）。
6. **字段目录**：✅ `EditorCatalogStrings.txt` 21439 键；本轮 LLM 翻译 781 行（685 个唯一源串，`field_translations.json` 697 条），剩余 63 条无中文全部为合理保留（单字母 A-Z、AI/CUE/ID/Id/CCPA/DNA、PCM 8-32/FLOAT、2D/3D、WCS 年份、'*'、'PU72516J'、'~Case.'/'~UpgradeWeapon.' 占位符）。内存扫描实证生效（"施法者地面高度"/"挂载点"/"瓦伦里安"/"BG_环境音_2D" 等命中）。
7. **类别目录**：✅ `EditorCategoryStrings.txt` 251 键；18 条补译（Buff增益/Tileset地形组/战争宝箱 III-VI 头像单位建筑星灵人类虫族），剩 3 条为 AI/UI/UI 保留。
8. **编辑器字符串**：✅ `EditorStrings.txt` 407 键；6 条无中文均为 TOKEN 格式串/内部 ID（第 2 节），正确保留。

## 4. 当前文件状态（验证通过）

| 文件 | 键数 | 无中文 | 备注 |
|---|---|---|---|
| GameStrings.txt | 199422 | 0 | 含并入的对象名 |
| ObjectStrings.txt | 199388 | 0 | 本身不被编辑器加载 |
| TriggerStrings.txt | 60801 | 0 | 触发器全部汉化 |
| EditorCatalogStrings.txt | 21439 | 63 | 63 条=合理保留 |
| EditorCategoryStrings.txt | 251 | 3 | AI/UI/UI |
| EditorStrings.txt | 407 | 6 | TOKEN 格式串 |

备份：`*.bak.fields_20260816_*`、`*.bak.final_20260816_*`、`GameStrings.txt.bak.mergeobj_*` 等。

## 5. 后续可选工作

- 若用户报告个别译文不准，改 `field_translations.json` 后重跑 `apply_fields.py`（幂等）。
- 官方 zhCN 永远缺失的战役文本（swarmstory/voidstory）如需补齐，参照触发器管道再做一轮。

## 6. 关键约束/坑（务必记住）

- **子代理无法写文件**（审批被禁用，write 报 "not strictly wider"）：子代理只读+返回，主代理用 `write` 落盘。
- workflow 的 agent() 返回可能被包成 `{"arguments": "<json>", "loop": "false"}` 信封：脚本里要 unwrap（取 .arguments 再 JSON.parse）。
- workflow schema：`additionalProperties` 只接受布尔。
- 官方 CASC 文件 UTF-8；控制台乱码只是 PowerShell 显示问题。
- 内存验证必须等 45 秒以上再扫描。
- 格式串/TOKEN 串（TYPE/ID/NAME 等）一律不译。

## 7. 术语速查

unit单位 ability技能 behavior行为 effect效果 actor演算体 trigger触发器 variable变量 validator验证器 requirement需求 objective目标 player玩家 region区域 upgrade升级 leaderboard记分板 dialog对话框 cinematic过场动画 bank数据银行 supply补给 mineral晶体矿 vespene高能瓦斯 life生命值 shields护盾 energy能量 armor护甲 damage伤害 attack攻击 order命令 cargo装载 victory胜利 defeat战败 mission任务 difficulty难度 score得分 timer计时器 camera镜头 terrain地形 creep菌毯 building建筑 weapon武器 turret炮塔 countdown倒计时 warning警告 overlay覆盖层 spray喷漆 preset预设 wave波次 warchest战争宝箱 portrait头像 doodad装饰物 hardpoint挂载点 attach附着点 tileset地形组 buff增益。
