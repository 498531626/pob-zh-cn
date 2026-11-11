-- Display-only localisation: game IDs, parser input and saved builds stay English.
local L = { mode = "bilingual", suspended = 0 }
local dictionary = LoadModule("Localization/Dictionary")
local passiveContexts = LoadModule("Localization/PassiveContexts")
local glyphs = LoadModule("Localization/Glyphs")
local rawDraw, rawWidth, rawCursor, rawColor = DrawString, DrawStringWidth, DrawStringCursorIndex, SetDrawColor
local currentColor = {1, 1, 1, 1}
local cache = {}
local atlas
local settingPath = GetScriptPath() .. "/Localization/language.cfg"
local file = io.open(settingPath, "r")
if file then
	local mode = file:read("*l")
	file:close()
	if mode == "en" or mode == "zh" or mode == "bilingual" then L.mode = mode end
end

function L:EffectiveMode()
	return IsKeyDown("ALT") and "en" or self.mode
end

function L:Cycle()
	self.mode = ({ en = "zh", zh = "bilingual", bilingual = "en" })[self.mode]
	local output = io.open(settingPath, "w")
	if output then output:write(self.mode, "\n"); output:close() end
end

function L:Translate(text, nodeId)
	if type(text) ~= "string" or self.suspended > 0 or self:EffectiveMode() == "en" then return text end
	local mode = self:EffectiveMode()
	local key = mode .. "\0" .. tostring(nodeId or "") .. "\0" .. text
	if cache[key] then return cache[key] end
	-- Colour prefixes can contain any mix of numeric and hex escape codes.
	local prefix, body = "", text
	while true do
		local code = body:match("^%^x%x%x%x%x%x%x") or body:match("^%^%d")
		if not code then break end
		prefix, body = prefix .. code, body:sub(#code + 1)
	end
	local trailing = body:match(":$") or (body:sub(-3) == "：" and "：") or ""
	local name = trailing ~= "" and body:sub(1, -#trailing - 1) or body
	local context = nodeId and passiveContexts[tostring(nodeId)]
	local direct = context and context[body] or dictionary[body]
	local zh = direct or (context and context[name]) or dictionary[name]
	local result = text
	if direct then
		result = prefix .. zh .. (mode == "bilingual" and " / " .. body or "")
	elseif zh then
		result = prefix .. zh .. (mode == "bilingual" and " / " .. name or "") .. trailing
	elseif body:find("\n", 1, true) then
		local lines = {}
		for line in (body .. "\n"):gmatch("(.-)\n") do
			lines[#lines + 1] = self:Translate(prefix .. line, nodeId)
		end
		result = table.concat(lines, "\n")
	end
	-- Bound memory when tooltips or character data contain many unique strings.
	if self.cacheSize == nil or self.cacheSize > 12000 then cache = {}; self.cacheSize = 0 end
	cache[key] = result
	self.cacheSize = self.cacheSize + 1
	return result
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
	if not text:find("[\128-\255]") then return rawWidth(height, font, text) end
	local width, longest = 0, 0
	for _, t in ipairs(tokens(text)) do
		if t.ch == "\n" then longest = math.max(longest, width); width = 0
		else width = width + tokenWidth(t, height, font) end
	end
	return math.max(longest, width)
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

function DrawStringWidth(height, font, text)
	return measure(height, font, L:Translate(text))
end

-- All alignments mirror the native renderer. Atlas glyphs share the same colour
-- and draw layer as the original text; western text keeps its original font.
function DrawString(left, top, align, height, font, text)
	text = L:Translate(text)
	if not text:find("[\128-\255]") then return rawDraw(left, top, align, height, font, text) end
	if not atlas then atlas = NewImageHandle(); atlas:Load("Localization/ChineseGlyphs.png") end
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
				local g, scale = t.glyph, height / glyphs.size
				DrawImage(atlas, x, y, glyphs.cell * scale, glyphs.cell * scale,
					g[1] / glyphs.width, g[2] / glyphs.height,
					(g[1] + glyphs.cell) / glyphs.width, (g[2] + glyphs.cell) / glyphs.height)
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
	local translated = self:Translate(text)
	local fit = math.min(height, height * (width - 6) / math.max(1, measure(height, font, translated)))
	fit = math.max(8, fit)
	-- Already translated; prevent a second lookup (e.g. English mode labels).
	self:WithoutTranslation(DrawString, x, y + (height - fit) / 2, "CENTER_X", fit, font, translated)
end

return L
