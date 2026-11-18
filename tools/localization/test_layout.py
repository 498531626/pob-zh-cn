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
local box=new('CheckBoxControl'):CheckBoxControl(nil,{554,80,18},string.rep('中文',40))
local panel=new('SectionControl'):SectionControl(nil,{320,60,360,100},'Panel')
box:SetAnchor('TOPLEFT',panel,'TOPLEFT',234,20)
local host=new('ControlHost'):ControlHost();host.controls={box}
host:DrawControls(viewport);checkError()
assert(box.labelWidth<=234,'Checkbox hit region crossed panel border')
local label=new('LabelControl'):LabelControl({'RIGHT',box,'LEFT'},{-4,0,128,16},text)
assert(label:GetSize()<=128,'Explicit label width was ignored')
local originalBuf='Cyclone'
local editor=new('EditControl'):EditControl(nil,{400,100,90,20},originalBuf)
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
for _,screen in ipairs({{1280,720},{1920,1080},{2560,1440}}) do
 GetScreenSize=function() return unpack(screen) end
 GetVirtualScreenSize=GetScreenSize
 for _,mode in ipairs({'zh','en','zh'}) do
  L.mode=mode
  for _,page in ipairs({'TREE','SKILLS','ITEMS','CALCS','CONFIG','NOTES','PARTY','IMPORT'}) do
   build.viewMode=page
   runCallback('OnFrame');checkError()
   if page=='ITEMS' then
    local controls=build.itemsTab.controls
    assert(controls.selectDBLabel:IsShown() and controls.selectDB:IsShown(),'Item database selector hidden')
    for index,key in ipairs({'uniqueDB','rareDB','visceraDB'}) do
     controls.selectDB:SetSel(index)
     runCallback('OnFrame');checkError()
     for _,other in ipairs({'uniqueDB','rareDB','visceraDB'}) do
      assert(controls[other]:IsShown()==(other==key),'Wrong database visible: '..key..' / '..other)
     end
    end
    assert(controls.selectDB.list[3]=='Viscera','Translated database key leaked into source list')
    assert(L:Translate('Viscera')==(mode=='en' and 'Viscera' or '脏器'),'Viscera language switching failed')
    controls.selectDB:SetSel(1)
   end
  end
  for k,v in pairs(baseline) do
   assert(build.calcsTab.calcsOutput[k]==v or v~=v,'Layout changed calculation: '..k)
  end
  assert(savedSkills()==skills,'Layout changed serialized skills')
 end
end
local compareTab=build.compareTab
local compareEntry=new('CompareEntry'):CompareEntry(build:SaveDB('code'),'Comparison')
compareTab.compareEntries={compareEntry}
compareTab.activeCompareIndex=1
compareTab.compareViewMode='CALCS'
local primaryEnv=build.calcsTab.calcsEnv
local compareEnv=compareEntry.calcsTab.calcsEnv
local auras='Arcane Surge, Arctic Armour, Clarity, Discipline, Infused Channelling, Lightning Golem Wrath, Purity of Elements, Righteous Fire of Arcane Devotion, Summon Flame Golem, Summon Lightning Golem, Summon Stone Golem, Vitality'
local buffs='1 Frenzy Charges, 3 Endurance Charges, 5 Inspiration Charges'
primaryEnv.player.output.BuffList=auras
compareEnv.player.output.BuffList=auras..', Aspect of Solaris, Determination, Herald of Purity, Spectre, Wrath, Unknown Buff'
for _,env in ipairs({primaryEnv,compareEnv}) do
 env.player.output.CombatList=buffs
 env.player.output.CurseList='Temporal Chains'
end
local originalDraw=DrawString
for _,mode in ipairs({'zh','en','zh'}) do
 L.mode=mode
 local isChinese=mode=='zh'
 local headerViewport={x=0,y=0,width=620,height=540}
 local colWidth=math.floor((headerViewport.width-20)/2)
 local height=compareTab:LayoutCalcsSkillControls(headerViewport,compareEntry)
 local columns={{},{}}
 DrawString=function(x,y,align,size,font,value)
  local column=x<colWidth and 1 or 2
  local translated=L:TranslateUI(value)
  table.insert(columns[column],(translated:gsub('^%^7','')))
  if y>compareTab.controls[(column==1 and 'prim' or 'cmp')..'CalcsMode'].y+2 then
   assert(y+size<=height-2,'Comparison list overlaps the separator')
   assert(DrawStringWidth(size,font,translated)<=colWidth-8,translated)
  end
 end
 compareTab:DrawCalcsSkillHeader(headerViewport,compareEntry,height,primaryEnv,compareEnv)
 DrawString=originalDraw
 assert(L:TranslateUI(compareTab.controls.subTabSummary.label)==(isChinese and '总览' or 'Summary'))
 for _,column in ipairs(columns) do
  local drawn=table.concat(column,' ')
  for _,expected in ipairs(isChinese and {'计算模式:', '光环／增益技能: 秘术增强(辅), 极地装甲', '战斗增益: 1 狂怒能量球, 3 耐力能量球, 5 启迪球', '诅咒／减益: 时空锁链'}
    or {'Calc Mode:', 'Aura/Buff Skills: '..auras, 'Combat Buffs: '..buffs, 'Curses/Debuffs: Temporal Chains'}) do
   assert(drawn:find(expected,1,true),expected..' missing from '..drawn)
  end
  if isChinese then
   for name in auras:gmatch('[^,]+') do
    assert(not drawn:find((name:gsub('^ ','')),1,true),drawn)
   end
  end
 end
 local right=table.concat(columns[2],' ')
 assert(right:find(isChinese and '灵体, 雷霆, Unknown Buff' or 'Spectre, Wrath, Unknown Buff',1,true),right)
