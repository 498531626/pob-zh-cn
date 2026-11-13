-- Path of Building
--
-- Class: Label Control
-- Simple text label.
--
local LabelClass = newClass("LabelControl", "Control", function(self, anchor, rect, label)
	self.Control(anchor, rect)
	self.label = label
	self.width = function()
		local width = DrawStringWidth(self:GetProperty("height"), "VAR", self:GetProperty("label"))
		if Localization and Localization:EffectiveMode() ~= "en" then
			local limit = self.maxLabelWidth or (self.rectStart[3] > 0 and self.rectStart[3])
			if limit then width = math.min(width, limit) end
		end
		return width
	end
end)

function LabelClass:Draw()
	local x, y = self:GetPos()
	if Localization then
		local width = self:GetSize()
		local rightAnchored = self.anchor.point and self.anchor.point:find("RIGHT")
		Localization:BoundedText(rightAnchored and x + width or x, y, rightAnchored and "RIGHT_X" or "LEFT", self:GetProperty("height"), "VAR", self:GetProperty("label"), width)
	else
		DrawString(x, y, "LEFT", self:GetProperty("height"), "VAR", self:GetProperty("label"))
	end
end
