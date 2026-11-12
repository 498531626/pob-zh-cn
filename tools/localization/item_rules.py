"""Finite, whole-clause item descriptions; never translate internal item data."""
import re

CONDITIONS = {
    'during Effect': '药剂持续期间', 'during effect': '药剂持续期间',
    'during any Flask Effect': '任意药剂持续期间', 'while affected by no Flasks': '未受到任何药剂效果影响时',
    'while Focused': '专注时', 'when you Focus': '进入专注时',
    'while Bleeding': '流血时', 'while moving': '移动时', 'while Fortified': '拥有护体时',
    'when on Low Life': '低血时', 'while on Low Life': '低血时',
    'when in Main Hand': '装备在主手时', 'when in Off Hand': '装备在副手时',
    'while you have no Energy Shield': '没有能量护盾时',
    'while you have a Bestial Minion': '拥有兽化召唤生物时',
    'while at maximum Frenzy Charges': '狂怒球达到上限时',
    'if you have Consumed a corpse Recently': '近期内消耗过灵柩时',
    'while you do not have Iron Reflexes': '未拥有霸体时',
    'against Ignited Enemies': '对被点燃的敌人', 'against Frozen Enemies': '对被冻结的敌人',
}
for name, zh in {'Agony':'苦痛', 'Thunder':'闪电', 'Purity':'纯净', 'Ash':'灰烬', 'Ice':'寒冰'}.items():
    CONDITIONS['while affected by Herald of '+name] = '受到'+zh+'之捷影响时'

WEAPONS = {'Axes':'斧类武器', 'Claws':'爪类武器', 'Daggers':'匕首', 'Maces or Sceptres':'锤或短杖',
           'Staves':'长杖', 'Swords':'剑类武器', 'Wands':'法杖', 'Melee Weapons':'近战武器',
           'Attacks':'攻击', 'Chaos Skills':'混沌技能', 'Minion Skills':'召唤生物技能'}
PER = {'Power Charge':'暴击球', 'Endurance Charge':'耐力球', 'Frenzy Charge':'狂怒球',
       'Grand Spectrum':'聚光之石', 'Level':'等级', 'White Socket':'白色插槽',
       'Red Socket':'红色插槽', 'Raised Zombie':'魔卫', 'Siphoning Charge':'轮回球', 'Chain':'连锁'}
STATS = {'maximum Life':'生命上限', 'maximum Energy Shield':'能量护盾上限',
         'Critical Strike Chance':'暴击几率', 'Critical Strike Chance for Spells':'法术暴击几率',
         'Global Critical Strike Chance':'全域暴击几率', 'Damage Over Time':'持续伤害',
         'Damage over Time':'持续伤害', 'Mine Laying Speed':'地雷投掷速度',
         'Endurance, Frenzy and Power Charge Duration':'耐力球、狂怒球和暴击球持续时间',
         'Chill and Freeze Duration on Enemies':'敌人的冰缓和冻结持续时间',
         'Prefix Modifier magnitudes':'前缀词缀数值', 'Suffix Modifier magnitudes':'后缀词缀数值',
         'Enchantment Modifier magnitudes':'附魔词缀数值', 'Stun Threshold':'晕眩门槛'}
for name, zh in {'Life':'生命', 'Mana':'魔力', 'Defence':'防御', 'Resistance':'抗性',
                 'Attribute':'属性', 'Physical':'物理', 'Physical and Chaos Damage':'物理和混沌伤害',
                 'Fire':'火焰', 'Cold':'冰霜', 'Lightning':'闪电', 'Chaos':'混沌',
                 'Elemental Damage':'元素伤害', 'Caster Damage':'施法伤害', 'Speed':'速度',
                 'Critical':'暴击', 'Ailment':'异常状态', 'Minion':'召唤生物'}.items():
    # PoEDB Tailoring Orb / Tempering Orb enchantments use this wording.
    STATS['Explicit '+name+' Modifier magnitudes'] = '外延'+zh+'词缀增幅'
AMOUNT = r'([+\-]?(?:\(\-?\d+(?:\.\d+)?-\-?\d+(?:\.\d+)?\)|\d+(?:\.\d+)?|#))'


def compose_item(text, resolve, terms):
    sockets = re.fullmatch(r'All Sockets are (Blue|Green|Red|White)', text)
    if sockets: return '所有插槽均为'+{'Blue':'蓝色','Green':'绿色','Red':'红色','White':'白色'}[sockets[1]]
    if '/' in text:
        parts = [resolve(part.strip()) for part in text.split('/')]
        if all(parts): return '\n'.join(parts)
    prefix = 'Added Small Passive Skills grant: '
    if text.startswith(prefix):
        base = resolve(text[len(prefix):])
        if base: return '增加的小天赋获得：'+base
    for suffix, zh in CONDITIONS.items():
        if text.endswith(' '+suffix):
            base = resolve(text[:-len(suffix)-1])
            if base: return zh+'，'+base
    for prefix, zh in [('Left ring slot: ', '左戒指栏位：'), ('Right ring slot: ', '右戒指栏位：')]:
        if text.startswith(prefix):
            base = resolve(text[len(prefix):])
            if base: return zh+base
    for suffix, zh in WEAPONS.items():
        if text.endswith(' with '+suffix):
            base = resolve(text[:-len(suffix)-6])
            if base: return '使用'+zh+'时，'+base
    for suffix, zh in PER.items():
        if text.endswith(' per '+suffix):
            base = resolve(text[:-len(suffix)-5])
            if base: return '每个'+zh+'使'+base if suffix!='Level' else '每级使'+base
    match = re.fullmatch(r'(.+) if (\d+) (Shaper|Elder|Crusader|Redeemer|Hunter|Warlord) Items are Equipped', text)
    if match:
        base, n, influence = match.groups(); base = resolve(base)
        if base:
            return '装备 '+n+' 件'+{'Shaper':'塑界者','Elder':'裂界者','Crusader':'圣战者','Redeemer':'救赎者','Hunter':'狩猎者','Warlord':'督军'}[influence]+'物品时，'+base
    match = re.fullmatch(AMOUNT+r'% (increased|reduced|more|less) (.+)', text)
    if match:
        value, operation, stat = match.groups()
        zh = STATS.get(stat) or terms.get(stat.casefold())
        if zh: return zh+{'increased':'提高 ', 'reduced':'降低 ', 'more':'总增 ', 'less':'总降 '}[operation]+value+'%'
    match = re.fullmatch(AMOUNT+r' (Prefix|Suffix) Modifiers? allowed', text)
    if match:
        value, kind = match.groups()
        return ('可拥有的前缀词缀数量 ' if kind=='Prefix' else '可拥有的后缀词缀数量 ')+value
    match = re.fullmatch(r'Has (\d+) (Abyssal )?Sockets?', text)
    if match: return '拥有 '+match[1]+(' 个深渊插槽' if match[2] else ' 个插槽')
    return None
