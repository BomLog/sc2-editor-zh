# SC2 银河编辑器汉化补全 (sc2-editor-zh)

对《星际争霸II》银河编辑器（SC2Editor_x64.exe）的外部汉化进行逆向分析与补全。

## 目录结构

| 路径 | 说明 |
|---|---|
| `RESUME.md` | 断点续做记忆：逆向结论、工作进度、续做步骤 |
| `localized_output/` | **最终汉化产物快照**（放置位置见下） |
| `*.py` | 汉化管道脚本（CASC 提取、LLM 批量翻译、回写、校验、内存验证） |
| `translations.json` | 触发器/对象名累计译文（源英文 → 中文） |
| `opaque_translations.json` | 不透明对象 ID 译文 |
| `field_translations.json` | 字段目录译文（枚举值/字段名/字段提示） |
| `field_plan.json` | 未汉化字段条目清单 |
| `casc_export/` | 官方 zhCN 数据（不随仓库分发，用 `casc_extract2.py` 重新提取） |

## 产物放置位置

`localized_output/` 内文件复制到：

```
D:\StarCraft II\Editor\LocalizedData\   ← GameStrings.txt / ObjectStrings.txt / TriggerStrings.txt
D:\StarCraft II\Editor\                 ← EditorCatalogStrings.txt / EditorCategoryStrings.txt / EditorStrings.txt
```

改前请先备份原文件。

## 逆向结论（关键）

- 编辑器启动时（经文件访问追踪实证）只读取：
  - `Editor\LocalizedData\TriggerStrings.txt`、`ObjectStrings.txt`（触发器模块字符串）
  - `Editor\EditorStrings.txt`、`EditorCatalogStrings.txt`、`EditorCategoryStrings.txt`（编辑器 UI/字段/类别目录）
- **`Editor\LocalizedData\GameStrings.txt` 启动时不被读取**；数据编辑器（Data 模块）的对象名来自地图文档依赖（CASC 的 zhCN.SC2Data 等），不读取 `Editor\LocalizedData` 下的同名文件。
- 因此：触发器名、字段目录、类别目录可外部覆盖；数据编辑器的对象名（演算体/效果/行为等）需通过
  on-disk Mods 结构（如 `D:\StarCraft II\Mods\Core.SC2Mod\zhCN.SC2Data\LocalizedData\...`）或其他机制注入（待验证）。
- `EDSTR_FIELDVALUE_CATALOGGAMELINK`（"TYPE - ID"）、`EDSTR_LAYOUTFRAMEFORMAT`（"NAME [TYPE]"）中的
  TYPE/ID/NAME 为运行时逐字替换的 TOKEN，不可翻译。
- 官方 zhCN CASC 数据不完整（虫群/虚空故事模式触发器、对象名等官方从未中文化），缺口由 LLM 批量补译。
