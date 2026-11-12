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
function DrawStringWidth(h, font, text) return #tostring(text) * h * 0.5 end
function DrawStringCursorIndex() return 0 end
function SetDrawColor() end
function GetVirtualScreenSize() return 1920,1080 end
function DrawImage() end
function NewImageHandle() return {Load=function() end} end
function wipeTable(t) t=t or {}; for k in pairs(t) do t[k]=nil end; return t end
Localization = LoadModule('Modules/Localization')
local L = Localization
assert(L.mode=='zh','Default language must be Chinese')
-- Load isolated module environments to check existing settings and persistence
-- without opening the user's language.cfg or nesting global drawing hooks.
for _,saved in ipairs({'missing','zh','en','bilingual','invalid'}) do
    local stored = saved ~= 'missing' and saved or nil
    local env = setmetatable({}, {__index=_G})
    env.io = setmetatable({open=function(path, mode)
        assert(path=='__localization_test_no_save__/Localization/language.cfg')
        if mode=='r' then
            if not stored then return nil end
            return {read=function() return stored end,close=function() end}
        end
        return {write=function(_,value) stored=value end,close=function() end}
    end}, {__index=io})
    local function reload()
        return setfenv(assert(loadfile('Modules/Localization.lua')),env)()
    end
    local selected=reload()
    assert(selected.mode==(saved=='en' and 'en' or 'zh'),'Legacy/default setting: '..saved)
    local first=selected.mode
    alt=true;assert(selected:EffectiveMode()==first);alt=false
    selected:Cycle()
    assert(selected.mode==(first=='zh' and 'en' or 'zh') and stored==selected.mode)
    assert(reload().mode==selected.mode,'Language did not persist')
    selected:Cycle();assert(selected.mode==first and stored==first)
