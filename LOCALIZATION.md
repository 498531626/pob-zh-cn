# 中英文对照版

本仓库仅维护官方 PoB 的中文显示层。当前官方基线见 `upstream-base.json`；后续稳定版通过 `upstream` 合入，再适配、生成并验证汉化，具体见 [上游同步流程](docs/upstream-sync.md)。项目执行约束见 `AGENTS.md`。

从 `E:\POB\启动POB开发版.cmd` 启动。`PathOfBuilding-Portable` 仍是下载时的官方英文版。

- F8 或左下角语言按钮：英文 → 中文 → 中英对照，立即切换并记住选择。
- 按住 Alt：临时显示英文；松开后恢复。Alt 同时有原版开发调试用途。
- 中文显示包括侧栏属性、计算页标签和已核对的公式说明、配置标签与提示、技能详情，以及 3.29 天赋名称、属性、专精、提醒和背景说明。
- 天赋的红色“PoB 尚未支持此效果”提示保留红色警告；相关属性文字仍可翻译。翻译不会使原本不支持的效果参与计算。
- 技能详情包括名称、标签、需求、消耗、冷却、品质、描述和数值词条，以及已核对的装备和升华提供的技能。中英对照模式的固定界面标签使用紧凑中文，完整详情中显示中文和英文。
- 物品页补充了暗金名称、装备底材、制作词缀、范围值和档位占位符，以及词缀档位、标签、版本、插槽和装备对比等动态提示。物品参考来自 PoEDB 同页的中英文卡片和词缀记录，先核对记录身份和数值，再用于显示。资料快照以 gzip 保存于 `tools/localization/item-reference/`。
- 物品专项清单包含历史、绝版及特殊数据，尚有未核对条目；`item-display-pending.json` 和 `item-runtime-pending.json` 保留这些原文，不能将此批更新理解为所有物品和所有词缀均已完成。
- 未核对的新内容仍回退英文。覆盖数字针对当前源码和检查用例，不代表所有历史天赋、珠宝变换、装备词缀或任意构筑状态均已验证。
- 界面输入框、内部技能 ID、物品词缀解析、构筑保存格式和计算数据继续使用原始数据。搜索与复制功能仍按原版英文运行。

## 翻译来源及核对

使用流亡编年史同版本中英文数据：

- https://poedb.tw/data/passive-skill-tree/3.29/data_cn.json?5
- https://poedb.tw/data/passive-skill-tree/3.29/data_us.json?5
- 宝石名称使用 `/cn/Skill_Gems`、`/us/Skill_Gems` 和对应的 `Support_Gems` 页面。

天赋先匹配节点编号，再核对本地英文原文。专精选项按 effect 编号匹配。属性说明核对数字后才启用；版本不同或数字不一致时不强行替换。同一英文有多个译法时使用 `PassiveContexts.lua` 按节点选择，避免把不同节点混为一项。原版把一条天赋拆成多行时，显示层按已核对的完整原文重组，保留各行对应的支持状态。

技能资料使用 PoEDB 中英文同页的宝石卡片；仅将本地存在的原文和数字占位符匹配为译文。存在单复数差异、译名冲突或不同换行的内容需人工核对，记录在 `gem-reviewed.json` 和含来源的 `skill-reviewed.json`。生成器拒绝数字对应不一致的片段和未绑定的数字占位符，避免直接显示 `{0}` 或改变数值含义。

`src/Localization/术语对照.csv` 和 `catalog.json` 列出词表与来源；按节点的译文见 `PassiveContexts.lua`，数值技能词条见 `SkillTemplates.lua`。覆盖统计见 `src/Localization/build-info.json`、`tools/localization/passive-coverage.json` 和 `gem-coverage.json`。字形来自本机微软雅黑副本，中文标点与汉字共用基线。

## 重新生成与验证

在源码目录执行：

```powershell
python tools/localization/export_item_sources.py
python tools/localization/build_locale.py
python tools/localization/test_locale.py
python tools/localization/audit_ui_display.py
python tools/localization/audit_skill_display.py
python tools/localization/audit_item_display.py
```

实际计算和天赋浮窗检查必须使用独立的临时副本，不能指向源目录，以免读取用户设置或构筑：

```powershell
python tools/localization/audit_calc_display.py --workspace E:/POB/Localization-QA --passives
python tools/localization/audit_item_runtime.py --workspace E:/POB/Localization-QA
```

参考数据快照保存在 `tools/localization/`，可用 `fetch_reference.ps1` 刷新。同版本生成使用 `pob-tree-en.json` 本地树快照；升级 PoB 或更换天赋树版本时必须同时重新导出本地树并调整参考版本，不能沿用旧的覆盖统计。

测试使用随程序附带的 LuaJIT。当前检查结果：

- 11,472 条按节点译文、167 个侧栏标签、602 个计算标签及 738 个配置标签通过专项检查；同时核对颜色、数字、未知内容回退、三种语言模式、Alt 回看、换行和缓存刷新。
- 界面源码清单检查 3,938 处文字出现位置。格式参数、技术字符串和拼接片段单独记录依据，拼接消息提供完整示例；未解决项为零。
- 经实际技能词条生成器检查 31,795 条去重显示文本，含普通宝石和装备、升华提供的技能；该检查范围内的未翻译项为零。
- 10 个代表性技能的 552 条去重计算说明未发现英文残留；英文、中文及对照模式的数值输出一致。
- 当前构筑天赋树的 2,865 个实际浮窗未发现英文残留，其中包含 697 行红色属性说明。此项关闭属性差异计算以逐点检查；属性差异格式另有专项检查。
- 真实窗口检查覆盖计算页、公式展开、天赋与属性对比、红色专精提示、选中技能的详情和中英切换。输入框保留原文，提示和标签按语言显示。
- 物品后台检查使用原版物品解析器、制作逻辑和 Tooltip，核对 1,332 件暗金与 6 件制作装备在三种语言模式下的原始文本和已解析词缀数值。物品实际窗口验收被用户按 Esc 中止，尚未完成制作操作的界面验收。
- 本批物品生成 23,156 条精确译文和 3,904 个数值模板。本地名称清单中的 1,295 个暗金名称均已匹配；1,094 个底材中仍有 5 个旧箭袋名称待核对。6 件制作样例的完整详情没有英文残留；全暗金浮窗中仍有 525 件包含未核对的来源、特殊效果或变体说明。词缀清单的待核对统计含重复档位与历史数据，不等同于当前物品数量。

界面、技能、计算和天赋的严格检查发现未翻译项时会写入对应 `*-pending.json` 并返回失败。物品清单包含历史和未核对数据，目前输出覆盖及待核对报告；物品数据被翻译过程修改时仍立即失败。上述结果不替代所有构筑、所有珠宝变换和完整游戏流程的回归验证；新增上游文字应重新运行生成和检查。
