"""Exercise bounded text and real pages in a disposable PoB copy."""
import argparse
import json
import os
from pathlib import Path
from test_locale import ROOT, run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True, type=Path)
    workspace = parser.parse_args().workspace.resolve()
    if workspace == ROOT.resolve() or not (workspace / 'src/HeadlessWrapper.lua').is_file():
        raise SystemExit('Supply a separate disposable PoB copy')
    os.chdir(workspace / 'src')
    quote = lambda path: json.dumps(path.as_posix(), ensure_ascii=False)
    run('package.path=' + quote(ROOT / 'runtime/lua/?.lua') + '..";"..'
        + quote(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n'
        + 'package.cpath=' + quote(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n'
        + 'AUDIT_SOURCE=' + quote(workspace / 'src') + '\n'
        + 'AUDIT_RUNTIME=' + quote(ROOT / 'runtime') + '\n' + r'''
arg={}
local f=assert(io.open('HeadlessWrapper.lua','r'));local source=f:read('*a');f:close()
source=source:gsub('^#@',''):gsub('dofile%("Launch.lua"%)',function() return [[
function GetScriptPath() return AUDIT_SOURCE end
function GetRuntimePath() return AUDIT_RUNTIME end
function GetUserPath() return AUDIT_SOURCE end
io.read=function() error('Unexpected startup prompt') end
function SetViewport(...)
 assert(select('#',...)==0 or type((...))=='number','Native viewport reset requires zero arguments')
end
function DrawStringWidth(height,font,text)
 return #tostring(text or ''):gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')*height*0.5
end
dofile('Launch.lua')
]] end)
assert(loadstring(source))()
local L=Localization
SetViewport(10,10,50,20);SetViewport()
newBuild()
build.skillsTab:PasteSocketGroup('Slot: Weapon 1\nCyclone 20/0  1\n')
runCallback('OnFrame')
local baseline={}
for k,v in pairs(build.calcsTab.calcsOutput) do if type(v)=='number' then baseline[k]=v end end
local function checkError()
 assert(not launch.promptMsg, launch.promptMsg)
end
local labels=LoadModule('Localization/CalcLabels')
local checked=0
for _,label in ipairs(labels) do
 for _,width in ipairs({0,1,8,20,80,128,224}) do
  local text,size=L:FitText('^xFF8800'..label..'^7:',16,'VAR',width)
  local measured=L:WithoutTranslation(DrawStringWidth,size,'VAR',text)
  assert(measured<=width+0.001,'Overflow: '..label..' / '..width..' / '..measured..' / '..text..' / '..size)
  assert(size>=10 and size<=16)
  checked=checked+1
 end
end
local text='^xFF8800'..string.rep('中文长文字',25)
for _,width in ipairs({80,240,600}) do
 for _,line in ipairs(L:WrapText(text,16,width,'VAR')) do
  assert(L:WithoutTranslation(DrawStringWidth,16,'VAR',line)<=width+0.001)
 end
end
local viewport={x=320,y=60,width=960,height=660}
local box=new('CheckBoxControl',nil,{554,80,18},string.rep('中文',40))
local panel=new('SectionControl',nil,{320,60,360,100},'Panel')
box:SetAnchor('TOPLEFT',panel,'TOPLEFT',234,20)
local host=new('ControlHost');host.controls={box}
host:DrawControls(viewport);checkError()
assert(box.labelWidth<=234,'Checkbox hit region crossed panel border')
local label=new('LabelControl',{'RIGHT',box,'LEFT'},{-4,0,128,16},text)
assert(label:GetSize()<=128,'Explicit label width was ignored')
local originalBuf='Cyclone'
local editor=new('EditControl',nil,{400,100,90,20},originalBuf)
editor:Draw(viewport,true)
assert(editor.buf==originalBuf,'Layout modified editable text')
local cursor=GetCursorPos
GetCursorPos=function() return 410,105 end
L:BoundedText(400,100,'LEFT',16,'VAR',text,40)
assert(L.overflowHint and L.overflowHint.text==text,'Elided text lost its full hover hint')
L:DrawOverflowHint(viewport);checkError()
assert(not L.overflowHint,'Hover hint persisted after drawing')
GetCursorPos=cursor
local json=require('dkjson')
local function savedSkills()
 local xml={};build.skillsTab:Save(xml);return json.encode(xml)
end
local skills=savedSkills()
for _,screen in ipairs({{1280,720},{1920,1080}}) do
 GetScreenSize=function() return unpack(screen) end
 GetVirtualScreenSize=GetScreenSize
 for _,mode in ipairs({'zh','en','zh'}) do
  L.mode=mode
  for _,page in ipairs({'TREE','SKILLS','ITEMS','CALCS','CONFIG','NOTES','PARTY','IMPORT'}) do
   build.viewMode=page
   runCallback('OnFrame');checkError()
  end
  for k,v in pairs(baseline) do
   assert(build.calcsTab.calcsOutput[k]==v or v~=v,'Layout changed calculation: '..k)
  end
  assert(savedSkills()==skills,'Layout changed serialized skills')
 end
end
local tooltip=new('Tooltip')
L.mode='zh';tooltip:AddLine(16,text)
local width=tooltip:GetSize()
assert(width<=712,'Unbounded tooltip paragraph')
tooltip:Draw(500,200,30,20,{x=0,y=0,width=1920,height=1080});checkError()
print('Layout: '..checked..' label/width cases; Chinese wrapping, checkbox hit bounds, explicit label widths, edit isolation, 8 pages at 2 resolutions, language switching and numeric outputs passed')
''')