end
local dict = LoadModule('Localization/Dictionary')
local panelLabels = LoadModule('Localization/PanelLabels')
local calcLabels = LoadModule('Localization/CalcLabels')
local templates = LoadModule('Localization/SkillTemplates')
local itemTemplates = LoadModule('Localization/ItemTemplates')
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
L.mode='zh'
assert(L:TranslateUI('Strength')==dict.Strength)
assert(L:Translate('Strength')==dict.Strength)
L.mode='zh'
-- Native text APIs accept numeric calculation cells. Both localisation hooks
-- must preserve this contract, including English and held Alt and untranslated scopes.
for _,mode in ipairs({'zh','en'}) do
    L.mode=mode
    for _,value in ipairs({0, -42, 1234.5}) do
        assert(DrawStringWidth(12,'VAR',value)==#tostring(value)*6)
        DrawString(0,0,'LEFT',12,'VAR',value)
        assert(rawDrawn[#rawDrawn]==value,'Numeric drawing argument changed')
        assert(L:WithoutTranslation(DrawStringWidth,12,'VAR',value)==#tostring(value)*6)
    end
end
alt=true
assert(DrawStringWidth(12,'VAR',123)==18)
DrawString(0,0,'LEFT',12,'VAR',123)
alt=false;L.mode='zh'
assert(L:Translate('1,177.0 x (1 - 0.0500) ^8(damage from non-crits)')=='1,177.0 x (1 - 0.0500) ^8(非暴击伤害)')
assert(L:Translate('+ 1,765.5 x 0.0500 ^8(damage from crits)')=='+ 1,765.5 x 0.0500 ^8(暴击伤害)')
assert(L:Translate('Life (10 remaining)')=='生命 (剩余 10)')
assert(L:Translate('base life of a level 83 monster')=='83 级怪物的基础生命')
assert(L:Translate('Recovers 120 Life over 3.50 Seconds')=='回复 120 生命，历时 3.50 秒')
assert(L:Translate('Recovers secret Life over 3.50 Seconds')=='Recovers secret Life over 3.50 Seconds')
L.mode='en';assert(L:Translate('Recovers 120 Life over 3.50 Seconds')=='Recovers 120 Life over 3.50 Seconds')
L.mode='zh'
assert(L:Translate('Skill Hit Damage: 1,608.6 DPS')==dict['Skill Hit Damage']..': 1,608.6 每秒伤害')
assert(L:Translate('^x8888FFFireball ^720+2/0')=='^x8888FF火球 ^720+2/0')
assert(L:Translate('Active Skill #12:')=='主动技能 #12：')
local function expand(s)
    return (s:gsub('{(%d+)}',function(i) return tostring(123.25 + tonumber(i)*100) end))
end
local function numberCounts(s)
    local result={}
    for n in s:gmatch('[%+%-]?%d+%.?%d*')do result[n]=(result[n]or 0)+1 end
    return result
end
for _,template in ipairs(itemTemplates)do
    local en=expand(template.en)
    L.mode='zh';local zh=L:Translate(en)
    assert(zh~=en,'Untranslated item template: '..template.en)
    local before,after=numberCounts(en),numberCounts(zh)
    for n,count in pairs(before)do assert(after[n]==count,'Item numeric value lost: '..template.en..' => '..zh)end
    assert(not zh:match('{%d+}'),'Unbound item number: '..template.en)
    L.mode='en';assert(L:Translate(en)==en,'Item English changed')
end
L.mode='zh'
assert(L:Translate('Affix: Tier 2 (of the Eagle)'):find('2',1,true))
assert(L:Translate('Tags: attack, speed')=='标签: 攻击, 速度')
assert(L:Translate('Level: 12 to 86')=='等级: 12 至 86')
assert(L:Translate('Variant: Current (3 variants)')=='变体：当前（3 个变体）')
assert(L:Translate("Watcher's Eye")=='守望之眼')
assert(L:Translate("^xAF6025Watcher's Eye, Prismatic Jewel")=='^xAF6025守望之眼, 三相珠宝')
L.mode='en';assert(L:Translate("Watcher's Eye, Prismatic Jewel")=="Watcher's Eye, Prismatic Jewel")
L.mode='zh';alt=true;assert(L:Translate("Watcher's Eye")=="守望之眼");alt=false
assert(L:Translate('Physical Damage: 12-34 (50.5 DPS)')=='物理伤害: 12-34 (50.5 每秒伤害)')
assert(L:Translate('Exclusive to: Blight')=='仅限于: 菌潮')
assert(dict.Blight~='菌潮','League name overwrote the skill name')
assert(L:Translate('Source: No longer obtainable')=='来源: 已绝版')
assert(L:Translate('Weapon Range: ^71.3 metres')=='武器范围: ^71.3 米')
assert(L:Translate('+(12-34) to maximum Life')~= '+(12-34) to maximum Life')
assert(L:Translate('+# to maximum Life')~= '+# to maximum Life')
assert(L:Translate('Secret Item Modifier 123')=='Secret Item Modifier 123')
for _,label in ipairs(calcLabels) do
    L.mode='zh';assert(L:Translate('^x8888FF'..label..'^7:')=='^x8888FF'..dict[label]..'^7:',label)
end
for _,template in ipairs(templates) do
    local en,zh=expand(template.en),expand(template.zh)
    zh=dict[en] or zh
    L.mode='zh';assert(L:Translate(en)==zh,template.en..' => '..L:Translate(en))
    L.mode='en';assert(L:Translate(en)==en)
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
alt=true; assert(L:Translate('Strength') == dict.Strength); alt=false
L:Cycle(); assert(L.mode=='en'); alt=true; assert(L:EffectiveMode()=='en'); alt=false; L:Cycle(); assert(L.mode=='zh')
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
-- Reproduce the screenshot's real SetBreakdownData path with numeric table
-- cells, including the separate thousands-separator width calculation branch.
function copyTable(t)
    local result={}
    for k,v in pairs(t) do result[k]=type(v)=='table' and copyTable(v) or v end
    return result
end
LoadModule('Classes/CalcBreakdownControl')
local B=CreatedClass
local rows={{value=1234.5},{value=0},{value=-42}}
local calcs={input={},calcsEnv={player={breakdown={Numeric={
    colList={{key='value',label='Strength'}},rowList=rows,
}}}},CheckFlag=function() return true end}
local breakdown=setmetatable({calcsTab=calcs},{__index=B})
for _,mode in ipairs({'zh','en'}) do
    L.mode=mode
    for _,separators in ipairs({false,true}) do
        main.showThousandsSeparators=separators
        breakdown:SetBreakdownData({{breakdown='Numeric'}})
        assert(breakdown.shown and breakdown.contentWidth>0)
        assert(breakdown.sectionList[1].rowList[1].value==1234.5)
    end
end
assert(rows[1].value==1234.5 and rows[2].value==0 and rows[3].value==-42)
L.mode='zh'
LoadModule('Classes/Tooltip')
local T = CreatedClass
local tip=setmetatable({}, {__index=T})
tip.lines={};tip.blocks={};tip:Clear()
tip.maxWidth=180
tip:AddLine(16,'^x8888FF'..'Strength')
assert(tip.lines[1].text=='^x8888FF力量')
L.mode='en';tip:Clear();tip.maxWidth=180
tip:AddLine(16,'^x8888FFStrength')
assert(tip.lines[1].text=='^x8888FFStrength')
L.mode='zh'
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
L.mode='zh'
assert(tip:CheckForUpdate('same-node'))
assert(not tip:CheckForUpdate('same-node'))
L.mode='en';assert(tip:CheckForUpdate('same-node'))
L.mode='zh';assert(tip:CheckForUpdate('same-node'))
alt=true;assert(not tip:CheckForUpdate('same-node'))
alt=false;assert(not tip:CheckForUpdate('same-node'))
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
alt=true;edit:Draw({})
assert(tip.lines[1].text=='力量')
alt=false
assert(viewportX==2+L:WithoutTranslation(DrawStringWidth,16,'VAR',dict.Level)+8)
L.mode='en';edit:Draw({})
assert(tip.lines[1].text=='Strength' and viewportX==2+#'Level'*8+8)
for _,p in ipairs({'Modules/Main.lua','Classes/PassiveTreeView.lua','Classes/EditControl.lua','Classes/ButtonControl.lua','Classes/SkillListControl.lua','Classes/GemTooltip.lua'}) do assert(loadfile(p)) end
print('Verified '..checked..' context translations and '..#panelLabels..' panel labels in two modes; actual comparison formatter, numeric preservation, colour, fallback, Alt language independence, wrapping, tooltip invalidation, edit isolation and Lua syntax passed.')
''')
