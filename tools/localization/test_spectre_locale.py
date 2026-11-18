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
local glyphs = LoadModule('Localization/Glyphs').chars
local utf8 = require('lua-utf8')
local count, arenaId, shieldId = 0
for id, spectre in pairs(data.spectres) do
    local name = available:GetRowValue(1, 1, id)
    assert(name ~= spectre.name and not name:match('%a'), name)
    for _, codepoint in utf8.codes(name) do
        if codepoint > 127 then assert(glyphs[utf8.char(codepoint)], name) end
    end
    if spectre.name == 'Arena Master' then arenaId = id end
    if spectre.energyShield then shieldId = id end
    count = count + 1
end
assert(count == #available.list and count > 0)
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
    local shieldLine = StripEscapes(tip.lines[3].text)
    assert(shieldLine:find(mode == 'zh' and '能量护盾：基础生命的 ' or 'Energy Shield: ', 1, true), shieldLine)
end
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
print(('Spectre library: %d IDs, Chinese glyphs, bilingual search, tooltips, saved IDs and main skill dropdown passed'):format(count))
''')
