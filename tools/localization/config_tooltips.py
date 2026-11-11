"""Translate finite source tooltip clauses; report every unresolved source line."""
import re
from config_locale import ACTIONS, STATES

PREDICATES = {
    'the enemy is Brittle': '敌人处于脆弱状态',
    'the enemy is Burning': '敌人正在燃烧',
    'the enemy is Sapped': '敌人处于力竭状态',
    'the enemy is Scorched': '敌人处于烧灼状态',
    'the enemy is Shocked': '敌人处于感电状态',
    'the enemy is Bleeding': '敌人正在流血',
    'you Totems have Hit Recently': '你的图腾近期内造成过击中',
    'you are Burning': '你正在燃烧', 'you are Chilled': '你被冰缓',
    'you are Poisoned': '你处于中毒状态', 'you are Shocked': '你处于感电状态',
    'you are channelling': '你正在引导', 'you have Blocked Recently': '你近期内进行过格挡',
    'you have Hit Recently': '你近期内造成过击中',
    'you have Killed Recently': '你近期内击杀过敌人',
    'you have Suppressed Recently': '你近期内压制过法术伤害',
    'you have been Hit Recently': '你近期内被击中过',
    'you have killed and taunted recently': '你近期内击杀并嘲讽过敌人',
    'you have used a Skill Recently': '你近期内使用过技能',
    'your Minions have Killed Recently': '你的召唤生物近期内击杀过敌人',
    'your Skills have Crit Recently': '你的技能近期内造成过暴击',
    'your Totems have Killed Recently': '你的图腾近期内击杀过敌人',
    'you have a Totem summoned': '你已召唤图腾',
}
STATS = {
    'Attack Speed': '攻击速度', 'Cast Speed': '施法速度',
    'Attack, Cast and Movement Speed': '攻击、施法及移动速度',
    'Attack, Cast, and Movement Speed': '攻击、施法及移动速度',
    'Action Speed': '行动速度', 'Damage': '伤害',
    'Damage Taken': '承受的伤害', 'Damage taken': '承受的伤害',
    'Movement Speed': '移动速度', 'Projectile Speed': '投射物速度',
    'Armour': '护甲', 'Evasion Rating': '闪避值',
    'maximum Energy Shield': '能量护盾上限', 'maximum Life': '生命上限',
    'Mana Regeneration Rate': '魔力再生率', 'character size per stack.': '每层角色体型',
    'Character Size': '角色体型', 'Area of Effect': '效果区域',
    'Physical Damage': '物理伤害', 'Elemental Damage': '元素伤害',
    'Elemental Damage taken': '承受的元素伤害',
    'Stun Duration on Enemies': '敌人被晕眩的持续时间',
    'Flask Charges gained': '药剂充能获取量', 'effect of Flasks': '药剂效果',
    'Effect of Curses': '诅咒效果', 'Effect of Curses on you': '你受到的诅咒效果',
    'Minion Attack and Cast Speed': '召唤生物攻击和施法速度',
    'Minion Movement Speed': '召唤生物移动速度', 'Minion Damage': '召唤生物伤害',
    'Life and Energy Shield Recovery Rate': '生命和能量护盾回复率',
    'chance to be Critically Hit': '被暴击几率', 'Critical Strike Chance': '暴击几率',
    'Cold Damage taken': '承受的冰霜伤害', 'Fire Damage taken': '承受的火焰伤害',
}


