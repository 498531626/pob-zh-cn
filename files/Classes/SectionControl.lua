-- Path of Building
--
-- Class: Section Control
-- Section box with label
--

local SectionClass = newClass("SectionControl", "Control", function(self, anchor, rect, label)
	self.Control(anchor, rect)
	self.label = label
end)

function SectionClass:Draw()
	local x, y = self:GetPos()
	local width, height = self:GetSize()
	SetDrawLayer(nil, -10)
	SetDrawColor(0.66, 0.66, 0.66)
	DrawImage(nil, x, y, width, height)
	SetDrawColor(0.1, 0.1, 0.1)
	DrawImage(nil, x + 2, y + 2, width - 4, height - 4)
	SetDrawLayer(nil, 0)
	local label = self:GetProperty("label")
	local fullLabel = label
	local textSize = 14
	if Localization and Localization:EffectiveMode() ~= "en" then label, textSize = Localization:FitText(label, 14, "VAR", width - 22) end
	local labelWidth = DrawStringWidth(textSize, "VAR", label)
	SetDrawColor(0.66, 0.66, 0.66)
	DrawImage(nil, x + 6, y - 8, labelWidth + 6, 18)
	SetDrawColor(0, 0, 0)
	DrawImage(nil, x + 7, y - 7, labelWidth + 4, 16)
	SetDrawColor(1, 1, 1)
	DrawString(x + 9, y - 6 + (14 - textSize) / 2, "LEFT", textSize, "VAR", label)
	if Localization and label ~= Localization:TranslateUI(fullLabel) then
		Localization:RecordOverflow(x + 9, y - 6, "LEFT", textSize, "VAR", label, Localization:TranslateUI(fullLabel))
	end
end
