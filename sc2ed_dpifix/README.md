# SC2 银河编辑器 DPI 修复与官方依赖汉化

本项目将 DPI 修复、编辑器外部字符串表和官方 CASC 依赖名称 Hook 合并到同一启动流程。当前版本见 [`VERSION`](VERSION)，更新内容见 [`CHANGELOG.md`](CHANGELOG.md)。

“官方依赖汉化”是独立可选功能。启用时，启动器会先校验游戏根目录下的 `Editor` 外置文件：文本和 TSV 使用严格 SHA-256，DLL 校验 PE 标志、必要导出和当前 Hook 版本。内容与内置版本一致则保留；文件缺失则释放内置副本；文件存在但不一致时先保存带版本号的备份，再原子替换并复核。随后挂起创建 `SC2Editor_x64.exe`、应用所选 DPI 修复、注入 `SC2EditorDependencyL10n.dll`，确认 Hook 安装成功后再恢复编辑器主线程。关闭汉化时不会校验或释放汉化文件，也不会注入 Hook。

覆盖目录类型：演算体、行为、技能、效果、验证器、模型；触发器由 `Editor/LocalizedData/TriggerStrings.txt` 提供。名称表仅从游戏 CASC 的 `mods` 和 `campaigns` 生成，不读取 `D:\StarCraft II\Mods` 下的自定义包。

## 构建

在 `E:\Code\sc2\Work` 已配置 Python 环境和 `E:\msys2\ucrt64\bin\g++.exe` 的机器上运行：

```powershell
cd E:\Code\sc2\Work\sc2ed_dpifix
.\build.ps1
```

生成器会重新扫描官方 CASC，刷新 `l10n/OfficialDependencyNames.tsv`、报告和随启动器打包的字符串资源。最终程序位于 `dist/SC2银河编辑器DPI修复.exe`。

启动器不会无备份覆盖异常外置文件，也不会修改 `SC2Editor_x64.exe` 或任何官方依赖包。

## 汉化署名

原始翻译文本由“头目”提供；GA 用户 hgzerg 补充注释；OB 进行了翻译校正和长期维护。完整说明见 [`CREDITS.md`](CREDITS.md)。

## Git 管理

源码、构建脚本、版本号、署名文件和 `OfficialDependencyNames.tsv` 纳入 Git。`build/`、`dist/`、编译 DLL、生成报告及打包用的大型字符串快照由 `sc2ed_dpifix/.gitignore` 排除，可通过 `build.ps1` 重建。
