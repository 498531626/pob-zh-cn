"""Check sidebar breakdown actor transitions in an explicit disposable copy."""
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
local function selectSkill(index)
 build.mainSocketGroup=index;build.buildFlag=true;runCallback('OnFrame')
end
local function minionHover()
 for _,line in ipairs(build.controls.statBox.list)do
  if line.actorName=='minion' and line.breakdown then
   build:SetDisplayStat({line=line,x=0,y=0,width=300},false)
   if build.controls.breakdown.shown then
    build:ClearDisplayStat()
    return {line=line,x=0,y=0,width=300}
   end
  end
 end
 error('No visible minion breakdown fixture')
end
for _,mode in ipairs({'zh','en'})do
 Localization.mode=mode
 newBuild()
 build.skillsTab:PasteSocketGroup('Raise Zombie 20/0  1')
 build.skillsTab:PasteSocketGroup('Fireball 20/0  1')
 selectSkill(1)
 assert(build.calcsTab.mainEnv.minion,'Minion fixture missing')
 local hover=minionHover()
 selectSkill(2)
 assert(not build.calcsTab.mainEnv.minion,'Minion did not disappear')
 -- The old row survives until the sidebar processes the next frame.
 build:SetDisplayStat(hover,false)
 assert(not build.controls.breakdown.shown and not build.breakdownInputs)
 -- The same stat can open again after a minion is selected again.
 selectSkill(1)
 build:SetDisplayStat(hover,true)
 assert(build.controls.breakdown.shown and build.controls.breakdown.pinned)
 selectSkill(2)
 assert(not build.controls.breakdown.shown and not build.controls.breakdown.pinned)
 assert(not build.breakdownInputs and not build.sidebarBreakdownData)
 runCallback('OnFrame')
 -- A normal player breakdown remains available after clearing the minion.
 local shown=false
 for _,line in ipairs(build.controls.statBox.list)do
  if line.actorName=='player' and line.breakdown then
   build:SetDisplayStat({line=line,x=0,y=0,width=300},false)
   if build.controls.breakdown.shown then shown=true;break end
  end
 end
 assert(shown,'Player breakdown did not recover')
 build:ClearDisplayStat()
 -- An environment that is not yet available must also clear its selection.
 local pane=build.calcsTab.controls.breakdown
 local env=build.calcsTab.calcsEnv
 build.calcsTab.calcsEnv=nil
 pane:SetBreakdownData({{breakdown='Life'}},true)
 assert(not pane.shown and not pane.sourceData and not pane.pinned)
 build.calcsTab.calcsEnv=env
end
print('Breakdown lifecycle: stale hover, pinned minion removal, retry, player recovery and unavailable environment passed in Chinese and English')
''')
