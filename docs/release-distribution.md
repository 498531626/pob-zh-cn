# 汉化双仓库与正式版更新

## 已确定的设计

| 内容 | GitHub | Gitee |
| --- | --- | --- |
| 开发汉化源码 | origin/localization | gitee/localization，保持同一提交 |
| 首次下载的完整便携包 | Releases 中的完整 ZIP | Releases 中同一 ZIP 的分卷及合并脚本 |
| 客户端更新清单 | 可备份，不作为默认更新入口 | release-stable 分支根目录 manifest.xml |
| 客户端更新文件 | 可备份 | 固定发布标签的 files/ 目录，通过 Raw 下载 |

官方 upstream 继续用于获取官方版本，不向它推送。开发源码不直接成为用户更新源。
Gitee 仓库尚未创建，因此本轮不配置远程、不推送、不上传附件，也不声称国内下载已验证。
正常构建不提供 Gitee 地址时仍生成关闭更新的便携包；不会写入占位在线地址。

客户端保持非开发者模式。启动时及每隔 12 小时检查汉化清单，后台下载变化的完整文件，
校验通过后提示用户确认更新；涉及运行库时交给 Update.exe，退出后替换并重启。
不连接官方更新源，不自动覆盖个人构筑、设置和语言选择。

## 本地工具

若本机没有 Gitee 授权，可由用户双击 `tools/packaging/Authorize-Gitee.cmd`，
或在自己的交互式终端中运行：

```powershell
python E:/POB/PathOfBuilding-Source/tools/packaging/authorize_gitee.py
```

脚本隐藏读取私人令牌，验证账号后仅存入 Windows Git Credential Manager。
令牌需有账号读取和仓库管理权限；不将令牌粘贴到聊天、不放入 Git、不嵌入更新客户端。
授权脚本本身不创建仓库或推送内容。

在仓库根目录运行，打包前需提交并验证修改。以下 Gitee URL 是示例，须换成实际公开仓库。

```powershell
# 配置一次源码远程；origin 已指向 GitHub 汉化仓库。
git remote add gitee https://gitee.com/用户名/仓库名.git

# 先预览；加 --execute 才实际推送。分别报告两边结果，失败不会强推或回退另一边。
python tools/packaging/sync_sources.py
python tools/packaging/sync_sources.py --execute

# 地址尚未确定时：准备可运行的离线包以及供 Gitee 发布的完整分卷。
python tools/packaging/build_portable.py --output E:/POB/Packages/新目录 --gitee-volumes

# 实际更新仓库建立后：生成启用汉化更新的包、分卷和更新站点文件树。
python tools/packaging/build_portable.py --output E:/POB/Packages/新目录 --gitee-volumes --gitee-repository https://gitee.com/用户名/仓库名 --release-id zh-2.67.2-20261113-r1
```

输出包括完整 ZIP、SHA-256、`*-gitee-assets/` 和（配置地址时）`*-update-site/`。
分卷每个不超过 90 MiB，包括 `.zip.001`、`.002` 等、Join-Portable.cmd 和说明。
收件人下载全部分卷及脚本到同一目录，运行合并脚本，自动校验得到与 GitHub 字节一致的 ZIP，
然后解压运行；不需要 Python 或 7-Zip。Git 推送不会同步 Releases 或附件，须两边分别上传。

`*-update-site/` 是独立发布文件树，不要复制进开发分支。其结构为：

```text
manifest.xml       稳定清单，引用固定发布标签
changelog.txt      此次更新说明
files/             平铺的便携版文件，与 ZIP 中一致
```

清单列出本次实际打包文件的 SHA-1，不复用官方旧清单；package-info.json 另记 SHA-256 和源码提交。
`Source default` 指向 Gitee `/raw/release-stable/`，用于后续检查清单；
program/runtime 的 Source 指向 `/raw/<release-id>/files/`，避免一次下载混入多个版本。
汉化发布标签独立于上游版本号，同一个 PoB 版本可发布多次汉化修复。标签发布后不可移动。

## 发布顺序

