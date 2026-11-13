"""Audit materialized calculator tables, including runtime modifier names/tags.

Requires an explicitly supplied disposable copy; never reads user builds.
"""
import argparse
import json
import os
import hashlib
from pathlib import Path
from test_locale import ROOT, run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--inventory-only', action='store_true')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if workspace == ROOT.resolve() or not (workspace / 'src/HeadlessWrapper.lua').is_file():
        raise SystemExit('Supply a separate disposable PoB copy')
    os.chdir(workspace / 'src')
    quote = lambda path: json.dumps(path.as_posix())
    fingerprints = {name: hashlib.sha256((workspace / 'src' / name).read_bytes()).hexdigest()
                    for name in ('Modules/Localization.lua', 'Modules/CalcSections.lua',
                                 'Classes/CalcBreakdownControl.lua', 'Modules/ModParser.lua',
                                 'Localization/CalcIdentifiers.lua', 'Localization/CalcIdentifierTerms.lua')}
    run('package.path=' + quote(ROOT / 'runtime/lua/?.lua') + '..";"..'
        + quote(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n'
        + 'package.cpath=' + quote(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n'
        + 'AUDIT_SOURCE=' + quote(workspace / 'src') + '\n'
        + 'AUDIT_RUNTIME=' + quote(ROOT / 'runtime') + '\n'
        + 'AUDIT_REPORT=' + quote(ROOT / 'tools/localization/calc-breakdown-audit.json') + '\n'
        + 'AUDIT_FINGERPRINTS=require("dkjson").decode(' + json.dumps(json.dumps(fingerprints)) + ')\n'
        + 'AUDIT_STRICT=' + ('false' if args.inventory_only else 'true') + '\n' + r'''
arg={}
local observed={}
local file=assert(io.open('HeadlessWrapper.lua','r'));local source=file:read('*a');file:close()
source=source:gsub('^#@',''):gsub('dofile%("Launch.lua"%)',function()return [[
function GetScriptPath()return AUDIT_SOURCE end
function GetRuntimePath()return AUDIT_RUNTIME end
function GetUserPath()return AUDIT_SOURCE end
io.read=function()error('Unexpected startup prompt')end
local originalLoad=LoadModule
function LoadModule(name,...)
 if name=='Modules/ModParser' then
  local originalCreate=modLib.createMod
  modLib.createMod=function(...)
   local mod=originalCreate(...)
   AUDIT_OBSERVE(mod)
   return mod
  end
 end
 return originalLoad(name,...)
end
dofile('Launch.lua')
]]end)
function AUDIT_OBSERVE(mod)
 if mod.name=='' or mod.name:match('nil$')then return end
 if not observed[mod.name] then observed[mod.name]=mod end
end
assert(loadstring(source))()
local L=Localization
local rows,seen,ids,unrenderable={},{},{},{}
local function record(text,kind)
 if type(text)~='string' or seen[text] or not text:match('%a%a')then return end
 seen[text]=true
 L.mode='zh';local zh=L:Translate(text)
 L.mode='en';assert(L:Translate(text)==text,'English mode changed: '..text)
 L.mode='zh'
 local plain=zh:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
 local words={};for word in plain:gmatch('%a%a+')do
  if word~='PoB' then words[#words+1]=word end
 end
 rows[#rows+1]={english=text,chinese=zh,kind=kind,remaining=words}
end
local function scan(t,kind,visited)
 if type(t)~='table' or visited[t]then return end;visited[t]=true
 for key,value in pairs(t)do
  if type(value)=='table' and key~='mod' then scan(value,kind,visited)
  elseif key=='sourceTooltip' and type(value)=='function' then
   L.mode='en';local tip=new('Tooltip');value(tip);L.mode='zh'
   for _,line in ipairs(tip.lines)do record(line.text,kind..' source tooltip')end
  elseif type(value)=='string' and (type(key)=='number' or key=='label' or key=='footer'
   or key=='name' or key=='source' or key=='sourceName' or key=='flags' or key=='tags' or key=='displayValue')then
   record(value,kind)
  end
 end
end
local numericChecks=0
for _,skill in ipairs({'Fireball','Arc','Cyclone','Puncture','Poisonous Concoction','Raise Zombie',
 'Storm Brand','Righteous Fire','Blade Vortex','Summon Stone Golem','Summon Holy Relic','Shockwave Totem'})do
 newBuild()
 build.skillsTab:PasteSocketGroup('Slot: Weapon 1\n'..skill..' 20/0  1\n')
 L.mode='en';runCallback('OnFrame')
 local baseline={};for key,value in pairs(build.calcsTab.calcsOutput)do if type(value)=='number'then baseline[key]=value end end
 for _,mode in ipairs({'zh','en'})do
  L.mode=mode;build.buildFlag=true;runCallback('OnFrame')
  for key,value in pairs(baseline)do
   assert(build.calcsTab.calcsOutput[key]==value or value~=value,'Calculation changed: '..skill..'/'..key)
   numericChecks=numericChecks+1
  end
 end
 L.mode='zh'
 local control=build.calcsTab.controls.breakdown
 local function sections(t)
  for key,value in pairs(t)do
   if key=='modName'then
    for _,id in ipairs(type(value)=='table'and value or{value})do ids[id]=true end
   elseif type(value)=='table'then sections(value)end
  end
 end
 sections(LoadModule('Modules/CalcSections'))
 -- Exercise every configured breakdown regardless of whether its UI is visible.
 local function materialize(t)
  if t.modName or t.breakdown then
   control.sectionList={}
   if t.modName then control:AddModSection(t)else control:AddBreakdownSection(t)end
   scan(control.sectionList,'materialized '..skill,{})
  end
  for _,v in pairs(t)do if type(v)=='table'then materialize(v)end end
 end
 materialize(LoadModule('Modules/CalcSections'))
end
-- Static schema keys are exercised even if the selected builds have no such
-- modifier. Runtime constructors also expose dynamic IDs absent from literals.
local control=build.calcsTab.controls.breakdown
for id in pairs(observed)do ids[id]=true end
local sorted={};for id in pairs(ids)do sorted[#sorted+1]=id end;table.sort(sorted)
for _,id in ipairs(sorted)do
 record(control:FormatModName(id),'identifier')
 local mod=observed[id]
 if mod then
  -- Use real tags/flags but a base source, so this test does not invent item IDs.
  mod=copyTable(mod,true);mod.source='Base'
  if mod.type=='BASE' or mod.type=='INC' or mod.type=='MORE' or mod.type=='FLAG' then
   control.sectionList={}
   local ok,err=pcall(control.AddModSection,control,{modName={id}},{{mod=mod,value=mod.value}})
   if ok then scan(control.sectionList,'runtime modifier',{})
   else unrenderable[#unrenderable+1]={id=id,reason=err}end
   assert(mod.name==id,'Display changed internal identifier')
  end
 end
end
-- Source totals append stat names after numeric/boolean values. These tooltip
-- closures are another display path, distinct from the table's Stat column.
local originalActor=control.calcsTab.calcsEnv.player
local originalMinion=control.calcsTab.input.showMinion
control.calcsTab.input.showMinion=false
for _,id in ipairs(sorted)do
 local db=new('ModDB')
 db:AddMod(modLib.createMod(id,'BASE',1,'Base'))
 control.calcsTab.calcsEnv.player={mainSkill={},modDB=db}
 control.sectionList={}
 control:AddModSection({modName={id}})
 scan(control.sectionList,'schema source totals',{})
end
control.calcsTab.calcsEnv.player=originalActor
control.calcsTab.input.showMinion=originalMinion
table.sort(rows,function(a,b)return a.english<b.english end)
local pending={};for _,row in ipairs(rows)do if #row.remaining>0 then pending[#pending+1]=row end end
local report={identifiers=sorted,observed_modifiers=0,texts=#rows,numeric_comparisons=numericChecks,source_sha256=AUDIT_FINGERPRINTS,
 rows=rows,pending=pending,unresolved_constructor_templates=unrenderable,
 scope='All evaluated CalcSections keys, every table from 12 skill fixtures, startup/runtime modifier constructors and their renderable notes/flags; unresolved pre-calculation constructor templates listed separately; no user builds.'}
for _ in pairs(observed)do report.observed_modifiers=report.observed_modifiers+1 end
file=assert(io.open(AUDIT_REPORT,'wb'));file:write(require('dkjson').encode(report,{indent=true}));file:close()
file=assert(io.open(AUDIT_REPORT:gsub('calc%-breakdown%-audit','calc-runtime-identifiers'),'wb'))
file:write(require('dkjson').encode(sorted,{indent=true}));file:close()
print('Materialized calculation audit: '..#sorted..' identifiers; '..#rows..' strings; '..#pending..' pending; '..numericChecks..' numeric comparisons')
assert(not AUDIT_STRICT or #pending==0,'Untranslated materialized calculator text; see calc-breakdown-audit.json')
''')
    for name in ('calc-breakdown-audit.json', 'calc-runtime-identifiers.json'):
        path = ROOT / 'tools/localization' / name
        path.write_text(json.dumps(json.loads(path.read_text('utf8')), ensure_ascii=False,
                                   sort_keys=True, indent=2) + '\n', 'utf8')
