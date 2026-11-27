"""Exercise parsed imported items in a disposable PoB copy, never user builds."""
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
local fixtures={
 {'Endless','Silver Flask','of the Pangolin','30% increased Charge Recovery\n53% increased Armour during Effect'},
 {'Alarmed','Divine Life Flask','of Alleviation',''},
 {'Horticultural','Prismatic Tincture','of Overpowering',''},
 {'Endless','Quicksilver Flask','of Persistence',''},
 {"Masochist's",'Diamond Flask','of Penetrating',''},
}
local tip=new('Tooltip'):Tooltip()
local rows={}
-- Exercise the complete keyed cluster inventory, then the actual imported
-- jewel from the report, including its appended notable descriptions.
local clusterData=LoadModule('Data/ClusterJewels')
local clusterCount=0
for name in pairs(clusterData.notableSortOrder)do
 clusterCount=clusterCount+1
 for _,mode in ipairs({'zh','en','zh'})do
  L.mode=mode
  for _,count in ipairs({'1','2','#'})do
   local line=count..' Added Passive Skill is '..name
   local display=L:Translate('^x8888FF'..line)
   if mode=='en' then
    assert(display=='^x8888FF'..line,'Cluster English text changed: '..name)
   else
    assert(not display:sub(9):match('%a'),'Untranslated cluster clause: '..line)
    assert(display:sub(1,8)=='^x8888FF' and display:sub(9,9)==count,'Cluster count/colour changed')
    assert(L:Translate(name)~=name,'Missing standalone cluster name: '..name)
   end
  end
 end
