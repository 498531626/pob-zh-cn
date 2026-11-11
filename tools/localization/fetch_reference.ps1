$ErrorActionPreference = 'Stop'
$requests = @(
    @('https://poedb.tw/cn/Skill_Gems', 'poedb-skills.html'),
    @('https://poedb.tw/us/Skill_Gems', 'poedb-skills-en.html'),
    @('https://poedb.tw/cn/Support_Gems', 'poedb-supports.html'),
    @('https://poedb.tw/us/Support_Gems', 'poedb-supports-en.html'),
    @('https://poedb.tw/data/passive-skill-tree/3.29/data_cn.json?5', 'poedb-tree-cn.json'),
    @('https://poedb.tw/data/passive-skill-tree/3.29/data_us.json?5', 'poedb-tree-us.json')
)
foreach ($request in $requests) {
    # OutFile preserves UTF-8 bytes; do not re-encode Invoke-WebRequest.Content.
    Invoke-WebRequest -Uri $request[0] -Headers @{'User-Agent'='Mozilla/5.0'} -OutFile (Join-Path $PSScriptRoot $request[1])
}
