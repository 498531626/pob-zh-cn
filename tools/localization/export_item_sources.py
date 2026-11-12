"""Inventory display strings from local item data, without loading user files."""
import json
import os
from pathlib import Path
from test_locale import ROOT, run

HERE = Path(__file__).resolve().parent


def export():
    paths = {kind: [p.relative_to(ROOT / 'src').with_suffix('').as_posix()
                    for p in sorted((ROOT / 'src/Data' / kind).glob('*.lua'))]
             for kind in ('Bases', 'Uniques')}
    paths['Mods'] = [p.relative_to(ROOT / 'src').with_suffix('').as_posix()
                     for p in sorted((ROOT / 'src/Data').glob('Mod*.lua'))
                     if p.stem not in ('ModCache', 'ModMap', 'ModFoulbornMap', 'ModNecropolis', 'ModScalability')]
    os.chdir(ROOT / 'src')
    run('local paths=' + '{' + ','.join(k + '={' + ','.join(json.dumps(p) for p in v) + '}'
                                      for k, v in paths.items()) + '}\n' + r'''
package.path='../runtime/lua/?.lua;'..package.path
local json=require('dkjson')
local rows,seen={},{}
local propertyFields={marauder=true,duelist=true,ranger=true,shadow=true,witch=true,templar=true,scion=true,
 ['left ring slot']=true,['right ring slot']=true,['instead grant']=true,['passive skills in radius also grant']=true}
local function add(text,kind,source)
 if type(text)~='string' or not text:match('%a')then return end
 local key=kind..'\0'..text
 if not seen[key]then seen[key]=true;rows[#rows+1]={english=text,kind=kind,source=source}end
end
local bases={}
for _,p in ipairs(paths.Bases)do assert(loadfile(p..'.lua'))(bases)end
for name,base in pairs(bases)do
 add(name:gsub(' %(.+%)',''),'base-name');add(base.type,'item-type');add(base.subType,'item-type')
 for line in (base.implicit or ''):gmatch('[^\n]+')do add(line,'base-stat')end
end
for _,p in ipairs(paths.Uniques)do
 for _,raw in ipairs(assert(loadfile(p..'.lua'))())do
  local lines={};for line in raw:gmatch('[^\n\r]+')do lines[#lines+1]=line end
  add(lines[1],'unique-name')
  for i=2,#lines do
   local line=lines[i]:gsub('{[^}]+}',''):match('^%s*(.-)%s*$')
   local field=line:match('^(%a[%a ]*):')
   if (not field or propertyFields[field:lower()])and not line:match('^%-%-')then add(line,'unique-stat')end
  end
 end
end
local function scan(t)
 if type(t)~='table'then return end
 if type(t[1])=='string'and type(t[2])=='string'then add(table.concat(t,'\n'),'craft-stat-group')end
 for k,v in pairs(t)do
  if type(k)=='number'and type(v)=='string'then add(v,'craft-stat')
  elseif type(v)=='table'and k~='tradeHashes'then scan(v)
  elseif k=='affix'then add(v,'affix-name')end
 end
end
for _,p in ipairs(paths.Mods)do scan(assert(loadfile(p..'.lua'))())end
-- Refresh the runtime snapshot with audit_item_runtime.py in a disposable copy.
local runtime=io.open('../tools/localization/item-runtime-source.json','rb')
if runtime then
 local extra=json.decode(runtime:read('*a'));runtime:close()
 for _,row in ipairs(extra)do add(row.english,row.kind,row.source)end
end
table.sort(rows,function(a,b)return a.kind==b.kind and a.english<b.english or a.kind<b.kind end)
local f=assert(io.open('../tools/localization/item-source.json','wb'));f:write(json.encode(rows,{indent=true}));f:close()
print('Local item display source rows: '..#rows)
''')


if __name__ == '__main__':
    export()
