"""Exercise selected gem controls and persistence in an isolated PoB copy."""
import argparse
import json
import os
from pathlib import Path
from test_locale import ROOT, run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True, type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if workspace == ROOT.resolve() or not (workspace/'src/HeadlessWrapper.lua').is_file():
        raise SystemExit('Supply a separate disposable PoB copy')
    os.chdir(workspace/'src')
    quote = lambda p: json.dumps(p.as_posix(), ensure_ascii=False)
    run('package.path='+quote(ROOT/'runtime/lua/?.lua')+'..";"..'+quote(ROOT/'runtime/lua/?/init.lua')+'..";"..package.path\n'
        +'package.cpath='+quote(ROOT/'runtime/?.dll')+'..";"..package.cpath\n'
        +'AUDIT_SOURCE='+quote(workspace/'src')+'\n'
        +'AUDIT_RUNTIME='+quote(ROOT/'runtime')+'\n'
        +'AUDIT_OUTPUT='+quote(ROOT/'tools/localization/selected-gems-audit.json')+'\n'+r'''
arg={}
local f=assert(io.open('HeadlessWrapper.lua','r'));local source=f:read('*a');f:close()
source=source:gsub('^#@','')
source=source:gsub('dofile%("Launch.lua"%)',[[
function GetScriptPath()return AUDIT_SOURCE end
function GetRuntimePath()return AUDIT_RUNTIME end
function GetUserPath()return AUDIT_SOURCE end
io.read=function()error('Unexpected startup prompt')end
-- The stock headless wrapper returns width=1 for every string. Use a
-- deterministic measurement so horizontal scrolling can be exercised.
function DrawStringWidth(height,font,text)return #StripEscapes(text)*height*0.5 end
dofile('Launch.lua')
]])
assert(loadstring(source))()
local L=Localization
local json=require('dkjson')
local names={'Static Strike','Melee Physical Damage','Ruthless','Shockwave','Fortify','Elemental Damage with Attacks'}
local expected={'充能打击','近战物理伤害(辅)','无情(辅)','震波（辅）','护体(辅)','武器元素伤害(辅)'}
newBuild()
local lines={'Slot: Weapon 1'}
for _,name in ipairs(names)do lines[#lines+1]=name..' 20/0  1' end
build.skillsTab:PasteSocketGroup(table.concat(lines,'\n')..'\n')
L.mode='en';runCallback('OnFrame')
local tab=build.skillsTab
local function saved()
 local xml={};tab:Save(xml);return json.encode(xml)
end
local baseline=saved()
local output={};for k,v in pairs(build.calcsTab.calcsOutput)do if type(v)=='number'then output[k]=v end end
local alt=false
local keyDown=IsKeyDown
IsKeyDown=function(key)if key=='ALT'then return alt end;return false end
local rawWithout=L.WithoutTranslation
local drawn={}
L.WithoutTranslation=function(self,func,...)
 if func==DrawString then drawn[#drawn+1]={x=select(1,...),text=select(6,...)} end
 return rawWithout(self,func,...)
end
local function draw(control,focused)
 control.hasFocus=focused
 drawn={};control:Draw({x=0,y=0,width=1920,height=1080},true)
 return drawn
end
local report={gems={},checks={'actual GemSelectControl Draw','inactive Chinese; focused English',
 'English/bilingual/Alt modes','English search and re-selection','scroll offset isolation',
 'skill serialization and numeric calculation outputs unchanged'}}
for i,name in ipairs(names)do
 local control=tab.gemSlots[i].nameSpec
 assert(control.translateInactive,'Gem selector did not enable inactive localization')
 assert(control.buf==name,'Fixture gem failed to resolve: '..name)
 control.IsMouseOver=function()return false end
 control.dropped=false
 control.caret=#name+1;control.sel=nil;control.blinkStart=0
 local normalWidth=control.width
 control.width=30 -- Force a valid horizontal English editing offset.
 control.controls.scrollBarH.offset=1
 local function contains(rows,text)
  for _,r in ipairs(rows)do if r.text==text then return r end end
 end
 for _,mode in ipairs({'en','zh','bilingual'})do
  L.mode=mode
  local text=mode=='en'and name or expected[i]
  local shown=assert(contains(draw(control,false),text),'Selected gem name not drawn: '..name..'/'..mode)
  if mode~='en'then assert(shown.x==0,'English scroll offset clipped Chinese name')end
  assert(control.controls.scrollBarH.offset==1,'Display changed editing scroll offset')
  assert(contains(draw(control,true),'^7'..name),'Focused gem editor lost English: '..name)
  assert(control.buf==name,'Display changed English buffer')
  assert(saved()==baseline,'Display changed serialized skills')
 end
 L.mode='zh';alt=true
 assert(contains(draw(control,false),name),'Alt failed to restore English gem name')
 alt=false
 -- Exercise the real search list and selected-gem callback with original names.
 control:UpdateSortCache();control:BuildList(name);control:SyncSelection();control:UpdateGem(false,false,false)
 assert(control.buf==name and saved()==baseline,'Search/re-selection changed skill identity')
 control.hasFocus=false
 control.width=normalWidth
 report.gems[#report.gems+1]={english=name,chinese=expected[i]}
end
L.WithoutTranslation=rawWithout;IsKeyDown=keyDown
for _,mode in ipairs({'en','zh','bilingual'})do
 L.mode=mode;build.buildFlag=true;runCallback('OnFrame')
 for k,v in pairs(output)do assert(build.calcsTab.calcsOutput[k]==v or v~=v,'Gem display changed calculation: '..k)end
 assert(saved()==baseline,'Language switch changed skill serialization')
end
local f=assert(io.open(AUDIT_OUTPUT,'wb'));f:write(json.encode(report,{indent=true}));f:close()
print('Selected gem display: 6 actual selectors; inactive/focused/3 languages/Alt/search/serialization/calculation checks passed')
''')
