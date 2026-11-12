"""Audit names, bases, affix names and stat lines from the local item inventory."""
import os
from test_locale import ROOT, run

if __name__ == '__main__':
    os.chdir(ROOT / 'src')
    run(r'''
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p)return assert(loadfile(p..'.lua'))()end
function GetScriptPath()return '__item_translation_audit_no_save__'end
function IsKeyDown()return false end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local json=require('dkjson')
local f=assert(io.open('../tools/localization/item-source.json','rb'));local rows=json.decode(f:read('*a'));f:close()
local L=LoadModule('Modules/Localization');L.mode='zh'
local pending,counts,totals={},{},{}
for _,row in ipairs(rows)do
 L.mode='zh';row.chinese=L:Translate(row.english)
 L.mode='en';assert(L:Translate(row.english)==row.english,'English mode changed item text')
 L.mode='bilingual';local both=L:Translate(row.english)
 if row.chinese~=row.english then assert(both~=row.chinese,'Item comparison mode lost English: '..row.english)end
 totals[row.kind]=(totals[row.kind]or 0)+1
 local words={}
 for word in row.chinese:gmatch('%a%a+')do if word~='PoB'and word~='DPS'then words[#words+1]=word end end
 if #words>0 then
  row.remaining_english_words=words;pending[#pending+1]=row;counts[row.kind]=(counts[row.kind]or 0)+1
 end
end
f=assert(io.open('../tools/localization/item-display-pending.json','wb'));f:write(json.encode(pending,{indent=true}));f:close()
f=assert(io.open('../tools/localization/item-display-audit.json','wb'));f:write(json.encode({total=#rows,by_kind=totals,pending_by_kind=counts},{indent=true}));f:close()
print('Item source display audit: '..#rows..' rows; pending '..json.encode(counts))
''')
