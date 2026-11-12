"""Check real skill-part selectors in a separate disposable PoB copy."""
import argparse
import json
import os
from pathlib import Path
from test_locale import ROOT, run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--fixture', action='store_true', help='Save a UI fixture inside the disposable copy')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if workspace == ROOT.resolve() or not (workspace / 'src/HeadlessWrapper.lua').is_file():
        raise SystemExit('Supply a separate disposable PoB copy')
    if args.fixture:
        (workspace / 'src/Builds').mkdir(exist_ok=True)
    os.chdir(workspace / 'src')
    quote = lambda p: json.dumps(p.as_posix(), ensure_ascii=False)
    run('package.path=' + quote(ROOT / 'runtime/lua/?.lua') + '..";"..'
        + quote(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n'
        + 'package.cpath=' + quote(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n'
        + 'AUDIT_SOURCE=' + quote(workspace / 'src') + '\n'
        + 'AUDIT_RUNTIME=' + quote(ROOT / 'runtime') + '\n'
        + 'WRITE_FIXTURE=' + ('true' if args.fixture else 'false') + '\n' + r'''
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
newBuild()
build.itemsTab:AddItem(new('Item','Rarity: NORMAL\nRusted Sword\n'))
build.skillsTab:PasteSocketGroup('Slot: Weapon 1\nFrost Blades 20/0  1\n')
build.viewMode='CALCS';runCallback('OnFrame')
local L=Localization
local controls={build.controls.mainSkillPart}
for _,section in ipairs(build.calcsTab.sectionList) do
 if section.controls.mainSkillPart then controls[#controls+1]=section.controls.mainSkillPart end
end
assert(#controls==2,'Expected sidebar and calculator skill-part selectors')
local expected={'近战击中','寒冰刀刃'}
local raw={'Melee hit','Icy blades'}
local rendered={}
local draw=DrawString
DrawString=function(x,y,align,height,font,text)
 rendered[#rendered+1]=L:TranslateUI(text)
 return draw(x,y,align,height,font,text)
end
local function snapshot()
 return build:SaveDB('skill-parts-audit')
end
for _,control in ipairs(controls) do
 assert(#control.list==2)
 for i,row in ipairs(control.list) do assert(row.val==i and row.label==raw[i]) end
 control.IsMouseOver=function()return false end
 for index=1,2 do
  control:SetSel(index);build.buildFlag=true;runCallback('OnFrame')
  assert(control.selIndex==index,'Skill-part selection was lost')
  local field=control==controls[1] and 'skillPart' or 'skillPartCalcs'
  assert(build.skillsTab.socketGroupList[1].gemList[1][field]==index,'Wrong stored skill-part index')
  local saved=snapshot()
  local baseline={}
  for key,value in pairs(build.calcsTab.calcsOutput) do
   if type(value)=='number' then baseline[key]=value end
  end
  for _,mode in ipairs({'en','zh'}) do
   L.mode=mode;build.buildFlag=true;runCallback('OnFrame')
   for key,value in pairs(baseline) do
    assert(build.calcsTab.calcsOutput[key]==value or value~=value,'Calculation changed: '..key)
   end
   assert(snapshot()==saved,'Language changed serialized build')
   for _,dropped in ipairs({false,true}) do
    rendered={};control.dropped=dropped
    control:Draw({x=0,y=0,width=1920,height=1080},true)
    local seen={};for _,text in ipairs(rendered) do seen[text]=true end
    assert(seen[mode=='zh' and expected[index] or raw[index]],'Selected label was not rendered: '..mode..'/'..index..'/'..tostring(dropped)..'/'..table.concat(rendered,'|'))
    if dropped then
     for i=1,2 do assert(seen[mode=='zh' and expected[i] or raw[i]],'Dropdown row was not rendered') end
    end
    for i,row in ipairs(control.list) do assert(row.val==i and row.label==raw[i]) end
   end
   control.dropped=false
  end
 end
end
DrawString=draw
assert(build.data.skills.FrostBlades.parts[1].name==raw[1])
assert(build.data.skills.FrostBlades.parts[2].name==raw[2])
if WRITE_FIXTURE then
 L.mode='zh'
 local f=assert(io.open(AUDIT_SOURCE..'/Builds/skill-parts.xml','wb'))
 f:write(snapshot());f:close()
end
print('Skill parts: both real selectors, both parts, closed/open drawing and English/Chinese passed; raw labels, indices, saved build and calculation values preserved')
''')
