# SC2 银河编辑器 DPI 修复 & 官方依赖汉化

<p align="center">
  <img src="app.ico" width="96" alt="SC2 Editor DPI Fix" />
</p>

> **一键让星际争霸 II 银河编辑器在高分屏上恢复清晰，同时把官方 CASC 依赖目录翻译为中文。**  
> 不修改编辑器可执行文件，不修改任何官方数据包。

当前版本：**1.5.0** · 更新日志见 [`CHANGELOG.md`](CHANGELOG.md) · 署名见 [`CREDITS.md`](CREDITS.md)

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| **清晰度修复（DPI Fix）** | 挂起启动编辑器 → 定位并 NOP 两处运行时 DPI-aware 调用 → 恢复运行。4 种模式可选：清晰适配、PMv2、系统增强、位图缩放 |
| **官方依赖汉化** | 运行时 DLL 注入，通过 IAT Hook 拦截 `SendMessageW`，在树节点插入/设置时实时翻译 19 万+ 条官方 CASC 依赖名称 |
| **编辑器界面汉化** | 释放完整的编辑器字符串资源到 `Editor/` 目录，覆盖界面文本、目录名称、触发器、游戏文本等 8 个文件 |
| **三种启动模式** | 清晰度修复 + 汉化 / 仅汉化 / 仅清晰度修复——按需独立开关 |
| **暂时卸载 / 恢复** | 打包地图前可一键暂存所有外置汉化文件，发布后一键恢复 |

## 📦 下载与安装

### 系统要求

- **操作系统**：Windows 10 / Windows 11（64 位）
- **星际争霸 II**：已安装银河编辑器（`SC2Editor_x64.exe`）
- **无需联网**：完全离线运行，不依赖任何网络服务
- **无需额外运行库**：VC++ 运行时已内嵌，无需单独安装

### 安装步骤

