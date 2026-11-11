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
local rawDrawn={}
function DrawString(x,y,align,h,font,text) rawDrawn[#rawDrawn+1]=text end
function DrawStringWidth(h, font, text) return #text * h * 0.5 end
function DrawStringCursorIndex() return 0 end
function SetDrawColor() end
function GetVirtualScreenSize() return 1920,1080 end
function DrawImage() end
function NewImageHandle() return {Load=function() end} end
function wipeTable(t) for k in pairs(t) do t[k]=nil end end
Localization = LoadModule('Modules/Localization')
local L = Localization
local dict = LoadModule('Localization/Dictionary')
local panelLabels = LoadModule('Localization/PanelLabels')
local calcLabels = LoadModule('Localization/CalcLabels')
local templates = LoadModule('Localization/SkillTemplates')
for en,zh in pairs(dict) do
    assert(not zh:match('{%d+}'),'Unbound numeric placeholder in exact translation: '..en)
end
for _,template in ipairs(templates) do
    for index in template.zh:gmatch('{(%d+)}') do
        assert(tonumber(index)<template.values,'Invalid numeric substitution: '..template.en)
    end
end
local configLabels = LoadModule('Localization/ConfigLabels')
for _,label in ipairs(configLabels) do
    local plain=label:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
    if plain:match('%a') then
        L.mode='zh';assert(L:Translate(label)~=label,label)
        L.mode='en';assert(L:Translate(label)==label,label)
    end
end
L.mode='bilingual'
assert(L:TranslateUI('Strength')==dict.Strength)
assert(L:Translate('Strength')==dict.Strength..' / Strength')
L.mode='zh'
assert(L:Translate('1,177.0 x (1 - 0.0500) ^8(damage from non-crits)')=='1,177.0 x (1 - 0.0500) ^8(非暴击伤害)')
assert(L:Translate('+ 1,765.5 x 0.0500 ^8(damage from crits)')=='+ 1,765.5 x 0.0500 ^8(暴击伤害)')
assert(L:Translate('Life (10 remaining)')=='生命 (剩余 10)')
assert(L:Translate('base life of a level 83 monster')=='83 级怪物的基础生命')
assert(L:Translate('Recovers 120 Life over 3.50 Seconds')=='回复 120 生命，历时 3.50 秒')
assert(L:Translate('Recovers secret Life over 3.50 Seconds')=='Recovers secret Life over 3.50 Seconds')
L.mode='bilingual'
assert(L:Translate('base life of a level 83 monster')=='83 级怪物的基础生命 / base life of a level 83 monster')
L.mode='en';assert(L:Translate('Recovers 120 Life over 3.50 Seconds')=='Recovers 120 Life over 3.50 Seconds')
L.mode='zh'
assert(L:Translate('Skill Hit Damage: 1,608.6 DPS')==dict['Skill Hit Damage']..': 1,608.6 每秒伤害')
assert(L:Translate('^x8888FFFireball ^720+2/0')=='^x8888FF火球 ^720+2/0')
assert(L:Translate('Active Skill #12:')=='主动技能 #12：')
local function expand(s)
    return (s:gsub('{(%d+)}',function(i) return tostring(123.25 + tonumber(i)*100) end))
end
for _,label in ipairs(calcLabels) do
    L.mode='zh';assert(L:Translate('^x8888FF'..label..'^7:')=='^x8888FF'..dict[label]..'^7:',label)
end
for _,template in ipairs(templates) do
    local en,zh=expand(template.en),expand(template.zh)
    zh=dict[en] or zh
    L.mode='zh';assert(L:Translate(en)==zh,template.en..' => '..L:Translate(en))
    L.mode='en';assert(L:Translate(en)==en)
    L.mode='bilingual';assert(L:Translate(en)==zh..' / '..en,template.en)
end
L.mode='zh'
assert(L:Translate('^xFF0000Strength ^8(Not supported in PoB yet)')=='^xFF0000力量 ^8（PoB 尚未支持此效果）')
assert(L:Translate('^x7F7F7FCast Time: ^70.75 sec')=='^x7F7F7F施放间隔: ^70.75 秒')
assert(L:Translate('^x7F7F7FRequires ^x7F7F7FLevel ^712^x7F7F7F, ^720 ^x7F7F7FInt')=='^x7F7F7F需求 ^x7F7F7F等级 ^712^x7F7F7F, ^720 ^x7F7F7F智慧')
assert(L:Translate('Unleashes a ball of fire towards a target which explodes, damaging nearby foes.')~= 'Unleashes a ball of fire towards a target which explodes, damaging nearby foes.')
assert(L:Translate('Deals 9 to 14 Fire Damage')=='造成 9 - 14 火焰伤害')
assert(L:Translate('Deals 9 garbage to 14 Fire Damage')=='Deals 9 garbage to 14 Fire Damage')
assert(L:Translate('An unknown property: keep this text')=='An unknown property: keep this text')
for _, label in ipairs(panelLabels) do
    L.mode='zh';assert(L:Translate('^7'..label..':')=='^7'..dict[label]..':',label)
    local raw='^x33FF77+1,234.5 '..label..' (+5.0%) ^8[+0.25 (+1.0%) per point]'
    local zh='^x33FF77+1,234.5 '..dict[label]..' (+5.0%) ^8[+0.25 (+1.0%) 每点]'
    assert(L:Translate(raw)==zh,label)
    L.mode='en';assert(L:Translate(raw)==raw)
    L.mode='bilingual';assert(L:Translate(raw)==zh..' / '..raw:sub(9))
end
L.mode='zh'
assert(L:Translate('^1-3.25% Movement Speed Modifier (-1.5%)')=='^1-3.25% 移动速度修正 (-1.5%)')
assert(L:Translate('^7+10 Unverified Stat')=='^7+10 Unverified Stat')
assert(L:Translate('^72 points to node ^8(Can be allocated without pathing to it)')=='^72 点到达此天赋 ^8（无需连通路径即可分配）')
assert(L:Translate('^7123^x808080 (Guard)')=='^7123^x808080 (护卫技能生效)')
local contexts = LoadModule('Localization/PassiveContexts')
local checked = 0
for nodeId, texts in pairs(contexts) do
    for en, zh in pairs(texts) do
        L.mode = 'zh'; assert(L:Translate(en,nodeId) == zh, nodeId .. ': ' .. en)
        assert(L:Translate('^x8888FF'..en,nodeId) == '^x8888FF'..zh)
        local suffix=' ^8(Not supported in PoB yet)'
        assert(L:Translate('^xF05050'..en..suffix,nodeId)=='^xF05050'..zh..' ^8（PoB 尚未支持此效果）')
        L.mode = 'en'; assert(L:Translate(en,nodeId) == en)
        L.mode = 'bilingual'; assert(L:Translate(en,nodeId) == zh .. ' / ' .. en)
        checked = checked + 1
    end
end
local grouped=0
for nodeId,context in pairs(LoadModule('Localization/PassiveContexts'))do
 for text in pairs(context)do
  if text:find('\n',1,true)then
   local lines={};for line in (text..'\n'):gmatch('(.-)\n')do lines[#lines+1]=line end
   L.mode='zh';local groups=L:PassiveLineGroups(nodeId,lines)
   assert(#groups==1 and groups[1].text==text and groups[1].last==#lines)
   L.mode='en';assert(#L:PassiveLineGroups(nodeId,lines)==#lines)
   grouped=grouped+1
  end
 end
end
assert(grouped>100,'Multiline passive fixtures missing')
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
L.mode='bilingual';tip:Clear();tip.maxWidth=180
tip:AddLine(16,'^x8888FFStrength')
assert(tip.lines[1].text=='^x8888FF力量 / Strength')
tip:Clear();tip.maxWidth=180
tip:AddLine(16,'^x8888FF'..string.rep('能量护盾',15))
assert(#tip.lines>1)
for _,line in ipairs(tip.lines) do assert(L:WithoutTranslation(DrawStringWidth,16,'VAR',line.text)<=180) end
-- Exercise the real comparison formatter, including node-path averages, rather
-- than only matching hand-constructed strings. No game state or saves are loaded.
local f=assert(io.open('Modules/Build.lua','r'));local source=f:read('*a');f:close()
local comparison=assert(source:match('(function buildMode:CompareStatList.-)\n%-%- Compare values of all display stats'))
buildMode={};s_format=string.format
colorCodes={POSITIVE='^x33FF77',NEGATIVE='^xDD0022'}
function matchFlags() return true end
function formatNumSep(s) return s end
assert(loadstring(comparison))()
local baseline={Life=100};local changed={Life=110}
local stats={{stat='Life',label='Total Life',fmt='d',compPercent=true}}
local actor={mainSkill={skillFlags={}}}
L.mode='zh';tip:Clear()
assert(buildMode:CompareStatList(tip,stats,actor,baseline,changed,'^7Allocating this node will give you:',2)==1)
assert(tip.lines[1].text=='^7点出此天赋后的属性变化：')
assert(tip.lines[2].text=='^x33FF77+10 总生命 (+10.0%) ^8[+5 (+5.0%) 每点]')
L.mode='en';tip:Clear()
buildMode:CompareStatList(tip,stats,actor,baseline,changed,'^7Allocating this node will give you:',2)
assert(tip.lines[2].text=='^x33FF77+10 Total Life (+10.0%) ^8[+5 (+5.0%) per point]')
assert(baseline.Life==100 and changed.Life==110)
L.mode='bilingual'
assert(tip:CheckForUpdate('same-node'))
assert(not tip:CheckForUpdate('same-node'))
L.mode='en';assert(tip:CheckForUpdate('same-node'))
alt=true;L.mode='zh';assert(not tip:CheckForUpdate('same-node'))
alt=false;assert(tip:CheckForUpdate('same-node'))
-- Exercise the actual edit control: only editable bytes are protected. Its
-- prompt width and tooltip must still follow the selected interface language.
LoadModule('Classes/EditControl')
local E=CreatedClass
local viewportX
function SetViewport(x) if x then viewportX=x end end
function SetDrawLayer() end
local contentWidth
local edit=setmetatable({buf='Strength',prompt='Level',font='VAR',textCol='^7',
 inactiveCol='^8',disableCol='^9',controls={
 scrollBarH={offset=0,IsShown=function()return false end,SetContentDimension=function(_,w)contentWidth=w end},
 scrollBarV={offset=0,IsShown=function()return false end}},
 GetPos=function()return 0,0 end,GetSize=function()return 200,20 end,
 IsEnabled=function()return true end,IsMouseOver=function()return true end,
 DrawControls=function()end,DrawTooltip=function()tip:Clear();tip:AddLine(16,'Strength')end}, {__index=E})
L.mode='zh';rawDrawn={};edit:Draw({})
assert(edit.buf=='Strength' and edit.prompt=='Level')
assert(tip.lines[1].text=='力量')
local inputDrawn=false
for _,s in ipairs(rawDrawn)do if s=='Strength'then inputDrawn=true end end
assert(inputDrawn,'Editable buffer was translated')
assert(viewportX==2+L:WithoutTranslation(DrawStringWidth,16,'VAR',dict.Level)+8)
assert(contentWidth==#'Strength'*8+2,'Editable width was translated')
L.mode='bilingual';edit:Draw({})
assert(tip.lines[1].text=='力量 / Strength')
assert(viewportX==2+L:WithoutTranslation(DrawStringWidth,16,'VAR',dict.Level)+8)
L.mode='en';edit:Draw({})
assert(tip.lines[1].text=='Strength' and viewportX==2+#'Level'*8+8)
for _,p in ipairs({'Modules/Main.lua','Classes/PassiveTreeView.lua','Classes/EditControl.lua','Classes/ButtonControl.lua','Classes/SkillListControl.lua','Classes/GemTooltip.lua'}) do assert(loadfile(p)) end
print('Verified '..checked..' context translations and '..#panelLabels..' panel labels in three modes; actual comparison formatter, numeric preservation, colour, fallback, Alt, wrapping, tooltip invalidation, edit isolation and Lua syntax passed.')
''')
