"""Inventory display fields, keeping database IDs/stat keys out of translation."""
import os
import json
from pathlib import Path
from test_locale import ROOT, run

HERE = Path(__file__).resolve().parent


def export():
    enchantments = [p.stem for p in sorted((ROOT/'src/Data').glob('Enchantment*.lua'))]
    os.chdir(ROOT/'src')
    run('local enchantments='+json.dumps(enchantments).replace('[','{').replace(']','}')+r'''
package.path='../runtime/lua/?.lua;'..package.path
local json=require('dkjson')
local rows,seen={},{}
local function add(text,kind,source)
 if type(text)~='string' or not text:match('%a')then return end
 local key=kind..'\0'..text
 if not seen[key]then seen[key]=true;rows[#rows+1]={english=text,kind=kind,source=source}end
end
local function load(name,...)return assert(loadfile('Data/'..name..'.lua'))(...)end
local function lines(t,kind,source)
 if type(t)=='string'then add(t,kind,source)
 elseif type(t)=='table'then
  for k,v in pairs(t)do if type(k)=='number' or type(v)=='table'then lines(v,kind,source)end end
 end
end
for _,e in pairs(load('Essence'))do add(e.name,'essence-name','Data/Essence.lua')end
for _,name in pairs(load('CurrencyNames'))do add(name,'currency-name','Data/CurrencyNames.lua')end
for _,god in pairs(load('Pantheons'))do
 for _,soul in pairs(god.souls)do
  add(soul.name,'pantheon-name','Data/Pantheons.lua')
  for _,mod in ipairs(soul.mods)do add(mod.line,'pantheon-stat','Data/Pantheons.lua')end
 end
end
ModFlag=setmetatable({},{__index=function()return 0 end})
local function mod()return {}end
for _,file in ipairs({'Minions','Spectres'})do
 local monsters={};load(file,monsters,mod,mod)
 for id,monster in pairs(monsters)do add(monster.name,file=='Minions'and 'minion-name'or 'spectre-name','Data/'..file..'.lua#'..id)end
end
for _,file in ipairs(enchantments)do lines(load(file),'enchantment-stat','Data/'..file..'.lua')end
for _,file in ipairs({'BeastCraft','Crucible'})do
 for _,m in pairs(load(file))do
  add(m.affix,'craft-affix','Data/'..file..'.lua')
  for _,line in ipairs(m)do add(line,'craft-extra-stat','Data/'..file..'.lua')end
 end
end
local function cluster(t)
 if type(t)~='table'then return end
 for k,v in pairs(t)do
  if k=='name'then add(v,'cluster-name','Data/ClusterJewels.lua')
  elseif k=='stats'or k=='enchant'then lines(v,'cluster-stat','Data/ClusterJewels.lua')
  elseif type(v)=='table'then cluster(v)end
 end
end
cluster(load('ClusterJewels'))
for _,node in pairs(load('TattooPassives').nodes)do
 add(node.dn,'tattoo-name','Data/TattooPassives.lua');lines(node.sd,'tattoo-stat','Data/TattooPassives.lua')
end
local bosses,list=load('BossSkills')
for _,b in pairs(bosses)do add(b.tooltip,'boss-skill-tooltip','Data/BossSkills.lua')end
for _,b in ipairs(list)do add(b.label,'boss-skill-name','Data/BossSkills.lua')end
table.sort(rows,function(a,b)return a.kind==b.kind and a.english<b.english or a.kind<b.kind end)
local f=assert(io.open('../tools/localization/database-source.json','wb'));f:write(json.encode(rows,{indent=true}));f:close()
print('Database display inventory: '..#rows..' unique category/text records')
''')


if __name__ == '__main__':
    export()
