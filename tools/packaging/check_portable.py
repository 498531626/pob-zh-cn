"""Extract and verify a portable ZIP without opening or controlling windows."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import struct
import xml.etree.ElementTree as ET
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, nargs='?')
    parser.add_argument('--workspace', type=Path)
    args = parser.parse_args()
    if args.workspace:
        check_extracted(args.workspace)
        return
    if not args.archive:
        parser.error('An archive is required')
    with tempfile.TemporaryDirectory(prefix='PoB clean portable ') as temporary:
        with zipfile.ZipFile(args.archive) as bundle:
            assert bundle.testzip() is None, 'ZIP CRC mismatch'
            for member in bundle.namelist():
                assert not Path(member).is_absolute() and '..' not in Path(member).parts
            bundle.extractall(temporary)
        package, = Path(temporary).iterdir()
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--workspace', str(package)], check=True)


def check_extracted(package):
    info = json.loads((package / 'package-info.json').read_text(encoding='utf-8'))
    for relative, digest in info['sha256'].items():
        assert hashlib.sha256((package / relative).read_bytes()).hexdigest() == digest, relative
    manifest = ET.parse(package / 'manifest.xml').getroot()
    for entry in manifest.findall('File'):
        relative = entry.get('name')
        assert hashlib.sha1((package / relative).read_bytes()).hexdigest() == entry.get('sha1'), relative
    version = manifest.find('Version')
    assert (version.get('updates') == 'enabled') == info['automatic_updates']
    sources = manifest.findall('Source')
    if info['automatic_updates']:
        assert all(entry.get('url').startswith('https://gitee.com/') for entry in sources)
        assert next(entry.get('url') for entry in sources if entry.get('part') == 'default') + 'manifest.xml' == info['update_manifest_url']
    else:
        assert not sources, 'Offline package must not contain upstream update URLs'
    for path in package.rglob('*'):
        assert path.name.lower() not in {'settings.xml', 'language.cfg', 'poe_api_response.json', '.git', 'first.run', 'installed.cfg'}
        assert 'Builds' not in path.parts
    assert info['developer_mode'] is False
    assert (package / 'Path of Building.exe').read_bytes()[:2] == b'MZ'
    runtime = package
    # Only the extracted runtime and Windows' system directories may resolve DLLs.
    os.environ['PATH'] = str(runtime) + os.pathsep + os.path.join(os.environ['SystemRoot'], 'System32')
    with os.add_dll_directory(str(runtime)):
        libraries = list(runtime.glob('*.dll'))
        if info['automatic_updates']:
            helper = (runtime / 'Update.exe').read_bytes()
            assert helper[:2] == b'MZ'
            old_crt = runtime / 'msvcr100.dll'
            data = old_crt.read_bytes()
            assert struct.unpack_from('<H', data, struct.unpack_from('<I', data, 60)[0] + 4)[0] == 0x14c
            libraries.remove(old_crt)  # x86 updater dependency; the app and Python are x64.
        loaded = [ctypes.WinDLL(str(path)) for path in libraries]
        print(f'Native DLL loading passed: {len(loaded)} bundled libraries')
        lua = ctypes.CDLL(str(runtime / 'lua51.dll'))
        lua.luaL_newstate.restype = ctypes.c_void_p
        lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
        lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lua.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        lua.lua_tolstring.restype = ctypes.c_char_p
        lua.lua_close.argtypes = [ctypes.c_void_p]
        state = lua.luaL_newstate()
        source = package
        quote = lambda path: json.dumps(path.as_posix(), ensure_ascii=False)
        os.chdir(source)
        code = ('package.path=' + quote(runtime / 'lua/?.lua') + '..";"..'
                + quote(runtime / 'lua/?/init.lua') + '..";"..package.path\n'
                + 'package.cpath=' + quote(runtime / '?.dll') + '..";"..package.cpath\n'
                + 'AUDIT_SOURCE=' + quote(source) + '\nAUDIT_RUNTIME=' + quote(runtime) + '\n' + r'''
AUDIT_UPDATES=__UPDATES__
AUDIT_CHANNEL=__CHANNEL__
arg={}
-- Even a stale installation marker must not trigger the official updater.
if not AUDIT_UPDATES then local marker=assert(io.open('first.run','w'));marker:close() end
local f=assert(io.open('HeadlessWrapper.lua','r'));local source=f:read('*a');f:close()
source=source:gsub('^#@',''):gsub('dofile%("Launch.lua"%)',function() return [[
function GetScriptPath() return AUDIT_SOURCE end
function GetRuntimePath() return AUDIT_RUNTIME end
function GetUserPath() error('Portable build accessed external user data') end
io.read=function() error('Unexpected startup prompt') end
UPDATE_CHECKS=0
LaunchSubScript=function() UPDATE_CHECKS=UPDATE_CHECKS+1 end
dofile('Launch.lua')
]] end)
assert(loadstring(source))()
assert(not launch.devMode, 'Release package entered developer mode')
assert(launch.versionBranch==AUDIT_CHANNEL and launch.versionPlatform=='win32')
assert(launch.updatesDisabled==not AUDIT_UPDATES and not launch.updateCheckRunning)
assert(UPDATE_CHECKS==(AUDIT_UPDATES and 1 or 0), 'Unexpected automatic check count')
assert(not io.open('first.run','r'), 'Installation marker not consumed')
assert(not not main.controls.checkUpdate.shown()==AUDIT_UPDATES, 'Wrong check-update visibility')
assert(not main.controls.applyUpdate.shown(), 'Apply update button is visible')
if AUDIT_UPDATES then
 local _,uy=main.controls.checkUpdate:GetPos()
 local _,ly=main.controls.language:GetPos()
 assert(uy+20<=ly,'Update and language buttons overlap')
 launch.updateAvailable='normal';assert(main.controls.applyUpdate.shown());launch.updateAvailable=nil
end
assert(not main.controls.versionLabel.label():lower():find('dev',1,true))
assert(not main.controls.devMode.shown(), 'Developer label is visible')
for _,key in ipairs({'F5','F6','PAUSE'}) do launch:OnKeyDown(key) end
assert(not launch.doRestart, 'Developer restart shortcut is active')
launch:CheckForUpdate(true);launch:CheckForUpdate(false)
if not AUDIT_UPDATES then launch:ApplyUpdate('normal') end
assert(not launch.updateCheckRunning and not launch.doRestart)
assert(UPDATE_CHECKS==(AUDIT_UPDATES and 3 or 0))
assert(not launch.promptMsg,launch.promptMsg)
assert(main.userPath==AUDIT_SOURCE..'/', 'Nonportable save path')
assert(Localization.mode=='zh','Default language must be Chinese')
assert(Localization:Translate('Fire Resistance')=='火焰抗性')
newBuild()
build.skillsTab:PasteSocketGroup('Slot: Weapon 1\nCyclone 20/0  1\n')
runCallback('OnFrame')
local baseline={}
for k,v in pairs(build.calcsTab.calcsOutput) do if type(v)=='number' then baseline[k]=v end end
assert(next(baseline), 'No calculated outputs')
local saved=assert(build:SaveDB('portable-smoke'))
assert(saved:find('Cyclone',1,true),'Skill missing from saved XML')
for _,mode in ipairs({'zh','en','zh'}) do
 Localization.mode=mode
 for _,page in ipairs({'TREE','SKILLS','ITEMS','CALCS','CONFIG','NOTES','PARTY','IMPORT'}) do
  build.viewMode=page;runCallback('OnFrame');assert(not launch.promptMsg,launch.promptMsg)
 end
 for k,v in pairs(baseline) do
  assert(build.calcsTab.calcsOutput[k]==v or v~=v,'Calculation changed: '..k)
 end
end
loadBuildFromXML(saved,'portable-smoke-reload')
assert(not launch.promptMsg,launch.promptMsg)
for k,v in pairs(baseline) do
 assert(build.calcsTab.calcsOutput[k]==v or v~=v,'XML roundtrip changed: '..k)
end
local output=assert(io.open(AUDIT_SOURCE..'/portable-smoke.xml','w'));output:write(saved);output:close()
main:OpenOptionsPopup()
assert(not main.popups[1].controls.disableDevAutoSave, 'Developer option is visible')
main:ClosePopup()
for _,file in ipairs({'help.txt','changelog.txt'}) do
 local handle=assert(io.open(file,'r'));assert(#handle:read('*a')>0);handle:close()
end
print('Release mode, developer controls disabled, configured update controls, headless startup, Chinese default, offline calculation, 8 pages, language switching, XML save/reload passed')
''')
        code = code.replace('__UPDATES__', 'true' if info['automatic_updates'] else 'false')
        code = code.replace('__CHANNEL__', json.dumps(info.get('update_channel', 'localization')))
        try:
            lua.luaL_openlibs(state)
            result = lua.luaL_loadstring(state, code.encode('utf-8')) or lua.lua_pcall(state, 0, 0, 0)
            if result:
                raise RuntimeError(lua.lua_tolstring(state, -1, None).decode('utf-8'))
        finally:
            lua.lua_close(state)
            os.chdir(package.parent)
    print(f"Package integrity passed: {len(info['sha256'])} files; fresh extraction under a path containing spaces")
    print('No GUI was opened. Native window rendering and clean-machine OS compatibility are not tested.')


if __name__ == '__main__':
    main()
