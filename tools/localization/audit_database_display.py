"""Audit display fields from the database inventory."""
import os
import csv
import json
from pathlib import Path
from test_locale import ROOT, run

if __name__ == '__main__':
    os.chdir(ROOT / 'src')
    run(r'''
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p)return assert(loadfile(p..'.lua'))()end
function GetScriptPath()return '__database_translation_audit_no_save__'end
function IsKeyDown()return false end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local json=require('dkjson')
local f=assert(io.open('../tools/localization/database-source.json','rb'));local rows=json.decode(f:read('*a'));f:close()
local L=LoadModule('Modules/Localization');L.mode='zh'
local pending,counts,totals,numberIssues,numberNotes={},{},{},{},{}
local function plain(text)return text:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d','')end
local function numbers(text)
 local values={};for n in plain(text):gmatch('[+-]?%d+%.?%d*')do values[#values+1]=tonumber(n)end
 table.sort(values);return table.concat(values,',')
end
for _,row in ipairs(rows)do
 L.mode='zh';row.chinese=L:Translate(row.english)
 L.mode='en';assert(L:Translate(row.english)==row.english,'English mode changed database text')
 L.mode='bilingual';local both=L:Translate(row.english)
 if row.chinese~=row.english then
  assert(both~=row.chinese,'Database comparison mode lost English: '..row.english)
  if row.kind:find('stat',1,true)or row.kind=='boss-skill-tooltip'then
   if numbers(row.chinese)~=numbers(row.english)then
    if row.english=='6% chance to gain a Frenzy Charge on Kill'and plain(row.chinese)=='击败敌人后有 6% 的几率获得 1 个狂怒球'then
     numberNotes[#numberNotes+1]={english=row.english,reason='PoEDB makes the singular article a explicit as 1; chance and charge count are unchanged.'}
    else numberIssues[#numberIssues+1]=row end
   end
  end
 end
 totals[row.kind]=(totals[row.kind]or 0)+1
 local words={}
 for word in plain(row.chinese):gmatch('%a%a+')do if word~='PoB'and word~='DPS'then words[#words+1]=word end end
 if #words>0 then
  row.remaining_english_words=words;pending[#pending+1]=row;counts[row.kind]=(counts[row.kind]or 0)+1
 end
end
f=assert(io.open('../tools/localization/database-display-pending.json','wb'));f:write(json.encode(pending,{indent=true}));f:close()
f=assert(io.open('../tools/localization/database-display-audit.json','wb'));f:write(json.encode({total=#rows,by_kind=totals,pending_by_kind=counts,number_issues=numberIssues,number_notes=numberNotes},{indent=true}));f:close()
print('Database display audit: '..#rows..' rows; pending '..json.encode(counts))
assert(#numberIssues==0,'Database number differences require review; see database-display-audit.json')
''')
    here = ROOT/'tools/localization'
    report = json.loads((here/'database-display-audit.json').read_text('utf8'))
    pending = json.loads((here/'database-display-pending.json').read_text('utf8'))
    kinds = {'essence-name':'精华名称', 'currency-name':'通货名称', 'spectre-name':'灵体名称',
             'minion-name':'召唤物名称', 'pantheon-name':'万神殿名称', 'pantheon-stat':'万神殿属性',
             'tattoo-name':'纹身及符文之结名称', 'tattoo-stat':'纹身及符文之结属性',
             'enchantment-stat':'附魔属性', 'craft-extra-stat':'兽园及熔炉工艺属性',
             'craft-affix':'工艺词缀名称', 'cluster-name':'星团名称', 'cluster-stat':'星团属性',
             'boss-skill-name':'首领技能预设名称', 'boss-skill-tooltip':'首领技能预设说明'}
    with (here/'database-display-pending.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['类别','英文原文','当前中文显示','源码位置'])
        for row in pending: writer.writerow([kinds[row['kind']],row['english'],row['chinese'],row['source']])
    lines = ['# 数据库汉化检查','',
             '检查当前源码中的显示字段；内部 ID、解析键和计算数据不纳入翻译。含英文的未核对条目保留原文。',
             '当前报告通过三种语言模式与已翻译属性的数值保持检查；不代表所有构筑的界面验收。','',
             '| 类别 | 检查条目 | 尚有英文 |','| --- | ---: | ---: |']
    for kind,total in sorted(report['by_kind'].items()):
        lines.append(f'| {kinds[kind]} | {total} | {report["pending_by_kind"].get(kind,0)} |')
    lines += ['', '同一文本在不同类别中分别计数。历史、特殊及当前参考未覆盖的内容仍可能显示英文。',
              '配对统计会保留参考资料中的译名歧义；人工核对记录和既有词典可能已解决这些歧义，以本表的实际显示检查为准。', '',
              '- [待核对清单（CSV，Excel 可打开）](database-display-pending.csv)',
              '- [待核对清单（JSON，含源码位置）](database-display-pending.json)',
              '- [参考配对统计与译名冲突](database-coverage.json)',
              '- [物品库待核对清单](item-display-pending.json)',
              '- [实际物品浮窗待核对清单](item-runtime-pending.json)', '',
              '生成：`python tools/localization/audit_database_display.py`。']
    (here/'数据库汉化检查.md').write_text('\n'.join(lines)+'\n','utf8')