def compose_tooltip(line, entries, glossary):
    def term(name):
        meta = glossary.get(name) or entries.get(name)
        return meta['zh'] if meta else None
    if line in entries:
        return entries[line]['zh']
    implication = re.fullmatch(r'This also implies that (.+?)\.*', line)
    if implication and implication[1] in PREDICATES:
        return '这也表示' + PREDICATES[implication[1]] + '。'
    curse = re.fullmatch(r'Sets the level of (.+) to apply to the player\.', line)
    if curse and (zh := term(curse[1])):
        return '设置施加于玩家的' + zh + '等级。'
    curse = re.fullmatch(r'Counts (.+) as self-cast for Balance of Terror without applying it to enemies\.', line)
    if curse and (zh := term(curse[1])):
        return '为恐惧之平衡判定计入自行施放的' + zh + '，但不将此诅咒施加于敌人。'
    expose = re.fullmatch(r'This applies -10% (Cold|Fire|Lightning) Resistance to the enemy\.', line)
    if expose:
        return '使敌人的' + {'Cold':'冰霜','Fire':'火焰','Lightning':'闪电'}[expose[1]] + '抗性 -10%。'
    condition = re.fullmatch(r'This effect will only be applied while you can inflict (Brittle|Scorched)\.', line)
    if condition:
        return '仅在你可以施加' + {'Brittle':'脆弱','Scorched':'烧灼'}[condition[1]] + '时应用此效果。'
    stat = re.fullmatch(r'(\d+(?:\.\d+)?%) (increased|reduced|more|less|inc) (.+?)( per stack| per \d+ Rampage)?', line)
    if stat and stat[3] in STATS:
        prefix = '每层使' if stat[4] == ' per stack' else ('每 ' + stat[4].split()[1] + ' 层暴走使' if stat[4] else '')
        return prefix + STATS[stat[3]] + {'increased':'提高','inc':'提高','reduced':'降低','more':'总增','less':'总降'}[stat[2]] + ' ' + stat[1]
    resistance = re.fullmatch(r'([+\-]?\d+%) to all (maximum Resistances|Elemental Resistances)',line)
    if resistance:
        return '所有' + ('抗性上限' if resistance[2]=='maximum Resistances' else '元素抗性') + ' ' + resistance[1]
    regeneration = re.fullmatch(r'(\d+(?:\.\d+)?%) of Life Regenerated per second',line)
    if regeneration:
        return '每秒再生 ' + regeneration[1] + ' 生命'
    charge = re.fullmatch(r'(\d+%) chance to gain a Power, Frenzy or Endurance Charge on (Hit|Kill)',line)
    if charge:
        return ('击中' if charge[2]=='Hit' else '击败敌人') + '时有 ' + charge[1] + ' 的几率获得一个暴击球、狂怒球或耐力球'
    duration = re.fullmatch(r'Buff has a base duration of (\d+)s with a (\d+)s Cooldown',line)
    if duration:
        return '增益的基础持续时间为 ' + duration[1] + ' 秒，冷却时间为 ' + duration[2] + ' 秒'
    stacks = re.fullmatch(r'Amount of (?:stacks of )?(.+?)(?: stacks)? applied to the enemy\.',line)
    if stacks and (zh := term(stacks[1])):
        return '施加于敌人的' + zh + '层数。'
    gain = re.fullmatch(r'Gain (\d+%) of (Physical|Non-Chaos) Damage as [Ee]xtra (Cold|Lightning|Fire|Chaos) Damage', line)
    if gain:
        return '获得等同于' + {'Physical':'物理','Non-Chaos':'非混沌'}[gain[2]] + '伤害 ' + gain[1] + ' 的额外' + {'Cold':'冰霜','Lightning':'闪电','Fire':'火焰','Chaos':'混沌'}[gain[3]] + '伤害'
    shrine = re.fullmatch(r'This will enable the (.+ Shrine) buff\.', line)
    if shrine:
        label = entries.get('Have ' + shrine[1] + '?')
        if label:
            zh = label['zh'].replace('你是否拥有','').replace('是否拥有','').rstrip('？')
            return '启用' + zh + '。'
    buff = re.fullmatch(r'This will enable the (.+) buff( itself)?(, which grants:|:|\.)', line)
    if buff and (zh := term(buff[1])):
        return '启用' + zh + '增益' + ('，提供：' if buff[3] in (', which grants:', ':') else '。')
    return None
