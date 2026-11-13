# Windows 汉化便携包

打包当前已提交的汉化源码和本仓库配套运行库，不覆盖外层官方便携版，
不复制用户构筑、设置、语言选择、API 响应、Git 目录或开发参考快照。
目标为 Windows 10/11 x64；收件人无需 Python、Lua、Git 或开发环境。

```powershell
python tools/packaging/build_portable.py --output E:/POB/Packages/新输出目录
python tools/packaging/check_portable.py 完整压缩包路径.zip
```

输出包括完整目录、ZIP 和 SHA-256 校验文件。已有输出不会覆盖。
ZIP 解压后双击 `Start-PoB.cmd`，或运行 `runtime/Path of Building.exe`。
须保留 `runtime/`、`src/` 和根目录文件的相对结构。
沿用源码版本的 manifest 和启动方式，启用现有 devMode，禁止官方更新覆盖汉化。
个人数据写入包内 `src/Builds`、`src/Settings.xml` 和
`src/Localization/language.cfg`；新版本解压到新目录，先备份再迁移个人数据。

文件列表由 Git 跟踪清单确定。沿用官方发布排除项，去除安装入口、
导出开发工具、32 位旧更新器及不供当前 x64 运行时使用的 `msvcr100.dll`。
保留完整历史天赋树、图片及汉化字形资源。

## 2026-11-13 验证

- 程序源码提交：`8931c84bf`；官方基线：2.67.2。
- 产物约 622.1 MiB；ZIP CRC 与 1415 个版本化文件 SHA-256 通过。
- 从 ZIP 解压到独立、路径含空格的临时目录，在子进程中验证，退出后清理。
- 限制 DLL 搜索 PATH 到包内 runtime 与 Windows System32；25 个随包 DLL 加载通过。
- 只用解压包内 LuaJIT、Lua 模块和数据，检查无界面启动、默认中文、关闭官方更新、
  包内数据路径、Cyclone 离线计算、8 个页面、中英切换及构筑 XML 写入/重载。
- `python tools/localization/test_locale.py` 通过：11472 个上下文翻译、176 个面板标签。
- 遵循用户要求，未打开或控制桌面窗口；未验证真实窗口绘制、显卡兼容性、
  联网导入或全新 Windows 虚拟机。DLL 加载通过不等于全新系统已验收。

分发包不包含验收生成的测试构筑；校验和与源提交记录在产物旁及 `package-info.json`。
