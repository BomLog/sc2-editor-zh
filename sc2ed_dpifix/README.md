# SC2 银河编辑器 DPI Fix

<p align="center">
  <img src="app.ico" width="96" alt="SC2 银河编辑器 DPI Fix" />
</p>

<p align="center">
  <strong>让银河编辑器在高分屏上清晰可用，并为官方 CASC 依赖目录提供中文名称。</strong><br />
  外置启动 · 运行时补丁 · 可随时切回原版
</p>

<p align="center">
  <a href="https://github.com/BomLog/sc2-editor-zh/releases">下载 Releases</a>
  · <a href="CHANGELOG.md">更新日志</a>
  · <a href="CREDITS.md">翻译与致谢</a>
</p>

> 当前版本：**v1.5.0**（2026-09-05）

## 这是什么？

这是一个面向 Windows 的《星际争霸 II》银河编辑器启动器。它把两个经常同时出现的问题拆成了独立开关：

- **高 DPI 清晰度**：解决编辑器在 125% / 150% 等缩放比例下文字模糊、字体溢出或控件错位。
- **中文本地化**：为编辑器界面、触发器、游戏对象，以及数据树中的官方 CASC 依赖和资源名称提供中文显示。

工具只对本次启动的编辑器进程施加补丁，并将汉化资源作为外置文件管理：

- 不修改 `SC2Editor_x64.exe`；
- 不修改官方 CASC 数据包；
- 不替换游戏本体文件；
- 关闭启动器后，可以直接用原版快捷方式启动编辑器。

## 功能一览

| 功能 | 作用 | 默认状态 |
| --- | --- | :---: |
| **清晰度修复** | 启动时为编辑器选择 DPI 处理策略，改善高分屏显示 | 开启 |
| **官方依赖汉化** | 运行时翻译数据树中的官方依赖、模型和资源名称 | 开启 |
| **编辑器界面汉化** | 释放界面、目录、触发器和游戏字符串到编辑器目录 | 随汉化开启 |
| **暂时卸载 / 恢复** | 打包地图或 Mod 前暂存外置汉化文件，完成后原样恢复 | — |
| **智能同步** | 只更新工具管理且未被用户修改过的文件 | 自动 |

## 快速开始

### 运行环境

- Windows 10 / 11（64 位）
- 已安装《星际争霸 II》银河编辑器（`SC2Editor_x64.exe`）
- 通常无需联网、无需单独安装 VC++ 运行库

### 安装与首次启动