1. 从 [Releases](https://github.com/BomLog/sc2-editor-zh/releases) 下载最新的 `SC2银河编辑器DPI修复.exe`（约 59 MB 单文件）
2. 放到任意目录即可运行——**无需安装，无需管理员权限**
3. 首次运行时选择你的 `SC2Editor_x64.exe` 路径（通常在 `D:\StarCraft II\Support64\SC2Editor_x64.exe`）
4. 路径会自动记忆，下次打开无需重选

## 🚀 使用说明

### 启动

双击 `SC2银河编辑器DPI修复.exe`，打开启动器界面：

```
┌──────────────────────────────────────────┐
│       SC2 银河编辑器 DPI 修复            │
│                                          │
│  » D:\StarCraft II\...\SC2Editor_x64.exe │
│                                          │
│  ┌─────────────┐ │ ┌─────────────┐       │
│  │ 清晰度修复 ✓│ │ │ 官方依赖汉化✓│      │
│  └─────────────┘ │ └─────────────┘       │
│                                          │
│  清晰适配  PMv2  系统增强  位图缩放      │
│                                          │
│       [ ▶ 启动修复版编辑器 ]             │
│                                          │
│    原汉化：头目 · hgzerg · OB            │
│    工具开发：BoomFirst                    │
└──────────────────────────────────────────┘
```

### 三种启动模式

| 开关状态 | 启动按钮文字 | 效果 |
|---------|-------------|------|
| 清晰度修复 ✓ + 汉化 ✓ | **启动修复版编辑器** | 同时应用 DPI 修复与完整汉化 |
| 清晰度修复 ✗ + 汉化 ✓ | **启动汉化版编辑器** | 仅注入汉化 DLL 和释放字符串资源，不修补 DPI |
| 清晰度修复 ✓ + 汉化 ✗ | **启动修复版编辑器** | 仅做 DPI 清晰度修复，不释放任何汉化文件 |

> 两个开关同时关闭时无法启动，会提示"没有需要修补的功能"。

### DPI 修复模式详解

| 模式 | 原理 | 适用场景 |
|------|------|---------|
| **清晰适配** | 系统矢量 DPI 缩放 + 字体比例微调 | 推荐——文字和 UI 都清晰锐利 |
| **PMv2** | Per-Monitor v2 DPI 感知 | 多显示器不同缩放比例时 |
| **系统增强** | 系统增强缩放（注册表热切换） | 兼容性最好的方案 |
| **位图缩放** | 关闭 DPI 感知，由系统拉伸 | 最后的退路 |

> 选择"清晰适配"时可额外调整字体缩放比例（默认 85%），数值越小字体越紧凑。

### 暂时卸载与恢复

用编辑器打包地图/Mod 时，建议先暂时卸载汉化：

1. **完全关闭编辑器**
2. 点击启动器中的 **「暂时卸载」** 按钮
3. 外置汉化文件被移入 `Editor/.sc2ed_dpifix_localization_disabled`，保留完整目录结构和 SHA-256 校验
4. 正常使用编辑器打包
5. 打包完毕后点击 **「恢复汉化」**，校验后原样恢复

## 🏗️ 技术架构

```
SC2银河编辑器DPI修复.exe
├── dpifix_core.py          核心引擎：进程创建、内存补丁、DLL 注入、资源释放
├── sc2ed_dpifix_qml.py     Qt Quick 动画界面（ANGLE/D3D11 渲染）
├── packages/
│   ├── hook/               → 释放到 deploy/（框架本地目录）
│   │   ├── package.json
│   │   ├── SC2EditorDependencyL10n.dll    运行时 Hook DLL（3 MB）
│   │   ├── OfficialDependencyNames.tsv    依赖名称翻译表（19万条）
│   │   └── OfficialResourceNames.tsv      资源名称翻译表
│   └── editor/             → 释放到编辑器 Editor/ 目录
│       ├── package.json
│       ├── EditorCatalogStrings.txt
│       ├── EditorCategoryStrings.txt
│       ├── EditorStrings.txt
│       └── LocalizedData/
│           ├── GameStrings.txt
│           ├── ObjectStrings.txt
│           ├── TriggerStrings.txt
│           ├── GameStringsProduct.txt
│           └── ObjectStringsProduct.txt
└── deploy/                 运行时工作目录（自动创建）
    ├── SC2EditorDependencyL10n.dll
    ├── SC2EditorDependencyL10n.log
    ├── SC2EditorDependencyL10n.data.json   文件基线记录
    └── *.tsv
```

### Hook 机制

注入的 `SC2EditorDependencyL10n.dll` 安装三个 Hook：

1. **缺省名称 Hook**：拦截树节点插入时的默认名称回调，翻译 CASC 对象 ID
2. **资源树 Hook**：拦截模型/资源路径的文本回调，翻译文件名 basename 和显示名
3. **IAT SendMessageW Hook**：拦截所有 `TVM_INSERTITEMW` / `TVM_SETITEMW` 消息，捕获晚设置的文本——这是覆盖率最高的路径

DLL 通过环境变量 `SC2ED_DPIFIX_L10N_DATA` 定位翻译表和日志文件，编辑器目录不存放任何 Hook 文件。

### 文件同步策略

释放到编辑器目录的文件采用智能同步：

- **与资源包一致** → 跳过（无需操作）
- **缺失** → 释放新文件
- **未被外部修改**（与释放时基线一致）→ 随资源包静默更新
- **已被外部修改** → 原样保留，启动器永不覆盖用户的修改

> 删除 `deploy/SC2EditorDependencyL10n.data.json` 后重启即可重新释放上游版本。

## 🔧 从源码构建

### 环境要求

- Python 3.11+（推荐 3.11.15）
- PySide6 6.11+
- PyInstaller
- MinGW-w64（g++，用于编译 Hook DLL）
- 星际争霸 II 已安装（用于从 CASC 生成翻译表）

### 构建步骤

```powershell
cd E:\Code\sc2\Work\sc2ed_dpifix

# 完整构建（重新生成翻译表 + 编译 DLL + 打包 EXE）
.\build.ps1

# 仅打包 EXE（翻译表和 DLL 已就绪时）
python -m PyInstaller --noconfirm --clean SC2DPIFix.spec
```

产出：`dist/SC2银河编辑器DPI修复.exe`（约 59 MB 单文件）

### 运行测试

```powershell
python -m pytest test_dpifix_core.py -v
```

## ❓ 常见问题

<details>
<summary><b>启动器打不开 / 闪退</b></summary>

- 确认系统为 64 位 Windows 10 或 Windows 11
- 尝试右键 → 以管理员身份运行
- 若使用远程桌面或虚拟机，确认 GPU 加速可用（Qt Quick 需要 D3D11）
</details>

<details>
<summary><b>编辑器启动后仍然模糊</b></summary>

- 确认"清晰度修复"开关已打开
- 尝试切换不同的 DPI 修复模式（推荐先试"系统增强"）
- 在 Windows 显示设置中确认缩放比例（125%/150% 均支持）
</details>

<details>
<summary><b>部分内容仍显示英文</b></summary>

- 数据树中的单字母代码、网格尺寸（12x12）、资产路径等技术标识是设计保留，不翻译
- 如发现应翻译但未翻译的内容，欢迎提 Issue
</details>

<details>
<summary><b>打包地图时报错</b></summary>

编辑器打包（Build / Publish）前请先暂时卸载汉化：关闭编辑器 → 点击"暂时卸载" → 重新打开编辑器打包 → 完成后"恢复汉化"。
</details>

<details>
<summary><b>想恢复到全英文编辑器</b></summary>

直接用原版快捷方式启动编辑器即可——本工具不修改任何可执行文件。要清理释放的字符串文件，删除编辑器目录下的对应 txt 文件和 `deploy/` 目录。
</details>

## 📄 许可

本项目仅用于改善星际争霸 II 银河编辑器的使用体验。  
星际争霸 II 及银河编辑器为暴雪娱乐（Blizzard Entertainment）的产品。

## 🙏 致谢

| 贡献者 | 贡献内容 |
|--------|---------|
| **头目** | 原始翻译文本 |
| **hgzerg**（GA 用户） | 注释补充 |
| **OB** | 翻译校正与长期维护 |
| **BoomFirst** | DPI 修复、官方 CASC 依赖汉化补全、运行时 Hook、启动器与工具链开发 |