end
print('Compare calculator: bilingual headers and lists, unknown entries, column width and header height passed')
local function gem(name, level, quality)
 return {grantedEffect={name=name},level=level,quality=quality,color='^4'}
end
local customLabel='3 Gems are for Pob Config, You will only use 1'
local primaryGroups={
 {slot='Gloves',displayLabel='Frostblink of Wintry Blast, Temporal Chains',gemList={
  gem('Frostblink of Wintry Blast',20,0),gem('Temporal Chains',1,0),gem('Herald of Ash',20,0)}},
 {slot='Weapon 1 Swap',displayLabel='<No active skills>',gemList={gem('Enlighten',2,0)}},
}
local compareGroups={
 {slot='Helmet',displayLabel='Frostblink of Wintry Blast, Temporal Chains',gemList={
  gem('Frostblink of Wintry Blast',21,20),gem('Temporal Chains',1,0),gem('Annihilation',3,20)}},
 {slot='Boots',label=customLabel,displayLabel=customLabel,gemList={{nameSpec='Unknown Gem',level=1,quality=0}}},
}
local originalPrimaryGroups=build.skillsTab.socketGroupList
local originalCompareGroups=compareEntry.skillsTab.socketGroupList
build.skillsTab.socketGroupList=primaryGroups
compareEntry.skillsTab.socketGroupList=compareGroups
compareTab.scrollY=0
for _,mode in ipairs({'zh','en','zh'}) do
 L.mode=mode
 local isChinese=mode=='zh'
 local drawn={}
 DrawString=function(x,_,_,_,_,value) drawn[L:TranslateUI(value)]=x end
 compareTab:DrawSkills({x=0,y=0,width=1180,height=720},compareEntry)
 DrawString=originalDraw
 local function text(chinese, english)
  return isChinese and chinese or english
 end
 local common='^4'..text('冰爆之冰霜闪现','Frostblink of Wintry Blast')..'^7 '
 local left=assert(drawn[common..'20/0'],'Missing primary gem')
 local right=assert(drawn[common..'21/20'],'Missing comparison gem')
 assert(left<right,'Comparison columns are not separated')
 assert(drawn[colorCodes.POSITIVE..'+ ^4'..text('抹灭（辅）','Annihilation')..'^7 3/20']==right)
 assert(drawn[colorCodes.NEGATIVE..'- '..text('抹灭（辅）','Annihilation')..'^7']==left)
 assert(drawn[colorCodes.POSITIVE..'+ ^4'..text('灰烬之捷','Herald of Ash')..'^7 20/0']==left)
 assert(drawn[colorCodes.NEGATIVE..'- '..text('灰烬之捷','Herald of Ash')..'^7']==right)
 assert(drawn['^7'..text('冰爆之冰霜闪现, 时空锁链 (头盔)','Frostblink of Wintry Blast, Temporal Chains (Helmet)')]==right)
 assert(drawn['^7'..text('<无生效技能> (武器 1（切换）)','<No active skills> (Weapon 1 Swap)')]==left)
 assert(drawn['^7'..customLabel..text(' (鞋子)',' (Boots)')]==right)
 assert(drawn[colorCodes.POSITIVE..'+ '..colorCodes.GEM..'Unknown Gem^7 1/0']==right)
 assert(primaryGroups[2].slot=='Weapon 1 Swap' and compareGroups[2].label==customLabel)
 assert(compareGroups[1].gemList[3].grantedEffect.name=='Annihilation')
end
build.skillsTab.socketGroupList=originalPrimaryGroups
compareEntry.skillsTab.socketGroupList=originalCompareGroups
print('Compare skills: bilingual group headers, gem names, level/quality, colours, differences and unchanged source data passed')
local tooltip=new('Tooltip'):Tooltip()
L.mode='zh';tooltip:AddLine(16,text)
local width=tooltip:GetSize()
assert(width<=712,'Unbounded tooltip paragraph')
tooltip:Draw(500,200,30,20,{x=0,y=0,width=1920,height=1080});checkError()
print('Layout: '..checked..' label/width cases; Chinese wrapping, checkbox hit bounds, explicit label widths, edit isolation, 8 pages at 3 resolutions including all 3 item databases, language switching and numeric outputs passed')
''')
