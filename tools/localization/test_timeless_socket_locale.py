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
    assert(not translated:find('(辅)',1,true),'Support gem alias leaked into socket label')
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
assert(L:Translate('Point Blank: 46882')=='零点射击: 46882')
assert(L:Translate('Iron Grip: 31683')=='钢铁之握: 31683')
assert(L:Translate('Iron Will: 6230')=='钢铁意志: 6230')
assert(L:Translate('Point Blank Support'):find('(辅)',1,true),'Real support gem lost its suffix')
local nodesChecked=0
local nodes=build.spec.tree.legion.nodes
local function snapshotNodes()
 local result={}
 for _,node in pairs(nodes) do result[#result+1]={id=node.id,dn=node.dn,sd=node.sd} end
 return json.encode(result)
end
local sourceNodes=snapshotNodes()
local byId={};for _,node in pairs(nodes) do byId[node.id]=node end
control.dropped=false
for jewelType=1,5 do
 popup.controls.jewelSelect:SetSel(jewelType)
 local selector=popup.controls.nodeSelect
 local originalList=json.encode(selector.list)
 for _,mode in ipairs({'zh','en','zh'}) do
  L.mode=mode
  for i,entry in ipairs(selector.list) do
   local translated=L:Translate(entry.label)
   assert(selector.valueAccessor(entry)==StripEscapes(translated),'Search/display mismatch')
   if mode=='zh' then
    assert(not translated:match('%a'),'Untranslated search node: '..entry.label..' -> '..translated)
    local node=byId[entry.id]
    if node and node['not'] and node.sd[1] then
     local expected=L:Translate(node.dn)..string.rep(' ',48)..L:Translate(node.sd[1])
       ..(node.sd[2] and ' '..L:Translate(node.sd[2]) or '')
     assert(translated==expected,'Joined node stats changed: '..entry.id)
    end
   else
    assert(translated==entry.label,'English search node changed')
   end
   if entry.id then
    selector.searchTerm=translated
    selector:UpdateSearch()
    assert(selector.searchInfos[i].matches,'Displayed node cannot be searched: '..translated)
    selector:ResetSearch()
   end
   nodesChecked=nodesChecked+1
  end
  selector.selIndex=2
  for _,expanded in ipairs({false,true}) do
   selector.dropped=expanded;runCallback('OnFrame')
   assert(not launch.promptMsg,launch.promptMsg)
   assert(selector.selIndex==2,'Drawing changed node selection')
  end
 end
 selector.dropped=false
 assert(json.encode(selector.list)==originalList,'Translation changed node keys or source labels')
end
assert(snapshotNodes()==sourceNodes,'Translation changed legion data')
local trade=popup.controls.tradeTypeSelection
local originalTrade=json.encode(trade.list)
for _,mode in ipairs({'zh','en','zh'}) do
 L.mode=mode
 for i,label in ipairs(trade.list) do
  local translated=L:Translate(label)
  if mode=='zh' then assert(not translated:match('%a'),'Untranslated trade type: '..label)
  else assert(translated==label) end
  trade:SetSel(i)
  assert(build.treeTab.tradeTypeIndex==i,'Trade type selection changed')
 end
 trade.dropped=true;runCallback('OnFrame');assert(not launch.promptMsg,launch.promptMsg)
 trade.dropped=false
end
assert(json.encode(trade.list)==originalTrade,'Translation changed trade request options')
print('Timeless details: '..nodesChecked..' node/mode cases; Chinese search, joined stats, five trade options, passive/support name separation and immutable source data passed')
print('Timeless socket popup: '..checked..' socket/mode cases; expanded/collapsed drawing, title, IDs, allocation markers, selection, source labels and fallback passed')
''')
