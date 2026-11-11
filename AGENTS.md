# 项目定位

本仓库维护 Path of Building 的简体中文显示层，保留官方玩法数据、计算逻辑、内部 ID、词缀解析与构筑保存格式。默认跟进官方稳定发布 tag，不主动跟进 dev 或扩展非汉化功能。

## 上游与更新

- `origin` 是用户的汉化仓库；`upstream` 是 `https://github.com/PathOfBuildingCommunity/PathOfBuilding.git`。
- 汉化集成分支为 `localization`；已接入版本和官方提交记录在 `upstream-base.json`。
- 更新操作遵循 [上游同步流程](docs/upstream-sync.md)。先在独立更新分支或 worktree 合入官方版本、解决冲突、适配汉化和验证，再串行合回 `localization`。
- 保留官方提交和汉化提交的边界，使用正常 merge 跟进新版本。不要用新 ZIP 覆盖整个目录，不重写用户已有历史；不要使用 ours 策略跳过真正的新版本更新。
- 用户要求“更新上游并适配汉化”即授权执行上述本地工作和验证后提交、集成；远程 push、发布另需用户明确要求。

## 汉化约束

- 翻译逻辑集中在 `src/Modules/Localization.lua`，词典和字形在 `src/Localization/`，生成工具与参考快照在 `tools/localization/`。
- 对官方代码的接入修改保持最少，重点检查 `Main.lua`、按钮、输入框、天赋树和 Tooltip。合并无冲突不代表汉化兼容。
- 界面显示可翻译，计算键名、技能 ID、输入解析和构筑序列化仍保持官方语义。未核对译文回退英文。
- 游戏版本或天赋树变化时重新导出实际 PoB 树，并更新同版本的中英文参考快照、版本元数据和覆盖统计。禁止用旧快照生成“新版已覆盖”的结论。
- 优先修改翻译输入及生成器，不直接手改生成的 Dictionary、Glyphs、PassiveContexts 或 coverage 文件。
- 至少运行专项汉化验证；影响绘制、输入、页面或运行库时补充真实窗口检查。报告静态检查、Lua 验证和真实界面验证各自的范围，不混称为完整回归。
- 本地构筑、设置、语言选择属于用户数据，更新时保留。外层 `PathOfBuilding-Portable` 是独立官方版本，不随源码汉化更新一起覆盖。
