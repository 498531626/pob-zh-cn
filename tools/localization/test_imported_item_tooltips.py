"""Exercise parsed imported magic items in a disposable PoB copy, never user builds."""
import argparse
import json
import os
from pathlib import Path
from test_locale import ROOT, run

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
workspace = parser.parse_args().workspace.resolve()
if workspace == ROOT.resolve() or not (workspace / 'src/HeadlessWrapper.lua').is_file():
    raise SystemExit('Supply a separate disposable PoB copy')
os.chdir(workspace / 'src')
path = lambda p: json.dumps(p.as_posix(), ensure_ascii=False)
run('package.path=' + path(ROOT / 'runtime/lua/?.lua') + '..";"..' +
    path(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n' +
    'package.cpath=' + path(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n' +
    'AUDIT_SOURCE=' + path(workspace / 'src') + '\n' +
    'AUDIT_RUNTIME=' + path(ROOT / 'runtime') + '\n' + r'''
arg={}
local f=assert(io.open('HeadlessWrapper.lua','r'));local source=f:read('*a');f:close()
source=source:gsub('^#@',''):gsub('dofile%("Launch.lua"%)',[[
function GetScriptPath()return AUDIT_SOURCE end
function GetRuntimePath()return AUDIT_RUNTIME end
function GetUserPath()return AUDIT_SOURCE end
io.read=function()error('Unexpected startup prompt')end
dofile('Launch.lua')
]])
assert(loadstring(source))()
newBuild()
main.showFlavourText=false
local L=Localization
local dict=LoadModule('Localization/Dictionary')
local fixtures={
 {'Endless','Silver Flask','of the Pangolin','30% increased Charge Recovery\n53% increased Armour during Effect'},
 {'Alarmed','Divine Life Flask','of Alleviation',''},
 {'Horticultural','Prismatic Tincture','of Overpowering',''},
 {'Endless','Quicksilver Flask','of Persistence',''},
 {"Masochist's",'Diamond Flask','of Penetrating',''},
}
local tip=new('Tooltip')
local rows={}
for i,parts in ipairs(fixtures)do
 local name=parts[1]..' '..parts[2]..' '..parts[3]
 local item=new('Item','Rarity: MAGIC\n'..name..'\nQuality: 20\nItem Level: 85\n'..parts[4])
 assert(item.baseName==parts[2] and item.rarity=='MAGIC','Import failed: '..name)
 build.itemsTab:AddItem(item,true)
 build.itemsTab.slots['Flask '..i]:SetSelItemId(item.id)
 rows[i]={item=item,raw=item:BuildRaw(),zh=dict[parts[1]]..' '..dict[parts[2]]..' '..dict[parts[3]]}
end
build.itemsTab:PopulateSlots()
build.buildFlag=true
runCallback('OnFrame')
build.viewMode='ITEMS'
-- Imported anointments and the editor must retain the English parser line,
-- while every current recipe displays the reviewed notable name.
local notableCount=0
local steelwood
local anointNames=LoadModule('Localization/AnointNames')
build.itemsTab:SetDisplayItem(new('Item','Rarity: RARE\nDragon Heart\nOnyx Amulet\nItem Level: 85'))
build.itemsTab:AnointDisplayItem(1)
local anointPopup=assert(main.popups[1])
local notableDB=assert(anointPopup.controls.notableDB)
for _,node in pairs(build.spec.nodes)do
 if node.recipe and #node.recipe>=1 then
  local zh=assert(anointNames[node.dn],'Missing anoint name: '..node.dn)
  L.mode='zh'
  assert(L:Translate('Allocates '..node.dn)=='分配 '..zh,node.dn)
  assert(L:Translate('Anoint '..node.dn)=='涂油分配 '..zh,node.dn)
  assert(notableDB:GetRowValue(1,1,node):find(zh,1,true),'Notable row: '..node.dn)
  L.mode='en';assert(L:Translate('Allocates '..node.dn)=='Allocates '..node.dn)
  notableCount=notableCount+1
  if node.dn=='Steelwood Stance'then steelwood=node end
 end
end
main:ClosePopup()
assert(steelwood and notableCount>100,'Anoint recipe inventory missing')
local amulet=new('Item','Rarity: RARE\nDragon Heart\nOnyx Amulet\nItem Level: 85\nAllocates Steelwood Stance (enchant)\n+129 to maximum Life')
local amuletRaw=amulet:BuildRaw()
build.itemsTab:AddItem(amulet,true)
build.itemsTab.slots.Amulet:SetSelItemId(amulet.id)
build.itemsTab:PopulateSlots()
build.itemsTab:SetDisplayItem(amulet)
L.mode='zh'
tip:Clear();build.itemsTab:AddItemTooltip(tip,amulet,nil,true)
local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
assert(text:find('分配 身坚如铁',1,true) and not text:find('Allocates',1,true),text)
assert(build.itemsTab:getAnoint(amulet)[1]=='Steelwood Stance')
assert(amulet:BuildRaw()==amuletRaw)
local edited=build.itemsTab:anointItem(steelwood)
assert(build.itemsTab:getAnoint(edited)[1]=='Steelwood Stance')
assert(edited:BuildRaw():find('Allocates Steelwood Stance',1,true))
assert(L:Translate('(replacing ^6New Item, Onyx Amulet^7)'):find('替换',1,true))
assert(L:Translate('Socket #12')=='插槽 #12')
assert(L:Translate('^7^7Loadouts:')=='^7^7配装方案:')
assert(L:Translate('Allocates Unknown Passive')=='Allocates Unknown Passive')
assert(L:Translate('Dragon Heart')=='Dragon Heart','User rare title was changed')
build.itemsTab:SetDisplayItem()
print('All '..notableCount..' anoint recipes and imported Steelwood Stance: display, editor and raw parser lines passed')
local saved=build:SaveDB('fixture')
for _,mode in ipairs({'zh','en','zh'})do
 L.mode=mode
 for i,row in ipairs(rows)do
  tip:Clear();build.itemsTab:AddItemTooltip(tip,row.item,build.itemsTab.slots['Flask '..i])
  local title=tip.lines[1].text:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
  assert(title==(mode=='en' and row.item.name or row.zh),title)
  local slot=build.itemsTab.slots['Flask '..i]
  local label=L:Translate(slot.list[slot.selIndex])
  assert(label:find(mode=='en' and row.item.name or row.zh,1,true),label)
  assert(row.item:BuildRaw()==row.raw,'Raw item changed')
  if i==1 and mode=='zh'then
   local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
   assert(text:find('充能获取量修正',1,true),text)
   assert(not text:find('Charge gain modifier',1,true),text)
  end
 end
 assert(build:SaveDB('fixture')==saved,'Display changed saved build XML')
end
-- Unsupported calculation effects must still receive their reviewed display
-- translation, including the red colour and the unsupported-effect suffix.
local ignite='When you Kill an Ignited Enemy, inflict an equivalent Ignite on each nearby Enemy'
local shock='When you Kill a Shocked Enemy, inflict an equivalent Shock on each nearby Enemy'
for _,name in ipairs({"Abberath's Hooves", "Berek's Respite"})do
 local item
 for _,candidate in pairs(main.uniqueDB.list)do if candidate.title==name then item=candidate;break end end
 assert(item,'Missing unique fixture: '..name)
 local raw=item:BuildRaw()
 for _,mode in ipairs({'zh','en'})do
  L.mode=mode;tip:Clear();build.itemsTab:AddItemTooltip(tip,item,nil,true)
  local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
  for _,stat in ipairs(name=="Berek's Respite" and {ignite,shock} or {ignite})do
   local expected=mode=='en' and stat or dict[stat]
   assert(expected,'Reviewed translation missing: '..stat)
   assert(text:find('^xF05050'..expected,1,true),text)
   if mode=='zh'then assert(not text:find(stat,1,true),text)end
  end
  assert(text:find(mode=='en' and '(Not supported in PoB yet)' or dict['(Not supported in PoB yet)'],1,true),text)
  assert(item:BuildRaw()==raw,'Unique display changed raw data')
 end
end
local f=assert(io.open(AUDIT_SOURCE..'/Imported-Item-QA.xml','wb'));f:write(saved);f:close()
print('Five imported magic names: real parsing, equipped slots, tooltips, language switching and identical saved build XML passed')
print('Unsupported ignite/shock propagation on both unique items: translated actual tooltips, red colour, warning and raw data preservation passed')
''')
