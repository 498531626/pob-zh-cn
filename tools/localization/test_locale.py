"""Run focused localisation checks with PoB's bundled LuaJIT, without game saves."""
import ctypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(code):
    lib = ctypes.CDLL(str(ROOT / 'runtime/lua51.dll'))
    lib.luaL_newstate.restype = ctypes.c_void_p
    state = lib.luaL_newstate()
    lib.luaL_openlibs.argtypes = [ctypes.c_void_p]
    lib.luaL_openlibs(state)
    lib.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    lib.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    lib.lua_tolstring.restype = ctypes.c_char_p
    lib.lua_close.argtypes = [ctypes.c_void_p]
    try:
        rc = lib.luaL_loadstring(state, code.encode('utf8')) or lib.lua_pcall(state, 0, 0, 0)
        if rc:
            raise RuntimeError(lib.lua_tolstring(state, -1, None).decode('utf8'))
    finally:
        lib.lua_close(state)


if __name__ == '__main__':
    import os
    os.chdir(ROOT / 'src')
    run(r'''
local alt = false
package.cpath = '../runtime/?.dll;' .. package.cpath
function LoadModule(p) return dofile(p .. '.lua') end
function IsKeyDown() return alt end
function GetScriptPath() return '__localization_test_no_save__' end
function DrawString() end
function DrawStringWidth(h, font, text) return #text * h * 0.5 end
function DrawStringCursorIndex() return 0 end
function SetDrawColor() end
function GetVirtualScreenSize() return 1920,1080 end
function DrawImage() end
function NewImageHandle() return {Load=function() end} end
function wipeTable(t) for k in pairs(t) do t[k]=nil end end
Localization = LoadModule('Modules/Localization')
local L = Localization
local contexts = LoadModule('Localization/PassiveContexts')
local checked = 0
for nodeId, texts in pairs(contexts) do
    for en, zh in pairs(texts) do
        L.mode = 'zh'; assert(L:Translate(en,nodeId) == zh, nodeId .. ': ' .. en)
        assert(L:Translate('^x8888FF'..en,nodeId) == '^x8888FF'..zh)
        L.mode = 'en'; assert(L:Translate(en,nodeId) == en)
        L.mode = 'bilingual'; assert(L:Translate(en,nodeId) == zh .. ' / ' .. en)
        checked = checked + 1
    end
end
L.mode = 'zh'; assert(L:Translate('UNVERIFIED NODE TEXT') == 'UNVERIFIED NODE TEXT')
alt=true; assert(L:Translate('Strength') == 'Strength'); alt=false
L:Cycle(); assert(L.mode=='bilingual'); L:Cycle(); assert(L.mode=='en'); L:Cycle(); assert(L.mode=='zh')
assert(L:WithoutTranslation(function() return L:Translate('Strength') end) == 'Strength')
local ok=pcall(function() L:WithoutTranslation(function() error('expected') end) end)
assert(not ok and L.suspended==0)
local wrapped=L:WrapText('能量护盾能量护盾能量护盾',16,65,'VAR')
assert(#wrapped>1)
for _,line in ipairs(wrapped) do
 assert(L:WithoutTranslation(DrawStringWidth,16,'VAR',line)<=65.01)
 assert(not line:match('[\128-\191]$') or require('lua-utf8').len(line)>0)
end
main={showFlavourText=false,notSupportedModTooltips=false}
function newClass() CreatedClass = {}; return CreatedClass end
LoadModule('Classes/Tooltip')
local T = CreatedClass
local tip=setmetatable({}, {__index=T})
tip.lines={};tip.blocks={};tip:Clear()
tip.maxWidth=180
tip:AddLine(16,'^x8888FF'..'Strength')
assert(tip.lines[1].text=='^x8888FF力量')
assert(tip:CheckForUpdate('same-node'))
assert(not tip:CheckForUpdate('same-node'))
L.mode='en';assert(tip:CheckForUpdate('same-node'))
alt=true;L.mode='zh';assert(not tip:CheckForUpdate('same-node'))
alt=false;assert(tip:CheckForUpdate('same-node'))
for _,p in ipairs({'Modules/Main.lua','Classes/PassiveTreeView.lua','Classes/EditControl.lua','Classes/ButtonControl.lua'}) do assert(loadfile(p)) end
print('Verified '..checked..' context translations in three modes; colour, fallback, Alt, wrapping, tooltip invalidation, edit isolation and Lua syntax passed.')
''')
