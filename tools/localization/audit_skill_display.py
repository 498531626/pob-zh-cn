"""Render actual local skill stats through StatDescriber; never load settings/saves."""
from pathlib import Path
import os
from test_locale import run, ROOT

if __name__ == '__main__':
    os.chdir(ROOT / 'src')
    run(r'''
package.cpath='../runtime/?.dll;'..package.cpath
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p,...) return assert(loadfile(p..'.lua'))(...) end
function round(n,p) local m=10^(p or 0);return math.floor(n*m+0.5)/m end
function copyTable(t,shallow) local o={};for k,v in pairs(t) do o[k]=not shallow and type(v)=='table' and copyTable(v) or v end;return o end
function IsKeyDown() return false end
function GetScriptPath() return '__localization_audit_no_save__' end
function DrawString() end
function DrawStringWidth() return 1 end
function DrawStringCursorIndex() return 0 end
function SetDrawColor() end
function ConPrintf(...) end
LoadModule('Data/Global')
data={};LoadModule('Data/Misc',data)
local skills, extraEffects={},{}
local function stub(...) return {...} end
for _,p in ipairs({'act_str','act_dex','act_int','sup_str','sup_dex','sup_int','other','glove','minion'}) do
 local sourceSkills={}
 LoadModule('Data/Skills/'..p,sourceSkills,stub,stub,stub)
 for id,effect in pairs(sourceSkills)do
  skills[id]=effect
  if p=='other' or p=='glove'then extraEffects[id]=true end
 end
end
local gems=LoadModule('Data/Gems')
local hybrid={}
for id,gem in pairs(gems) do
 if gem.vaalGem then
  for _,alt in ipairs({'AltX','AltY'}) do
   local effect=skills[gem.secondaryGrantedEffectId..alt]
   if effect then
    local g=copyTable(gem);g.name='Vaal '..effect.baseTypeName;g.secondaryGrantedEffectId=gem.secondaryGrantedEffectId..alt;hybrid[id..alt]=g
   end
  end
 end
end
for id,g in pairs(hybrid) do gems[id]=g end
LoadModule('Modules/CalcTools')
local describe=LoadModule('Modules/StatDescriber')
local L=LoadModule('Modules/Localization');L.mode='zh'
local json=require('dkjson')
local rows, seen={},{}
local function check(s,id,kind)
 if not s or s=='' then return end
 if not seen[s] then
  seen[s]=true
  rows[#rows+1]={english=s,chinese=L:Translate(s),skill=id,kind=kind}
 end
end
for id,gem in pairs(gems) do
 check(gem.name,id,'gem-name');check(gem.tagString,id,'tags')
 for _,effectId in ipairs({gem.grantedEffectId,gem.secondaryGrantedEffectId}) do
  local effect=skills[effectId]
  if effect then
   check(effect.name,effectId,'effect-name');check(effect.description,effectId,'description')
   for n=1,40 do
    if effect.levels[n] then
     for _,q in ipairs({0,20,23}) do
      local stats=calcLib.buildSkillInstanceStats({level=n,quality=q},effect)
      for _,s in ipairs(describe(stats,effect.statDescriptionScope or 'skill_stat_descriptions')) do
       check(s,effectId,'stat')
      end
     end
    end
   end
  end
 end
end
for id in pairs(extraEffects)do
 local effect=skills[id]
 check(effect.name,id,'granted-effect-name');check(effect.description,id,'granted-description')
 for level in pairs(effect.levels or {})do
  if type(level)=='number'then
   for _,q in ipairs({0,20,23})do
    local stats=calcLib.buildSkillInstanceStats({level=level,quality=q},effect)
    for _,s in ipairs(describe(stats,effect.statDescriptionScope or 'skill_stat_descriptions'))do check(s,id,'granted-stat')end
   end
  end
 end
end
table.sort(rows,function(a,b)return a.english<b.english end)
local file=assert(io.open('../tools/localization/skill-display-audit.json','w'))
file:write(json.encode(rows,{indent=true}));file:close()
local counts={};local pending={}
for _,row in ipairs(rows) do
 local englishWords={}
 local plain=row.chinese:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')
 for word in plain:gmatch('%a%a+')do if word~='PoB' and word~='DPS'then englishWords[#englishWords+1]=word end end
 if #englishWords>0 then
  row.remaining_english_words=englishWords
  counts[row.kind]=(counts[row.kind] or 0)+1;pending[#pending+1]=row
 end
end
file=assert(io.open('../tools/localization/skill-display-pending.json','w'));file:write(json.encode(pending,{indent=true}));file:close()
print('Actual gem and player-granted skill display audit: '..#rows..' unique strings; pending '..json.encode(counts))
assert(#pending==0,'Untranslated skill display text; see skill-display-pending.json')
''')
