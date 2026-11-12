"""Regression coverage for dynamic calculation panel text (no user saves)."""
import os
from test_locale import ROOT, run

if __name__ == '__main__':
    os.chdir(ROOT / 'src')
    run(r'''
function LoadModule(p) return dofile(p .. '.lua') end
local alt=false
function IsKeyDown() return alt end
function GetScriptPath() return '__no_user_saves__' end
local L=LoadModule('Modules/Localization')
local cases={
 {'Anger, Hatred, Leap Slam, Wrath','愤怒, 憎恨, 跃击, 雷霆'},
 {'1 Power Charges, 5 Endurance Charges','1 暴击能量球, 5 耐力能量球'},
 {'0 Frenzy Charges','0 狂怒能量球'},
 {'Physical Damage Gain As Cold','物理伤害额外获得为冰霜伤害'},
 {'Physical Damage Convert To Fire','物理伤害转化为火焰伤害'},
 {'Lightning Min','最小闪电伤害'}, {'Lightning Max','最大闪电伤害'},
 {'Fire Min','最小火焰伤害'}, {'Fire Max','最大火焰伤害'},
 {'23% more','23% 总增'}, {'20% less','20% 总降'},
 {'12.5% increased','12.5% 提高'}, {'3% reduced','3% 降低'},
}
for _,case in ipairs(cases) do
 local en,zh=unpack(case)
 L.mode='zh';assert(L:Translate(en)==zh,en..' => '..L:Translate(en))
 assert(L:Translate('^x8888FF'..en)=='^x8888FF'..zh)
 L.mode='en';assert(L:Translate(en)==en)
 L.mode='zh'
 assert(L:TranslateUI(en)==zh)
 alt=true;assert(L:Translate(en)==zh);alt=false
end
L.mode='zh'
for _,en in ipairs({'Anger, Unknown Buff','1 Unknown Charges','Lightning Unknown','Unknown Damage Gain As Cold','1,234.5','1, 234','23garbage% more'}) do
 assert(L:Translate(en)==en,'Unknown or numeric input changed: '..en)
end
local calcClass={}
function newClass() return calcClass end
bit=require('bit')
dofile('Classes/CalcBreakdownControl.lua')
for _,row in ipairs({
 {'PhysicalDamageGainAsCold','物理伤害额外获得为冰霜伤害'},
 {'LightningMin','最小闪电伤害'}, {'FireMax','最大火焰伤害'},
}) do
 local raw=calcClass:FormatModName(row[1])
 assert(L:TranslateUI(raw)==row[2],raw)
 assert(row[1]:match('^[%a]+$'),'Internal identifier changed')
end
assert(L:TranslateUI(calcClass:FormatModValue(23,'MORE'))=='23% 总增')
assert(L:TranslateUI(calcClass:FormatModValue(-20,'MORE'))=='20% 总降')
print('Calculation panel text: '..#cases..' cases; colours, English/Chinese, Alt independence and unknown fallback passed')
''')
