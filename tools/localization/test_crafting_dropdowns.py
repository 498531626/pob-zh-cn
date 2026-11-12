"""Audit assembled crafting dropdown labels, including ranges and affix metadata."""
import json
import os
from test_locale import ROOT, run

os.chdir(ROOT / 'src')
paths = [p.relative_to(ROOT / 'src').with_suffix('').as_posix()
         for p in sorted((ROOT / 'src/Data').glob('Mod*.lua'))
         if p.stem not in ('ModCache', 'ModMap', 'ModFoulbornMap', 'ModScalability')]
run('local paths={' + ','.join(json.dumps(p) for p in paths) + '}\n' + r'''
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p)return dofile(p..'.lua')end
function GetScriptPath()return '__dropdown_test_no_save__'end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local L=LoadModule('Modules/Localization')
local glyphs=LoadModule('Localization/Glyphs').chars
local dictionary=LoadModule('Localization/Dictionary')
local json=require('dkjson')
local function plain(s)return(s:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d',''))end
local function numbers(s)
 local result={}
 for n in plain(s):gmatch('[%+%-]?%d+%.?%d*')do result[#result+1]=n end
 table.sort(result);return table.concat(result,'|')
end
local cases={
 '(14-16) - (20-22) Added Fire Damage',
 'Adds (14-16) to (20-22) Lightning Damage',
 '+(51-55) to maximum Mana',
 '(51-55)% of Damage taken Recouped as Mana',
 '(51-55)% increased Mana Cost Efficiency',
 '(7-8)% increased Attack and Cast Speed',
 '(25-28)% increased Brand Attachment range',
 '(16-20)% to Cold and Chaos Resistances',
 '+(31-35) to Dexterity and Intelligence',
 '(33-40)% increased Effect of Non-Damaging Ailments',
 'You have Vaal Pact while Focused/15% of Damage Leeched as Life while Focused',
 '(14-16)% increased Mine Throwing Speed',
 '+1 to Minimum Endurance Charges',
 '(3-4)% chance to gain an Endurance Charge on Kill',
 '(36-40)% increased Totem Placement speed',
 '(14-16)% increased Trap Throwing Speed',
}
-- Assert exact composition rather than accepting a changed label as translated.
for _,stat in ipairs(cases)do
 L.mode='zh';local expected=L:Translate(stat)
 assert(not plain(expected):find('%a%a+'),'Screenshot core unresolved: '..stat..' => '..expected)
 for _,kind in ipairs({'Prefix','Suffix'})do
  local label=stat..' ('..kind..')'
  assert(L:Translate(label)==expected..' ('..dictionary[kind]..')','Broken rolled label: '..label..' => '..L:Translate(label))
  assert(L:Translate('^7'..label)=='^7'..L:Translate(label),'Colour prefix changed')
  assert(numbers(label)==numbers(L:Translate(label)),'Numeric rolls changed: '..label)
  L.mode='en';assert(L:Translate(label)==label);L.mode='zh'
 end
end
local counts,pending={},{}
local checked=0
local function check(mod,path)
 if type(mod)~='table'then return end
 if (mod.type=='Prefix' or mod.type=='Suffix') and type(mod[1])=='string'then
  local original=json.encode(mod)
  local stat=table.concat(mod,'/');local label=stat..' ('..mod.type..')'
  L.mode='zh';local core=L:Translate(stat);local translated=L:Translate(label)
  assert(translated==core..' ('..dictionary[mod.type]..')','Assembly regression: '..path..' '..label)
  assert(numbers(label)==numbers(translated),'Rolls changed: '..label..' => '..translated)
  local named=mod.affix and mod.affix..'   ^8['..stat..']'
  if named then
   assert(L:Translate(named)==L:Translate(mod.affix)..'   ^8['..core..']','Named affix regression: '..named)
  end
  L.mode='en';assert(L:Translate(label)==label);if named then assert(L:Translate(named)==named)end;L.mode='zh'
  assert(json.encode(mod)==original,'Translation modified source mod: '..label)
  checked=checked+1;counts[path]=(counts[path]or 0)+1
  if plain(translated):find('%a%a+')then pending[#pending+1]={source=path,english=label,chinese=translated}end
 else
  for k,v in pairs(mod)do if type(v)=='table' and k~='tradeHashes'then check(v,path)end end
 end
end
for _,path in ipairs(paths)do check(LoadModule(path),path)end
for _,template in ipairs(LoadModule('Localization/CraftingTemplates'))do
 for char in template.zh:gmatch('[\194-\244][\128-\191]+')do assert(glyphs[char],'Missing crafting glyph: '..char)end
end
assert(L:Translate('Unverified (12-34) modifier (Suffix)')=='Unverified (12-34) modifier ('..dictionary.Suffix..')')
for _,unknown in ipairs({'Unknown Graft skill name','Focus has garbage% increased Cooldown Recovery Rate'})do
 assert(L:Translate(unknown)==unknown,'Unknown text was rewritten: '..unknown)
end
local f=assert(io.open('../tools/localization/crafting-dropdown-audit.json','wb'))
f:write(json.encode({checked=checked,by_source=counts,pending_count=#pending,pending=pending},{indent=true}));f:close()
assert(#pending==0,'Crafting dropdown translation missing: '..(pending[1]and pending[1].english or ''))
print('Crafting dropdowns: '..checked..' assembled labels; exact composition, numeric rolls, colours and English switching passed; '..#pending..' unresolved base translations recorded')
''')
