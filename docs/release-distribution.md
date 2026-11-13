# GitHub 发布与汉化更新

源码、完整便携包、更新清单和更新文件均仅使用 GitHub：
https://github.com/498531626/pob-zh-cn 。仓库已公开，保留完整官方和汉化提交历史。

- 开发源码：`origin/localization`。
- 完整便携 ZIP 与 SHA-256：GitHub Releases。
- 稳定清单：`https://raw.githubusercontent.com/498531626/pob-zh-cn/release-stable/manifest.xml`。
- 更新载荷：`https://raw.githubusercontent.com/498531626/pob-zh-cn/<release-id>/files/`。

官方 `upstream` 仅用于跟进上游，不向它推送。源码推送、Release 附件和更新站点是三个独立步骤。
客户端使用非开发者模式，启动时及每隔 12 小时检查汉化清单，仅下载有变化的完整文件，
验证 SHA-1 后提示用户确认应用；涉及运行库时由 Update.exe 在退出后替换并重启。
个人构筑、设置和语言选择不进入更新文件列表。不连接官方项目的更新源。

## 构建与验证

```powershell
python tools/packaging/sync_sources.py
python tools/packaging/sync_sources.py --execute
python tools/packaging/build_portable.py --output E:/POB/Packages/新目录 --github-repository https://github.com/498531626/pob-zh-cn --release-id zh-版本-日期-批次
python tools/packaging/check_portable.py 完整ZIP路径
python tools/packaging/test_releases.py
```

同步工具只推送 `origin/localization`。构建要求已提交的干净源码；不带仓库参数时生成关闭在线更新的包。
输出完整 ZIP、SHA-256、发布计划，以及 `*-update-site/`：根目录的 manifest.xml、changelog.txt 和 files/。
ZIP 包含原始资源，无需用户合并下载分卷。目标系统为 Windows 10/11 x64，无需开发环境。

## 发布顺序

1. 验证并提交汉化，推送 `origin/localization`。
2. 用实际 GitHub 地址构建，验证解压后的正式包。
3. 在隔离的发布 checkout 中提交 update-site 文件树；首次使用独立 orphan `release-stable` 分支。
   不覆盖开发 checkout，发布提交不应以开发源码提交为父提交。
4. 给候选文件树创建不可移动的 release-id 标签，先推送标签到 origin。
5. 匿名探测标签中的清单、脚本、中文字库、EXE 与 DLL，验证实际文件哈希。
6. 探测成功后正常快进推送 `release-stable`，不强推覆盖并行发布；再验证稳定地址。
7. 在 GitHub Release 上传完整 ZIP 与 SHA-256，确认附件完整后公开 Release。
8. 从独立旧包副本执行真实下载、应用更新及重复检查，确认保存个人数据。

```powershell
python tools/packaging/probe_update_site.py https://raw.githubusercontent.com/498531626/pob-zh-cn/发布标签/manifest.xml
python tools/packaging/probe_update_site.py https://raw.githubusercontent.com/498531626/pob-zh-cn/release-stable/manifest.xml --all-files
```

发布标签指向更新文件树；若需对应源码标签，使用 `source-<release-id>` 指向原始汉化提交。
不移动已发布标签；新的汉化修复使用新的 release-id，同一官方版本可以多次发布。
源码在发布 checkout 中可作为只读 Git 对象来源，使 Git 传输复用已有资源对象。

## 验证范围

发布工具的无界面测试覆盖真实 Lua/curl 下载、重定向、增删改、404、哈希错误、HTML 页面拒绝、
路径检查、个人数据保护、重复更新、原生 x86 更新器与仅推送 GitHub 的源码流程。
完整包检查包括 CRC、SHA-256、SHA-1、25 个原生库加载、默认中文、中英文切换、8 个页面、
离线计算及 XML 构筑读写。真实远程下载另行执行，不把模拟站点通过当成 GitHub 验收。
用户要求不控制电脑，所有验收均在隔离副本和无界面进程中进行，不打开桌面窗口。
