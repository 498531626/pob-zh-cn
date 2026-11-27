"""Exercise v2.69 loadout UI and merged control contracts without user data."""
import json
import os
import shutil
import tempfile
from contextlib import ExitStack
from pathlib import Path
from test_locale import ROOT, run


with tempfile.TemporaryDirectory(prefix='pob-2690-') as directory, ExitStack() as cleanup:
    workspace = Path(directory)
    shutil.copytree(ROOT / 'src', workspace / 'src',
                    ignore=shutil.ignore_patterns('Builds', 'Settings.xml', 'language.cfg', '__pycache__'))
    shutil.copy2(ROOT / 'manifest.xml', workspace / 'manifest.xml')
    cleanup.callback(os.chdir, Path.cwd())
    os.chdir(workspace / 'src')
    quote = lambda path: json.dumps(path.as_posix())
    run('package.path=' + quote(ROOT / 'runtime/lua/?.lua') + '..";"..' +
        quote(ROOT / 'runtime/lua/?/init.lua') + '..";"..package.path\n' +
        'package.cpath=' + quote(ROOT / 'runtime/?.dll') + '..";"..package.cpath\n' +
        'AUDIT_SOURCE=' + quote(workspace / 'src') + '\n' +
        'AUDIT_RUNTIME=' + quote(ROOT / 'runtime') + '\n' + r'''
arg = {}
local file = assert(io.open('HeadlessWrapper.lua', 'r'))
local source = file:read('*a'); file:close()
source = source:gsub('^#@', ''):gsub('dofile%("Launch.lua"%)', [[
function GetScriptPath() return AUDIT_SOURCE end
function GetRuntimePath() return AUDIT_RUNTIME end
function GetUserPath() return AUDIT_SOURCE end
io.read = function() error('Unexpected startup prompt') end
dofile('Launch.lua')
]])
assert(loadstring(source))()
newBuild()
local L = Localization
local playerName = 'Player Cyclone 玩家 配装'
build:NewLoadout(playerName)
build:SyncLoadouts()
assert(#build.loadoutsList == 2)
build.skillsTab:PasteSocketGroup('Slot: Weapon 1\nCyclone 20/0  1\n')
runCallback('OnFrame')
local renamed = playerName .. ' 改名'
build:RenameLoadout(playerName, renamed)
build:SyncLoadouts()
local copied = renamed .. ' copy'
build:CopyLoadout(renamed, copied)
build:SyncLoadouts()
assert(#build.loadoutsList == 3)
build:SetActiveLoadout(build:GetLoadoutByName(copied))
runCallback('OnFrame')
local baseline = {}
for key, value in pairs(build.calcsTab.calcsOutput) do
    if type(value) == 'number' then baseline[key] = value end
end
local saved = build:SaveDB('code')
for _, mode in ipairs({'zh', 'en', 'zh'}) do
    L.mode = mode
    build:OpenBuildSetManagePopup()
    local popup = main.popups[1]
    local list = popup.controls[1]
    local row = list:GetRowValue(1, 3, build.loadoutsList[3])
    local display = L:TranslateUI(row)
    assert(display:find(copied, 1, true), 'User loadout title was translated')
    assert(mode == 'en' and display == row or mode == 'zh' and display:find('点', 1, true), display)
    assert(L:Translate('Manage Loadouts') == (mode == 'zh' and '管理配装方案' or 'Manage Loadouts'))
    for _, screen in ipairs({{1280, 720}, {1920, 1080}, {2560, 1440}}) do
        GetVirtualScreenSize = function() return unpack(screen) end
        popup:Draw({x=0, y=0, width=screen[1], height=screen[2]}, {})
        assert(not launch.promptMsg, launch.promptMsg)
    end
    main:ClosePopup()
    assert(build:SaveDB('code') == saved, 'Language/UI changed saved loadout data')
    for key, value in pairs(baseline) do
        assert(build.calcsTab.calcsOutput[key] == value or value ~= value, key)
    end
end
loadBuildFromXML(saved, 'Loadout round trip')
assert(#build.loadoutsList == 3)
local restored = build:GetLoadoutByName(copied)
assert(build.treeTab.specList[restored.specId].title == copied)
assert(build.itemsTab.itemSets[restored.itemSetId].title == copied)
assert(build.skillsTab.skillSets[restored.skillSetId].title == copied)
assert(build.configTab.configSets[restored.configSetId].title == copied)
build.itemsTab.controls.itemList:UpdateLoadoutList()
for _, value in ipairs(build.itemsTab.controls.itemList.controls.loadoutFilter.list) do
    assert(value ~= '^7^7Manage', 'Management action leaked into item filter')
end
-- Focus may remain on a search editor while another control shows its tooltip.
local focused = {hasFocus=true, IsMouseOver=function() return false end}
local other = {IsShown=function() return true end, GetPos=function() return 0,0 end,
    GetSize=function() return 10,10 end, Draw=function(_, _, blocked) assert(not blocked) end}
local host = new('ControlHost'):ControlHost()
host.selControl = focused; host.controls = {other}
host:DrawControls({x=0, y=0, width=1280, height=720})
focused.dropped = true
other.Draw = function(_, _, blocked) assert(blocked) end
host:DrawControls({x=0, y=0, width=1280, height=720})
print('v2.69 loadouts: create/rename/copy, three resolutions, language/data/numeric preservation, XML round trip, item filter and focus tooltip contracts passed')
''')
