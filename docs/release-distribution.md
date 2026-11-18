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

汉化版本使用四段数字 `vX.Y.Z.N`：前三段与实际接入的官方版本完全相同，最后一段为从 1 开始的汉化补丁序号。
例如官方 `v2.68.1` 对应 `v2.68.1.1`，同一原版再次发布为 `v2.68.1.2`；升级官方 `v2.68.2` 后从 `v2.68.2.1` 开始。
源码 `manifest.xml` 记录当前开发版本，`upstream-base.json` 仅记录官方三段版本和提交，不加汉化序号。
客户端界面、便携包文件名、包元数据、更新清单和 Release 标签均使用四段汉化版本；官方数据和构筑格式不改。

```powershell
python tools/packaging/sync_sources.py
python tools/packaging/sync_sources.py --execute
python tools/packaging/build_portable.py --output E:/POB/Packages/新目录 --github-repository https://github.com/498531626/pob-zh-cn --release-id v2.68.1.1
python tools/packaging/check_portable.py 完整ZIP路径
python tools/packaging/test_releases.py
```

同步工具只推送 `origin/localization`。构建要求已提交的干净源码；不带仓库参数时生成关闭在线更新的包。
本地构建省略 `--release-id` 时使用源码清单中的四段版本；构建本身不会消耗发布序号。
输出完整 ZIP、SHA-256、发布计划，以及 `*-update-site/`：根目录的 manifest.xml、changelog.txt 和 files/。
ZIP 包含原始资源，无需用户合并下载分卷。目标系统为 Windows 10/11 x64，无需开发环境。

## 发布顺序

推荐在 GitHub Actions 手动运行 `Publish Chinese portable release`，选择 `localization` 分支，release-id 留空即可。
发布器读取 origin 现有的 `vX.Y.Z.N` 标签，按数字取同一官方版本的最大 N 加一，无匹配标签时从 1 开始。
旧日期格式标签不参与计数。也可手动填写预期版本，但必须等于自动计算的下一个版本，防止跳号或重复发布。
序号以不可变标签为准；若发布在创建标签后失败，该序号已占用，下次使用下一号，不覆盖旧标签。
发布时将选定版本写入生成包及更新清单，不修改源码分支；本地源码清单不随远程发布自动回写。
它在 GitHub Windows runner 上构建和无界面验证，上传候选标签、探测匿名下载、上传完整附件，
再推进稳定更新分支并公开 Release；不会在每次源码推送时自动发布。所需权限由工作流的 `contents: write` 提供。
本地无需上传约 623 MiB 的整包；也不需要额外保存发布令牌。

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
