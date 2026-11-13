-- Shared validation for update manifests. User data is never update-managed.
local policy = { }

function policy.ValidName(name)
	if type(name) ~= "string" or name == "" or name:find('[%c\\:"]') or name:sub(1, 1) == "/" then return false end
	for segment in (name.."/"):gmatch("(.-)/") do
		if segment == "" or segment == "." or segment == ".." or segment:match("[ .]$") then return false end
	end
	local lower = name:lower()
	if lower == "manifest.xml" or lower == "settings.xml" or lower == "localization/language.cfg"
		or lower == "first.run" or lower == "installed.cfg" or lower == "builds" or lower:match("^builds/")
		or lower:match("^update/") or lower:match("^%.") then return false end
	return true
end

function policy.ValidSource(url)
	return type(url) == "string" and not url:find('[%c"]') and
		(url:match("^https://[^/@]+/") or url:match("^http://127%.0%.0%.1:%d+/")) ~= nil
end

return policy
