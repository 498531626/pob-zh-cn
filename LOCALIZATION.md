# 中英文对照版

本仓库仅维护官方 PoB 的中文显示层。当前官方基线见 `upstream-base.json`；后续稳定版通过 `upstream` 合入，再适配、生成并验证汉化，具体见 [上游同步流程](docs/upstream-sync.md)。项目执行约束见 `AGENTS.md`。

从 `E:\POB\启动POB开发版.cmd` 启动。`PathOfBuilding-Portable` 仍是下载时的官方英文版。

- F8 或左下角语言按钮：英文 → 中文 → 中英对照，立即切换并记住选择。
- 按住 Alt：临时显示英文；松开后恢复。Alt 同时有原版开发调试用途。
- 本次补充 3.29 天赋树的普通点、核心天赋、升华点、专精选项及说明。不是完整软件的全量汉化；装备词缀、历史版本独有天赋、动态替换的珠宝天赋、部分配置和提示仍可能显示英文。
- 界面输入框、内部技能 ID、物品词缀解析、构筑保存格式和计算数据继续使用原始数据。搜索与复制功能仍按原版英文运行。

## 翻译来源及核对

使用流亡编年史同版本中英文数据：

- https://poedb.tw/data/passive-skill-tree/3.29/data_cn.json?5
- https://poedb.tw/data/passive-skill-tree/3.29/data_us.json?5
- 宝石名称使用 `/cn/Skill_Gems`、`/us/Skill_Gems` 和对应的 `Support_Gems` 页面。

天赋先匹配节点编号，再核对本地英文原文。专精选项按 effect 编号匹配。属性说明核对数字后才启用；版本不同或数字不一致时不强行替换。同一英文有多个译法时使用 `PassiveContexts.lua` 按节点选择，避免把不同节点混为一项。

`src/Localization/术语对照.csv` 列出通用词表与来源；按节点的译文见 `PassiveContexts.lua`。`tools/localization/passive-coverage.json` 记录覆盖率和未匹配项。字形来自本机微软雅黑副本，供本地版本使用。

## 重新生成与验证

在源码目录执行：

```powershell
python tools/localization/build_locale.py
python tools/localization/test_locale.py
```

参考数据快照保存在 `tools/localization/`，可用 `fetch_reference.ps1` 刷新。同版本生成使用 `pob-tree-en.json` 本地树快照；升级 PoB 或更换天赋树版本时必须同时重新导出本地树并调整参考版本，不能沿用旧的覆盖统计。

测试使用随程序附带的 LuaJIT。已验证全部按节点词条的英文、中文、对照显示结果，以及颜色、中文换行、Alt 回看、提示缓存刷新、输入框隔离与 Lua 语法。尚未完成真实窗口中所有节点、珠宝变换天赋与完整构筑流程的回归验证。
