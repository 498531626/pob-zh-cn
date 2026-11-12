"""Regressions for unique flask effects, jewel clauses and runtime-only stats."""
import json
import os
from test_locale import ROOT, run

os.chdir(ROOT / 'src')
reviewed = json.loads((ROOT / 'tools/localization/unique-reviewed.json').read_text('utf8'))
cases = []
for english, chinese in reviewed.items():
    for values in (['17', '31', '53'], ['(10-20)', '(30-40)', '(50-60)']):
        en, zh = english, chinese
        for index, value in enumerate(values):
            en, zh = en.replace('{'+str(index)+'}', value), zh.replace('{'+str(index)+'}', value)
        cases.append([en, zh])
run('local cases=' + '{' + ','.join('{'+json.dumps(e, ensure_ascii=False)+','+json.dumps(z, ensure_ascii=False)+'}' for e,z in cases) + '}\n' + r'''
function LoadModule(p)return dofile(p..'.lua')end
function GetScriptPath()return '__unique_test_no_user_data__'end
function IsKeyDown()return false end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local L=LoadModule('Modules/Localization')
for _,case in ipairs(cases)do
 L.mode='zh'
 assert(L:Translate(case[1])==case[2],case[1]..' => '..L:Translate(case[1]))
 assert(L:Translate('^xF05050'..case[1])=='^xF05050'..case[2],case[1])
 L.mode='en';assert(L:Translate(case[1])==case[1],'English changed')
end
L.mode='zh'
assert(L:Translate('Gain (1-3) Frenzy Charge on use')=='使用时获得 (1-3) 个狂怒球')
assert(L:Translate('Gain secret Frenzy Charge on use')=='Gain secret Frenzy Charge on use')
assert(L:Translate('Marauder: 1% of Life Regenerated per second')~='Marauder: 1% of Life Regenerated per second')
assert(L:Translate('Passive Skills in radius of Iron Reflexes can be allocated without being connected to your tree')~='Passive Skills in radius of Iron Reflexes can be allocated without being connected to your tree')
print('Unique localization: reviewed clauses, numeric rolls, colours, English fallback and runtime jewel stats passed')
''')
