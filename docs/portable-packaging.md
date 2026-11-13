# Windows 汉化便携包

打包当前已提交的汉化源码和本仓库配套运行库，不覆盖外层官方便携版，
不复制用户构筑、设置、语言选择、API 响应、Git 目录或开发参考快照。
目标为 Windows 10/11 x64；收件人无需 Python、Lua、Git 或开发环境。

```powershell
python tools/packaging/build_portable.py --output E:/POB/Packages/新输出目录
python tools/packaging/check_portable.py 完整压缩包路径.zip
```

输出包括完整目录、ZIP 和 SHA-256 校验文件。已有输出不会覆盖。
ZIP 解压后双击根目录的 `Path of Building.exe` 或 `Start-PoB.cmd`。
采用官方便携版的平铺结构，脚本、运行库和资源都在同一根目录。
打包时为 manifest 写入 `branch="localization"`、`platform="win32"`，
确保以非开发者模式运行。默认不配置在线更新，独立的 `updates="disabled"` 属性关闭更新。
提供 `--gitee-repository` 时改为 release-stable 渠道，启用自己的汉化更新源；
详细说明见 [双仓库发布与更新流程](release-distribution.md)。
启动代码在首次安装、手动/定期检查和应用更新处遵循该开关。
源码目录自己的 manifest 保持原样，开发启动行为不变。
个人数据写入包内 `Builds`、`Settings.xml` 和 `Localization/language.cfg`。
新版本解压到新目录，先备份再迁移个人数据。旧开发模式包的数据在 `src/` 下，
须将其 `src/Builds`、`src/Settings.xml`、`src/Localization/language.cfg`
分别迁移到新包的上述位置，不能把整个旧 `src/` 覆盖进去。

文件列表由 Git 跟踪清单确定。沿用官方发布排除项，去除安装入口、
导出开发工具。离线包去除旧更新器及 x86 `msvcr100.dll`；在线更新包保留两者，
用于在主程序退出后替换运行库，不能用 x64 Python 直接加载这个 x86 DLL。
保留完整历史天赋树、图片及汉化字形资源。

## 2026-11-13 验证

- 官方基线：2.67.2；具体源码提交见产物的 `package-info.json`。
- 初版误用 devMode 关闭更新，已改为正式便携模式及独立更新开关。
- 产物约 622.1 MiB；ZIP CRC 与文件 SHA-256 验证。
- 从 ZIP 解压到独立、路径含空格的临时目录，在子进程中验证，退出后清理。
- 限制 DLL 搜索 PATH 到包内 runtime 与 Windows System32；25 个随包 DLL 加载通过。
- 只用解压包内 LuaJIT、Lua 模块和数据，检查无界面启动、默认中文、关闭官方更新、
  包内数据路径、Cyclone 离线计算、8 个页面、中英切换及构筑 XML 写入/重载。
- 新包额外断言 devMode 为 false、版本文案不含 Dev、无开发者选项、
  F5 不触发开发重启、无更新按钮，且遗留 first.run 也不会启动官方更新。
- `python tools/localization/test_locale.py` 通过：11472 个上下文翻译、176 个面板标签。
- 修正版的 `python tools/localization/check_calc_localization.py` 全部通过：
  2249 个计算属性、实际明细 3418 个字符串、15924 次数值对比、4214 个布局用例，
  并覆盖物品搜索、导入装备提示及 8 页中英文显示。
- 遵循用户要求，未打开或控制桌面窗口；未验证真实窗口绘制、显卡兼容性、
  联网导入或全新 Windows 虚拟机。DLL 加载通过不等于全新系统已验收。

分发包不包含验收生成的测试构筑；校验和与源提交记录在产物旁及 `package-info.json`。
