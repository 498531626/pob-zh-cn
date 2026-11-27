# v2.69.0 专用名称编年史核对（2026-11-27）

本轮按用户要求执行“先去流亡编年史查找并对比，找不到对应中文名称后再直译”。这适用于本轮新增名称；没有把可成功请求页面、同名页面或搜索结果本身当作已核对证据。

## 结果与输入

| 范围 | 核对结果 | 生成输入 |
| --- | --- | --- |
| 原有参考未覆盖的灵体英文名称 | 247 / 247 在线配对成功；本批没有保留直译 | `tools/localization/spectre-reference-reviewed.json` |
| 新增损坏灌注辅助宝石 | 上游实际新增 12 个，全部按同一 `_Support` 页面英文和中文宝石卡片配对 | `tools/localization/upstream-2690-gem-names.json` |
| 已有遗漏宝石名称 Fireball of Radiation | 英文卡片与中文卡片对应“辐射之火球”；与 12 个新增宝石一起记录，共 13 项 | 同上 |
| 灵体技能友好显示名称 | 177 项逐项检索；175 项在本轮查询范围内未找到与本地技能对应的中文友好标题，采用已注明的直译；另外 2 项沿用同名术语的语义参考，不宣称同 ID 配对 | `tools/localization/spectre-skill-names.json` |

灵体源代码有重复 ID 赋值，不能把源代码赋值次数当成实际可用灵体数量。整库的实际运行时 ID 数量与筛选、排序、保存验证由主更新记录报告；这里的 247 是旧名称参考未覆盖的独立英文名称数量。

## 配对方法

灵体名称先复用当前 3.30 的已有双语参考；未覆盖名称逐一读取同一 slug 的 `/us/`、`/cn/` 页面。对比页面 `data-category="MonsterVarieties"` 的 `data-tabname` 中共同的怪物变体 ID，并在有当前本地 ID 时优先选择该变体。这个方法同时覆盖多变体标签页及没有 `tab-pane` 的单怪物页面。中文名称取怪物卡片名称，不能误取页面中的技能标题、同名物品或另一怪物变体。

宝石核对要求英文宝石卡片名称等于本地名称（允许正式的 ` Support` 后缀），并且对应中文卡片名称唯一。Fireball of Radiation 的页面有多个卡片，但中英文各自的名称集合均只有一个值，译名一致。

灵体技能先按本地技能 ID 找到实际拥有该技能的怪物；对比中英文页面同变体的技能卡片，核对 ID、卡片结构和数字序列，再查 PoB 友好显示名称的专页。编年史很多怪物技能卡片的中英文标题都保留内部 ID，例如 `IncaMinionProjectile`，没有对应 PoB 友好名称的中文标题。这类条目使用 `literal-translation-after-reference-search`，不冒称编年史官方译名。包含已有正式技能名称的组合沿用已配对基础术语，例如“灼热光线图腾”沿用 Scorching Ray 的“灼热光线”。

175 个直译技能名称的参考状态分别为：171 项参考卡片保留内部技能 ID、1 项拥有者页面没有可配对的友好技能标题、2 项仅留在技能源码中且无当前可选灵体拥有者（Hammer Smoke、Stab），以及 Bone Mortar 的同名页面实际对应另一技能变体。各项都保存实际查询过的名称页 URL 和请求结果。这里的“未找到”只说明本轮直接名称页和相关怪物技能卡片没有提供可配对中文标题，不表示编年史整站绝对不存在任何相关译文。

## 核对中纠正的示例

