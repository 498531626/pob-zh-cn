"""Exercise actual display formatting for player/minion buffs without user saves."""
import os
from test_locale import ROOT, run

os.chdir(ROOT / 'src')
run(r'''
function LoadModule(p) return dofile(p .. '.lua') end
function GetScriptPath() return '__buff_test_no_save__' end
local L=LoadModule('Modules/Localization'); Localization=L
LoadModule('Modules/CalcFormat')
local dict=LoadModule('Localization/Dictionary')
local aura='Clarity, Determination, Discipline, Lightning Golem Wrath, Spectre, Vitality, Wrath, Zealotry'
local actor={output={BuffList=aura,CombatList='5 Inspiration Charges',Minion={BuffList=aura,CombatList='3 Ghost Shrouds, 10 Crab Barriers, 2 Spirit Infusions'}}}
local expected='清晰, 坚定, 纪律, 闪电魔像愤怒, 灵体, 活力, 雷霆, 奋锐光环'
L.mode='zh'
assert(formatCalcStr('{output:BuffList}',actor)==expected,formatCalcStr('{output:BuffList}',actor))
assert(formatCalcStr('{output:CombatList}',actor)=='5 启迪球')
assert(formatCalcStr('{output:Minion.BuffList}',actor)==expected)
assert(formatCalcStr('{output:Minion.CombatList}',actor)=='3 幽魂缠身, 10 深海屏障, 2 精魂灌注')
actor.output.BuffList='Anger, Unknown Buff, Wrath'
assert(formatCalcStr('{output:BuffList}',actor)=='愤怒, Unknown Buff, 雷霆')
actor.output.BuffList='Unknown Buff, Anger'
assert(formatCalcStr('{output:BuffList}',actor)=='Unknown Buff, 愤怒')
actor.output.BuffList='^1Anger, ^2Unknown Buff, ^3Wrath'
assert(formatCalcStr('{output:BuffList}',actor)=='^1愤怒, ^2Unknown Buff, ^3雷霆')
-- Audit every literal combat label emitted by the real calculator, including
-- counted effects other than charges. Fail when an upstream addition is missed.
local f=assert(io.open('Modules/Calcs.lua'));local source=f:read('*a');f:close()
local count=0
for name in source:gmatch('t_insert%(combatList, s_format%("%%d ([^"]+)"') do
 assert(dict[name],'Missing counted combat effect: '..name)
 assert(L:TranslateCalcList('5 '..name)=='5 '..dict[name],name)
 count=count+1
end
for name in source:gmatch('t_insert%(combatList, "([^"]+)"%)') do
 assert(dict[name],'Missing combat effect: '..name)
 count=count+1
end
for _,name in ipairs({'Wrath - Perfect Spirit of Fortune','Vitality - Perfect Warlord','Determination - Perfect Guardian Turtle'}) do
 local skill,minion=name:match('^(.+) %- (.+)$')
 assert(L:Translate(name)==dict[skill]..' - '..dict[minion],name)
end
assert(L:Translate('Spectre')=='灵体')
assert(L:Translate('Energy Shield Recharge')=='能量护盾充能')
assert(L:Translate('Unknown Skill - Perfect Warlord')=='Unknown Skill - Perfect Warlord')
-- The formatter must not change calculation output, arbitrary strings, or numbers.
actor.output.Other='Anger, Unknown Buff';actor.output.Number=12345.5
assert(formatCalcStr('{output:Other}',actor)==actor.output.Other)
assert(formatCalcStr('{output:Number}',actor)=='12345.5')
assert(formatCalcStr('{output:MinionMissing.BuffList}',actor)=='')
assert(formatCalcStr('{output:BuffList}',nil)=='')
assert(actor.output.CombatList=='5 Inspiration Charges')
L.mode='en'
for _,field in ipairs({'BuffList','CombatList'}) do
 assert(formatCalcStr('{output:'..field..'}',actor)==actor.output[field])
end
assert(L:TranslateCalcList('')=='')
print('Calculation buffs: screenshot fixtures, '..count..' emitted combat labels, player/minion, unknown entries, colours, source names, numeric isolation and English passed')
''')
