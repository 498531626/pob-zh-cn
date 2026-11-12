"""Check the complete source inventory of item names and property text."""
import os
from test_locale import ROOT,run

os.chdir(ROOT/'src')
run(r'''
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p)return dofile(p..'.lua')end
function GetScriptPath()return '__item_inventory_no_user_data__'end
function IsKeyDown()return false end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local json=require('dkjson')
local f=assert(io.open('../tools/localization/item-source.json','rb'))
local rows=assert(json.decode(f:read('*a')));f:close()
local L=LoadModule('Modules/Localization')
local counts={}
local scopes={['affix-name']=true,['base-name']=true,['base-stat']=true,['craft-stat']=true,
 ['craft-stat-group']=true,['unique-name']=true,['unique-stat']=true,['item-type']=true}
local function values(text)
 local v={};for n in text:gmatch('[%+%-]?%d+%.?%d*')do v[#v+1]=n end
 table.sort(v);return table.concat(v,'|')
end
for _,row in ipairs(rows)do
 if scopes[row.kind]then
  local en=row.english
  L.mode='zh';local zh=L:Translate(en)
  for word in zh:gmatch('%a%a+')do
   assert(word=='PoB'or word=='DPS','Untranslated '..row.kind..': '..en..' => '..zh)
  end
  local numericZh=zh
  -- A Chinese count of one can spell out English a/an/each/per. Normalise
  -- count units only, never percentages or other gameplay magnitudes.
  if values(en)~=values(zh)and (en:match('%f[%a]a%f[%A]')or en:match('%f[%a]an%f[%A]')
   or en:find('each',1,true)or en:find('per ',1,true)or en:find('every ',1,true))then
   numericZh=numericZh:gsub('1 个','一个'):gsub('1 名','一名'):gsub('1 次','一次'):gsub('每 1 秒','每秒')
  end
  assert(values(en)==values(numericZh),'Numeric change: '..en..' => '..zh)
  assert(L:Translate('^x8888FF'..en)=='^x8888FF'..zh,'Colour changed: '..en)
  L.mode='en';assert(L:Translate(en)==en,'English changed: '..en)
  counts[row.kind]=(counts[row.kind]or 0)+1
 end
end
assert(counts['craft-stat']>19000 and counts['craft-stat-group']>2000 and counts['affix-name']>2100,'Incomplete crafting inventory')
L.mode='zh'
assert(L:Translate('Upfront Cost to Use or Trigger a Skill, with a 0.1 second Cooldown')=='使用或触发技能的预付消耗；冷却时间为 0.1 秒','Split upfront-cost clause regressed')
assert(L:Translate('Crafting unknown property 123')=='Crafting unknown property 123')
assert(L:Translate('Added Small Passive Skills also grant: Unknown property 123')=='Added Small Passive Skills also grant: Unknown property 123')
print('Complete item display inventory passed: '..json.encode(counts))
''')
