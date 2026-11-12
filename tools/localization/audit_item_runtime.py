"""Audit actual item tooltips and data preservation in a disposable copy.

Usage: python audit_item_runtime.py --workspace E:/POB/Localization-QA
The copy must have src/HeadlessWrapper.lua and the usual runtime/data assets.
Never starts from the source checkout or loads its settings/builds.
"""
import argparse
import os
from pathlib import Path
from test_locale import ROOT, run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--export-only', action='store_true', help='Refresh runtime item display inventory before generating translations')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if workspace == ROOT.resolve() or not (workspace/'src/HeadlessWrapper.lua').is_file():
        raise SystemExit('Supply a separate disposable PoB copy with HeadlessWrapper.lua')
    os.chdir(workspace/'src')
    # Only absolute paths supplied by us enter these quoted Lua literals.
    import json
    path = lambda p: json.dumps(p.as_posix(), ensure_ascii=False)
    run('package.path='+path(ROOT/'runtime/lua/?.lua')+'..";"..'+path(ROOT/'runtime/lua/?/init.lua')+'..";"..package.path\n'
        +'package.cpath='+path(ROOT/'runtime/?.dll')+'..";"..package.cpath\n'
        +'AUDIT_SOURCE='+path(workspace/'src')+'\n'
        +'AUDIT_RUNTIME='+path(ROOT/'runtime')+'\n'
        +'AUDIT_EXPORT_ONLY='+('true' if args.export_only else 'false')+'\n'
        +'AUDIT_OUTPUT='+path(ROOT/'tools/localization/item-runtime-audit.json')+'\n'
        +'AUDIT_PENDING='+path(ROOT/'tools/localization/item-runtime-pending.json')+'\n'+r'''
arg={}
local f=assert(io.open('HeadlessWrapper.lua','r'));local source=f:read('*a');f:close()
source=source:gsub('^#@','')
source=source:gsub('dofile%("Launch.lua"%)',[[
function GetScriptPath()return AUDIT_SOURCE end
function GetRuntimePath()return AUDIT_RUNTIME end
function GetUserPath()return AUDIT_SOURCE end
io.read=function()error('Unexpected startup prompt')end
dofile('Launch.lua')
]])
assert(loadstring(source))()
local L=Localization
local json=require('dkjson')
newBuild()
local inventory,inventorySeen={},{}
local function inventoryAdd(text,kind,source)
 if type(text)~='string'or not text:match('%a')then return end
 local key=kind..'\0'..text
 if not inventorySeen[key]then
  inventorySeen[key]=true;inventory[#inventory+1]={english=text,kind=kind,source=source}
 end
end
-- These objects include programmatically generated and special uniques that
-- are absent from the top-level Data/Uniques/*.lua static inventory.
for _,item in pairs(main.uniqueDB.list)do
 inventoryAdd(item.title,'unique-name','runtime uniqueDB parsed title')
end
for _,raw in ipairs(data.uniques.generated)do
 local lines={};for line in raw:gmatch('[^\n\r]+')do lines[#lines+1]=line end
 local title=1
 while lines[title]and (lines[title]:match('^Item Class:')or lines[title]:match('^Rarity:'))do title=title+1 end
 inventoryAdd(lines[title],'unique-name','Data/Uniques/Special/Generated.lua')
 for i=title+2,#lines do
  local line=lines[i]:gsub('{[^}]+}','')
  if not line:match('^%a[%a ]*:')and not line:match('^%-%-')then
   inventoryAdd(line,'unique-stat','Data/Uniques/Special/Generated.lua')
  end
 end
end
main.showFlavourText=false
build.itemsTab.showStatDifferences=false
local tip=new('Tooltip')
local rows,pending,titlePending={},{},{}
local function check(item,kind)
 local original=item:BuildRaw()
 local function fingerprint(t,seen)
  if type(t)~='table'then return type(t)=='number'and tostring(t)or ''end
  if seen[t]then return ''end;seen[t]=true
  local out={};for k,v in pairs(t)do
   if type(v)=='number'then out[#out+1]=tostring(k)..'='..tostring(v)
   elseif type(v)=='table'then out[#out+1]=tostring(k)..'{'..fingerprint(v,seen)..'}'end
  end;table.sort(out);return table.concat(out,';')
 end
 local mods=fingerprint(item.modList,{})
 local text={}
 for _,mode in ipairs({'en','zh'})do
  L.mode=mode;tip:Clear();build.itemsTab:AddItemTooltip(tip,item,nil,true)
  local lines={};for _,line in ipairs(tip.lines)do lines[#lines+1]=line.text or ''end
  text[mode]=table.concat(lines,'\n')
  if mode=='en' then
   for _,line in ipairs(lines)do
    local plain=(line:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d',''))
    plain=plain:gsub(' %(Not supported in PoB yet%)$','')
    inventoryAdd(plain,'unique-tooltip','runtime uniqueDB tooltip')
   end
  end
  assert(item:BuildRaw()==original,'Displayed item changed serialization: '..item.name)
  assert(fingerprint(item.modList,{})==mods,'Displayed item changed parsed modifiers: '..item.name)
 end
 local rest=text.zh:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
 local words={};for w in rest:gmatch('%a%a+')do if w~='PoB'and w~='Ctrl'and w~='Alt'and w~='Shift'and w~='DPS'and w~='RGBA'then words[#words+1]=w end end
 local row={name=item.name,kind=kind,english=text.en,chinese=text.zh}
 L.mode='zh';row.title=item.title;row.translated_title=L:Translate(item.title)
 if kind=='unique'and row.translated_title:match('%a%a')then
  titlePending[#titlePending+1]={english=item.title,chinese=row.translated_title}
 end
 if item.title=="Watcher's Eye"then
  assert(row.translated_title=='守望之眼','Generated unique title is missing')
  assert(L:Translate(item.name)=='守望之眼, 三相珠宝','Generated unique list name is incomplete')
 end
 rows[#rows+1]=row
 if #words>0 then row.remaining_english_words=words;pending[#pending+1]=row end
end
for _,item in pairs(main.uniqueDB.list)do check(item,'unique')end
local crafted=0
for _,base in ipairs({'Vaal Regalia','Hubris Circlet','Titan Gauntlets','Opal Ring','Imperial Claw','Spine Bow'})do
 build.itemsTab.showStatDifferences=true
 local item=new('Item','Rarity: RARE\nNew Item\n'..base..'\nItem Level: 86\n')
 if item.base then
  item.crafted=true;item:BuildAndParseRaw()
  for id,mod in pairs(item.affixes or {})do
   if mod.type=='Prefix' and mod[1] and mod[1]:find('maximum Life',1,true)then item.prefixes[1]={modId=id};break end
  end
  for id,mod in pairs(item.affixes or {})do
   if mod.type=='Suffix' and mod[1] and mod[1]:find('Fire Resistance',1,true)then item.suffixes[1]={modId=id};break end
  end
  item:Craft();check(item,'crafted');crafted=crafted+1
 end
end
table.sort(titlePending,function(a,b)return a.english<b.english end)
table.sort(inventory,function(a,b)return a.kind==b.kind and a.english<b.english or a.kind<b.kind end)
local inventoryFile=assert(io.open(AUDIT_OUTPUT:gsub('item%-runtime%-audit','item-runtime-source'),'wb'))
inventoryFile:write(json.encode(inventory,{indent=true}));inventoryFile:close()
if AUDIT_EXPORT_ONLY then print('Runtime unique inventory: '..#inventory..' display records');return end
local f=assert(io.open(AUDIT_OUTPUT,'wb'));f:write(json.encode({total=#rows,crafted=crafted,untranslated_tooltips=#pending,untranslated_titles=titlePending,items=rows},{indent=true}));f:close()
f=assert(io.open(AUDIT_PENDING,'wb'));f:write(json.encode(pending,{indent=true}));f:close()
for _,row in ipairs(pending)do assert(row.kind~='crafted','Crafting sample has untranslated detail: '..row.name)end
assert(crafted==6,'Expected all six crafting fixtures to parse')
print('Actual item tooltip audit: '..#rows..' items, '..crafted..' crafted; serialization and parsed numbers unchanged in 2 modes; '..#pending..' tooltips have English')

''')
