# 词缀下拉框漏译修复与验证（2026-11-13）

截图中的“为物品添加词缀 → 隐匿”列表由 ItemsTab.lua 动态拼接：
`table.concat(mod, "/") .. " (" .. mod.type .. ")"`。
前后缀选择还会显示 `mod.affix .. "   ^8[" .. table.concat(mod, "/") .. "]"`。

原始词条已有译文，不意味着拼接后的显示文字也能命中。
原有通用括号处理会同时拆开数值范围 `(14-16)` 和尾部 `(Prefix)`，
导致完整数值模板匹配失败，出现英文残留、中英重复。
多属性词缀使用 `/` 拼接，而参考数据中的完整属性组使用换行，这也需要完整匹配或逐条匹配。
固定界面文字扫描与单条原文覆盖率没有验证这些实际组合，是此处反复遗漏的原因。

本次在显示层先识别准确的词缀元数据边界，再翻译完整属性。
带名称词缀要求准确的三个空格和灰色方括号分隔，避免干扰计算面板属性差异说明。
补充小天赋属性的显示包装；使用独立的已核对词句模板补齐隐匿、珠宝、药剂、嫁接等词缀。
已有精确词典与技能、物品模板优先，新模板仅作为后备。
内部 ID、数据表、英文解析行与保存格式不作修改。

## 翻译输入与生成

- `tools/localization/crafting-reviewed.json`：按本地 Data/Mod*.lua 语义核对的完整句与数值模板。
- `crafting-families.json`：明确列举元素、珠宝种类和对应中文的有限组合。
- `crafting-grafts.json`：按本地 ModGraft 语义核对的嫁接词句；已有技能名沿用项目词典。
- `build_crafting_locale.py`：生成 `src/Localization/CraftingTemplates.lua`，校验数字占位符对应关系。
- `build_locale.py`：调用该生成器，并将新增译文加入字形输入。

新增嫁接技能名核对来源：
[虚弱之握](https://poedb.tw/cn/Enervating_Grasp)、
[天坠冰晶](https://poedb.tw/cn/Falling_Crystals)、
[焚世箴言](https://poedb.tw/cn/His_Burning_Message)、
[血肉过载](https://poedb.tw/cn/Overcharged_Sinews)、
[白霜漫舞](https://poedb.tw/cn/Dance_in_the_White)、
[灰风呼号](https://poedb.tw/cn/The_Grey_Wind_Howls)。
核对日期为 2026-11-13；这里只引用名称，不导入网页上的玩法数据。

## 验证范围

- `test_crafting_dropdowns.py`：从本地 Mod 数据读取 8,135 条具有 Prefix/Suffix 类型的词缀，
  构造实际显示标签并验证完整翻译、带名称包装、数值集合、颜色前缀、英文回切、
  数据表不变、未知文本回退和新增译文字形。`crafting-dropdown-audit.json` 记录逐来源数量，
  此范围内属性正文残留英文为 0。此计数不等于所有界面、所有历史物品或全部词缀名称覆盖率。
- `test_crafting_runtime.py --workspace <独立副本>`：真实 Onyx Amulet 编辑弹窗的 24 条可用隐匿词缀全部显示中文；
  选中并添加截图中的魔力回复词缀，验证解析收到原始英文行，中文→英文→中文切换后
  物品原文、构筑 XML 和计算数值不变。用户构筑与设置不参与测试。
- `test_locale.py`：11,472 条上下文译文及 176 个面板标签、实际差异格式、数值、颜色、回退、编辑隔离和语法。
- `test_unique_locale.py`、`test_interface_ui.py`：暗金属性与 126 条界面消息专项检查。
- `test_layout.py`：4,214 组标签/宽度、8 个页面、2 种分辨率及数值与保存不变。
- 原生窗口首次抽查：独立副本中实际展开同一隐匿下拉框，检查范围、前后缀和多属性行，
  已确认截图对应的中英混排消失。最终候选另通过下列独立 HEAD 专项及实际弹窗 Lua 验证。

核心词缀专项还使用 HEAD 中的已提交词典、字形和模板与本次独立代码组合验证，
确保没有依赖共享工作区中其他尚未提交的翻译修改。
