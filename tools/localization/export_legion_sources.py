"""Export timeless jewel display text from this checkout, retaining stable IDs."""
import os
from test_locale import ROOT, run


def export():
    os.chdir(ROOT / 'src')
    run(r'''
package.path='../runtime/lua/?.lua;'..package.path
local json=require('dkjson')
local rows={}
local data=dofile('Data/TimelessJewelData/LegionPassives.lua')
for _,kind in ipairs({'nodes','additions'}) do
 for _,node in ipairs(data[kind]) do
  if node.id:match('^vaal_') or node.id:match('^karui_') or node.id:match('^maraketh_')
   or node.id:match('^templar_') or node.id:match('^eternal_') then
   local source='Data/TimelessJewelData/LegionPassives.lua#'..node.id
   rows[#rows+1]={english=node.dn,kind='timeless-name',source=source}
   for _,line in ipairs(node.sd or {}) do
    rows[#rows+1]={english=line,kind='timeless-stat',source=source}
   end
  end
 end
end
-- Militant Faith also appends this amount to existing notable passives.
rows[#rows+1]={english='+5 to Devotion',kind='timeless-stat',source='Classes/PassiveSpec.lua'}
table.sort(rows,function(a,b) return a.source==b.source and a.english<b.english or a.source<b.source end)
local f=assert(io.open('../tools/localization/legion-source.json','wb'))
f:write(json.encode(rows,{indent=true}));f:close()
print('Timeless jewel display inventory: '..#rows..' records')
''')


if __name__ == '__main__':
    export()
