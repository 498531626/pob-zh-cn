-- Display-only localisation: game IDs, parser input and saved builds stay English.
local L = { mode = "zh", suspended = 0 }
L.credit = "简体中文汉化：拽弑"
local dictionary = LoadModule("Localization/Dictionary")
local passiveContexts = LoadModule("Localization/PassiveContexts")
local anointNames = LoadModule("Localization/AnointNames")
local panelLabels = LoadModule("Localization/PanelLabels")
local skillTemplates = LoadModule("Localization/SkillTemplates")
local itemTemplates = LoadModule("Localization/ItemTemplates")
local craftingTemplates = LoadModule("Localization/CraftingTemplates")
local itemDisplayTerms = LoadModule("Localization/ItemDisplayTerms")
local itemTemplateIndex = {}
for _, template in ipairs(itemTemplates) do
	local key = template.en:match("%a+") or ""
	itemTemplateIndex[key] = itemTemplateIndex[key] or {}
	table.insert(itemTemplateIndex[key], template)
end
local displayTemplates = LoadModule("Localization/DisplayTemplates")
local displayTerms = LoadModule("Localization/DisplayTerms")
local calcLabels = LoadModule("Localization/CalcLabels")
local calcIdentifiers = LoadModule("Localization/CalcIdentifiers")
local calcIdentifierTerms = LoadModule("Localization/CalcIdentifierTerms")
local numericFields = {}
for _, labels in ipairs({calcLabels, panelLabels}) do
	for _, label in ipairs(labels) do numericFields[label:gsub(":$", "")] = true end
end
local glyphs = LoadModule("Localization/Glyphs")
local rawDraw, rawWidth, rawCursor, rawColor = DrawString, DrawStringWidth, DrawStringCursorIndex, SetDrawColor
local rawViewport = SetViewport
local textViewport
local currentColor = {1, 1, 1, 1}
local cache = {}
local itemNames = {}
local timelessLabels = {}
local passiveNames = {}
local function passiveNameChinese(name)
	if passiveNames[name] ~= nil then return passiveNames[name] or nil end
	local translated
	for _, context in pairs(passiveContexts) do
		if context[name] then
			if translated and translated ~= context[name] then
				passiveNames[name] = false
				return nil
			end
			translated = context[name]
		end
	end
	passiveNames[name] = translated or false
	return translated
end

-- The node dropdown combines a name and up to two independent stat lines.
-- Register exact source labels so numbers, IDs and saved search rows stay intact.
function L:RegisterTimelessNodes(nodes)
	for _, node in pairs(nodes) do
		if node["not"] and node.sd and node.sd[1] then
			local label = node.dn .. string.rep(" ", 48) .. node.sd[1]
			if node.sd[2] then label = label .. " " .. node.sd[2] end
			timelessLabels[label] = {node.dn, node.sd[1], node.sd[2]}
		end
	end
	cache = {}
