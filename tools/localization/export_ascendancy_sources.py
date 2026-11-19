"""Export current ascendancy display fields without loading settings or saves."""
import hashlib
import json
import os
from pathlib import Path

from test_locale import ROOT, run

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / 'pob-ascendancies-en.json'


if __name__ == '__main__':
    previous = Path.cwd()
    try:
        os.chdir(ROOT / 'src')
        run('package.path=' + json.dumps((ROOT / 'runtime/lua/?.lua').as_posix())
            + '..";"..package.path\nlocal output=' + json.dumps(OUTPUT.as_posix()) + '\n' + r'''
local json=require('dkjson')
local trees={}
for _,version in ipairs({'3_30','3_30_ruthless'})do
 local tree=dofile('TreeData/'..version..'/tree.lua')
 local nodes={}
 for id,node in pairs(tree.nodes)do
  if node.ascendancyName then
   nodes[tostring(id)]={name=node.name,stats=node.stats,reminderText=node.reminderText,
    flavourText=node.flavourText,ascendancyName=node.ascendancyName}
  end
 end
 trees[version]=nodes
end
local file=assert(io.open(output,'wb'));file:write(json.encode(trees));file:close()
''')
        trees = json.loads(OUTPUT.read_text('utf8'))
        report = {'trees': trees, 'source_sha256': {
            version: hashlib.sha256((ROOT / 'src/TreeData' / version / 'tree.lua').read_bytes()).hexdigest()
            for version in trees}}
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf8')
    finally:
        os.chdir(previous)
