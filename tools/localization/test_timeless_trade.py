"""Exercise region switching in an isolated, headless PoB without user saves."""
import json
import os
from contextlib import ExitStack
from pathlib import Path
import shutil
import tempfile
from test_locale import ROOT, run


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='pob-timeless-trade-') as directory, ExitStack() as cleanup:
        cleanup.callback(os.chdir, Path.cwd())
        workspace = Path(directory)
        shutil.copytree(ROOT / 'src', workspace / 'src',
                        ignore=shutil.ignore_patterns('Builds', 'Settings.xml', 'language.cfg', '__pycache__'))
        shutil.copy2(ROOT / 'manifest.xml', workspace / 'manifest.xml')
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
assert(main.timelessJewelTradeRegion=='cn','Default region')
local json=require('dkjson')
local pending={}
launch.DownloadPage=function(_,url,callback,options)
 pending[#pending+1]={url=url,callback=callback,options=options}
end
main.api.authToken='test-international-token'
local function reply(request,leagues,err)
 local result={}
 for _,league in ipairs(leagues) do result[#result+1]={id=league,realm='pc'} end
 request.callback({body=json.encode({result=result})},err)
end
build.treeTab:FindTimelessJewel()
local c=main.popups[1].controls
assert(pending[1].url=='https://poe.game.qq.com/api/trade/data/leagues')
assert(not pending[1].options or not pending[1].options.header,'OAuth sent to China')
assert(c.searchTradeLeagueSelect:GetSelValue()=='永久','Safe loading fallback')
assert(c.realmSelection:GetSelValue()=='PC' and not c.realmSelection.enabled)
reply(pending[1],{'永久','S31赛季（专家）','S31赛季','永久（专家）'})
assert(c.searchTradeLeagueSelect:GetSelValue()=='S31赛季','Challenge league first')
local helpers=require('Classes.TradeHelpers')
local query,opened,copied
helpers.B64GzipEncode=function(raw) query=json.decode(raw);return 'encoded' end
OpenURL=function(url) opened=url end
Copy=function(url) copied=url end
build.timelessData.jewelType={id=4}
build.timelessData.sharedResults={conqueror={id=3},devotionVariant1={id=2},devotionVariant2={id=7}}
build.timelessData.searchResults={{seed=5000},{seed=6000}}
c.tradeTypeSelection:SetSel(2)
c.searchTradeButton.onClick()
assert(opened=='https://poe.game.qq.com/trade/search/S31%E8%B5%9B%E5%AD%A3/encoded')
assert(opened==copied and query.status.option=='available')
assert(query.stats[1].filters[1].value.min==5000 and query.stats[1].filters[2].value.max==6000)
assert(query.stats[1].filters[1].id==data.timelessJewelTradeIDs[4].keystone[2])
assert(query.stats[2].filters[2].id==data.timelessJewelTradeIDs[4].devotion[6])
c.searchTradeLeagueSelect:SetSel(4)
c.tradeRegionSelection:SetSel(2)
assert(not c.searchTradeButton.lastSearch,'Batch not reset')
assert(pending[2].url=='https://www.pathofexile.com/api/trade/data/leagues')
c.realmSelection:SetSel(3)
assert(c.searchTradeLeagueSelect:GetSelValue()=='Standard')
c.tradeRegionSelection:SetSel(1)
assert(c.searchTradeLeagueSelect:GetSelValue()=='永久（专家）','China league not remembered')
reply(pending[2],{'International Test','Standard'})
assert(c.searchTradeLeagueSelect:GetSelValue()=='永久（专家）','Stale response changed China list')
assert(#build.treeTab.tradeLeaguesList['cn:pc']==4,'Cache mutated on switch')
c.tradeRegionSelection:SetSel(2)
assert(c.realmSelection:GetSelValue()=='Xbox' and c.realmSelection.enabled)
reply(pending[#pending],{'Console Test'},'offline')
assert(c.searchTradeLeagueSelect:GetSelValue()=='Standard','International error fallback')
build.treeTab.tradeLeaguesList.xbox={'Hardcore Test'}
c.tradeRegionSelection:SetSel(1)
c.tradeRegionSelection:SetSel(2)
c.searchTradeButton.onClick()
assert(opened=='https://www.pathofexile.com/trade/search/xbox/Hardcore%20Test/encoded')
assert(opened==copied)
main:ClosePopup()
build.treeTab:FindTimelessJewel()
c=main.popups[1].controls
assert(c.tradeRegionSelection:GetSelValue().id=='global','Popup choice lost')
c.tradeRegionSelection:SetSel(1)
-- Repeat an uncached failed China load; its fallback must never use Standard.
build.treeTab.tradeLeaguesList['cn:pc']=nil
c.tradeRegionSelection:SetSel(2)
c.tradeRegionSelection:SetSel(1)
pending[#pending].callback({body='true'})
assert(c.searchTradeLeagueSelect:GetSelValue()=='永久（专家）','China error fallback')
for _,mode in ipairs({'zh','en','zh'}) do
 Localization.mode=mode
 if mode=='zh' then
  assert(Localization:Translate('China')=='国服')
  assert(Localization:Translate('International')=='国际服')
  assert(Localization:Translate('Trade Site:')=='交易区服：')
 end
 for _,control in ipairs({c.tradeRegionSelection,c.realmSelection,c.searchTradeLeagueSelect}) do
  control.dropped=true;runCallback('OnFrame');control.dropped=false
  assert(not launch.promptMsg,launch.promptMsg)
 end
 local x,y=c.tradeRegionSelection:GetPos()
 local w,h=c.tradeRegionSelection:GetSize()
 for name,other in pairs({minimum=c.totalMinimumWeight,fallback=c.fallbackWeightsList,node=c.nodeSelect,maximum=c.searchMore,realm=c.realmSelection}) do
  local ox,oy=other:GetPos();local ow,oh=other:GetSize()
  assert(x+w<=ox or ox+ow<=x or y+h<=oy or oy+oh<=y,'Trade region overlap '..name..': '..x..','..y..','..w..','..h..' vs '..ox..','..oy..','..ow..','..oh)
 end
end
-- Persist the preference through the real settings serializer/loader in memory.
local saved
common.xml.SaveXMLFile=function(xml) saved=copyTable(xml);return true end
main.timelessJewelTradeRegion='global'
main:SaveSettings()
common.xml.LoadXMLFile=function() return {saved} end
main.timelessJewelTradeRegion='cn'
main:LoadSettings(true)
assert(main.timelessJewelTradeRegion=='global','Settings preference lost')
print('Timeless trade: China/international URLs, seeds/devotions, leagues, cache isolation, late responses, loading/error fallbacks, PC/console switching, popup/settings persistence and both display languages passed')
''')