end
local atlas
local passiveMultiline = {}
for id, context in pairs(passiveContexts) do
	local groups = {}
	for text in pairs(context) do
		if text:find("\n", 1, true) then
			local lines = {}
			for line in (text .. "\n"):gmatch("(.-)\n") do lines[#lines+1] = line end
			groups[#groups+1] = {text=text, lines=lines}
		end
	end
	table.sort(groups, function(a,b) return #a.lines > #b.lines end)
	passiveMultiline[id] = groups
end
local settingPath = GetScriptPath() .. "/Localization/language.cfg"
local file = io.open(settingPath, "r")
if file then
	local mode = file:read("*l")
	file:close()
	if mode == "en" or mode == "zh" then L.mode = mode end
end

function L:EffectiveMode()
	return self.mode
end

-- Tree recipes use image IDs (AmberOil), while the dictionary uses item names.
-- Resolve only the displayed label; recipe IDs must remain unchanged.
function L:RecipeName(recipeName)
	local short = recipeName:match("^(.+)Oil$")
	if not short then return recipeName end
	local name = short .. " Oil"
	if self:EffectiveMode() ~= "en" and dictionary[name] then
		return self:Translate(name)
	end
	return short
end

function L:Cycle()
	self.mode = ({ en = "zh", zh = "en" })[self.mode]
	local output = io.open(settingPath, "w")
	if output then output:write(self.mode, "\n"); output:close() end
end

-- The tree parser splits one stat into several sd lines. Rejoin only exact
-- source sequences already verified in this node's translation context.
function L:PassiveLineGroups(nodeId, lines)
	local result, index = {}, 1
	local candidates = self:EffectiveMode() ~= "en" and passiveMultiline[tostring(nodeId)] or {}
	while index <= #lines do
		local matched
		for _, candidate in ipairs(candidates or {}) do
			local same = true
			for offset, line in ipairs(candidate.lines) do
				if lines[index+offset-1] ~= line then same=false;break end
			end
			if same then matched=candidate;break end
		end
		local last = matched and index+#matched.lines-1 or index
		result[#result+1] = {first=index,last=last,text=matched and matched.text or lines[index]}
		index = last+1
	end
	return result
end

-- Only recognise the display formats emitted by CompareStatList. Retain the
-- exact numeric text, separators, signs, units, percentages and colour codes.
local gemFields = {
	["Level"]=true, ["Cost & Reservation Multiplier"]=true, ["Reservation Override"]=true,
	["Reservation"]=true, ["Cost"]=true, ["Cooldown Time"]=true, ["Soul Gain Prevention"]=true,
	["Attack Speed"]=true, ["Attack Time"]=true, ["Attack Damage"]=true, ["Cast Time"]=true,
	["Critical Strike Chance"]=true, ["Effectiveness of Added Damage"]=true, ["Quality"]=true,
}
local function formattedChinese(body)
	for _, template in ipairs(displayTemplates) do
		local values = {body:match(template.pattern)}
		if #values == #template.kinds then
			local valid = true
			for i, value in ipairs(values) do
				local translated = displayTerms[value] or dictionary[value]
				if template.kinds[i] == "text" then -- UI names and error payloads stay verbatim.
				elseif template.kinds[i] == "term" and translated ~= nil then values[i] = translated
				elseif value ~= "" and value:gsub("[%d%s%+%-%.,%%]", "") ~= "" then valid = false; break end
			end
			if valid then return (template.zh:gsub("{(%d+)}", function(i) return values[tonumber(i)+1] end)) end
		end
	end
end
-- These UI messages append user-controlled names, paths or status text. Keep
-- that payload intact unless it has a reviewed exact translation of its own.
local function interfaceChinese(body, nodeId)
	local parts = timelessLabels[body]
	if parts then
		return L:Translate(parts[1], nil, "zh") .. string.rep(" ", 48)
			.. L:Translate(parts[2], nil, "zh")
			.. (parts[3] and " " .. L:Translate(parts[3], nil, "zh") or "")
	end
	local context = nodeId and passiveContexts[tostring(nodeId)]
	local function nameChinese(value)
		local base, seed = value:match("^(.-)( %d+)$")
		return (context and context[value]) or anointNames[value] or dictionary[value]
			or (base and dictionary[base] and dictionary[base] .. seed) or value
	end
	local class, startingClass = body:match("^Changing class to (.-) will reset your passive tree%.\nThis can be avoided by connecting one of the (.-) starting nodes to your tree%.$")
	if class then return "切换为" .. nameChinese(class) .. "将重置天赋树。\n将一个" .. nameChinese(startingClass) .. "起始天赋连接到当前天赋树，可避免重置。" end
	local required, act, quests, extra, lab = body:match("^Required Level: (%d+)\nEstimated Progress:\nAct: ([^\n]+)\nQuestpoints: (%d+)\nExtra Skillpoints: (%d+)(.*)$")
	if required then return "需求等级：" .. required .. "\n预计进度：\n章节：" .. nameChinese(act) .. "\n任务天赋点：" .. quests .. "\n额外天赋点：" .. extra .. L:Translate(lab, nil, "zh") end
	local attribute, requiredItem = body:match("^You do not meet the (%a+) requirement of (.+)$")
	if attribute and dictionary[attribute] then return "未满足“" .. nameChinese(requiredItem) .. "”的" .. dictionary[attribute] .. "需求" end
	local node = body:match("^This option is specific to '(.-)'%.$")
	if node then return "此选项仅适用于“" .. nameChinese(node) .. "”。" end
	local off, def = body:match("^When enabled, an estimate of the offensive and defensive strength of\neach unallocated passive is calculated and displayed visually%.\nOffensive power shows as (%a+), defensive power as (%a+)%.$")
	local colors = {red="红色", green="绿色", blue="蓝色", yellow="黄色", purple="紫色", orange="橙色", cyan="青色"}
	if colors[off] and colors[def] then return "启用后，将估算每个未分配天赋的进攻与防御强度，\n并以颜色显示。\n进攻强度显示为" .. colors[off] .. "，防御强度显示为" .. colors[def] .. "。" end
	local characterClass, level, league = body:match("^(.-) lvl (%d+) in (.+)$")
	if characterClass then return nameChinese(characterClass) .. " 等级 " .. level .. "（" .. nameChinese(league) .. "）" end
	characterClass, level = body:match("^(.-) lvl (%d+)$")
	if characterClass then return nameChinese(characterClass) .. " 等级 " .. level end
	local slot, socket = body:match("^(.+) Abyssal Socket (%d+)$")
	if slot then return nameChinese(slot) .. " 深渊插槽 " .. socket end
	local source = body:match("^%+%d+%% Quality from (.+)$")
	if source then return body:match("^(%+%d+%%)") .. " 品质，来自 " .. nameChinese(source) end
	local override = body:match("^Override: (.+)$")
	if override then return "覆盖：" .. nameChinese(override) end
	local enabled = body:match("^Enable (.+)$")
	if enabled and dictionary[enabled] then return "启用 " .. dictionary[enabled] end
	local unsupported = body:match('^"(.-)" not supported%.  Select a specific stat from the dropdown%.$')
	if unsupported then return "不支持“" .. unsupported .. "”。请从下拉框中选择具体属性。" end
	local importError = body:match("^Error importing character data, try again %((.*)%)$")
	if importError then return "导入角色数据失败，请重试（" .. importError .. "）" end
	local listError = body:match("^Error retrieving character list, try again %((.*)%)$")
	if listError then return "获取角色列表失败，请重试（" .. listError .. "）" end
	local mod, tier = body:match("^(.-) %- Tier: (%d+)$")
	if mod then return L:Translate(mod, nil, "zh") .. " — 阶级：" .. tier end
	local groupSkill, provider, removal = body:match("^This is a special group created for the '(.-)' skill,\nwhich is being provided by (.-)%.\nYou cannot delete this group, but it will disappear if you (.-)%.$")
	local removals = {["un-allocate the node"]="取消分配此天赋", ["un-equip the item"]="卸下此物品"}
	if groupSkill and removals[removal] then return "此特殊技能组用于技能“" .. nameChinese(groupSkill) .. "”，\n由 " .. provider .. " 提供。\n无法手动删除此技能组；" .. removals[removal] .. "后，此组会自动消失。" end
	local supportProvider = body:match("^You cannot add support gems to this group, but support gems in\nany other group socketed into (.-)\nwill automatically apply to the skill%.$")
	if supportProvider then return "无法直接向此组添加辅助宝石，但插入 " .. supportProvider .. " 中的\n其他技能组的辅助宝石会自动作用于此技能。" end
	local prefixes = {
		["Convert to "]="转换为 ", ["Character import status: "]="角色导入状态：",
		["Current Path: "]="当前路径：", ["User settings path cannot be loaded: "]="无法加载用户设置路径：",
		["Path of Building Community Fork v"]="PoB 社区版 v", ["Sorted by "]="排序依据：",
		["Whisper for "]="发送交易私聊：", ["Search for "]="搜索：", ["Sorting "]="正在排序：",
		["Overrides the default save location for builds.\nThe default location is: '"]="覆盖构筑的默认保存位置。\n默认位置为：'",
		["which is being provided by "]="此技能由以下物品或天赋提供：",
		["any other group socketed into "]="对应物品：",
		["Current build: "]="当前构筑：", ["Version: "]="版本：",
		["Price: "]="价格：",
	}
	local rawPayload = {
		["Current build: "]=true, ["Version: "]=true, ["Current Path: "]=true,
		["User settings path cannot be loaded: "]=true, ["Path of Building Community Fork v"]=true,
		["Convert to "]=true, ["Sorting "]=true,
		["Overrides the default save location for builds.\nThe default location is: '"]=true,
	}
	for prefix, chinese in pairs(prefixes) do
		if body:sub(1, #prefix) == prefix then
			local value = body:sub(#prefix+1)
			if prefix == "Character import status: " then return chinese .. L:Translate(value, nil, "zh") end
			if prefix == "Current build: " and value:match("^%s*(.-)%s*$") == "Unnamed build" then value = dictionary["Unnamed build"] end
			return chinese .. (rawPayload[prefix] and value or nameChinese(value))
		end
	end
	local skill = body:match("^This is a special group created for the '(.-)' skill,$")
	if skill then return "此特殊技能组用于技能“" .. (dictionary[skill] or skill) .. "”，" end
	local name = body:match("^(.-) can appear on:$")
	if name then return nameChinese(name) .. "可出现在：" end
	name = body:match("^(.-) was successfully added to your build%.$")
	if name then return nameChinese(name) .. "已成功加入构筑。" end
	name = body:match("^(.-) only:$")
	if name then return "仅 " .. nameChinese(name) .. "：" end
	local variant, count = body:match("^Variant: (.-) %((%d+) variants%)$")
	if variant then return "变体：" .. nameChinese(variant) .. "（" .. count .. " 个变体）" end
	local version = body:match("^Convert will replace all trees that are not Version (.-)%.\nThis action cannot be undone%.%s*$")
	if version then return "转换将替换所有非 " .. version .. " 版本的天赋树。\n此操作无法撤销。\n" end
	local action, target, result = body:match("^(%a+) (.-) (changes nothing.-)%.$")
	if not action then action, target, result = body:match("^(%a+) (.-) (will give you:)%s*$") end
	local actions = {Anointing="涂油分配", Allocating="分配"}
	if actions[action] then
		local reasons = {
			["changes nothing"]="不会产生变化。",
			["changes nothing because this node is already allocated on the tree"]="不会产生变化，因为天赋树上已分配此天赋。",
			["changes nothing because this node is already anointed"]="不会产生变化，因为此天赋已经涂油分配。",
			["will give you:"]="将产生以下变化：",
		}
		if reasons[result] then return actions[action] .. "“" .. nameChinese(target) .. "”" .. reasons[result] end
	end
	local verb, target = body:match("^(%a+) (.+)$")
	local verbs = {Anoint="涂油分配 ", Remove="移除 ", Allocates="分配 "}
	if verbs[verb] and (anointNames[target] or dictionary[target] or (context and context[target])) then return verbs[verb] .. nameChinese(target) end
	local replaced = body:match("^%(replacing (.-)%)$")
	if replaced then return "（替换 " .. L:Translate(replaced, nil, "zh") .. "）" end
	local socket = body:match("^Socket #(%d+)$")
	if socket then return "插槽 #" .. socket end
	-- Timeless socket labels retain their English key and numeric socket ID.
	-- Translate only reviewed names, preserving the allocated-node marker.
	local marker = body:sub(1, 2) == "# " and "# " or ""
	local socketName, socketId = body:sub(#marker + 1):match("^(.+): (%d+)$")
	local socketTranslation = socketName and (passiveNameChinese(socketName) or dictionary[socketName])
	if socketTranslation then
		return marker .. socketTranslation .. ": " .. socketId
	end
	-- UI messages may include Chinese user names; numeric/game grammar remains
	-- constrained by the reviewed template kinds.
	if body:find("[\128-\255]") then return formattedChinese(body) end
end
local function buffChinese(value)
	if dictionary[value] then return dictionary[value] end
	local count, name = value:match("^(%d+) (.+)$")
	if count and dictionary[name] and (name:match(" Charges$") or name == "Ghost Shrouds" or name == "Crab Barriers" or name == "Spirit Infusions") then
		return count .. " " .. dictionary[name]
	end
end

-- These outputs are display lists, not arbitrary comma-containing item names.
-- Keep unknown entries individually so one new buff cannot hide known names.
function L:TranslateCalcList(text)
	if self.suspended > 0 or self:EffectiveMode() == "en" then return text end
	local parts, cursor = {}, 1
	while true do
		local first, last = text:find(", ", cursor, true)
		local part = text:sub(cursor, first and first - 1 or #text)
		parts[#parts + 1] = buffChinese(part) or self:Translate(part)
		if not first then return table.concat(parts, ", ") end
		cursor = last + 1
	end
end

-- Restricted calculator note grammar. Unknown phrases fail as a whole instead
-- of turning arbitrary user text into a mixture of Chinese and English.
local calcPhraseIndex, calcIdentifierKeys
local function calcNoteChinese(body)
	if body:find("\n", 1, true) then return end
	local function canonical(value) return value:lower():gsub("[%s'%-]", "") end
	-- Source-total rows append an identifier after their value. A normal item
	-- sentence such as "20% increased ... for each ..." uses the item templates.
	local numericStat = body:match("^[%+%-]?[%d%.]+ base (.+)$")
		or body:match("^[%d%.]+%% increased (.+)$") or body:match("^[%d%.]+%% reduced (.+)$")
		or body:match("^[%d%.]+%% more (.+)$") or body:match("^[%d%.]+%% less (.+)$")
	if numericStat then
		if not calcIdentifierKeys then
			calcIdentifierKeys = {}; for en in pairs(calcIdentifiers) do calcIdentifierKeys[canonical(en)] = true end
		end
		if not calcIdentifierKeys[canonical(numericStat)] then return end
	end
	local enums = {Calculation=true, EnemyConfig=true, Gem=true, ["Max Level"]=true,
		["Socketed In"]=true, True=true, False=true}
	if not (enums[body] or body:match("^Condition: ") or body:match("^%a+ Condition[: ,]")
		or body:match("^Skill type: ") or body:match("^Skill: ") or body:match("^If ")
		or body:match("^When in slot #") or body:match("^Ignore Cond[, ]")
		or body:match("^Global, ") or body:match("^Buff, ") or body:match("^Debuff, ")
		or body:match("^Ailment, ") or body:match("^Modifier: ")
		or body:match("^Total from ")
		or body:match("^True ") or body:match("^False ")
		or body:match("^[%+%-]?[%d%.]+%%? per ") or body:match("^[%+%-]?[%d%.]+%%? of ")
		or body:match("^[%+%-]?[%d%.]+ base ")
		or body:match("^[%d%.]+%% increased ") or body:match("^[%d%.]+%% reduced ")
		or body:match("^[%d%.]+%% more ") or body:match("^[%d%.]+%% less ")
		or body:match("^[%+%-]?[%d%.]+ %+ [%d%.]+ per ") or body == "+inf base") then return end
	if not calcPhraseIndex then
		calcPhraseIndex = {}
		-- Deterministic priority: reviewed calculator terms override identifiers,
		-- which override general UI/name vocabulary in this note grammar only.
		for _, source in ipairs({dictionary, calcIdentifiers, calcIdentifierTerms}) do
			local keys = {}; for en in pairs(source) do keys[#keys+1] = en end
			table.sort(keys)
			for _, en in ipairs(keys) do
				local zh = source[en]
				if not en:find("[^%w%s'%-]") and not zh:find("%a") and (source ~= dictionary or not en:find("%d")) then
					local key = canonical(en)
					if not calcPhraseIndex[key] or source ~= dictionary then calcPhraseIndex[key] = zh end
				end
			end
		end
	end
	local valid = true
	local translated = body:gsub("[^,:<>=+/#%%{}()%?]+", function(fragment)
		local lead, text, tail = fragment:match("^(%s*)(.-)(%s*)$")
		if text == "" then return fragment end
		local words = {}; for word in text:gmatch("%S+") do words[#words+1] = word end
		local memo = {}
		local function resolve(start)
			if start > #words then return "" end
			if memo[start] ~= nil then return memo[start] or nil end
			for finish = #words, start, -1 do
				local en = table.concat(words, " ", start, finish)
				local zh = calcPhraseIndex[canonical(en)] or (tonumber(en) and en)
				if zh then
					local rest = resolve(finish + 1)
					if rest then memo[start] = zh .. rest; return memo[start] end
				end
			end
			memo[start] = false
		end
		local zh = resolve(1)
		if not zh then valid = false; return fragment end
		return lead .. zh .. tail
	end)
	if valid then return translated end
end

local function dynamicChinese(body)
	-- This flag list otherwise enters the legacy comma/title formatter, which
	-- can translate only its last member and hide the unresolved first flag.
	if body:match("^Ailment, ") then return calcNoteChinese(body) end
	-- Crafting dropdowns append affix metadata to complete numeric stat lines.
	-- Resolve the stat before the generic parenthesis handler can split its rolls.
	local colouredStat, affixColour, colouredType = body:match("^(.-) (%^%d)%((Prefix)%)$")
	if not colouredStat then colouredStat, affixColour, colouredType = body:match("^(.-) (%^%d)%((Suffix)%)$") end
	if not colouredStat then colouredStat, affixColour, colouredType = body:match("^(.-) (%^x%x%x%x%x%x%x)%((Prefix)%)$") end
	if not colouredStat then colouredStat, affixColour, colouredType = body:match("^(.-) (%^x%x%x%x%x%x%x)%((Suffix)%)$") end
	if colouredStat then return L:Translate(colouredStat, nil, "zh") .. " " .. affixColour .. "(" .. dictionary[colouredType] .. ")" end
	local stat, affixType = body:match("^(.-) %((Prefix)%)$")
	if not stat then stat, affixType = body:match("^(.-) %((Suffix)%)$") end
	if stat then return L:Translate(stat, nil, "zh") .. " (" .. dictionary[affixType] .. ")" end
	local affix, stats = body:match("^(.-)   %^8%[(.+)%]$")
	if affix then return L:Translate(affix, nil, "zh") .. "   ^8[" .. L:Translate(stats, nil, "zh") .. "]" end
	local bracketed = body:match("^%[(.+)%]$")
	if bracketed then return "[" .. L:Translate(bracketed, nil, "zh") .. "]" end
	local smallStat = body:match("^Added Small Passive Skills also grant: (.+)$")
	if smallStat then
		local translated = L:Translate(smallStat, nil, "zh")
		if translated ~= smallStat then return "增加的小天赋还获得：" .. translated end
	end
	local interface = interfaceChinese(body)
	if interface then return interface end
	-- Full DPS rows prefix skill labels with their instance count. Translate
	-- the remaining label independently, preserving the count and colour codes.
	local skillCount, skillLabel = body:match("^(%d+x )(.+)$")
	if skillCount then
		local translated = L:Translate(skillLabel, nil, "zh")
		if translated ~= skillLabel then return skillCount .. translated end
	end
	local title, base = body:match("^(.-), (.-)$")
	if dictionary[base] and not title:find(":", 1, true) then return (dictionary[title] or title) .. ", " .. dictionary[base] end
	local equipSlot = body:match("^Equipping this item in (.-) will give you:$")
	if equipSlot and dictionary[equipSlot] then return "在" .. dictionary[equipSlot] .. "装备此物品将产生以下变化：" end
	local removeSlot = body:match("^Removing this item from (.-) will give you:$")
	if removeSlot and dictionary[removeSlot] then return "从" .. dictionary[removeSlot] .. "移除此物品将产生以下变化：" end
	local itemStat, itemStatValue = body:match("^(.-): (.+)$")
	if (itemStat == "Physical Damage" or itemStat == "Elemental Damage" or itemStat == "Chaos Damage" or itemStat == "Sockets") and dictionary[itemStat] then
		return dictionary[itemStat] .. ": " .. itemStatValue:gsub("%f[%a]DPS%f[%A]", "每秒伤害")
	end
	if itemStat == "Weapon Range" and dictionary[itemStat] then
		local plain = itemStatValue:gsub("%^x%x%x%x%x%x%x", ""):gsub("%^%d", "")
		if plain:match("^[%d%.]+ metres$") then return dictionary[itemStat] .. ": " .. itemStatValue:gsub("metres$", "米") end
	end
	if itemStat == "Variant" then
		local variant, count = itemStatValue:match("^(.-) %((%d+) variants%)$")
		return dictionary.Variant .. ": " .. L:Translate(variant or itemStatValue, nil, "zh") .. (count and "（共 " .. count .. " 个版本）" or "")
	end
	if itemStat == "Limited to" or itemStat == "Radius" or itemStat == "Source" or itemStat == "Exclusive to" or itemStat == "Tincture effect modifier" then
		local value = L:Translate(itemStatValue, nil, "zh")
		if itemStat == "Exclusive to" then
			local values={}
			for league in itemStatValue:gmatch("[^,]+")do
				local name=league:match("^%s*(.-)%s*$");values[#values+1]=itemDisplayTerms[name] or dictionary[name] or name
			end
			value=table.concat(values, "、")
		end
		return (dictionary[itemStat] or itemStat) .. ": " .. value
	end
	local average, minimum = body:match("^Flask uptime: ([%d%.]+%%) average, ([%d%.]+%%) minimum$")
	if average then return "药剂覆盖率：平均 " .. average .. "，最低 " .. minimum end
	local foulborn = body:match("^Foulborn (.+)$")
	if foulborn then
		local translated = L:Translate(foulborn, nil, "zh")
		if translated ~= foulborn then return dictionary.Foulborn .. " " .. translated end
	end
	local itemField, itemValue = body:match("^(Affix): (.+)$")
	if not itemField then itemField, itemValue = body:match("^(Tags): (.+)$") end
	if itemField == "Affix" then
		local tier, affix = itemValue:match("^Tier (%d+) %((.+)%)$")
		if tier then return dictionary.Affix .. ": " .. tier .. " 阶（" .. L:Translate(affix, nil, "zh") .. "）" end
		return dictionary.Affix .. ": " .. L:Translate(itemValue, nil, "zh")
	elseif itemField == "Tags" then
		local tags = {attack="攻击", caster="施法", life="生命", mana="魔力", resource="资源",
			defences="防御", defence="防御", armour="护甲", evasion="闪避", energy_shield="能量护盾",
			critical="暴击", speed="速度", physical_damage="物理伤害", physical="物理", fire="火焰",
			cold="冰霜", lightning="闪电", chaos="混沌", damage="伤害", elemental_damage="元素伤害",
			elemental="元素", attribute="属性", resistance="抗性", ailment="异常状态", gem="技能石",
			minion="召唤生物", curse="诅咒", aura="光环", block="格挡", flask="药剂", poison="中毒",
			bleed="流血", bleeding="流血", dot="持续伤害"}
		return dictionary.Tags .. ": " .. itemValue:gsub("[%a_]+", function(tag) return tags[tag] or tag end)
	end
	local itemCount = body:match("^(%d+) Tiers$")
	if itemCount then return itemCount .. " 个档位" end
	local fromLevel, toLevel = body:match("^Level: (%d+) to (%d+)$")
	if fromLevel then return dictionary.Level .. ": " .. fromLevel .. " 至 " .. toLevel end
	local retained = body:match("^%[Retained%] (.+)$")
	if retained then return "[保留] " .. L:Translate(retained, nil, "zh") end
	if body:find("/", 1, true) then
		local parts, valid = {}, true
		for part in body:gmatch("[^/]+") do
			local translated = L:Translate(part, nil, "zh")
			if translated == part then valid=false;break end
			parts[#parts+1] = translated
		end
		if valid and #parts > 1 then return table.concat(parts, "/") end
		local joined = body:gsub("/", "\n")
		local translated = L:Translate(joined, nil, "zh")
		if translated ~= joined and not translated:find("%a") then return translated:gsub("\n", "/") end
	end
	-- Calcs emits comma-separated buff names and counted charge labels. Only
	-- translate complete known entries; never split numeric thousands commas.
	local buff = buffChinese(body)
	if buff then return buff end
	-- Spectre sources combine a skill with a monster name in breakdown tables.
	local sourceSkill, sourceMinion = body:match("^(.+) %- (.+)$")
	if dictionary[sourceSkill] and dictionary[sourceMinion] then
		return dictionary[sourceSkill] .. " - " .. dictionary[sourceMinion]
	end
	if body:find(", ", 1, true) then
		local parts, cursor = {}, 1
		while true do
			local first, last = body:find(", ", cursor, true)
			local part = body:sub(cursor, first and first-1 or #body)
			local translated = buffChinese(part)
			if not translated then break end
			parts[#parts+1] = translated
			if not first then return table.concat(parts, ", ") end
			cursor = last+1
		end
	end
	local number = body:match("^([%d%,%.]+) DPS$")
	if number then return number .. " 每秒伤害" end
	local mathPrefix, low, high = body:match("^([=%+%*/x%s%-]*)([%+%-]?[%d%,%.]+) to ([%+%-]?[%d%,%.]+)$")
	if low then return mathPrefix .. low .. " 至 " .. high end
	number = body:match("^(%d+) [Ww]arnings?$")
	if number then return number .. " 条警告" end
	local namedField, value = body:match("^(Current build):%s*(.+)$")
	if not namedField then namedField, value = body:match("^(Version):%s*(.+)$") end
	if namedField then return dictionary[namedField] .. ": " .. value end
	number = body:match("^Level:%s*(%d+)$")
	if number then return dictionary.Level .. ": " .. number end
	local sort = body:match("^Sort by (.+)$")
	if sort and dictionary[sort] then return "按" .. dictionary[sort] .. "排序" end
	local minion = body:match("^Sort by Minion (.+)$")
	if minion and dictionary[minion] then return "按召唤生物" .. dictionary[minion] .. "排序" end
	local version, variant = body:match("^(%d+%.%d+) %((.-)%)$")
	local variants = {ruthless="残暴模式", alternate="替代版本", ["ruthless alternate"]="残暴模式替代版本"}
	if variants[variant] then return version .. "（" .. variants[variant] .. "）" end
	local field, tail = body:match("^(.-):%s*(.+)$")
	local plainField = field and field:gsub("%^x%x%x%x%x%x%x", ""):gsub("%^%d", "")
	if numericFields[plainField] and dictionary[plainField] and not gemFields[plainField] then
		local codes = field:match("(%^x%x%x%x%x%x%x)$") or field:match("(%^%d)$") or ""
		-- Section headers concatenate their live value after the label. Only
		-- known calculation/sidebar fields enter this path; values stay intact.
		return dictionary[plainField] .. codes .. ": " .. tail:gsub("%f[%a]DPS%f[%A]", "每秒伤害")
	end
	local index = body:match("^Active Skill #(%d+):$")
	if index then return "主动技能 #" .. index .. "：" end
	index = body:match("^Active Skill #(%d+)'s Main Minion Skill:$")
	if index then return "主动技能 #" .. index .. " 的召唤生物主技能：" end
	local gemName, gemNumbers = body:match("^(.-)( %^7%d.*)$")
	if gemName and dictionary[gemName] then
		local plain = gemNumbers:gsub("%^x%x%x%x%x%x%x", ""):gsub("%^%d", "")
		if plain:match("^ %d[%d%+%/]*$") then return dictionary[gemName] .. gemNumbers end
	end
	field, tail = body:match("^(.-): (.+)$")
	if gemFields[field] then
		tail = tail:gsub("([%d%,%.]+) to ([%d%,%.]+)", "%1 至 %2")
		tail = tail:gsub("Instant", dictionary.Instant):gsub("of base", dictionary["of base"])
			:gsub("%f[%a]sec%f[%A]", dictionary.sec):gsub("%f[%a]uses%f[%A]", dictionary.uses)
			:gsub("%f[%a]Mana%f[%A]", dictionary.Mana):gsub("%f[%a]Life%f[%A]", dictionary.Life)
			:gsub("%f[%a]Rage%f[%A]", dictionary.Rage):gsub("%(Max%)", dictionary["(Max)"])
		return dictionary[field] .. ": " .. tail
	end
	if body:match("^Requires ") then
		local plain = body:gsub("%^x%x%x%x%x%x%x", ""):gsub("%^%d", "")
		local check = plain:gsub("^Requires ", ""):gsub("Level ", ""):gsub("Str", "")
			:gsub("Dex", ""):gsub("Int", ""):gsub("Omni", ""):gsub("[%d%s,]", "")
		if check == "" then
			return body:gsub("^Requires ", dictionary.Requires .. " "):gsub("Level ", dictionary.Level .. " ")
				:gsub("Str", dictionary.Strength):gsub("Dex", dictionary.Dexterity):gsub("Int", dictionary.Intelligence)
				:gsub("Omni", dictionary.Omni)
		end
	end
	local quality, source = body:match("^(%+%d+%%) Quality from (.+)$")
	if quality and dictionary["Quality from " .. source] then return quality .. " " .. dictionary["Quality from " .. source] end
	for _, template in ipairs(skillTemplates) do
		local values = {body:match(template.pattern)}
		if #values == template.values then
			local valid = true
			for _, value in ipairs(values) do
				if not value:match("^[%+%-]?%d+%.?%d*$") and not value:match("^[%+%-]?%(%-?%d+%.?%d*%-%-?%d+%.?%d*%)$") then valid = false; break end
			end
			if valid then return (template.zh:gsub("{(%d+)}", function(i) return values[tonumber(i) + 1] end)) end
		end
	end
	for _, template in ipairs(itemTemplateIndex[body:match("%a+") or ""] or {}) do
		local values = {body:match(template.pattern)}
		if #values == template.values then
			local valid = true
			for _, value in ipairs(values) do
				if not value:match("^[%+%-]?%d+%.?%d*$") and not value:match("^[%+%-]?%(%-?%d+%.?%d*%-%-?%d+%.?%d*%)$") and not value:match("^[%+%-]?#$") then valid=false;break end
			end
			if valid then return (template.zh:gsub("{(%d+)}", function(i) return values[tonumber(i)+1] end)) end
		end
	end
	for _, template in ipairs(craftingTemplates) do
		local values = {body:match(template.pattern)}
		if template.values == 0 and body == template.en then return template.zh end
		if template.values > 0 and #values == template.values then
			local valid = true
			for _, value in ipairs(values) do
				if not value:match("^[%+%-]?%d+%.?%d*$") and not value:match("^[%+%-]?%(%-?%d+%.?%d*%-%-?%d+%.?%d*%)$") then valid=false;break end
			end
			if valid then return (template.zh:gsub("{(%d+)}", function(i) return values[tonumber(i)+1] end)) end
		end
	end
	-- Calculation breakdowns retain their formula and values. Only complete,
	-- reviewed annotations are replaced; an unknown annotation stays original.
	-- Prefer a complete reviewed format over annotations such as "(1 uses)".
	-- Let Translate strip inline colours before applying the complete format.
	local plain = body:gsub("%^x%x%x%x%x%x%x", ""):gsub("%^%d", "")
	local formatted = formattedChinese(plain)
	if formatted then return plain == body and formatted or nil end
	local formulaChanged = false
	local renderedParts = {}
	body:gsub("%b()", function(part)
		local function replace(value)
			formulaChanged = true; renderedParts[part] = value; return value
		end
		if dictionary[part] then return replace(dictionary[part]) end
		local inner = part:sub(2, -2)
		local note = dictionary[inner] or formattedChinese(inner)
		if not note then
			local translated = L:Translate(inner, nil, "zh")
			if translated ~= inner then note = translated end
		end
		if note then return replace("(" .. note .. ")") end
		return part
	end)
	if formulaChanged then
		local pieces, cursor = {}, 1
		while true do
			local first, last = body:find("%b()", cursor)
			if not first then break end
			pieces[#pieces+1] = L:Translate(body:sub(cursor, first-1), nil, "zh")
			local part = body:sub(first, last)
			pieces[#pieces+1] = renderedParts[part] or part
			cursor = last+1
		end
		pieces[#pieces+1] = L:Translate(body:sub(cursor), nil, "zh")
		return (table.concat(pieces):gsub("([%d%,%.]+) to ([%d%,%.]+)", "%1 至 %2"))
	end
	local math, suffix = body:match("^(.-%s)([%a][%a%s/]+)$")
	if math and math:find("%d") and math:gsub("[%d%s%+%-%*/x=%,%.%%%(%):]", "") == "" and dictionary[suffix] then
		return math .. dictionary[suffix]
	end
	if body:match("^[%+%-]") then
		for _, label in ipairs(panelLabels) do
			local first, last = body:find(" " .. label, 1, true)
			if first then
				local value, tail = body:sub(1, first - 1), body:sub(last + 1)
				if value:find("%d") and value:gsub("[%d%+%-%.,%%'%s]", ""):gsub("s", "") == ""
					and (tail == "" or tail:match("^ %(") or tail:match("^ %^8%[")) then
					return value .. " " .. dictionary[label] .. tail:gsub("per point", dictionary["per point"])
				end
			end
		end
	end
	local count, tail = body:match("^(%d+) points to node(.*)$")
	if count then
		return count .. " " .. dictionary["points to node"] .. tail:gsub("%(Can be allocated without pathing to it%)", dictionary["(Can be allocated without pathing to it)"])
	end
	count = body:match("^(%d+) nodes in trace path$")
	if count then return count .. " " .. dictionary["nodes in trace path"] end
	local value, code, suffix = body:match("^(.-)(%^x%x%x%x%x%x%x) %((%a+)%)$")
	if value and (suffix == "Guard" or suffix == "Immune") and value:find("%d") then
		return value .. code .. " (" .. dictionary[suffix] .. ")"
	end
	return calcNoteChinese(body)
end

function L:Translate(text, nodeId, displayMode)
	if type(text) ~= "string" or self.suspended > 0 or self:EffectiveMode() == "en" then return text end
	local mode = displayMode or self:EffectiveMode()
	local key = mode .. "\0" .. tostring(nodeId or "") .. "\0" .. text
	if cache[key] then return cache[key] end
	-- Colour prefixes can contain any mix of numeric and hex escape codes.
	local prefix, body = "", text
	while true do
		local code = body:match("^%^x%x%x%x%x%x%x") or body:match("^%^%d")
		if not code then break end
		prefix, body = prefix .. code, body:sub(#code + 1)
	end
	if body:sub(1,3) == "<- " or body:sub(1,3) == "-> " then
		prefix, body = prefix .. body:sub(1,3), body:sub(4)
	end
	local leading, rest = body:match("^(%s+)(.+)$")
	if leading then
		local translated = self:Translate(prefix .. rest, nodeId, displayMode)
		if translated ~= prefix .. rest then return prefix .. leading .. translated:sub(#prefix+1) end
	end
	local core, whitespace = body:match("^(.-)(%s+)$")
	if core and core ~= "" then
		local translated = self:Translate(prefix .. core, nodeId, displayMode)
		if translated ~= prefix .. core then return translated .. whitespace end
	end
	-- This suffix is added after unsupported passive/gem stats are formatted.
	-- Resolve the original line with its node context, preserving its red colour.
	local unsupported = " ^8(Not supported in PoB yet)"
	if body:sub(-#unsupported) == unsupported then
		return self:Translate(prefix .. body:sub(1, -#unsupported - 1), nodeId, displayMode)
			.. " ^8" .. self:Translate("(Not supported in PoB yet)", nil, displayMode)
	end
	local trailing = body:match("(%^x%x%x%x%x%x%x:)$") or body:match("(%^%d:)$")
		or body:match(":$") or (body:sub(-3) == "：" and "：") or ""
	local name = trailing ~= "" and body:sub(1, -#trailing - 1) or body
	local context = nodeId and passiveContexts[tostring(nodeId)]
	local direct = context and context[body] or dictionary[body] or calcIdentifiers[body] or itemNames[body]
	local zh = direct or (context and context[name]) or dictionary[name] or calcIdentifiers[name]
	-- Strip inline colours before matching a complete message. Otherwise a
	-- partial dynamic clause can prevent the remaining lines from translating.
	local dynamic = not zh and not (body:find("^", 1, true) and body:find("\n", 1, true))
		and (interfaceChinese(body, nodeId) or (not body:find("[\128-\255]") and dynamicChinese(body)))
	local result = text
	if direct then
		result = prefix .. zh
	elseif zh then
		result = prefix .. zh .. trailing
	elseif dynamic then
		result = prefix .. dynamic
	elseif body:find("^", 1, true) then
		local plain = body:gsub("%^x%x%x%x%x%x%x", ""):gsub("%^%d", "")
		if plain ~= body then
			local translated = self:Translate(plain, nodeId, "zh")
			if translated ~= plain then
				-- Inline colour codes split otherwise exact sentences. Restore
				-- highlights on known terms after translating the complete text.
				local start = 1
				while start <= #body do
					local first = body:find("^", start, true)
					if not first then break end
					local code = body:sub(first):match("^%^x%x%x%x%x%x%x") or body:sub(first):match("^%^%d")
					if code then
						local nextCode = body:find("^", first + #code, true) or (#body + 1)
						local term = body:sub(first + #code, nextCode - 1):match("^%s*(.-)%s*$")
						local zhTerm = dictionary[term]
						if code ~= "^7" and zhTerm then
							local left, right = translated:find(zhTerm, 1, true)
							if left then translated = translated:sub(1,left-1)..code..zhTerm.."^7"..translated:sub(right+1) end
						end
						start = nextCode
					else start = first + 1 end
				end
				result = prefix .. translated
			end
		end
	end
	if result == text and body:find("\n", 1, true) then
		local lines = {}
		for line in (body .. "\n"):gmatch("(.-)\n") do
			lines[#lines + 1] = self:Translate(prefix .. line, nodeId, displayMode)
		end
		result = table.concat(lines, "\n")
	end
	-- Bound memory when tooltips or character data contain many unique strings.
	if self.cacheSize == nil or self.cacheSize > 12000 then cache = {}; self.cacheSize = 0 end
	cache[key] = result
	self.cacheSize = self.cacheSize + 1
	return result
end

-- Skill-part labels can share English names with item bases or affixes.
local skillPartNames = LoadModule("Localization/SkillPartNames")
function L:TranslateSkillPart(text, mode)
	if self.suspended > 0 or (mode or self:EffectiveMode()) == "en" then return text end
	if skillPartNames[text] then return skillPartNames[text] end
	return self:Translate(text, nil, mode)
end

-- UI labels and detail tooltips follow the same selected language.
function L:TranslateUI(text)
	return self:Translate(text)
end

-- Translate parsed item name components, never the item or its saved raw text.
-- Register the English display strings, so dropdowns and tooltip measurements
-- resolve them at draw time and still switch back to English immediately.
function L:RegisterItemName(item)
	if item.rarity ~= "MAGIC" or not item.baseName then return end
	local function part(text)
		text = (text or ""):match("^%s*(.-)%s*$")
		return dictionary[text] or text
	end
	local prefix, suffix = part(item.namePrefix), part(item.nameSuffix)
	local function register(base)
		local raw = (item.namePrefix or "") .. base .. (item.nameSuffix or "")
		local zh = (prefix ~= "" and prefix .. " " or "") .. part(base)
			.. (suffix ~= "" and " " .. suffix or "")
		if itemNames[raw] ~= zh then
			itemNames[raw] = zh
			cache = {}
		end
	end
	register(item.baseName)
	register((item.baseName:gsub(" %(.+%)", "")))
end

-- Search the reviewed Chinese text even when the interface is in English.
function L:TranslateForSearch(text)
	local mode, suspended = self.mode, self.suspended
	self.mode, self.suspended = "zh", 0
	local ok, result = pcall(self.TranslateUI, self, text)
	self.mode, self.suspended = mode, suspended
	if not ok then error(result) end
	return result
end

function L:ItemListName(item)
	if self:EffectiveMode() == "en" or self.suspended > 0 then return item.name end
	if item.rarity == "MAGIC" and item.baseName then
		local function part(text)
			return self:TranslateUI((text or ""):match("^%s*(.-)%s*$"))
		end
		local prefix, suffix = part(item.namePrefix), part(item.nameSuffix)
		return (prefix ~= "" and prefix .. " " or "") .. self:TranslateUI(item.baseName)
			.. (suffix ~= "" and " " .. suffix or "")
	end
	return self:TranslateUI(item.name)
end

local function tokens(text)
	local result = {}
	local i = 1
	while i <= #text do
		local tail = text:sub(i)
		local code = tail:match("^%^x%x%x%x%x%x%x") or tail:match("^%^%d")
		if code then
			result[#result + 1] = { color = code }; i = i + #code
		else
			local b = text:byte(i)
			local count = b < 128 and 1 or b < 224 and 2 or b < 240 and 3 or 4
			local ch = text:sub(i, i + count - 1)
			result[#result + 1] = { ch = ch, glyph = glyphs.chars[ch] }
			i = i + count
		end
	end
	return result
end

local function tokenWidth(t, height, font)
	return t.color and 0 or t.glyph and t.glyph[3] * height / glyphs.size or rawWidth(height, font, t.ch)
end

local function measure(height, font, text)
	-- Calculation breakdown cells may be numbers; preserve native coercion.
	if type(text) ~= "string" or not text:find("[\128-\255]") then return rawWidth(height, font, text) end
	local width, longest = 0, 0
	for _, t in ipairs(tokens(text)) do
		if t.ch == "\n" then longest = math.max(longest, width); width = 0
		else width = width + tokenWidth(t, height, font) end
	end
	return math.max(longest, width)
end

-- List clipping uses the same glyph advances as drawing, on UTF-8 boundaries.
function L:ClipText(text, height, font, width)
	if measure(height, font, text) <= width then return text end
	if width < rawWidth(height, font, "...") then return "" end
	local result, used = "", 0
	local limit = width - rawWidth(height, font, "...")
	for _, t in ipairs(tokens(text)) do
		local advance = tokenWidth(t, height, font)
		if used + advance > limit then break end
		result, used = result .. (t.color or t.ch), used + advance
	end
	return result .. "..."
end

-- Wrap display text on UTF-8 boundaries, preferring spaces for English words.
-- The original wrapper only splits on whitespace, so long Chinese paragraphs
-- otherwise overflow the window. Preserve colour when starting the next line.
function L:WrapText(text, height, width, font)
	local lines, line, color, lastSpace = {}, "", "", nil
	for _, t in ipairs(tokens(text)) do
		if t.color then color = t.color; line = line .. t.color
		elseif t.ch == "\n" then
			lines[#lines + 1] = line; line = color; lastSpace = nil
		else
			local nextLine = line .. t.ch
			if measure(height, font, nextLine) > width and measure(height, font, line) > 0 then
				if lastSpace and t.ch:byte() < 128 then
					lines[#lines + 1] = line:sub(1, lastSpace - 1)
					line = color .. line:sub(lastSpace + 1) .. t.ch
				else
					lines[#lines + 1] = line; line = color .. t.ch
				end
				lastSpace = nil
			else line = nextLine end
			if t.ch == " " then lastSpace = #line end
		end
	end
	lines[#lines + 1] = line
	return lines
end

function SetDrawColor(...)
	currentColor = {...}
	return rawColor(...)
end

-- Native viewports use local text coordinates. Keep their origin as well as
-- their width so fallback fitting and hover hints work in scrolled controls.
function SetViewport(x, y, width, height)
	textViewport = x and { x = x, y = y, width = width, height = height } or nil
	if rawViewport then
		if x then return rawViewport(x, y, width, height) end
		return rawViewport()
	end
end

function DrawStringWidth(height, font, text)
	return measure(height, font, L:TranslateUI(text))
end

-- Hit testing must use the same atlas advances and byte offsets as the editor.
function DrawStringCursorIndex(height, font, text, cursorX, cursorY)
	if not text:find("[\128-\255]") then return rawCursor(height, font, text, cursorX, cursorY) end
	local targetLine = math.max(0, math.ceil(cursorY / height) - 1)
	local line, x, index = 0, 0, 1
	for _, token in ipairs(tokens(text)) do
		if token.ch == "\n" then
			if line == targetLine then return index end
			line, x = line + 1, 0
		elseif token.ch then
			local width = tokenWidth(token, height, font)
			if line == targetLine and cursorX < x + width / 2 then return index end
			x = x + width
		end
		index = index + #(token.ch or token.color)
	end
	return #text + 1
end

-- All alignments mirror the native renderer. Atlas glyphs share the same colour
-- and draw layer as the original text; western text keeps its original font.
function DrawString(left, top, align, height, font, text)
	text = L:TranslateUI(text)
	if type(text) ~= "string" or not text:find("[\128-\255]") then return rawDraw(left, top, align, height, font, text) end
	if L.suspended == 0 then
		local screenW = GetVirtualScreenSize()
		local low, high = 2, screenW - 2
		if textViewport then low, high = 0, textViewport.width
		elseif L.textBounds then low, high = L.textBounds[1], L.textBounds[2] end
		local anchor = left
		if align == "CENTER" then anchor = screenW / 2 + left
		elseif align == "RIGHT" then anchor = screenW - left end
		anchor = math.max(low, math.min(high, anchor))
		local available = high - anchor
		if align == "RIGHT" or align == "RIGHT_X" then available = anchor - low
		elseif align == "CENTER" or align == "CENTER_X" then available = 2 * math.min(anchor - low, high - anchor) end
		local original, originalHeight = text, height
		text, height = L:FitText(text, height, font, available)
		top = top + (originalHeight - height) / 2
		if align == "CENTER" then left = anchor - screenW / 2
		elseif align == "RIGHT" then left = screenW - anchor else left = anchor end
		if text ~= original then L:RecordOverflow(anchor, top, align, height, font, text, original) end
	end
	if not atlas then atlas = NewImageHandle(); atlas:Load("Localization/ChineseGlyphs.png") end
	-- Prefer glyphs filtered at the actual UI size instead of shrinking a 48px image.
	local pixelSize = math.floor(height + 0.5)
	local strike = glyphs.strikes and glyphs.strikes[pixelSize]
	local originalColor = currentColor
	local screenW = GetVirtualScreenSize()
	local y = top
	for line in (text .. "\n"):gmatch("(.-)\n") do
		local width = measure(height, font, line)
		local x = left
		if align == "CENTER" then x = (screenW - width) / 2 + left
		elseif align == "CENTER_X" then x = left - width / 2
		elseif align == "RIGHT" then x = screenW - width - left
		elseif align == "RIGHT_X" then x = left - width end
		for _, t in ipairs(tokens(line)) do
			if t.color then rawColor(t.color)
			elseif t.glyph then
				local g = strike and strike.chars[t.ch] or t.glyph
				local cell, scale = strike and strike.cell or glyphs.cell, height / (strike and pixelSize or glyphs.size)
				DrawImage(atlas, x, y, cell * scale, cell * scale,
					g[1] / glyphs.width, g[2] / glyphs.height,
					(g[1] + cell) / glyphs.width, (g[2] + cell) / glyphs.height)
				x = x + tokenWidth(t, height, font)
			else
				rawDraw(x, y, "LEFT", height, font, t.ch)
				x = x + tokenWidth(t, height, font)
			end
		end
		y = y + height
	end
	rawColor(unpack(originalColor))
end

-- Raw drawing scope protects editable user text and its cursor/selection widths.
function L:WithoutTranslation(func, ...)
	self.suspended = self.suspended + 1
	local ok, result = pcall(func, ...)
	self.suspended = self.suspended - 1
	if not ok then error(result) end
	return result
end

function L:ButtonText(x, y, width, height, font, text)
	self:BoundedText(x, y, "CENTER_X", height, font, text, width - 6)
end

-- Fixed-width calculation cells need bounds after translation, including the
-- atlas glyph advances. Keep a readable minimum, then elide on UTF-8 boundaries.
function L:FitText(text, height, font, width)
	text = self:TranslateUI(text)
	width = math.max(0, width)
	local measured = measure(height, font, text)
	local fit = math.min(height, math.max(math.min(10, height), height * width / math.max(1, measured)))
	if measure(fit, font, text) > width then
		if width < rawWidth(fit, font, "...") then return "", fit end
		text = self:ClipText(text, fit, font, width)
	end
	return text, fit
end

function L:BoundedText(x, y, align, height, font, text, width)
	if self:EffectiveMode() == "en" or self.suspended > 0 then
		return DrawString(x, y, align, height, font, text)
	end
	local low, high = 2, GetVirtualScreenSize() - 2
	if textViewport then low, high = 0, textViewport.width
	elseif self.textBounds then low, high = self.textBounds[1], self.textBounds[2] end
	x = math.max(low, math.min(high, x))
	-- Restrict explicit cell widths to their visible host as well.
	local visible = high - x
	if align == "RIGHT_X" then visible = x - low
	elseif align == "CENTER_X" then visible = 2 * math.min(x - low, high - x) end
	width = math.min(width, math.max(0, visible))
	local fitted, size = self:FitText(text, height, font, width)
	if fitted ~= self:TranslateUI(text) then self:RecordOverflow(x, y, align, size, font, fitted, self:TranslateUI(text)) end
	return self:WithoutTranslation(DrawString, x, y + (height - size) / 2, align, size, font, fitted)
end

function L:LeftLabelWidth(control, right)
	local left = self.textBounds and self.textBounds[1] or 2
	local ancestor = control.anchor and control.anchor.other
	local seen = {}
	while ancestor and not seen[ancestor] do
		seen[ancestor] = true
		if ancestor._className == "SectionControl" or ancestor._className == "PopupDialog" then
			left = math.max(left, ancestor:GetPos() + 8)
			break
		end
		ancestor = ancestor.anchor and ancestor.anchor.other
	end
	return math.max(0, right - left)
end

L.CalcText = L.BoundedText

function L:RecordOverflow(x, y, align, height, font, fitted, full)
	if not GetCursorPos or self.suppressOverflow then return end
	local width = measure(height, font, fitted)
	if align == "RIGHT_X" or align == "RIGHT" then x = x - width
	elseif align == "CENTER_X" or align == "CENTER" then x = x - width / 2 end
	if textViewport then x, y = x + textViewport.x, y + textViewport.y end
	local cx, cy = GetCursorPos()
	if cx >= x and cx <= x + width and cy >= y and cy <= y + height then
		self.overflowHint = { x = x, y = y, width = width, height = height, text = full }
	end
end

function L:DrawControl(host, control, viewPort, noTooltip)
	local previous = self.textBounds
	local previousSuppression = self.suppressOverflow
	self.suppressOverflow = previousSuppression or noTooltip
	local left, right = viewPort.x, viewPort.x + viewPort.width
	if host.GetPos and host.GetSize then
		local hx = host:GetPos()
		local hw = host:GetSize()
		if hw and hw > 0 then left, right = math.max(left, hx + 2), math.min(right, hx + hw - 2) end
	end
	local x = control:GetPos()
	local width = control:GetSize()
	-- Labels and checkboxes can place text outside their own rectangle.
	if control._className ~= "LabelControl" and control._className ~= "CheckBoxControl" and width and width > 0 then
		left, right = math.max(left, x), math.min(right, x + width)
	end
	self.textBounds = {left, math.max(left, right)}
	local ok, err = pcall(control.Draw, control, viewPort, noTooltip)
	self.textBounds = previous
	self.suppressOverflow = previousSuppression
	if not ok then error(err) end
end

function L:DrawOverflowHint(viewPort)
	local hint = self.overflowHint
	self.overflowHint = nil
	if not hint or not main or not new then return end
	self.overflowTooltip = self.overflowTooltip or new("Tooltip")
	local tooltip = self.overflowTooltip
	if tooltip:CheckForUpdate(hint.text, viewPort.width) then
		tooltip.maxWidth = math.min(600, viewPort.width - 16)
		self:WithoutTranslation(tooltip.AddLine, tooltip, 14, hint.text)
	end
	SetDrawLayer(nil, 110)
	tooltip:Draw(hint.x, hint.y, hint.width, hint.height, viewPort)
	SetDrawLayer(nil, 0)
end

return L