end
assert(clusterCount>=300,'Cluster notable inventory missing')
local clusterItem=new('Item'):Item([[Rarity: RARE
Rapture Glisten
Large Cluster Jewel
Item Level: 75
Adds 8 Passive Skills (enchant)
2 Added Passive Skills are Jewel Sockets (enchant)
Added Small Passive Skills grant: 12% increased Lightning Damage (enchant)
Added Small Passive Skills also grant: Regenerate 0.15% of Life per Second
1 Added Passive Skill is Overshock
1 Added Passive Skill is Prismatic Heart
1 Added Passive Skill is Widespread Destruction]])
assert(clusterItem.clusterJewel and #clusterItem.jewelData.clusterJewelNotables==3,'Cluster import failed')
local clusterRaw=clusterItem:BuildRaw()
local clusterSaved=build:SaveDB('fixture')
for _,mode in ipairs({'zh','en','zh'})do
 L.mode=mode;tip:Clear();build.itemsTab:AddItemTooltip(tip,clusterItem,nil,true)
 local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
 assert(text:find(mode=='en' and 'Rapture Glisten' or '狂喜之辉',1,true),text)
 for _,name in ipairs({'Overshock','Prismatic Heart','Widespread Destruction'})do
  local label=mode=='en' and name or dict[name]
  assert(text:find((mode=='en' and '1 Added Passive Skill is ' or '1 个增加的天赋为')..label,1,true),text)
  assert(text:find(label..'\n',1,true),'Appended cluster title missing: '..name)
  if mode=='zh' then assert(not text:find(name,1,true),text)end
 end
 assert(clusterItem:BuildRaw()==clusterRaw and build:SaveDB('fixture')==clusterSaved,'Cluster display changed saved data')
end
assert(L:Translate('1 Added Passive Skill is Unknown Passive')=='1 Added Passive Skill is Unknown Passive')
print('All '..clusterCount..' cluster notable names/clauses and imported Rapture Glisten tooltip: colours, counts, language switching and raw data passed')
-- Check every live cluster notable/keystone, including effects and reminder
-- text. Runtime subgraph nodes use generated IDs, so also test context-free
-- translation rather than only the original tree node ID.
local json=require('dkjson')
local function plain(text)return text:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')end
local function contains(text,part)
 return plain(text):gsub('%s',''):find(plain(part):gsub('%s',''),1,true)
end
local function numbers(text)
 local normalized=plain(text):gsub('%f[%a]six%f[%A]','6'):gsub('六','6')
 local result={};for n in normalized:gmatch('[%+%-]?%d+%.?%d*')do result[#result+1]=tonumber(n)end
 table.sort(result);return table.concat(result,',')
end
local function tooltipText()
 local result={};for _,line in ipairs(tip.lines)do result[#result+1]=line.text or ''end
 return table.concat(result,'\n')
end
local effectCount,reminderCount,nodeCount=0,0,0
local treeView=build.treeTab.viewer
for name,node in pairs(build.spec.tree.clusterNodeMap)do
 nodeCount=nodeCount+1
 local original=json.encode({name=node.dn,sd=node.sd,reminders=node.reminderText,mods=node.mods})
 for _,mode in ipairs({'zh','en','zh'})do
  L.mode=mode;tip:Clear();treeView:AddNodeTooltip(tip,node,build,true)
  local text=tooltipText()
  for _,field in ipairs({'sd','reminderText'})do
   for _,en in ipairs(node[field]or{})do
    local translated=L:Translate(en)
    assert(L:Translate('^x8888FF'..en)=='^x8888FF'..translated,'Cluster colour changed: '..en)
    if mode=='zh' then
     assert(not plain(translated):match('%a%a'),'Untranslated cluster effect: '..name..': '..en..' => '..translated)
     assert(numbers(en)==numbers(translated),'Cluster numeric change: '..name..': '..en)
     assert(L:Translate(en,node.id)==translated,'Cluster context differs from generated node: '..en)
    else assert(translated==en,'English cluster effect changed: '..en)end
    if field=='reminderText'then assert(contains(text,translated),'Cluster tooltip omitted reminder: '..name..': '..en..'\n'..text)end
   end
  end
  for _,group in ipairs(L:PassiveLineGroups(node.id,node.sd))do
   local expected=L:Translate(group.text,node.id)
   assert(contains(text,expected),'Cluster tooltip omitted effect group: '..name..': '..group.text..'\n'..text)
  end
 end
 effectCount=effectCount+#node.sd;reminderCount=reminderCount+#(node.reminderText or{})
 assert(json.encode({name=node.dn,sd=node.sd,reminders=node.reminderText,mods=node.mods})==original,'Cluster parser data changed')
end
-- Reproduce the equipped socket tooltip, then inspect every generated node
-- in the 8-passive subgraph. This is the actual tree hover path in the report.
local equippedCluster=new('Item'):Item([[Rarity: RARE
8 Passive Only! Not 9!
Large Cluster Jewel
Item Level: 75
Adds 8 Passive Skills (enchant)
2 Added Passive Skills are Jewel Sockets (enchant)
Added Small Passive Skills grant: 10% increased Spell Damage (enchant)
1 Added Passive Skill is Arcane Adept
1 Added Passive Skill is Burden Projection
1 Added Passive Skill is Essence Rush]])
local outerSocket
for id in pairs(build.spec.tree.sockets)do
 local node=build.spec.nodes[id]
 if node and node.expansionJewel and node.expansionJewel.size==2 then outerSocket=node;break end
end
assert(outerSocket,'No outer cluster socket')
build.itemsTab:AddItem(equippedCluster,true)
build.spec:AllocNode(outerSocket)
build.spec.jewels[outerSocket.id]=equippedCluster.id
build.spec:BuildClusterJewelGraphs()
build.itemsTab:PopulateSlots()
build.buildFlag=true;runCallback('OnFrame')
local equippedRaw=equippedCluster:BuildRaw()
local equippedSaved=build:SaveDB('fixture')
local outputLife=build.calcsTab.mainOutput.Life
local screenshotStats={
 {'5% increased Attack and Cast Speed while Channelling','持续吟唱时，攻击和施法速度加快 5%'},
 {'Gain Arcane Surge after Channelling for 1 second','吟唱 1 秒后，获得秘术增强'},
 {'8% chance to Knock Enemies Back on Hit with Spell Damage','法术伤害击中有 8% 的几率击退敌人'},
 {'40% increased Damage while Leeching Energy Shield','偷取能量护盾时，伤害提高 40%'},
 {'5% increased Attack and Cast Speed while Leeching Energy Shield','偷取能量护盾时攻击和施法速度加快 5%'},
}
for _,mode in ipairs({'zh','en','zh'})do
 L.mode=mode;tip:Clear();treeView:AddNodeTooltip(tip,outerSocket,build)
 local text=tooltipText()
 for _,row in ipairs(screenshotStats)do
  local expected=mode=='en' and row[1]or L:Translate(row[1])
  assert(contains(text,expected),'Equipped socket missing: '..row[1]..'\n'..text)
  if mode=='zh'then
   assert(not text:find(row[1],1,true),'Equipped socket English leak: '..row[1])
   if row[2]~=''then assert(expected==row[2],expected)end
  end
 end
 local notableSeen={}
 for _,graph in pairs(build.spec.subGraphs)do
  for _,node in ipairs(graph.nodes)do
   if node.type=='Notable'then notableSeen[node.dn]=true end
   if node.type~='Socket'and node.type~='Mastery'then
    tip:Clear();treeView:AddNodeTooltip(tip,node,build,true)
    local rendered=tooltipText()
    for _,stat in ipairs(node.sd)do
     local expected=L:Translate(stat)
     assert(contains(rendered,expected),'Generated cluster node missing: '..stat)
     if mode=='zh'then assert(not plain(expected):match('%a%a'),'Generated cluster node untranslated: '..stat)end
    end
   end
  end
 end
 for _,name in ipairs({'Arcane Adept','Burden Projection','Essence Rush'})do assert(notableSeen[name],'Equipped graph missing notable: '..name)end
 assert(equippedCluster:BuildRaw()==equippedRaw and build:SaveDB('fixture')==equippedSaved,'Equipped cluster display changed saved data')
 assert(build.calcsTab.mainOutput.Life==outputLife,'Equipped cluster display changed calculation output')
end
print('Cluster effects: '..nodeCount..' live nodes, '..effectCount..' effect occurrences, '..reminderCount..' reminders; actual equipped socket/generated node tooltips, language switching, numbers and unchanged raw/mod/save data passed')
-- Restore a fresh build so equipped fixture allocations cannot affect later tests.
newBuild();L.mode='zh';tip=new('Tooltip'):Tooltip()
-- Imported rarity affixes must translate in actual item tooltips without
-- changing the parser input, its signed value, or the saved item.
for _,stat in ipairs({'+26% to Item Rarity', '+26% TO ITEM RARITY', '-10% to Item Rarity'})do
 local item=new('Item'):Item('Rarity: RARE\nRapture Corona\nHubris Circlet\nItem Level: 85\n'..stat)
 local raw=item:BuildRaw()
 local amount=stat:match('^[%+%-]%d+')
 local mod=assert(item.explicitModLines[1].modList[1],'Rarity affix not parsed')
 assert(mod.name=='LootRarity' and mod.type=='BASE' and mod.value==tonumber(amount),'Rarity parser semantics changed')
 for _,mode in ipairs({'zh','en','zh'})do
  L.mode=mode;tip:Clear();build.itemsTab:AddItemTooltip(tip,item,nil,true)
  local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
  local expected=mode=='en' and stat or '物品掉落稀有度 '..amount..'%'
  assert(text:find(expected,1,true),text)
  assert(item:BuildRaw()==raw,'Rarity display changed raw item')
  assert(mod.name=='LootRarity' and mod.type=='BASE' and mod.value==tonumber(amount),'Rarity display changed numeric modifier')
 end
end
L.mode='zh'
assert(L:Translate('^x8888FF+(21-26)% to Item Rarity')=='^x8888FF物品掉落稀有度 +(21-26)%')
assert(L:Translate('+26% to Unknown Item Rarity')=='+26% to Unknown Item Rarity')
print('Imported item rarity: mixed/upper case, signed values, ranges, colour, language switching and raw item preservation passed')
local rareRows={}
for _,parts in ipairs({
 {'Rage Horn','Divine Crown','怒火之角','神启头冠','Helmet'},
 {'Fate Wrap','Sacred Chainmail','命运之裹','神圣锁甲','Body Armour'},
 {'Corruption Claw','Zealot Gloves','腐化之爪','狂热者手套','Gloves'},
 {'My custom name','Divine Crown','My custom name','神启头冠','Helmet'},
})do
 local item=new('Item'):Item('Rarity: RARE\n'..parts[1]..'\n'..parts[2]..'\nItem Level: 85')
 assert(item.title==parts[1] and item.baseName==parts[2], 'Rare name import failed: '..parts[1])
 build.itemsTab:AddItem(item,true)
 rareRows[#rareRows+1]={item=item, parts=parts, raw=item:BuildRaw()}
end
for _,row in ipairs(rareRows)do
 local item,parts=row.item,row.parts
 local slot=assert(build.itemsTab.slots[parts[5]])
 slot:SetSelItemId(item.id)
 build.itemsTab:PopulateSlots()
 slot:UpdateEquippedDetails()
 assert(slot.hideSelDetail and slot.list[slot.selIndex].detail=='^8(equipped)', 'Equipped metadata missing')
 local saved=build:SaveDB('fixture')
 for _,mode in ipairs({'zh','en','zh'})do
  L.mode=mode;tip:Clear();build.itemsTab:AddItemTooltip(tip,item,slot)
  local title,base=parts[mode=='en' and 1 or 3],parts[mode=='en' and 2 or 4]
  local label=title..', '..base
  assert(L:ItemListName(item)==label,L:ItemListName(item))
  local slotLabel=L:Translate(slot:GetDisplayLabel(slot.list[slot.selIndex]))
  assert(slotLabel==colorCodes.RARE..label,slotLabel)
  assert(L:Translate(slot.list[slot.selIndex].detail)==(mode=='en' and '^8(equipped)' or '^8（已装备）'))
  assert(tip.lines[1].text==colorCodes.RARE..title,tip.lines[1].text)
  assert(tip.lines[2].text==colorCodes.RARE..base,tip.lines[2].text)
  assert(item:BuildRaw()==row.raw and build:SaveDB('fixture')==saved,'Rare name display changed saved data')
 end
end
print('Imported rare names: equipped slots, item list, tooltip titles and bases, custom names and saved data passed')
for i,parts in ipairs(fixtures)do
 local name=parts[1]..' '..parts[2]..' '..parts[3]
 local item=new('Item'):Item('Rarity: MAGIC\n'..name..'\nQuality: 20\nItem Level: 85\n'..parts[4])
 assert(item.baseName==parts[2] and item.rarity=='MAGIC','Import failed: '..name)
 build.itemsTab:AddItem(item,true)
 build.itemsTab.slots['Flask '..i]:SetSelItemId(item.id)
 rows[i]={item=item,raw=item:BuildRaw(),zh=dict[parts[1]]..' '..dict[parts[2]]..' '..dict[parts[3]]}
end
build.itemsTab:PopulateSlots()
build.buildFlag=true
runCallback('OnFrame')
build.viewMode='ITEMS'
-- Imported anointments and the editor must retain the English parser line,
-- while every current recipe displays the reviewed notable name.
local notableCount=0
local steelwood
local anointNames=LoadModule('Localization/AnointNames')
build.itemsTab:SetDisplayItem(new('Item'):Item('Rarity: RARE\nDragon Heart\nOnyx Amulet\nItem Level: 85'))
build.itemsTab:AnointDisplayItem(1)
local anointPopup=assert(main.popups[1])
local notableDB=assert(anointPopup.controls.notableDB)
for _,node in pairs(build.spec.nodes)do
 if node.recipe and #node.recipe>=1 then
  local zh=assert(anointNames[node.dn],'Missing anoint name: '..node.dn)
  L.mode='zh'
  assert(L:Translate('Allocates '..node.dn)=='分配 '..zh,node.dn)
  assert(L:Translate('Anoint '..node.dn)=='涂油分配 '..zh,node.dn)
  assert(notableDB:GetRowValue(1,1,node):find(zh,1,true),'Notable row: '..node.dn)
  L.mode='en';assert(L:Translate('Allocates '..node.dn)=='Allocates '..node.dn)
  notableCount=notableCount+1
  if node.dn=='Steelwood Stance'then steelwood=node end
 end
end
main:ClosePopup()
assert(steelwood and notableCount>100,'Anoint recipe inventory missing')
local amulet=new('Item'):Item('Rarity: RARE\nDragon Heart\nOnyx Amulet\nItem Level: 85\nAllocates Steelwood Stance (enchant)\n+129 to maximum Life')
local amuletRaw=amulet:BuildRaw()
build.itemsTab:AddItem(amulet,true)
build.itemsTab.slots.Amulet:SetSelItemId(amulet.id)
build.itemsTab:PopulateSlots()
build.itemsTab:SetDisplayItem(amulet)
L.mode='zh'
tip:Clear();build.itemsTab:AddItemTooltip(tip,amulet,nil,true)
local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
assert(text:find('分配 身坚如铁',1,true) and not text:find('Allocates',1,true),text)
assert(build.itemsTab:getAnoint(amulet)[1]=='Steelwood Stance')
assert(amulet:BuildRaw()==amuletRaw)
local edited=build.itemsTab:anointItem(steelwood)
assert(build.itemsTab:getAnoint(edited)[1]=='Steelwood Stance')
assert(edited:BuildRaw():find('Allocates Steelwood Stance',1,true))
assert(L:Translate('(replacing ^6New Item, Onyx Amulet^7)'):find('替换',1,true))
assert(L:Translate('Socket #12')=='插槽 #12')
assert(L:Translate('^7^7Loadouts:')=='^7^7配装方案:')
assert(L:Translate('Allocates Unknown Passive')=='Allocates Unknown Passive')
assert(L:Translate('Dragon Heart')=='Dragon Heart','User rare title was changed')
build.itemsTab:SetDisplayItem()
print('All '..notableCount..' anoint recipes and imported Steelwood Stance: display, editor and raw parser lines passed')
local saved=build:SaveDB('fixture')
for _,mode in ipairs({'zh','en','zh'})do
 L.mode=mode
 for i,row in ipairs(rows)do
  tip:Clear();build.itemsTab:AddItemTooltip(tip,row.item,build.itemsTab.slots['Flask '..i])
  local title=tip.lines[1].text:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
  assert(title==(mode=='en' and row.item.name or row.zh),title)
  local slot=build.itemsTab.slots['Flask '..i]
  local label=L:Translate(slot:GetDisplayLabel(slot.list[slot.selIndex]))
  assert(label:find(mode=='en' and row.item.name or row.zh,1,true),label)
  assert(row.item:BuildRaw()==row.raw,'Raw item changed')
  if i==1 and mode=='zh'then
   local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
   assert(text:find('充能获取量修正',1,true),text)
   assert(not text:find('Charge gain modifier',1,true),text)
  end
 end
 assert(build:SaveDB('fixture')==saved,'Display changed saved build XML')
end
-- Unsupported calculation effects must still receive their reviewed display
-- translation, including the red colour and the unsupported-effect suffix.
local ignite='When you Kill an Ignited Enemy, inflict an equivalent Ignite on each Enemy within 2 metres'
local shock='When you Kill a Shocked Enemy, inflict an equivalent Shock on each Enemy within 2 metres'
for _,name in ipairs({"Abberath's Hooves", "Berek's Respite"})do
 local item
 for _,candidate in pairs(main.uniqueDB.list)do if candidate.title==name then item=candidate;break end end
 assert(item,'Missing unique fixture: '..name)
 local raw=item:BuildRaw()
 for _,mode in ipairs({'zh','en'})do
  L.mode=mode;tip:Clear();build.itemsTab:AddItemTooltip(tip,item,nil,true)
  local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
  for _,stat in ipairs(name=="Berek's Respite" and {ignite,shock} or {ignite})do
   local expected=mode=='en' and stat or dict[stat]
   assert(expected,'Reviewed translation missing: '..stat)
   assert(text:find('^xF05050'..expected,1,true),text)
   if mode=='zh'then assert(not text:find(stat,1,true),text)end
  end
  assert(text:find(mode=='en' and '(Not supported in PoB yet)' or dict['(Not supported in PoB yet)'],1,true),text)
  assert(item:BuildRaw()==raw,'Unique display changed raw data')
 end
end
-- The reported ring contains an unsupported custom enchant and a granted
-- skill clause without the usual trailing "Skill". Check the actual tooltip,
-- including developer parser diagnostics, without changing imported data.
local tower='Your Chilling Towers Freeze Enemies for 0.2 seconds while they are affected by Chilling Beams'
local towerZh='你的冰冻塔使受到冰缓光束影响的敌人冻结 0.2 秒'
local ring=new('Item'):Item('Rarity: RARE\nMiracle Band\nUnset Ring\nItem Level: 85\n'..tower..' (enchant)\nGrants Level 20 Aspect of the Spider\n+34 to maximum Energy Shield')
local ringRaw=ring:BuildRaw()
local devMode=launch.devModeAlt
for _,developer in ipairs({false,true})do
 launch.devModeAlt=developer
 for _,mode in ipairs({'zh','en','zh'})do
  L.mode=mode;tip:Clear();build.itemsTab:AddItemTooltip(tip,ring,nil,true)
  local text='';for _,line in ipairs(tip.lines)do text=text..(line.text or '')..'\n'end
  assert(text:find(mode=='en' and 'Miracle Band' or '奇迹之环',1,true),text)
  assert(text:find(mode=='en' and tower or towerZh,1,true),text)
  assert(text:find(mode=='en' and 'Grants Level 20 Aspect of the Spider' or '获得 20 级蛛之势',1,true),text)
  if mode=='zh'then
   assert(not text:lower():find('chilling',1,true),text)
   assert(not text:find('Aspect of the Spider',1,true),text)
   assert(text:find('^xF05050'..towerZh,1,true),text)
   assert(text:find('（PoB 尚未支持此效果）',1,true),text)
  end
  assert(ring:BuildRaw()==ringRaw,'Ring display changed parser data')
 end
end
launch.devModeAlt=devMode
L.mode='zh'
assert(L:Translate('Grants Level 30 Aspect of the Spider')=='获得 30 级蛛之势')
assert(L:Translate('Grants Level 20 Aspect of the Spider Skill')=='获得 20 级蛛之势技能')
assert(L:Translate(tower:gsub('0%.2','0.4'))==towerZh:gsub('0%.2','0.4'))
print('Imported Miracle Band: enchantment, granted skill, developer diagnostics, language switching and raw data preservation passed')
local f=assert(io.open(AUDIT_SOURCE..'/Imported-Item-QA.xml','wb'));f:write(saved);f:close()
print('Five imported magic names: real parsing, equipped slots, tooltips, language switching and identical saved build XML passed')
print('Unsupported ignite/shock propagation on both unique items: translated actual tooltips, red colour, warning and raw data preservation passed')
''')
