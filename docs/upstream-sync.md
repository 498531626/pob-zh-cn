# 跟进官方版本并维护汉化

本项目是官方 PoB 的中文显示层。官方功能、数据和计算修复通过 Git 合并引入，再由 Codex 适配显示层；不会因官方程序自动更新而自动完成汉化。

## 已有基线

- 汉化仓库：`origin`，集成分支 `localization`。
- 官方仓库：`upstream`，默认选择正式稳定发布 tag。
- 当前已接入：`upstream-base.json` 中的 tag 与完整 commit。
- 最初源码来自 v2.67.2 ZIP，本地提交没有官方父提交。首次关联会核对本地初始快照与官方同版本树，并用一次保留当前文件的合并连接历史。后续更新必须正常三方合并，不能重复使用该策略。

首次核对结果：官方 tag 的 1593 个文件中，初始本地提交遗漏了被 `*.cfg` 忽略的 `manifest.cfg`，另有 5 个文件丢失 Unix 可执行位；其余文件 blob 全部一致，无源码内容差异。本次将已有且内容一致的 `manifest.cfg` 纳入跟踪、恢复上述模式位后连接历史，保留全部现有汉化内容及提交。

## 每次更新步骤

1. 检查 Git 状态、当前分支和 worktree；保留用户改动。查询官方发布页确认目标稳定版，不把 dev 提交或预发布当成稳定版。
2. 只获取目标 tag，例如 `git fetch --no-tags upstream tag vX.Y.Z`。不要直接 `git pull upstream dev`。
3. 运行 `python tools/upstream/check_update.py vX.Y.Z`。报告官方改动、本地改动、重叠文件和重点复核项；即使没有文件重叠也要检查调用合同与数据版本。
4. 从 `localization` 创建独立 `update/vX.Y.Z` 分支，必要时使用 worktree。执行 `git merge --no-ff --no-commit vX.Y.Z`，逐项解决冲突。保留官方新行为，再重新接入汉化，不整体选择 ours/theirs。
5. 检查启动流程、绘制函数、UTF-8 字宽/换行、F8 中英文切换与 Alt 不改变语言、输入框隔离、天赋节点上下文和提示缓存。根据新版界面补齐词条。计算、解析和构筑格式继续遵循官方。
6. 若游戏数据或树版本变化，重新导出本地树快照，并获取同版本中英文参考；调整 `fetch_reference.ps1`、`passive_locale.py` 和生成器中的版本/来源信息。版本不匹配时保留英文并记录缺口。
7. 检查官方 runtime 文件或压缩包的变化。当前源码运行使用已展开的 `runtime/`，如新版只更新运行时压缩包，也需按官方开发安装方式同步展开文件；保留设置、构筑和本地数据。
8. 运行 `python tools/localization/build_locale.py`，审查生成差异，然后运行 `python tools/localization/test_locale.py`。按变更范围运行相关 `spec` 测试。真实窗口检查语言切换、中文绘制、主要页面、构筑导入/保存/重开与计算；使用测试构筑或副本，避免覆盖用户构筑。
9. 验证通过后提交合并和适配，更新 `upstream-base.json`、`LOCALIZATION.md` 中版本、覆盖率与实际验证范围。无法完成的验证明确写出，不能冒称通过。
10. 将更新分支串行合回 `localization`，保留正常合并历史。仅用户明确要求时 push 或发布。

## 现有汉化输入与产物

| 类型 | 路径 |
| --- | --- |
| 手工界面词条 | `tools/localization/ui-terms.json` |
| 参考数据与本地树快照 | `tools/localization/poedb-*`、`pob-tree-en.json` |
| 词典与字形生成 | `tools/localization/build_locale.py` |
| 天赋 ID、英文与数字核对 | `tools/localization/passive_locale.py` |
| 生成的运行资源 | `src/Localization/` 中的词典、上下文、字形及 catalog |
| 覆盖报告 | `tools/localization/passive-coverage.json` |
| Lua 专项验证 | `tools/localization/test_locale.py` |

目前参考版本 3.29 及 PoB 版本字段仍有硬编码。接入新版时必须复核，不能只重跑生成脚本。

## 以后如何发起

直接告诉 Codex：**“检查官方稳定版更新，把这个汉化项目升级并适配汉化。”** 也可指定 tag。Codex 应执行上述流程，报告接入版本、新增翻译、剩余英文、验证情况和本地提交。

日常汉化和正式更新均从外层 `启动POB开发版.cmd` 启动验证；外层官方免安装目录独立保留。
