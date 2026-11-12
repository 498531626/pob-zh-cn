"""Whole-clause display grammar for the remaining unique-item inventory.

Named skills and passives must resolve to an existing reviewed Chinese name.
Unknown payloads never become enabled templates.
"""
import re

N = r'([+\-]?(?:\(\-?\d+(?:\.\d+)?-\-?\d+(?:\.\d+)?\)|\d+(?:\.\d+)?|#))'
ATTR = {'Strength':'力量', 'Dexterity':'敏捷', 'Intelligence':'智慧', 'Devotion':'奉献'}
MINIONS = {
    'Holy Armaments':'神圣武装', 'Living Lightning':'活体闪电', 'Raised Spectres':'灵体',
    'Raised Spiders':'蜘蛛', 'Raised Zombies':'魔卫', 'Sentinels of Absolution':'赦罪哨兵',
    'Sentinels of Dominance':'霸气哨兵', 'Sentinels of Purity':'纯净哨兵',
    'Summoned Golems':'魔像', 'Summoned Holy Relics':'圣物', 'Summoned Phantasms':'幻灵',
    'Summoned Raging Spirits':'愤怒狂灵', 'Summoned Reapers':'追命死灵',
    'Summoned Skeletons':'魔侍', 'Summoned Spectral Wolves':'幽狼',
}


def complete_item(text, resolve, terms):
    def term(name):
        return terms.get(name.casefold())
    def support(name):
        value = term(name)
        if not value: return None
        if re.search(r'[（(]强辅[)）]$', value): return value
        value = re.sub(r'[（(]辅[)）]$', '', value)
        return value if value.endswith('辅助') else value+'辅助'
    schemas = [
        (N+r' to Level of all (.+) Gems', lambda m: '所有'+term(m[2])+'宝石等级 '+m[1] if term(m[2]) else None),
        (N+r' Added Passive Skill is (.+)', lambda m: m[1]+' 个增加的天赋为'+term(m[2]) if term(m[2]) else None),
        (r'Socketed (Gems|Slam Gems|Spells) are [Ss]upported by [Ll]evel '+N+r' (.+)',
         lambda m: '插槽内的'+{'Gems':'宝石','Slam Gems':'猛击宝石','Spells':'法术'}[m[1]]+'受到 '+m[2]+' 级'+support(m[3]) if support(m[3]) else None),
        (r'Grants Level '+N+r' (.+) Skill', lambda m: '获得 '+m[1]+' 级'+term(m[2])+'技能' if term(m[2]) else None),
        (r'Grants (.+) Skill', lambda m: '获得'+term(m[1])+'技能' if term(m[1]) else None),
        (r'(.+) has no Reservation', lambda m: term(m[1])+'没有保留效果' if term(m[1]) else None),
        (r'Aura Skills other than (.+) are Disabled', lambda m: '除'+term(m[1])+'以外的光环技能被禁用' if term(m[1]) else None),
        (r'Unaffected by (.+)', lambda m: '不受'+term(m[1])+'影响' if term(m[1]) else None),
        (r'Immune to (.+)', lambda m: '免疫'+term(m[1]) if term(m[1]) else None),
        (r'Requires Class (.+)', lambda m: '职业需求：'+term(m[1]) if term(m[1]) else None),
    ]
    for pattern, render in schemas:
        m = re.fullmatch(pattern, text)
        if m:
            result = render(m)
            if result: return result
    m = re.fullmatch(r'(Cannot have Minions other than|Maximum number of) (.+?)( is Doubled)?', text)
    if m and m[2] in MINIONS:
        name = MINIONS[m[2]]
        if m[1]=='Cannot have Minions other than' and not m[3]: return '无法拥有'+name+'以外的召唤生物'
        if m[1]=='Maximum number of' and m[3]: return name+'数量上限翻倍'
    wrappers = [
        (r'Passive Skills in Radius also grant (.+)', lambda m,b: '范围内的天赋还提供'+b),
        (r'(.+) while using (.+)', lambda m,b: '使用'+term(m[2])+'时，'+b if term(m[2]) else None),
        (r'(.+) per '+N+r' (Strength|Dexterity|Intelligence|Devotion)', lambda m,b: '每 '+m[2]+' 点'+ATTR[m[3]]+'使'+b),
        (r'(.+) if you\x27ve cast (.+) in the past '+N+r' seconds', lambda m,b: '过去 '+m[3]+' 秒内施放过'+term(m[2])+'时，'+b if term(m[2]) else None),
        (r'(.+) when Socketed with a (Red|Green|Blue) Gem', lambda m,b: '插入'+{'Red':'红色','Green':'绿色','Blue':'蓝色'}[m[2]]+'宝石时，'+b),
        (r'(.+) per Raised Spectre', lambda m,b: '每个灵体使'+b),
        (r'(.+) per Skeleton you own', lambda m,b: '每个你拥有的魔侍使'+b),
        (r'(.+) for each Map Item Modifier affecting the Area', lambda m,b: '每个影响此区域的地图词缀使'+b),
        (r'(.+) if you have used a (Fire|Cold) Skill Recently', lambda m,b: '近期内使用过'+{'Fire':'火焰','Cold':'冰霜'}[m[2]]+'技能时，'+b),
        (r'(.+) if you\x27ve used a Movement Skill Recently', lambda m,b: '近期内使用过位移技能时，'+b),
        (r'(.+) if you\x27ve Consumed a Corpse Recently', lambda m,b: '近期内消耗过灵柩时，'+b),
        (r'(.+) if you\x27ve Ignited an Enemy Recently', lambda m,b: '近期内点燃过敌人时，'+b),
        (r'(.+) while Poisoned', lambda m,b: '中毒时，'+b),
        (r'(.+) while Unarmed', lambda m,b: '空手时，'+b),
        (r'(.+) while Sane', lambda m,b: '理智状态下，'+b),
        (r'(.+) during Soul Gain Prevention', lambda m,b: '阻灵术期间，'+b),
        (r'(.+) while affected by Glorious Madness', lambda m,b: '受到疯狂荣光影响时，'+b),
    ]
    for pattern, render in wrappers:
        m = re.fullmatch(pattern, text)
        if m:
            base = resolve(m[1])
            if base:
                result = render(m,base)
                if result: return result
    return None
