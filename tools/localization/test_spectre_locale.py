"""Exercise the real spectre library in a disposable PoB copy."""
import argparse
import json
import os
from pathlib import Path
from test_locale import ROOT, run

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
workspace = parser.parse_args().workspace.resolve()
if workspace == ROOT.resolve() or not (workspace / 'src/HeadlessWrapper.lua').is_file():
    raise SystemExit('Supply a separate disposable PoB copy')
os.chdir(workspace / 'src')
quote = lambda path: json.dumps(path.as_posix(), ensure_ascii=False)
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
local locale = Localization
locale.mode = 'zh'
assert(locale:Translate('<No spectres in build>') == '<构筑中没有灵体>')
assert(locale:Translate('Necromancer') == '召唤师')
assert(locale.SpectreName('Necromancer') == '死灵法师')
build:OpenSpectreLibrary()
local controls = main.popups[1].controls
local available, selected = controls.source, controls.list
local recommendedCount = #available.list
assert(recommendedCount > 0)
controls.sortMonsterCheckboxShowAll.state = true
controls.sortMonsterCheckboxShowAll.changeFunc(true)
assert(#available.list > recommendedCount, 'Show All must retain the upstream recommended filter')
local glyphs = LoadModule('Localization/Glyphs').chars
local utf8 = require('lua-utf8')
local count, shownCount, arenaId, shieldId = 0, 0
local categories = {Beast=true, Humanoid=true, Eldritch=true, Construct=true, Demon=true, Undead=true}
for id, spectre in pairs(data.spectres) do
    local name = available:GetRowValue(1, 1, id)
    assert(name ~= spectre.name and name:find('[\128-\255]'), name)
    for _, codepoint in utf8.codes(name) do
        if codepoint > 127 then assert(glyphs[utf8.char(codepoint)], name) end
    end
    if spectre.name == 'Arena Master' then arenaId = id end
    if spectre.energyShield then shieldId = id end
    if categories[spectre.monsterCategory] then shownCount = shownCount + 1 end
    count = count + 1
end
assert(shownCount == #available.list and count > 0, ('Categorized spectre IDs %d / shown %d'):format(shownCount, #available.list))
assert(arenaId and shieldId)
local search = available.controls.searchText
for _, mode in ipairs({'zh', 'en', 'zh'}) do
    locale.mode = mode
    for _, term in ipairs({'竞技场大师', 'ARENA MASTER'}) do
        search:SetText(term, true)
        assert(#available.list == 1 and available.selValue == arenaId, term)
    end
    assert(available:GetRowValue(1, 1, arenaId) == (mode == 'zh' and '竞技场大师' or 'Arena Master'))
    local tip = new('Tooltip'):Tooltip()
    available:AddValueTooltip(tip, 1, shieldId)
    assert(StripEscapes(tip.lines[1].text) == available:GetRowValue(1, 1, shieldId))
    local shieldLine
    for _, line in ipairs(tip.lines) do
        if line.text and StripEscapes(line.text):find(mode == 'zh' and '能量护盾：基础生命的 ' or 'Energy Shield: ', 1, true) then shieldLine = line.text end
    end
    assert(shieldLine, 'Missing translated Energy Shield tooltip')
end
search:SetText('', true)
for sort = 1, 12 do
    available.controls.sortModeDropDown:SetSel(sort)
    assert(#available.list == shownCount, 'Sorting lost categorized IDs')
end
local areaCount = 0
for _, spectre in pairs(data.spectres) do
    for _, location in ipairs(spectre.spawnLocation) do
        local translated = locale.SpectreLocation(location)
        assert(translated ~= location and translated:find('[\128-\255]'), translated)
        locale.mode = 'en'; assert(locale.SpectreLocation(location) == location); locale.mode = 'zh'
        areaCount = areaCount + 1
    end
end
search:SetText('竞技场大师', true)
controls.source.controls.add:Click()
assert(selected.list[1] == arenaId and selected:GetRowValue(1, 1, arenaId) == '竞技场大师')
assert(#build.spectreList == 0)
controls.save:Click()
assert(build.spectreList[1] == arenaId)
local saved = {}
build:Save(saved)
assert(saved[1].elem == 'Spectre' and saved[1].attrib.id == arenaId)
assert(data.spectres[arenaId].name == 'Arena Master')

build.skillsTab:PasteSocketGroup('Slot: Weapon 1\nRaise Spectre 20/0  1\n')
runCallback('OnFrame')
local dropdown = build.controls.mainSkillMinion
local entry = dropdown.list[dropdown.selIndex]
assert(entry and entry.minionId == arenaId and entry.label == 'Arena Master', 'Wrong spectre dropdown entry')
assert(dropdown:GetDisplayLabel(entry) == '竞技场大师')
locale.mode = 'en'
assert(dropdown:GetDisplayLabel(entry) == 'Arena Master')
assert(dropdown:GetDisplayLabel(nil) == nil)
print(('Spectre library: %d IDs, %d spawn labels, 12 sorts, Chinese glyphs, bilingual search, tooltips, saved IDs and main skill dropdown passed'):format(count, areaCount))
''')
