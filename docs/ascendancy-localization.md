# 升华天赋汉化补齐（2026-11-20）

本轮检查当前 3.30 标准与残酷模式的全部升华源节点，包含血脉、贵族升华和仍保留在数据中的旧升华。补充 365 条属性与括号说明：标准树 317 条，残酷模式独立描述 48 条。名称与背景文字同时纳入检查。

中文参考的属性列表常混入说明文字，导致中英文列表长度不同，原有整组配对会跳过这些条目。本轮在 `passive-reviewed.json` 中逐条核对英文含义后补充配对，不按数字或列表位置自动推定对应关系。282 条使用已有中文参考，83 条按本地英文直译或修正参考中的含义错误；直译状态记录为 `direct-translation-local-semantics-reviewed`，不代表官方译名已核对。新增译文校验数字、正负号与小数；保留独立的总增/总降含义和触发条件。

残酷模式与标准模式可能共用节点 ID、使用不同文字。`export_ascendancy_sources.py` 导出两棵实际树的升华显示字段，并记录源文件 SHA-256；生成器拒绝使用过期导出。`ascendancy-reviewed.json` 的译文仅用于对应版本中确实存在的原文，并加入节点上下文，支持跨行属性重组。未改动官方树数据、解析和计算逻辑。

验证命令：

```powershell
D:/POB/python-tools/python.exe tools/localization/export_ascendancy_sources.py
D:/POB/python-tools/python.exe tools/localization/build_locale.py
D:/POB/python-tools/python.exe tools/localization/test_ascendancy_locale.py
D:/POB/python-tools/python.exe tools/localization/check_calc_localization.py
```

升华专项在无用户设置和存档的临时副本中运行 LuaJIT：每个版本检查 565 个源节点，两版本共 3,637 条源文本；每个版本的 521 个实际节点分别开启、关闭不支持效果提示，检查实际 Tooltip。所有检查均无英文残留，并验证英文模式保留原文。结果见 `tools/localization/ascendancy-tooltip-audit.json`。

计算页专项通过，包括 2,302 个标识符、实际表格 3,475 条文字、15,994 次数值对照及布局检查。以上为静态与无界面 Lua 验证，未进行桌面或真实窗口操作；未对历史版本的所有天赋树作覆盖声明。应用运行时缓存译文，重启 PoB 后加载更新。
