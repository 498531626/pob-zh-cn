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
 {'Arcane Surge, Grace, Herald of Agony, Malevolence, Steelskin, Virulence Stack Limit, Vitality',
  '秘术增强(辅), 优雅, 苦痛之捷, 怨毒光环, 钢铁之肤, 毒力层数上限, 活力'},
 {'Dot','持续伤害'}, {'Buff','增益'}, {'Damage','伤害'},
 {'Aura Debuff','光环减益'}, {'Debuff','减益'}, {'Global','全局效果'},
 {'1 Power Charges, 5 Endurance Charges','1 暴击能量球, 5 耐力能量球'},
 {'0 Frenzy Charges','0 狂怒能量球'},
 {'Physical Damage Gain As Cold','物理伤害额外获得为冰霜伤害'},
 {'Physical Damage Convert To Fire','物理伤害转化为火焰伤害'},
 {'Lightning Min','最小闪电伤害'}, {'Lightning Max','最大闪电伤害'},
 {'Fire Min','最小火焰伤害'}, {'Fire Max','最大火焰伤害'},
 {'23% more','23% 总增'}, {'20% less','20% 总降'},
 {'12.5% increased','12.5% 提高'}, {'3% reduced','3% 降低'},
 {'Full Poison DPS:','完整中毒每秒伤害:'},
 {'6x Bladefall of Impaling:','6x 穿刺之虚空刀雨:'},
 {'12x Bladefall of Impaling^7:','12x 穿刺之虚空刀雨^7:'},
 {'Full Impale DPS:','完整穿刺每秒伤害:'},
 {'Full Decay DPS:','完整腐蚀每秒伤害:'},
 {'Full DoT DPS:','完整持续每秒伤害:'},
 {'Full Culling DPS:','完整终结贡献伤害:'},
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
for _,en in ipairs({'Anger, Unknown Buff','1 Unknown Charges','Lightning Unknown','Unknown Damage Gain As Cold','1,234.5','1, 234','23garbage% more','6x Unknown Skill:','6x 2,475,963.5'}) do
 assert(L:Translate(en)==en,'Unknown or numeric input changed: '..en)
end
-- Use the real sidebar formatter to cover the count/name composition that
-- previously bypassed exact skill translations. Numeric outputs stay separate.
local file=assert(io.open('Modules/Build.lua','r'))
local source=file:read('*a');file:close()
local formatter=assert(source:match('(function buildMode:AddDisplayStatList.-)\nfunction buildMode:InsertItemWarnings'))
buildMode={};t_insert=table.insert
colorCodes={CUSTOM='^x00FFAA',WARNING='^xFFAA00'}
function matchFlags() return true end
assert(loadstring(formatter))()
local rows={}
local view=setmetatable({controls={statBox={list=rows}},FormatStat=function(_,_,value) return tostring(value) end},{__index=buildMode})
local skill={name='Bladefall of Impaling',count=6,dps=412660.5833333333}
local actor={mainSkill={skillFlags={}},output={SkillDPS={skill},CrabBarriersMax=0},modDB={Flag=function()return false end}}
view:AddDisplayStatList({{stat='SkillDPS'}},actor)
assert(rows[1][1]=='^x00FFAA6x Bladefall of Impaling:')
L.mode='zh';assert(L:Translate(rows[1][1])=='^x00FFAA6x 穿刺之虚空刀雨:')
assert(tonumber(rows[1][2])==skill.dps*skill.count)
assert(skill.name=='Bladefall of Impaling' and skill.count==6)
L.mode='en';assert(L:Translate(rows[1][1])==rows[1][1]);L.mode='zh'
local calcClass={}
function newClass() return calcClass end
bit=require('bit')
dofile('Classes/CalcBreakdownControl.lua')
for _,row in ipairs({
 {'PhysicalDamageGainAsCold','物理伤害额外获得为冰霜伤害'},
 {'LightningMin','最小闪电伤害'}, {'FireMax','最大火焰伤害'},
 {'Multiplier:VirulenceStacksMax','最大毒力层数'},
 {'GuardAbsorbRate','护卫伤害吸收比例'},
 {'GuardAbsorbLimit','护卫伤害吸收上限'},
 {'AvoidBleed','避免流血几率'},
 {'ArcaneSurgeManaRegen','秘术增强魔力再生'},
 {'ArcaneSurgeCastSpeed','秘术增强施法速度'},
}) do
 local raw=calcClass:FormatModName(row[1])
 assert(L:TranslateUI(raw)==row[2],raw)
 L.mode='en';assert(L:TranslateUI(raw)==raw);L.mode='zh'
 assert(calcClass:FormatModName(row[1])==raw,'Internal identifier changed')
end
assert(L:TranslateUI(calcClass:FormatModValue(23,'MORE'))=='23% 总增')
assert(L:TranslateUI(calcClass:FormatModValue(-20,'MORE'))=='20% 总降')
print('Calculation panel text: '..#cases..' cases; colours, English/Chinese, Alt independence and unknown fallback passed')
''')
