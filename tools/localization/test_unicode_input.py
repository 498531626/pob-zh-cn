"""Check startup capability detection after lua-utf8 creates its global."""
import os
from test_locale import ROOT, run


if __name__ == '__main__':
    os.chdir(ROOT / 'src')
    run(r'''
package.cpath='../runtime/?.dll;'..package.cpath
local utf8=require('lua-utf8')
assert(type(_G.utf8)=='table','Fixture must reproduce the real library side effect')
local file=assert(io.open('Modules/Main.lua','r'))
local source=file:read('*a');file:close()
local detect=assert(source:match('(function main:DetectUnicodeSupport%(%).-\nend)'))
local calls,installed,notices=0,false,0
local unicodeInput={Install=function()calls=calls+1;return installed end}
local env=setmetatable({main={},unicodeInput=unicodeInput,
 ConPrintf=function()notices=notices+1 end},{__index=_G})
setfenv(assert(loadstring(detect)),env)()
for _,globalPresent in ipairs({true,false}) do
 for _,bridgeAvailable in ipairs({true,false}) do
  local globals=globalPresent and {utf8=utf8} or {}
  env._G=globals;installed=bridgeAvailable
  local before=calls
  env.main:DetectUnicodeSupport()
  assert(calls==before+1,'UTF-8 library global skipped native input installation')
  assert(env.main.unicode==(globalPresent or bridgeAvailable),'Capability fallback changed')
 end
end
assert(notices==3)
-- Reproduce startup module order: Common loads lua-utf8 before Main detects
-- character support. Confirm the production bridge handles headless startup.
function LoadModule(path)return dofile(path..'.lua')end
local bridge=LoadModule('Modules/UnicodeInput')
assert(bridge:Install()==false,'Headless runtime unexpectedly owns a GLFW window')
print('Unicode startup: bridge always attempted with/without utf8 global; native, alternate-runtime and headless fallbacks passed')
''')
