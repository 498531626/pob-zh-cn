"""Exercise real item filtering and UTF-8 editing without opening user builds."""
import os
from test_locale import ROOT, run

os.chdir(ROOT / 'src')
run(r'''
package.cpath='../runtime/?.dll;'..package.cpath
function LoadModule(p) return dofile(p..'.lua') end
function GetScriptPath() return '__localization_test_no_save__' end
function DrawString() end
function DrawStringWidth(h,f,s) return #s*h/2 end
function DrawStringCursorIndex() return 1 end
function SetDrawColor() end
function GetTime() return 0 end
local ctrl=false
function IsKeyDown(k) return k=='CTRL' and ctrl end
function PCall(f,...) local ok,result=pcall(f,...);if ok then return nil,result else return result end end
Localization=LoadModule('Modules/Localization')
local classes={}
function newClass(name) local c={};classes[name]=c;return c end
dofile('Classes/EditControl.lua')
dofile('Classes/ItemDBControl.lua')
-- Use the production OR-pattern parser, including its local table helper.
local f=assert(io.open('Modules/Common.lua'));local source=f:read('*a');f:close()
assert(loadstring('local t_insert=table.insert\n'..assert(source:match('(function string:matchOrPattern.-)\nfunction ImportBuild'))))()
local edit=setmetatable({buf='',caret=1,filterPattern='[%c]',limit=100,
 IsShown=function()return true end,IsEnabled=function()return true end,
 GetMouseOverControl=function()end,ScrollCaretIntoView=function()end,
 AddUndoState=function(self)self.lastUndoState={caret=self.caret}end}, {__index=classes.EditControl})
main={unicode=true}
for _,ch in ipairs({'守','望','之','眼'})do edit:OnChar(ch)end
assert(edit.buf=='守望之眼')
edit:OnKeyDown('BACK');assert(edit.buf=='守望之')
edit.caret=1;edit:OnKeyDown('DELETE');assert(edit.buf=='望之')
edit:OnKeyDown('RIGHT');assert(edit.caret==4)
edit:OnKeyDown('LEFT');assert(edit.caret==1)
edit.sel=1;edit.caret=#edit.buf+1;edit:OnChar('三相');assert(edit.buf=='三相')
function Paste()return '守望之眼' end
ctrl=true;edit.sel=1;edit:OnKeyDown('v');ctrl=false;assert(edit.buf=='守望之眼')
edit.caret=7;ctrl=true;edit:OnKeyDown('BACK');ctrl=false
assert(require('lua-utf8').len(edit.buf)==3)
for x=0,150 do
 local index=DrawStringCursorIndex(16,'VAR','守望之眼',x,8)
 assert(index==1 or index==4 or index==7 or index==10 or index==13)
end
local item={name="Watcher's Eye",baseName='Prismatic Jewel',
 enchantModLines={},implicitModLines={{line='+20 to maximum Life'}},
 explicitModLines={{line='+30 to maximum Mana'}},baseModList={}}
local control=setmetatable({dbType='RARE',controls={slot={selIndex=1},type={selIndex=1},
 search={},searchMode={selIndex=1}}}, {__index=classes.ItemDBControl})
local function check(query,mode,expected)
 control.controls.search.buf=query;control.controls.searchMode.selIndex=mode
 assert(not not control:DoesItemMatchFilters(item)==expected,query..' mode '..mode)
end
for _,mode in ipairs({'zh','en'})do
 Localization.mode=mode
 check('守望之眼',1,true);check('守望',2,true);check('三相珠宝',2,true)
 check('WATCHER',2,true);check('生命',3,true);check('魔力',3,true)
 check('守望之眼',3,false);check('生命',2,false);check('不存在的装备',1,false)
 check('守望|不存在',1,true);check('(',1,false);check('',1,true)
 assert(Localization.mode==mode and Localization.suspended==0)
end
assert(item.name=="Watcher's Eye" and item.implicitModLines[1].line=='+20 to maximum Life')
print('Chinese/English item names, bases, modifiers, search modes and UTF-8 input/paste/delete/caret checks passed.')
''')
