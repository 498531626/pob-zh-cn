"""Check the actual timeless socket popup in a disposable PoB source copy."""
import argparse
import json
import os
from pathlib import Path
from test_locale import ROOT, run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True, type=Path)
    workspace = parser.parse_args().workspace.resolve()
    if workspace == ROOT.resolve() or not (workspace / 'src/HeadlessWrapper.lua').is_file():
        raise SystemExit('Supply a separate disposable PoB copy')
    os.chdir(workspace / 'src')
    quote = lambda path: json.dumps(path.as_posix(), ensure_ascii=False)
    run('package.path=' + quote(ROOT / 'runtime/lua/?.lua') + '..";"..'
        + quote(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n'
        + 'package.cpath=' + quote(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n'
        + 'AUDIT_SOURCE=' + quote(workspace / 'src') + '\n'
        + 'AUDIT_RUNTIME=' + quote(ROOT / 'runtime') + '\n' + r'''
arg={}
local f=assert(io.open('HeadlessWrapper.lua','r'));local source=f:read('*a');f:close()
source=source:gsub('^#@',''):gsub('dofile%("Launch.lua"%)',function() return [[
function GetScriptPath() return AUDIT_SOURCE end
function GetRuntimePath() return AUDIT_RUNTIME end
function GetUserPath() return AUDIT_SOURCE end
io.read=function() error('Unexpected startup prompt') end
dofile('Launch.lua')
]] end)
assert(loadstring(source))()
newBuild()
build.treeTab:FindTimelessJewel()
local popup=main.popups[1]
local control=assert(popup.controls.socketSelect)
local json=require('dkjson')
local original=json.encode(control.list)
local L=Localization
local checked=0
for _,mode in ipairs({'zh','en','zh'}) do
 L.mode=mode
 assert(L:Translate(popup.title)==(mode=='zh' and '寻找永恒珠宝' or popup.title))
 for i,entry in ipairs(control.list) do
  local translated=L:Translate(entry.label)
  if mode=='zh' then
   assert(not translated:match('%a'),'Untranslated socket: '..entry.label)
   if entry.id~=-1 then
    assert(translated:match(': (%d+)$')==tostring(entry.id),'Socket ID changed')
    assert(L:Translate('# '..entry.label)=='# '..translated,'Allocated marker changed')
   end
  else
   assert(translated==entry.label,'English label changed')
  end
  control.selIndex=i
  control.dropped=false
  runCallback('OnFrame')
  control.dropped=true
  runCallback('OnFrame')
  assert(not launch.promptMsg,launch.promptMsg)
  assert(control.selIndex==i,'Drawing changed selection')
  checked=checked+1
 end
end
assert(json.encode(control.list)==original,'Drawing changed socket keys or labels')
L.mode='zh'
assert(L:Translate('Unverified Socket: 12345')=='Unverified Socket: 12345')
assert(L:Translate('^x8888FF# Conduit: 48768')=='^x8888FF# 能量连接: 48768')
print('Timeless socket popup: '..checked..' socket/mode cases; expanded/collapsed drawing, title, IDs, allocation markers, selection, source labels and fallback passed')
''')
