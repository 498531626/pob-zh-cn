"""Check every current ascendancy source and real tooltip in an isolated copy."""
import json
import os
from pathlib import Path
import shutil
import tempfile

from test_locale import ROOT, run


def check(workspace):
    os.chdir(workspace / 'src')
    quote = lambda p: json.dumps(p.as_posix())
    run('package.path=' + quote(ROOT / 'runtime/lua/?.lua') + '..";"..'
        + quote(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n'
        + 'package.cpath=' + quote(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n'
        + 'AUDIT_SOURCE=' + quote(workspace / 'src') + '\n'
        + 'AUDIT_RUNTIME=' + quote(ROOT / 'runtime') + '\n'
        + 'AUDIT_REPORT=' + quote(ROOT / 'tools/localization/ascendancy-tooltip-audit.json') + '\n'
        + r'''
arg={}
local f=assert(io.open('HeadlessWrapper.lua','r'));local source=f:read('*a');f:close()
source=source:gsub('^#@',''):gsub('dofile%("Launch.lua"%)',function()return [[
function GetScriptPath()return AUDIT_SOURCE end
function GetRuntimePath()return AUDIT_RUNTIME end
function GetUserPath()return AUDIT_SOURCE end
io.read=function()error('Unexpected startup prompt')end
dofile('Launch.lua')
]] end)
assert(loadstring(source))()
newBuild()
local L=Localization
local json=require('dkjson')
local report={versions={},pending={}}
local function checkText(text,id,version,kind)
 local plain=text:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
 for word in plain:gmatch('%a%a+')do
  if word~='PoB' and word~='Ctrl' and word~='Shift' and word~='Alt' then
   report.pending[#report.pending+1]={version=version,node=id,kind=kind,text=text}
   return
  end
 end
end
for _,version in ipairs({'3_30','3_30_ruthless'})do
 local raw=dofile('TreeData/'..version..'/tree.lua')
 local counts={source_nodes=0,source_lines=0,tooltip_nodes=0,tooltip_lines=0}
 report.versions[version]=counts
 for id,node in pairs(raw.nodes)do
  if node.ascendancyName then
   counts.source_nodes=counts.source_nodes+1
   for _,field in ipairs({'name','stats','reminderText','flavourText'})do
    local lines=type(node[field])=='table' and node[field] or {node[field]}
    for _,text in ipairs(lines)do
     L.mode='zh';checkText(L:Translate(text,id),id,version,field)
     L.mode='en';assert(L:Translate(text,id)==text,'English source changed')
     counts.source_lines=counts.source_lines+1
    end
   end
  end
 end
 build.spec=new('PassiveSpec'):PassiveSpec(build,version)
 local viewer=build.treeTab.viewer
 viewer.showStatDifferences=false
 local tip=new('Tooltip'):Tooltip()
 for _,warnings in ipairs({false,true})do
  main.notSupportedModTooltips=warnings;main.showFlavourText=true;L.mode='zh'
  for id,node in pairs(build.spec.nodes)do
   if node.ascendancyName then
    tip:Clear();viewer:AddNodeTooltip(tip,node,build,true)
    counts.tooltip_nodes=counts.tooltip_nodes+1
    for _,line in ipairs(tip.lines)do
     if line.text then
      checkText(line.text,id,version,'tooltip')
      counts.tooltip_lines=counts.tooltip_lines+1
     end
    end
   end
  end
 end
end
report.scope='All 3.30 standard/Ruthless ascendancy sources, including bloodlines and inactive nodes; actual grouped-node tooltips with unsupported warnings on/off; English identity checked. No desktop interaction.'
f=assert(io.open(AUDIT_REPORT,'wb'));f:write(json.encode(report,{indent=true}));f:close()
assert(#report.pending==0,'Untranslated ascendancies: '..#report.pending..'; see ascendancy-tooltip-audit.json')
print('All current ascendancy source and tooltip checks passed')
''')


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='pob-ascendancy-locale-') as directory:
        workspace = Path(directory)
        shutil.copytree(ROOT / 'src', workspace / 'src',
                        ignore=shutil.ignore_patterns('Builds', 'Settings.xml', 'language.cfg', '__pycache__'))
        shutil.copy2(ROOT / 'manifest.xml', workspace / 'manifest.xml')
        try:
            check(workspace)
        finally:
            os.chdir(ROOT)