1. 从 [Releases](https://github.com/BomLog/sc2-editor-zh/releases) 下载最新的 `SC2银河编辑器DPI修复.exe`。
2. 将 EXE 放在任意目录，双击运行即可；它是单文件程序，不需要安装向导。
3. 首次启动时选择 `SC2Editor_x64.exe`。常见位置：

   ```text
   D:\StarCraft II\Support64\SC2Editor_x64.exe
   C:\Program Files (x86)\StarCraft II\Support64\SC2Editor_x64.exe
   ```

4. 选择功能开关和 DPI 模式，点击启动按钮。

路径会保存在启动器配置中，下次无需重复选择。若编辑器本身以管理员身份运行，请让启动器以同等权限运行。

## 启动器怎么选？

### 两个独立开关

| 清晰度修复 | 官方依赖汉化 | 启动结果 |
| :---: | :---: | --- |
| ✓ | ✓ | 应用 DPI 修复，并启用完整汉化（推荐） |
| ✗ | ✓ | 仅启用汉化，不改变 DPI 行为 |
| ✓ | ✗ | 仅应用 DPI 修复，不释放或注入汉化资源 |
| ✗ | ✗ | 不执行任何处理，启动按钮不可用 |

### DPI 模式

| 模式 | 显示特点 | 适合场景 |
| --- | --- | --- |
| **清晰适配** | 保留原生物理像素渲染，并统一调整字体比例 | 首选；希望文字锐利且不挤出控件 |
| **PMv2 高清** | Per-Monitor v2 感知，由系统按显示器缩放控件 | 多显示器、不同缩放比例 |
| **系统增强** | Windows GDI 矢量缩放，兼容性好但边缘略柔和 | 个别面板在 PMv2 下异常时 |
| **位图** | 由系统整窗拉伸，最稳定但清晰度最低 | 其他模式均不兼容时的兜底方案 |

“清晰适配”提供 75% / 80% / **85%** / 90% / 100% 字体档位。字体仍然溢出时逐级调小；字太紧凑则调大。

## 汉化资源与打包地图

### 汉化包含哪些内容？

- 编辑器菜单、面板和目录名称；
- 触发器和游戏文本；
- 数据树中的官方依赖名称（约 29.9 万条运行时名称表）；
- 模型、资源路径的显示名称（约 9.3 万条资源名称表）。

少量英文会被刻意保留，例如对象 ID、单字母代码、网格尺寸、文件路径和其他技术标识。这些内容用于定位资源，翻译后反而可能造成误判。

### 打包前请暂时卸载

编辑器的 Build / Publish 可能会把外置字符串文件当作地图内容处理。打包地图或 Mod 前按下面流程操作：

1. 完全关闭银河编辑器。
2. 在启动器点击 **暂时卸载**。
3. 工具将汉化文件移入编辑器目录下的 `.sc2ed_dpifix_localization_disabled`，同时写入校验清单。
4. 用原版或启动器打开编辑器并完成打包。
5. 关闭编辑器，点击 **恢复汉化**；校验通过后文件会恢复到原位置。

如果编辑器正在运行，暂存和恢复都会被拒绝，以避免移动正在使用的文件。

### 文件保护策略

汉化文件首次释放后归用户所有。启动器会记录释放时的 SHA-256 基线：

- 文件缺失：释放新文件；
- 文件与资源包一致：跳过操作；
- 文件只被工具更新过：允许随版本更新；
- 文件被用户或第三方修改过：保留原文件，启动器不会覆盖。

如需强制重新建立基线，可在关闭编辑器后删除 `deploy/SC2EditorDependencyL10n.data.json`，再重新启动。

## 工作原理（简要）

```text
启动器
  ├─ 读取编辑器路径与用户选项
  ├─ 挂起创建 SC2Editor_x64.exe
  ├─ 在目标进程内存中定位 DPI 调用并按模式修补
  ├─ （可选）注入 SC2EditorDependencyL10n.dll
  └─ 恢复编辑器运行

汉化资源
  ├─ packages/editor  → 编辑器目录（界面与游戏字符串）
  └─ packages/hook    → deploy/（DLL 与运行时 TSV 名称表）
```

运行时 Hook 主要覆盖三条路径：默认对象名称、资源树文本，以及 `SendMessageW` 中的 `TVM_INSERTITEMW` / `TVM_SETITEMW`。这样既能翻译树节点初始名称，也能覆盖编辑器稍后设置的文本。

“系统增强”模式可能会在启动瞬间写入当前编辑器路径对应的 Windows 兼容层设置，进程创建后立即清理，用于实现热切换；编辑器可执行文件本身不会被改写。

## 项目结构

```text
sc2ed_dpifix/
├─ dpifix_core.py                 # 进程启动、DPI 补丁、资源释放与 Hook 注入
├─ sc2ed_dpifix_qml.py            # Qt Quick 启动器界面
├─ packages/
│  ├─ hook/                       # DLL + 官方依赖/资源名称表
│  │  ├─ SC2EditorDependencyL10n.dll
│  │  ├─ OfficialDependencyNames.tsv
│  │  └─ OfficialResourceNames.tsv
│  └─ editor/                     # 编辑器读取的外置字符串
│     ├─ EditorCatalogStrings.txt
│     ├─ EditorCategoryStrings.txt
│     ├─ EditorStrings.txt
│     └─ LocalizedData/*.txt
├─ deploy/                        # 运行时自动创建的 Hook 工作目录
├─ build.ps1                      # 完整构建入口
├─ SC2DPIFix.spec                 # PyInstaller 配置
└─ test_dpifix_core.py            # 核心逻辑测试
```

## 从源码构建

### 依赖

- Python 3.11+
- PySide6 6.11+
- PyInstaller
- MinGW-w64（编译 Hook DLL）
- 已安装的《星际争霸 II》及银河编辑器（生成官方名称表时需要）

### 构建命令

在仓库目录执行：

```powershell
cd E:\Code\sc2\Work\sc2ed_dpifix

# 完整构建：生成官方名称表、编译 Hook、打包单文件 EXE
.\build.ps1

# 资源和 DLL 已准备好时，仅重新打包 EXE
python -m PyInstaller --noconfirm --clean SC2DPIFix.spec

# 运行核心测试
python -m pytest test_dpifix_core.py -v
```

产物位于 `dist/SC2银河编辑器DPI修复.exe`。完整构建会读取本机 SC2 数据，首次运行时间可能较长。

## 常见问题

<details>
<summary><b>启动器打不开或闪退</b></summary>

确认系统为 64 位 Windows 10 / 11，并检查杀毒软件是否拦截了 PySide6/Qt 组件。远程桌面或虚拟机环境需要可用的 GPU / D3D11 加速；如果仍然失败，请在 Issue 中附上启动器提示和日志信息。
</details>

<details>
<summary><b>编辑器仍然模糊，或字体仍然溢出</b></summary>

确认“清晰度修复”已开启。优先尝试“清晰适配”并将字体设为 80%～90%；若多显示器布局异常，改试“PMv2 高清”；若某些旧面板不兼容，使用“系统增强”。
</details>

<details>
<summary><b>部分名称仍是英文</b></summary>

技术标识、文件路径和少数没有可靠中文来源的名称会保留原文。如果确认是普通界面文本或对象名称缺失，欢迎提交 Issue，并附上编辑器版本、名称所在面板和 `deploy/SC2EditorDependencyL10n.log`（注意移除个人路径）。
</details>

<details>
<summary><b>打包地图时报错</b></summary>

完全关闭编辑器 → 点击“暂时卸载” → 重新打开并打包 → 关闭编辑器 → 点击“恢复汉化”。不要在编辑器运行时手动移动 `Editor/*.txt` 文件。
</details>

<details>
<summary><b>如何恢复原版？</b></summary>

直接使用原版快捷方式启动 `SC2Editor_x64.exe` 即可。若要清理外置资源，请先关闭编辑器，再删除由本工具释放的 `Editor` 字符串文件和本项目的 `deploy/` 目录；用户自行修改过的文件请先备份。
</details>

## 许可与声明

本项目用于改善《星际争霸 II》银河编辑器的使用体验，不包含暴雪官方数据包，也不代表 Blizzard Entertainment。星际争霸 II、银河编辑器及相关名称归其各自权利人所有。

翻译资源沿用原汉化项目的署名与授权范围；具体贡献者请参阅 [`CREDITS.md`](CREDITS.md)。

## 致谢

- **头目**：原始汉化文本
- **hgzerg**（GA 用户）：注释补充
- **OB**：翻译校正与长期维护
- **BoomFirst**：DPI 修复、官方 CASC 依赖汉化补全、运行时 Hook、启动器与构建工具链

发现问题或有改进建议，欢迎提交 [Issue](https://github.com/BomLog/sc2-editor-zh/issues) 或 Pull Request。
