"""Verify the real crafting popup and saved items in a disposable PoB copy."""
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
quote = lambda p: json.dumps(p.as_posix(), ensure_ascii=False)
run('package.path=' + quote(ROOT / 'runtime/lua/?.lua') + '..";"..'
    + quote(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n'
    + 'package.cpath=' + quote(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n'
    + 'AUDIT_SOURCE=' + quote(workspace / 'src') + '\n'
    + 'AUDIT_RUNTIME=' + quote(ROOT / 'runtime') + '\n' + r'''
arg={}
local f=assert(io.open('HeadlessWrapper.lua'));local source=f:read('*a');f:close()
source=source:gsub('^#@',''):gsub('dofile%("Launch.lua"%)',[[
function GetScriptPath()return AUDIT_SOURCE end
function GetRuntimePath()return AUDIT_RUNTIME end
function GetUserPath()return AUDIT_SOURCE end
io.read=function()error('Unexpected startup prompt')end
dofile('Launch.lua')
]])
assert(loadstring(source))()
newBuild()
build.viewMode='ITEMS'
local tab=build.itemsTab
tab:SetDisplayItem(new('Item','Rarity: RARE\nDragon Heart\nOnyx Amulet\nItem Level: 85'))
tab:AddCustomModifierToDisplayItem()
local popup=assert(main.popups[1])
local controls=popup.controls
for i,row in ipairs(controls.source.list)do if row.sourceId=='VEILED'then controls.source:SetSel(i);break end end
assert(controls.source.list[controls.source.selIndex].sourceId=='VEILED')
local selected
local count=0
for i,row in ipairs(controls.modSelect.list)do
 local original=row.label
 Localization.mode='zh'
 local zh=Localization:Translate(original)
 assert(not zh:find('%a%a+'),'Actual popup untranslated: '..original..' => '..zh)
 Localization.mode='en';assert(Localization:Translate(original)==original)
 assert(row.label==original,'Dropdown label mutated')
 if original:find('Damage taken Recouped as Mana',1,true)then selected=i end
 count=count+1
end
assert(selected and count>20,'Screenshot fixture not available')
controls.modSelect:SetSel(selected)
local selectedMod=controls.modSelect.list[selected].mod
local expected={};for _,line in ipairs(selectedMod)do expected[#expected+1]=line end
controls.save:Click()
local item=tab.displayItem
assert(#item.explicitModLines==#expected,'Selected modifier was not added')
for i,line in ipairs(expected)do assert(item.explicitModLines[i].line==line,'Parser received translated text')end
local raw=item:BuildRaw()
assert(not raw:find('[\128-\255]'),'Translated text leaked into raw item')
tab:AddItem(item,true)
tab.slots.Amulet:SetSelItemId(item.id)
tab:PopulateSlots();build.buildFlag=true;runCallback('OnFrame')
local baseline={}
for k,v in pairs(build.calcsTab.calcsOutput)do if type(v)=='number'then baseline[k]=v end end
local saved=build:SaveDB('crafting-fixture')
for _,mode in ipairs({'zh','en','zh'})do
 Localization.mode=mode
 tab:AddCustomModifierToDisplayItem()
 runCallback('OnFrame')
 assert(not launch.promptMsg,launch.promptMsg)
 main:ClosePopup()
 assert(item:BuildRaw()==raw,'Language changed raw item')
 assert(build:SaveDB('crafting-fixture')==saved,'Language changed saved build XML')
 for k,v in pairs(baseline)do assert(build.calcsTab.calcsOutput[k]==v or v~=v,'Language changed calculation: '..k)end
end
print('Actual veiled popup: '..count..' translated rows; selection adds original English parser lines; raw item, saved XML and calculated numbers unchanged across zh/en/zh')
''')
