"""Require every exported unique property, including legacy rolls, to translate.

This checks the production Lua display layer, not just Python rule output.
The exporter excludes item metadata; all remaining property text is checked.
"""
import os
from test_locale import ROOT, run

os.chdir(ROOT / 'src')
run(r'''
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p)return dofile(p..'.lua')end
function GetScriptPath()return '__unique_inventory_no_user_data__'end
function IsKeyDown()return false end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local json=require('dkjson')
local file=assert(io.open('../tools/localization/item-source.json','rb'))
local rows=assert(json.decode(file:read('*a')));file:close()
local L=LoadModule('Modules/Localization')
local checked=0
local function numbers(text)
 local values={}
 for value in text:gmatch('[%+%-]?%d+%.?%d*')do values[#values+1]=value end
 table.sort(values);return table.concat(values,'|')
end
for _,row in ipairs(rows)do
 if row.kind=='unique-stat'then
  local en=row.english
  assert(not en:match('^%s*LevelReq:')and not en:match('^%s*Selected Variant:')
   and not en:match('^%s*Selected Alt Variant:')and not en:match('^%s*Has Alt Variant:'),'Metadata counted as a property')
  L.mode='zh';local zh=L:Translate(en)
  for word in zh:gmatch('%a%a+')do
   assert(word=='PoB'or word=='DPS','Untranslated property: '..en..' => '..zh)
  end
  -- Existing paired translations express English each/a/an as the Chinese
  -- numeral 1. Only these explicit article phrases are equivalent; gameplay
  -- values and all numeric substitutions are still compared exactly.
  local numericZh=zh
  if en:find('for each Curse on Enemy',1,true)then numericZh=numericZh:gsub('每有 1 个','每有一个')end
  if en:match('^%d+%% chance to gain a Frenzy Charge on Kill$')then numericZh=numericZh:gsub('1 个狂怒球','一个狂怒球')end
  if en=='When you Kill a Shocked Enemy, inflict an equivalent Shock on each nearby Enemy'
   or en=='When you Kill an Ignited Enemy, inflict an equivalent Ignite on each nearby Enemy'then
   numericZh=numericZh:gsub('击败 1 名','击败一名')
  end
  assert(numbers(en)==numbers(numericZh),'Numeric change: '..en..' => '..zh)
  assert(L:Translate('^x8888FF'..en)=='^x8888FF'..zh,'Colour changed: '..en)
  L.mode='en';assert(L:Translate(en)==en,'English changed: '..en)
  checked=checked+1
 end
end
assert(checked>9000,'Unique inventory unexpectedly incomplete')
L.mode='zh'
assert(L:Translate('Secret unreviewed property 123')=='Secret unreviewed property 123')
assert(L:Translate('+3 to Level of all Secret Unreviewed Skill Gems')=='+3 to Level of all Secret Unreviewed Skill Gems')
assert(L:Translate('Socketed Gems are Supported by Level 20 Secret Unreviewed Support')=='Socketed Gems are Supported by Level 20 Secret Unreviewed Support')
print('Unique inventory: '..checked..' properties translated; numeric values, colours, English and unknown fallback preserved')
''')