| 英文 | 本轮采用的编年史名称 | 证据 |
| --- | --- | --- |
| Spectral Leader | 怨灵兵长 | [英文](https://poedb.tw/us/Spectral_Leader)、[中文](https://poedb.tw/cn/Spectral_Leader)，`WarHeroCasterAtlasUber` |
| Vaal Construct | 瓦尔创造物 | [英文](https://poedb.tw/us/Vaal_Construct)、[中文](https://poedb.tw/cn/Vaal_Construct)，`FragmentPoisonCloud` |
| Auto-Enforcer | 自动执行者 | [英文](https://poedb.tw/us/Auto-Enforcer)、[中文](https://poedb.tw/cn/Auto-Enforcer)，`RobotAutomatonEliteSpectre` |
| Charged Colossus（本地键尾随空格） | 充能巨羊魔 | [英文](https://poedb.tw/us/Charged_Colossus_)、[中文](https://poedb.tw/cn/Charged_Colossus_)，`MountainGoatmanChampionAtlasUber` |
| Necrotic Bones（本地键尾随空格） | 死灵之骸 | [英文](https://poedb.tw/us/Necrotic_Bones_)、[中文](https://poedb.tw/cn/Necrotic_Bones_)，`SkeletonCannon1AtlasUber` |
| Tentacle Miscreation | 古灵实验者:扫荡者 | [英文](https://poedb.tw/us/Tentacle_Miscreation)、[中文](https://poedb.tw/cn/Tentacle_Miscreation)，按本地 `DemonFemaleRanged` 变体选择，避免另一变体全角冒号混入 |
| Bone Mortar | 骸骨迫击炮（直译；同名参考技能为白岩炮塔） | [英文](https://poedb.tw/us/Bone_Mortar)、[中文](https://poedb.tw/cn/Bone_Mortar)，同名页对应 breach_bone_mortar，非本地 SkeletonCannonBoneMortar |
| Doom Arrow | 厄运箭矢（同名术语参考） | [英文](https://poedb.tw/us/Doom_Arrow)、[中文](https://poedb.tw/cn/Doom_Arrow)，参考为 doom_arrow，非本地 AzmeriHydraDoomArrow |
| Encumbrance Support | 负重（辅） | [英文](https://poedb.tw/us/Encumbrance_Support)、[中文](https://poedb.tw/cn/Encumbrance_Support) |
| Impotence Support | 无能（辅） | [英文](https://poedb.tw/us/Impotence_Support)、[中文](https://poedb.tw/cn/Impotence_Support) |

两条英文键中的尾随空格属于上游显示数据；只为查询正确页面保留相应 slug 末尾下划线，没有改动官方数据或内部 ID。

还核对了新版六种怪物分类：Beast=野兽、Humanoid=人形、Eldritch=古灵、Construct=构造体、Demon=恶魔、Undead=亡灵。可在缓存的 Consuming Thrall、Conjuror of Rot、Cairn Annihilator 等双语怪物卡片第一属性中复核。

[Pact of Ghorr 中文页](https://poedb.tw/cn/Pact_of_Ghorr)存在同页用语差异：技能说明称“咕尔饥渴”，独立增益卡片及其属性正文称“戈尔之饥”，英文对应同一 Hunger of Ghorr。新版配置说明采用增益卡片标题“戈尔之饥”，不继续使用无来源的“咕尔之饥”。这记录的是编年史同页差异，没有声称参考自身用词完全一致。

## 快照与验证边界

本轮专名查询记录位于 `tools/localization/upstream-2690-reference/requests.json`，保存 1,028 个语言 URL 的结果，其中 670 个成功响应已存为 gzip 快照并记录解压后 SHA-256，358 个查询返回 HTTP 404。这里没有把网络超时或连接失败归类为“没有译名”；本批最终请求结果没有网络不可达项。直接名称页 404 后，仍通过同 ID 怪物技能卡片继续核对；两个尾随空格的灵体查询也在改用正确 slug 后配对成功。

名称输入的所有元数据标明实际英文/中文 URL、检索日期及匹配 ID；技能直译另有查询结果和原因。已检查 JSON 可读取、247 个灵体输入全部为配对状态、13 个宝石输入全部为配对状态、177 个技能输入覆盖本轮未覆盖名称、技能名称中的数字（如 20 Fuses、Mortar 2）保持不变。最终 Lua 生成、字形、运行时显示及保存验证由主代理在统一生成后完成，本报告不将参考核对当成完整界面验收。

地点名称参考由主代理单独处理，见其 `spectre-area-reviewed.json`、`area-reference/` 及主更新记录；此处不重复计入 247 个灵体名称。

## 同名技能复核修正

Bone Mortar、Doom Arrow、Mortar 的友好名称页面均为 ActiveSkills 技能卡片，但没有本地灵体技能 ID，不能将同名卡片当成同 ID 核对。此前沿用拥有者页面 matched_ids 的标注已移除。Bone Mortar 参考卡片是 breach_bone_mortar（施放 1.00 秒、冷却 10 秒、额外 12 投射物），本地为 SkeletonCannonBoneMortar（施放 1.5 秒、冷却 4 秒、额外 1 投射物）；因此本地使用直译“骸骨迫击炮”，不套用另一技能的“白岩炮塔”。Doom Arrow 的 doom_arrow 参考有 5 箭及狂怒球条款，而本地 AzmeriHydraDoomArrow 为 10 箭及物理转冰霜；Mortar 参考为 mortar_with_ground_effects，本地多个同名技能行为不同。这两项仅将“厄运箭矢”“迫击炮”作为同名术语语义参考，分别保存参考技能代码与本地技能 ID，不作为同 ID 已核对译文计数。最终统计为 175 项检索后直译、2 项同名语义参考、0 项新增同 ID 中文友好标题配对。
