"""Check real item-list row formatting without reading or writing user builds."""
import os
from test_locale import ROOT, run

os.chdir(ROOT / 'src')
run(r'''
local alt = false
function LoadModule(p) return dofile(p .. '.lua') end
function IsKeyDown() return alt end
function GetScriptPath() return '__localization_test_no_save__' end
function DrawString() end
function DrawStringWidth(h, font, text)
    return #tostring(text):gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','') * h * 0.5
end
function DrawStringCursorIndex() return 0 end
function SetDrawColor() end
Localization = LoadModule('Modules/Localization')
local L = Localization
local dict = LoadModule('Localization/Dictionary')
local class = {}
function newClass() return class end
dofile('Classes/ItemListControl.lua')
colorCodes = {RARE='^6', MAGIC='^3', UNIQUE='^5'}
local item = {rarity='RARE',name='New Item, Rebuking Blade'}
local set = {title="Strength's 中文 33-45"}
local control = setmetatable({itemsTab={items={[1]=item},
    GetEquippedSlotForItem=function() return {},set end}}, {__index=class})
function control:FindEquippedAbyssJewel() return nil end
function control:FindSocketedJewel() return nil end
for _,mode in ipairs({'zh'}) do
    L.mode=mode
    assert(control:GetRowValue(1,1,1)=='^6'..dict['New Item']..', '..dict['Rebuking Blade'].."  ^9(用于 '"..set.title.."')")
    control.itemsTab.GetEquippedSlotForItem=function() return nil end
    assert(control:GetRowValue(1,1,1):find('(未使用)',1,true))
    control.itemsTab.GetEquippedSlotForItem=function() return {},set end
    local magic={rarity='MAGIC',name='Endless Silver Flask of the Pangolin',
        baseName='Silver Flask',namePrefix='Endless ',nameSuffix=' of the Pangolin'}
    assert(L:ItemListName(magic)==dict.Endless..' '..dict['Silver Flask']..' '..dict['of the Pangolin'])
    magic.namePrefix='Unverified ';magic.nameSuffix=' of Unknown'
    assert(L:ItemListName(magic)=='Unverified '..dict['Silver Flask']..' of Unknown')
    assert(L:ItemListName({rarity='RARE',name='My custom name, Rebuking Blade'})=='My custom name, '..dict['Rebuking Blade'])
    for _,label in ipairs({'Any Loadout','Current Loadout','Unused Items'}) do
        assert(L:TranslateUI(label)~=label)
    end
end
L.mode='en'
assert(control:GetRowValue(1,1,1)=="^6New Item, Rebuking Blade  ^9(Used in '"..set.title.."')")
L.mode='zh';alt=true
assert(L:ItemListName(item)==dict['New Item']..', '..dict['Rebuking Blade'])
alt=false
local text='^6新建物品, 责难刀  ^9(用于 33-45)'
for width=24,320 do
    local clipped=L:ClipText(text,12,'VAR',width)
    assert(DrawStringWidth(12,'VAR',clipped)<=width)
    assert(not clipped:find('[\128-\191]%.%.%.$') or clipped:match('[\224-\239][\128-\191][\128-\191]%.%.%.$'))
end
assert(item.name=='New Item, Rebuking Blade' and set.title=="Strength's 中文 33-45")
-- Real equipped-slot population keeps raw English labels. Translation must
-- therefore work at render/measurement time, not just in ItemListName.
local slotClass={}
function newClass() return slotClass end
dofile('Classes/ItemSlotControl.lua')
function wipeTable(t) for k in pairs(t) do t[k]=nil end end
local fixtures={
 {'Endless','Silver Flask','of the Pangolin'},
 {'Alarmed','Divine Life Flask','of Alleviation'},
 {'Horticultural','Prismatic Tincture','of Overpowering'},
 {'Endless','Quicksilver Flask','of Persistence'},
 {"Masochist's",'Diamond Flask','of Penetrating'},
}
local equipped={}
for i,parts in ipairs(fixtures) do
 equipped[i]={id=i,rarity='MAGIC',baseName=parts[2],namePrefix=parts[1]..' ',nameSuffix=' '..parts[3],
  name=table.concat(parts,' ')}
end
local slot=setmetatable({itemsTab={items=equipped,IsItemValidForSlot=function()return true end},
 items={},list={},selItemId=1,abyssalSocketList={}}, {__index=slotClass})
L.mode='zh'
local stale=L:Translate(equipped[1].name) -- previous untranslated cache entry
slot:Populate()
for i,parts in ipairs(fixtures) do
 for _,part in ipairs(parts) do assert(dict[part], 'Missing reviewed term: '..part) end
 local raw=equipped[i].name
 local zh=dict[parts[1]]..' '..dict[parts[2]]..' '..dict[parts[3]]
 assert(L:Translate('^3'..raw)=='^3'..zh,raw..' => '..L:Translate(raw))
 assert(L:ItemListName(equipped[i])==zh)
 L.mode='en';assert(L:Translate('^3'..raw)=='^3'..raw)
 L.mode='zh';assert(L:Translate(raw)==zh)
 assert(equipped[i].name==raw)
end
for _,text in ipairs({'^8Charge gain modifier: ^7+30%', '^8Flask effect modifier: ^7+25%',
 '^8Flask effect duration: ^76.20s','^8Charges used: ^740 ^8of ^760 ^8(^71 ^8uses)'}) do
 local zh=L:Translate(text)
 assert(zh~=text and not zh:match('modifier') and not zh:match('Charges'),zh)
 assert(zh:gsub('%^%d',''):gsub('[^%d+%.%-]','')==text:gsub('%^%d',''):gsub('[^%d+%.%-]',''),zh)
 L.mode='en';assert(L:Translate(text)==text);L.mode='zh'
end
local f=assert(io.open('Classes/ItemsTab.lua','r'));local source=f:read('*a');f:close()
local help=assert(source:match('%[%[(%^7Double%-click an item.-)%]%]'))
assert(not L:Translate(help):find('Double-click',1,true),'Item operation help remains English')
assert(L:Translate('Any slot')=='任意装备槽' and L:Translate('Any type')=='任意类型')
f=assert(io.open('Classes/SharedItemListControl.lua','r'));source=f:read('*a');f:close()
local shared=assert(source:match('self.defaultText = "(.-)"')):gsub('\\n','\n')
assert(not L:Translate(shared):find('This is a list',1,true))
f=assert(io.open('Modules/Main.lua','r'));source=f:read('*a');f:close()
local toast=assert(source:match('ToastNotification:Add%(%[%[(.-)%]%]%)')):gsub('^\n','')
local body=toast:gsub('^[^\n]*\n?','')
assert(not L:Translate(body):find('The program',1,true),'Split developer notification body remains English')
L.mode='en'
assert(L:Translate(shared)==shared and L:Translate(body)==body)
L.mode='zh'
print('Item rows: names, affixes, usage, custom titles, filters, English and Alt language independence and UTF-8 clipping passed.')
''')
