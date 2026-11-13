# 抗性计算明细漏译修复

截图中的 `Cold Resist Max` 来自 `CalcBreakdownControl:FormatModName`：
计算键 `ColdResistMax` 在生成明细表的“属性”列时才被拆成英文单词。
词典已有 `Cold Resist`，但没有这个带 `Max` 的完整标签，显示层精确匹配失败后保留英文。
固定 `CalcSections` 标题覆盖检查和只扫描计算输出 breakdown 字符串的审计，
都不能替代明细控件实际生成的属性列检查。

在 `tools/localization/calc-extra.json` 补入 16 个显示词条，包括四种抗性及元素抗性上限、
图腾抗性与图腾抗性上限。`Cold Resist Max` 显示为“冰霜抗性上限”。
使用生成器输出词典、术语表和条目统计，保留原有无关词条及来源记录。
不修改计算键、抗性数值、构筑文件或用户语言设置。

验证：

- `test_calc_panel_locale.py`：20 种实际属性格式化结果、颜色、英文切换、未知项回退；
  使用真实 `AddModSection` 重建截图的 `+75 ColdResistMax` 与 `-60 FireResist` 混合表，
  检查角色／召唤物路径、来源、内部属性名和数值保持不变。
- `test_calc_buff_lists.py`：56 个战斗标签及已有增益列表回归通过。
- `test_locale.py`：11,472 个上下文翻译、176 个侧栏标签及 Lua 语法等专项检查通过。
- `test_layout.py --workspace E:/POB/Resistance-QA-20261113`：隔离副本 4,214 组宽度、
  8 页、两种分辨率、语言切换、计算数值和技能序列化检查通过。

真实窗口检查过程中，界面自动化被用户物理 Escape 中止；未完成修复后的原生窗口验收。
检查范围为截图和同类抗性明细，不代表所有构筑的动态文本已经全部覆盖。
