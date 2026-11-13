-- SimpleGraphic maps non-ASCII character events through its key-name table.
-- Preserve its ASCII handler and pass GLFW Unicode characters as UTF-8.
local input = {}

function input:Install()
	if self.callback then return true end
	local ok, ffi = pcall(require, "ffi")
	if not ok or ffi.os ~= "Windows" then return false end
	ffi.cdef[[
		typedef struct GLFWwindow GLFWwindow;
		typedef void (*POBcharfun)(GLFWwindow*, unsigned int);
		GLFWwindow* glfwGetCurrentContext(void);
		POBcharfun glfwSetCharCallback(GLFWwindow*, POBcharfun);
	]]
	local loaded, glfw = pcall(ffi.load, "glfw3")
	if not loaded then return false end
	local window = glfw.glfwGetCurrentContext()
	if window == nil then return false end -- Headless checks have no window.
	local utf8 = require("lua-utf8")
	self.callback = ffi.cast("POBcharfun", function(wnd, codepoint)
		if codepoint < 128 then
			if self.original ~= nil then self.original(wnd, codepoint) end
		elseif codepoint <= 0x10FFFF and not (codepoint >= 0xD800 and codepoint <= 0xDFFF) then
			launch:OnChar(utf8.char(codepoint))
		end
	end)
	self.glfw = glfw -- Keep the library and callback alive for the window lifetime.
	self.original = glfw.glfwSetCharCallback(window, self.callback)
	return true
end

return input
