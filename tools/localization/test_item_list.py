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
print('Item rows: names, affixes, usage, custom titles, filters, English and Alt language independence and UTF-8 clipping passed.')
''')
