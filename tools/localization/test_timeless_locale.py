"""Check every timeless jewel display field and rolled values using bundled Lua."""
import os
from test_locale import ROOT, run


if __name__ == '__main__':
    os.chdir(ROOT / 'src')
    run(r'''
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p) return dofile(p..'.lua') end
function GetScriptPath() return '__timeless_test_no_save__' end
function DrawString() end
function DrawStringWidth(_,_,text) return #text end
function DrawStringCursorIndex() return 0 end
function SetDrawColor() end
function GetVirtualScreenSize() return 1920,1080 end
function NewImageHandle() return {Load=function() end} end
function wipeTable(t) for k in pairs(t) do t[k]=nil end;return t end
function newClass() TooltipClass={};return TooltipClass end
main={showFlavourText=false}
local L=LoadModule('Modules/Localization')
Localization=L
local data=LoadModule('Data/TimelessJewelData/LegionPassives')
local json=require('dkjson')
local before=json.encode(data)
local pending,seen={},{}
local checked=0
local function check(text)
 if text=='' then return end
 checked=checked+1
 L.mode='zh'
 local zh=L:Translate(text,36949)
 if zh:match('%a') and not seen[text] then pending[#pending+1]=text;seen[text]=true end
 -- Word order can differ, but each value (including ranges) must survive.
 local function values(s)
  local result={};for n in s:gmatch('[%+%-]?%d+%.?%d*') do result[#result+1]=n end
  table.sort(result);return table.concat(result,'|')
 end
 local numericZh=zh
 if text:find('a Frenzy Charge',1,true) then numericZh=numericZh:gsub('1 个狂怒球','狂怒球') end
 if text:find('an Endurance Charge',1,true) then numericZh=numericZh:gsub('1 个耐力球','耐力球') end
 if text:find('a Power Charge',1,true) then numericZh=numericZh:gsub('1 个暴击球','暴击球') end
 assert(values(text)==values(numericZh),'Numeric change: '..text..' -> '..zh)
 assert(L:Translate('^x8888FF'..text,36949)=='^x8888FF'..zh,'Colour change: '..text)
 L.mode='en';assert(L:Translate(text,36949)==text,'English changed: '..text)
end
for _,kind in ipairs({'nodes','additions'}) do
 for _,node in ipairs(data[kind]) do
  if node.id:match('^vaal_') or node.id:match('^karui_') or node.id:match('^maraketh_')
   or node.id:match('^templar_') or node.id:match('^eternal_') then
   check(node.dn)
   for _,line in ipairs(node.sd or {}) do
    check(line)
    for _,side in ipairs({1,2}) do
     local rolled=line:gsub('%((%-?%d+%.?%d*)%-(%-?%d+%.?%d*)%)',function(a,b) return side==1 and a or b end)
     check(rolled)
    end
   end
  end
 end
end
check('+5 to Devotion');check('+10 to Devotion')
L.mode='zh'
assert(L:Translate('+10 to Unverified Timeless Stat',36949)=='+10 to Unverified Timeless Stat')
assert(json.encode(data)==before,'Timeless gameplay data changed')
table.sort(pending)
local f=assert(io.open('../tools/localization/timeless-pending.json','wb'))
f:write(json.encode(pending,{indent=true}));f:close()
assert(#pending==0,'Untranslated timeless texts: '..#pending..' (see timeless-pending.json)')
assert(L:Translate('+10 to Devotion',36949)=='+10 奉献')
-- The replaced node retains its original tree ID, including when cached.
LoadModule('Classes/Tooltip')
local tip=setmetatable({lines={},blocks={}}, {__index=TooltipClass})
for _,mode in ipairs({'zh','en','zh'}) do
 L.mode=mode;tip:Clear();tip.localizationNodeId=36949
 tip:AddLine(18,'Devotion');tip:AddLine(16,'^x8888FF+10 to Devotion')
 assert(tip.lines[1].text==(mode=='zh' and '奉献' or 'Devotion'))
 assert(tip.lines[2].text==(mode=='zh' and '^x8888FF+10 奉献' or '^x8888FF+10 to Devotion'))
end
print('Timeless localisation: '..checked..' display/roll checks; colours, numbers, English and source data preserved')
''')
