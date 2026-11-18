"""Exercise real gem search controls in an explicit disposable PoB copy."""
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
quote = lambda p: json.dumps(p.as_posix())
run('package.path=' + quote(ROOT / 'runtime/lua/?.lua') + '..";"..' +
    quote(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n' +
    'package.cpath=' + quote(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n' +
    'AUDIT_SOURCE=' + quote(workspace / 'src') + '\n' +
    'AUDIT_RUNTIME=' + quote(ROOT / 'runtime') + '\n' + r'''
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
local function contains(control,name)
 for _,id in ipairs(control.list)do
  if control.gems[id] and control.gems[id].name==name then return true end
 end
 return false
end
for _,mode in ipairs({'zh','en'})do
 newBuild();Localization.mode=mode;main.unicode=true
 build.skillsTab:PasteSocketGroup('Fireball 20/0  1')
 build.viewMode='SKILLS';runCallback('OnFrame')
 local control=build.skillsTab.gemSlots[1].nameSpec
 control:OnFocusGained();control:SetText('');control.caret=1
 control:OnChar('召');control:OnChar('唤')
 assert(control.buf=='召唤','Chinese input was filtered: '..control.buf)
 assert(contains(control,'Summon Lightning Golem'),'Chinese partial search missing golem')
 control:OnKeyDown('BACK');assert(control.buf=='召','Backspace split UTF-8')
 control:OnChar('唤闪电魔像')
 assert(control.buf=='召唤闪电魔像' and contains(control,'Summon Lightning Golem'))
 control:OnKeyDown('RETURN')
 local gem=build.skillsTab.displayGroup.gemList[1]
 assert(gem.gemData.name=='Summon Lightning Golem' and gem.nameSpec=='Summon Lightning Golem')
 local selectedId=gem.gemId
 local saved=build:SaveDB('fixture')
 assert(not saved:find('召唤闪电魔像',1,true),'Chinese search leaked into save')
 -- Paste through the real shortcut, then select with the normal Return path.
 control:OnFocusGained();control:SelectAll()
 local oldPaste,oldKey=Paste,IsKeyDown
 Paste=function()return '物理转闪电' end
 IsKeyDown=function(key)return key=='CTRL' end
 control:OnKeyDown('v');Paste,IsKeyDown=oldPaste,oldKey
 assert(control.buf=='物理转闪电' and contains(control,'Physical to Lightning'),control.buf..' / '..table.concat(control.list,','))
 control:OnKeyDown('RETURN')
 assert(build.skillsTab.displayGroup.gemList[1].gemData.name=='Physical to Lightning')
 for _,case in ipairs({
  {'火球','Fireball'}, {'FIREBALL','Fireball'},
  {'CtF','Cold to Fire'}, {'物理转闪电:lightning','Physical to Lightning'},
  {':active:fire','Fireball'},
 })do
  control:BuildList(case[1]);assert(contains(control,case[2]),case[1]..' => '..case[2])
 end
 control:BuildList('物理转闪电:-lightning')
 assert(not contains(control,'Physical to Lightning'),'Negated tag was ignored')
 control:BuildList('不存在的技能');assert(control.noMatches)
 control:BuildList('');assert(not control.noMatches)
 -- The imbued-support selector shares the search implementation and keeps
 -- its existing support-only eligibility rules.
 local imbued=build.skillsTab.controls.imbuedSupport
 imbued:UpdateSortCache();imbued:PopulateGemList();imbued:BuildList('物理转闪电')
 assert(contains(imbued,'Physical to Lightning'),'Imbued Chinese search failed')
 imbued:BuildList('火球');assert(not contains(imbued,'Fireball'))
 assert(Localization.mode==mode and Localization.suspended==0)
 assert(build.data.gems[selectedId].name=='Summon Lightning Golem','Internal gem name changed')
end
print('Gem search: Chinese input/paste/delete, partial/full names, Return selection, canonical save, English/abbreviations/tags and imbued support filtering passed in both languages')
''')
