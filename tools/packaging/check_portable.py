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
    for path in package.rglob('*'):
        assert path.name.lower() not in {'settings.xml', 'language.cfg', 'poe_api_response.json', '.git', 'first.run', 'installed.cfg'}
        assert 'Builds' not in path.parts
    assert (package / 'runtime/Path of Building.exe').read_bytes()[:2] == b'MZ'
    runtime = package / 'runtime'
    # Only the extracted runtime and Windows' system directories may resolve DLLs.
    os.environ['PATH'] = str(runtime) + os.pathsep + os.path.join(os.environ['SystemRoot'], 'System32')
    with os.add_dll_directory(str(runtime)):
        loaded = [ctypes.WinDLL(str(path)) for path in runtime.glob('*.dll')]
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
        source = package / 'src'
        quote = lambda path: json.dumps(path.as_posix(), ensure_ascii=False)
        os.chdir(source)
        code = ('package.path=' + quote(runtime / 'lua/?.lua') + '..";"..'
                + quote(runtime / 'lua/?/init.lua') + '..";"..package.path\n'
                + 'package.cpath=' + quote(runtime / '?.dll') + '..";"..package.cpath\n'
                + 'AUDIT_SOURCE=' + quote(source) + '\nAUDIT_RUNTIME=' + quote(runtime) + '\n' + r'''
arg={}
local f=assert(io.open('HeadlessWrapper.lua','r'));local source=f:read('*a');f:close()
source=source:gsub('^#@',''):gsub('dofile%("Launch.lua"%)',function() return [[
function GetScriptPath() return AUDIT_SOURCE end
function GetRuntimePath() return AUDIT_RUNTIME end
function GetUserPath() error('Portable build accessed external user data') end
io.read=function() error('Unexpected startup prompt') end
dofile('Launch.lua')
]] end)
assert(loadstring(source))()
assert(launch.devMode and not launch.updateCheckRunning, 'Official updates enabled')
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
print('Headless startup, Chinese default, offline calculation, 8 pages, language switching, XML save/reload passed')
''')
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
