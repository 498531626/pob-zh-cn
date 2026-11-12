"""Verify complete UI messages, including coloured statuses and user payloads."""
import json
import os
from test_locale import ROOT, run

os.chdir(ROOT / 'src')
run(r'''
package.path='../runtime/lua/?.lua;'..package.path
function LoadModule(p)return dofile(p..'.lua')end
function GetScriptPath()return '__interface_test_no_save__'end
function DrawString()end
function DrawStringWidth()return 1 end
function DrawStringCursorIndex()return 0 end
function SetDrawColor()end
local L=LoadModule('Modules/Localization')
local dictionary=LoadModule('Localization/Dictionary')
local json=require('dkjson')
local function read(name)
 local f=assert(io.open('../tools/localization/'..name));local t=json.decode(f:read('*a'));f:close();return t
end
local function plain(s)return(s:gsub('%^x%x%x%x%x%x%x',''):gsub('%^%d',''))end
local count=0
for en,zh in pairs(read('interface-ui.json'))do
 L.mode='zh';assert(plain(L:Translate('^7'..en))==plain(dictionary[en] or zh),'Incomplete UI: '..en..' => '..L:Translate(en))
 L.mode='en';assert(L:Translate(en)==en,'English changed: '..en)
 count=count+1
end
L.mode='zh'
assert(L:Translate('Character import status: ^xFF8000Not authenticated')=='角色导入状态：^xFF8000未授权')
assert(L:Translate('Character import status: Logging in... (42) - URL copied to clipboard')=='角色导入状态：正在登录…（42）— 链接已复制到剪贴板')
local unknown='Character import status: Unknown service error 玩家 name'
assert(L:Translate(unknown)=='角色导入状态：Unknown service error 玩家 name')
assert(L:Translate('Current build:  Player Unnamed build 中文')=='当前构筑： Player Unnamed build 中文')
assert(L:Translate('Current build:  Unnamed build')=='当前构筑：未命名构筑')
local unholy='This will enable the Unholy Might buff.\n(Grants 100% of Physical Damage converted to ^xD02090Chaos ^7Damage)\n(25% chance to apply Wither on Hit)'
assert(not plain(L:Translate(unholy)):find('Grants',1,true),'Coloured multiline tooltip was only partially translated')
for _,name in ipairs({'Player build','玩家 "x"',"Player's build",'C:/folder/build.xml'})do
 local msg="Are you sure you want to delete '"..name.."'?"
 assert(L:Translate(msg)=='确定删除“'..name..'”吗？','Name changed: '..name)
 L.mode='en';assert(L:Translate(msg)==msg);L.mode='zh'
end
print('Interface: '..count..' exact messages, coloured and timed authentication states, unknown errors, user names and English switching passed')
''')
