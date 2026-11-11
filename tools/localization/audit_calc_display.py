"""Audit actual calculator breakdowns in an explicitly supplied disposable copy.

Usage: python audit_calc_display.py --workspace E:/POB/Localization-QA
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
    parser.add_argument('--passives', action='store_true', help='Also exercise all current passive tooltips, with stat comparisons off')
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
        +'AUDIT_OUTPUT='+path(ROOT/'tools/localization/calculation-display-audit.json')+'\n'
        +'AUDIT_PENDING='+path(ROOT/'tools/localization/calculation-display-pending.json')+'\n'+r'''
AUDIT_PASSIVES=__PASSIVES__
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
local rows,seen={},{}
local function scan(t,skill,visited)
 if type(t)~='table' or visited[t]then return end
 visited[t]=true
 for key,value in pairs(t)do
  if type(value)=='table'then scan(value,skill,visited)
  elseif type(value)=='string' and (type(key)=='number' or key=='label' or key=='footer') and value:match('%a%a') and not seen[value]then
   seen[value]=true;rows[#rows+1]={english=value,chinese=L:Translate(value),skill=skill}
  end
 end
end
for _,skill in ipairs({'Fireball','Arc','Cyclone','Puncture','Poisonous Concoction','Raise Zombie','Storm Brand','Righteous Fire','Blade Vortex','Summon Stone Golem'})do
 newBuild()
 build.skillsTab:PasteSocketGroup('Slot: Weapon 1\n'..skill..' 20/0  1\n')
 L.mode='en';runCallback('OnFrame')
 local baseline={}
 for key,value in pairs(build.calcsTab.calcsOutput)do if type(value)=='number'then baseline[key]=value end end
 for _,mode in ipairs({'zh','bilingual'})do
  L.mode=mode;build.buildFlag=true;runCallback('OnFrame')
  for key,value in pairs(baseline)do assert(build.calcsTab.calcsOutput[key]==value or value~=value,'Calculation changed with language: '..skill..'/'..key)end
 end
 L.mode='zh'
 scan(build.calcsTab.calcsEnv.player.breakdown,skill,{})
 if build.calcsTab.calcsEnv.minion then scan(build.calcsTab.calcsEnv.minion.breakdown,skill,{})end
end
table.sort(rows,function(a,b)return a.english<b.english end)
local pending={}
for _,row in ipairs(rows)do
 local plain=row.chinese:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
 local words={}
 for word in plain:gmatch('%a%a+')do if word~='PoB'then words[#words+1]=word end end
 if #words>0 then row.remaining_english_words=words;pending[#pending+1]=row end
end
f=assert(io.open(AUDIT_OUTPUT,'wb'));f:write(json.encode(rows,{indent=true}));f:close()
f=assert(io.open(AUDIT_PENDING,'wb'));f:write(json.encode(pending,{indent=true}));f:close()
print('Actual calculator breakdown audit: '..#rows..' unique strings; remaining English: '..#pending..'; numerical outputs identical in all three languages')
assert(#pending==0,'Untranslated calculation display text; see calculation-display-pending.json')
if AUDIT_PASSIVES then
 newBuild();L.mode='zh';main.notSupportedModTooltips=true;main.showFlavourText=true
 local viewer=build.treeTab.viewer;viewer.showStatDifferences=false
 local tip=new('Tooltip')
 local unresolved,seen={},{}
 local count,redCount=0,0
 local redSamples={}
 for id,node in pairs(build.spec.nodes)do
  if node.dn and node.type~='ClassStart' then
   tip:Clear();viewer:AddNodeTooltip(tip,node,build);count=count+1
   for _,line in ipairs(tip.lines)do
    local text=line.text or ''
    if text:sub(1,#colorCodes.UNSUPPORTED)==colorCodes.UNSUPPORTED and text:find('[\128-\255]')then
     redCount=redCount+1
     if #redSamples<10 then redSamples[#redSamples+1]={node=id,name=node.dn,text=text}end
    end
    local plain=text:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
    local english=false
    for word in plain:gmatch('%a%a+')do if word~='PoB' and word~='Ctrl' and word~='Shift' and word~='Alt' then english=true end end
    if english and not seen[text]then
     seen[text]=true;unresolved[#unresolved+1]={node=id,name=node.dn,text=text}
    end
   end
  end
 end
 table.sort(unresolved,function(a,b)return a.text<b.text end)
 local report={nodes=count,red_lines=redCount,red_samples=redSamples,pending=unresolved,scope='Actual current-tree tooltips; flavour and unsupported warnings on; stat comparisons off'}
 f=assert(io.open(AUDIT_OUTPUT:gsub('calculation%-display%-audit','passive-tooltip-audit'),'wb'));f:write(json.encode(report,{indent=true}));f:close()
 print('Actual passive tooltips: '..count..' nodes; Chinese red lines: '..redCount..'; pending English: '..#unresolved)
 assert(#unresolved==0,'Untranslated passive tooltip; see passive-tooltip-audit.json')
end
'''.replace('__PASSIVES__', 'true' if args.passives else 'false'))