1. 完成汉化和无界面验证，提交到 localization，再同步到 GitHub、Gitee。
2. 构建启用实际 Gitee 更新地址的新包，验收 ZIP；初次启用时需用户重新下载整包。
3. 在隔离的发布 checkout 准备更新分支。首次建立独立的 orphan `release-stable` 分支，
   内容为 update-site 的文件树，不修改当前开发 checkout。后续在该分支上正常追加发布提交。
4. 对候选发布提交创建对应 release-id 标签，先推送标签到 Gitee。
   对候选标签上的 manifest 执行匿名下载探测，确保清单、Lua、中文图片和运行库直链返回实际文件。
5. 候选验证通过后再更新远程 release-stable 分支，使客户端发现该版本。发布前再次确认远程分支
   未被其他发布推进，不强制覆盖并行发布。
6. 在 GitHub Releases 上传完整 ZIP、校验文件，在 Gitee Releases 上传全部分卷、合并脚本、
   volumes.json 和说明；两边说明使用同一 release-id 和源码提交。Gitee 中也推送相应的源码标签。
7. 验证稳定清单直链，并从旧正式版副本验证更新到新版本，保留用户数据。

```powershell
python tools/packaging/check_portable.py 完整ZIP路径
python tools/packaging/probe_update_site.py https://gitee.com/用户名/仓库名/raw/发布标签/manifest.xml
python tools/packaging/probe_update_site.py https://gitee.com/用户名/仓库名/raw/release-stable/manifest.xml --all-files
python tools/packaging/test_releases.py
python tools/localization/check_calc_localization.py
```

标签指向发布文件树提交；localization 分支保存开发源码。不要把发布标签误打在开发源码提交上。
若另需源码标签，可使用 `source-<release-id>`，避免同名标签对应不同提交。

## 待实际仓库验证的条件

- Gitee 的 Raw 文件需要公开、免登录、无验证码；仅能打开网页不代表程序可以下载。
  客户端已支持重定向和 HTTP 错误处理，HTML 登录页、404、哈希不符不会进入应用更新阶段。
- Gitee 官方帮助当前列出普通项目单附件 100M、仓库附件总量 1G：
  https://help.gitee.com/repository/release/create 。分卷解决单附件上限，不改变总量上限。
  当前约 622 MiB 的整包分卷占同样的总容量，保留多个完整版本需要实际核对或提高配额。
- Raw 更新文件使用代码仓库存储，仍受代码仓库容量和访问规则约束；它不是无限容量下载服务。
  本地现有 Git 对象约 1.1 GiB，完整历史能否同步到新 Gitee 仓库须检查账户实际配额。
  若不足，应申请更高配额或另设发布仓库，不自动改写已有历史。
- 当前校验为 HTTPS + 文件哈希；未新增独立数字签名体系，也不承诺更新应用阶段支持自动回滚。
- 本轮只验证本机 HTTP 模拟站点和独立副本，不控制桌面，不混称真实 Gitee/CDN 或图形窗口验收。

## 2026-11-13 本地验收

- 11 项发布测试通过，使用真实 LuaJIT、curl 和本机 HTTP 服务，覆盖文件增删改、重定向、
  404、损坏文件、HTML 登录页、危险路径及个人数据保护；更新后再次检查返回无更新。
- 使用真实 Update.exe 与其 x86 运行库，在不创建窗口的子进程中完成测试文件替换。
- 两个本地 bare 仓库验证源码一次推送到双远程，不涉及真实 GitHub/Gitee 推送。
- 测试分卷通过生成的 Windows 合并脚本还原，逐字节一致并自动验证 SHA-256。
- 启用更新的完整测试包通过独立解压验收：非开发者模式、更新按钮与语言按钮不重叠、
  默认中文、25 个 x64 DLL 加载、8 页中英切换、离线计算、XML 保存重载。
  其 Gitee 地址仅为本地测试占位，产物位于 Release-QA，不用于分发，也未请求该在线地址。
- 完整计算汉化专项通过：2249 属性、3418 实际明细字符串、15924 次数值对比、4214 布局用例。
