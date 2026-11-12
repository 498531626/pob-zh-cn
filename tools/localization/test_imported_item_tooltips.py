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
local f=assert(io.open(AUDIT_SOURCE..'/Imported-Item-QA.xml','wb'));f:write(saved);f:close()
print('Five imported magic names: real parsing, equipped slots, tooltips, language switching and identical saved build XML passed')
''')
