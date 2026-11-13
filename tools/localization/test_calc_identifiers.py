"""Gate all current calculation IDs, notes, glyphs and unknown fallback."""
import json
import os
from calc_identifier_locale import build, inventory
from test_locale import ROOT, run


if __name__ == '__main__':
    translations, report = build(write=False)
    assert not report['pending'], report['pending']
    names, schema = inventory()
    os.chdir(ROOT / 'src')
    run('AUDIT_IDS=' + '{' + ','.join(json.dumps(name) for name in sorted(names)) + '}\n' + r'''
function LoadModule(p)return dofile(p..'.lua')end
function GetScriptPath()return '__no_user_saves__'end
local L=LoadModule('Modules/Localization')
local glyphs=LoadModule('Localization/Glyphs')
local names=LoadModule('Localization/CalcIdentifiers')
local terms=LoadModule('Localization/CalcIdentifierTerms')
local class={};function newClass()return class end
bit=require('bit');dofile('Classes/CalcBreakdownControl.lua')
local function numbers(text)
 text=text:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
 local result={};for number in text:gmatch('%d+%.?%d*')do result[#result+1]=number end
 return table.concat(result,',')
end
for _,id in ipairs(AUDIT_IDS)do
 local raw=class:FormatModName(id)
 L.mode='zh';local zh=L:Translate(raw)
 assert(zh~=raw and not zh:find('%a'),'Untranslated current identifier: '..id..' => '..zh)
 assert(numbers(zh)==numbers(raw),'Identifier numeric meaning changed: '..id)
 assert(L:Translate('^x8888FF'..raw)=='^x8888FF'..zh,'Colour prefix changed')
 L.mode='en';assert(L:Translate(raw)==raw,'English mode changed')
 assert(class:FormatModName(id)==raw,'Internal formatter changed with language')
end
L.mode='zh'
assert(L:Translate('Enemy Curse Limit')=='敌人承受诅咒数量上限')
assert(L:Translate('Cold Resist Max')=='冰霜抗性上限')
assert(L:Translate('Curse Limit Is Maximum Power Charges')=='诅咒数量上限等于暴击能量球数量上限')
for _,text in ipairs({
 'Condition: Not Never Crit', 'Enemy Condition: On Brittle Ground',
 'Ailment, Hit',
 'Skill type: Not Aura', 'Skill: Raise Zombie / Raise Spectre',
 '+20% of Life, Global, Condition: Not Never Crit',
 '+0.9 per 1 Life, Buff, If Life Unreserved >= 2',
 'If Shaper Item >= 2, If Elder Item >= 2',
 '+75 base Cold Resist Max', '-60 base Fire Resist',
 '23% increased Enemy Curse Limit', '20% reduced Cold Resist Max',
 '23% more Enemy Curse Limit', '20% less Enemy Curse Limit',
 'True Cannot Split', 'When in slot #1',
 '1% per 1 Totem Fire Resist Over Cap', '15% per 1 Chain Remaining',
 'Totem level: 70', '1478 ^8(base life for a level 70 monster)',
 'Totems Summoned: 1 ^8(can be overridden in the Configuration tab)',
 'x 1.67 ^8(totem placement speed)',
})do
 local zh=L:Translate(text)
 local plain=zh:gsub('%^x%x%x%x%x%x%x',''):gsub('^x ','')
 assert(zh~=text and not plain:find('%a'),'Untranslated note: '..text..' => '..zh)
 assert(numbers(zh)==numbers(text),'Note numeric value changed: '..text)
 local lhs={};local rhs={}
 for mark in text:gmatch('[%+%%%<%>%=/#]')do lhs[#lhs+1]=mark end
 for mark in zh:gmatch('[%+%%%<%>%=/#]')do rhs[#rhs+1]=mark end
 assert(table.concat(lhs)==table.concat(rhs),'Note operators changed: '..text)
 L.mode='en';assert(L:Translate(text)==text);L.mode='zh'
end
for _,text in ipairs({'UnknownCalcStat','Enemy Unknown Future Stat','Condition: Unknown Future Condition',
 'If Unknown Future Value >= 2','+1 per Unknown Future Value','My private build notes','1,234.5'})do
 assert(L:Translate(text)==text,'Unknown input partially translated: '..text)
end
local checked={}
for _,table in ipairs({names,terms})do
 for _,zh in pairs(table)do
  for char in zh:gmatch('[\194-\244][\128-\191]+')do
   assert(glyphs.chars[char],'Missing calculation glyph: '..char)
   checked[char]=true
  end
 end
end
print('All '..#AUDIT_IDS..' current calculation identifiers, dynamic notes, numeric/operators, colours, English, unknown fallback and glyphs passed')
''')
