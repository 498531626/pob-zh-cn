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

local checked=0
local tip=new('Tooltip'):Tooltip()
local originalAlt=launch.devModeAlt
local function textOf(t)
 local lines={};for _,line in ipairs(t.lines) do lines[#lines+1]=line.text or '' end
 return table.concat(lines,'\n')
end
for _,raw in ipairs(data.viscera) do
 local item=new('Item'):Item(raw)
 local before=item:BuildRaw()
 local originalName=item.name
 assert(item.baseName and item.type=='Viscera','Viscera parse failed: '..originalName)
 build.itemsTab:AddItem(item,true)
 for _,mode in ipairs({'zh','en','zh'}) do
  L.mode=mode
  local name=L:ItemListName(item)
  if mode=='zh' then assert(not name:match('%a'),'Untranslated viscera name: '..originalName)
  else assert(name==originalName,'English name changed') end
  for _,alt in ipairs({false,true}) do
   launch.devModeAlt=alt
   tip:Clear();build.itemsTab:AddItemTooltip(tip,item,nil,true)
   local title=tip.lines[1].text
   if mode=='zh' then assert(not StripEscapes(title):match('%a'),'Untranslated title: '..title) end
  end
  assert(item:BuildRaw()==before and item.name==originalName,'Display changed source item')
 end
 checked=checked+1
end
local raw='Greater Blazing Skull\nBlazing Skull\nImplicits: 1\nWhen you Kill a Rare Monster, 23% chance to gain one of its Modifiers for 10 seconds'
local item=new('Item'):Item(raw)
local before=item:BuildRaw()
for _,mode in ipairs({'zh','en','zh'}) do
 L.mode=mode;launch.devModeAlt=true
 tip:Clear();build.itemsTab:AddItemTooltip(tip,item,nil,true)
 local text=textOf(tip)
 if mode=='zh' then
  assert(text:find('高阶炽焰头骨',1,true),text)
  assert(not text:match('[Ww][Hh][Ee][Nn]'),text)
  assert(text:find('23%%') and text:find('10'),text)
  assert(text:find("^1'",1,true),'Developer diagnostic colour disappeared')
  assert(text:find('PoB',1,true),'Unsupported warning disappeared')
 else
  assert(text:find('Greater Blazing Skull',1,true),text)
  assert(text:find("^1'When you Kill a Rare Monster",1,true),text)
 end
 assert(item:BuildRaw()==before,'Diagnostic changed parsed item')
end
L.mode='zh';launch.devModeAlt=originalAlt
local upper="^xF05050When you Kill a Rare Monster, 23% chance to gain one of its Modifiers for 10 seconds   ^1'WHEN YOU KILL A RARE MONSTER, 23% CHANCE TO GAIN ONE OF ITS MODIFIERS FOR 10 SECONDS'"
assert(not L:Translate(upper):match('WHEN'),L:Translate(upper))
local unknown="^1Unknown effect   ^1'UNKNOWN EFFECT'"
assert(L:Translate(unknown)==unknown,'Unknown developer text changed')
for _,name in ipairs({'Head','Body','Arm','Leg'}) do
 local slot=assert(build.itemsTab.slots[name])
 assert(not L:Translate(slot.label..':'):match('%a'),'Untranslated slot: '..slot.label)
end
assert(L:Translate('Wickerman:')=='柳条人：')
assert(L:Translate('Viscera')=='脏器')
print('Wickerman: '..checked..' parsed parts; all tier/number names, real tooltip titles, language switching, screenshot roll/developer remainder, slot labels and raw item preservation passed')
''')
