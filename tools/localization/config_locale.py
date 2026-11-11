"""Compose only actual config labels using finite UI grammar and known terms."""
import re

ALIASES = {
    'Power Charges': '暴击球', 'Frenzy Charges': '狂怒球', 'Endurance Charges': '耐力球',
    'Endur. Charges': '耐力球', 'Siphoning Charges': '轮回能量球', 'Challenger Charges': '挑战球',
    'Blitz Charges': '闪电球', 'Inspiration Charges': '启迪球', 'Blood Charges': '鲜血球',
    'Ghost Shrouds': '幽魂缠身', 'Fortification Stacks': '护体层数', 'Spirit Infusions': '精魂灌注',
    'Gale Force': '飓风之力', 'Rampage Kills': '暴走击杀', 'Soul Eater Stacks': '噬魂者层数',
    'Minion Soul Eater Stacks': '召唤生物噬魂者层数', 'Mana Burn Stacks': '魔力燃烧层数',
}
STATES = {
    'Bleeding': '正在流血', 'Blinded': '被致盲', 'Crushed': '处于碾压状态',
    'Cursed': '受到诅咒', 'Debilitated': '处于虚弱状态', 'Hindered': '被阻碍',
    'Intimidated': '受到恐吓', 'Maimed': '被瘫痪', 'Moving': '正在移动',
    'Poisoned': '处于中毒状态', 'Stunned': '被晕眩', 'Taunted': '被嘲讽',
    'Unnerved': '处于胆怯状态', 'Brittle': '处于脆弱状态', 'Chilled': '被冰缓',
    'Frozen': '被冻结', 'Sapped': '处于力竭状态', 'Shocked': '处于感电状态',
    'Burning': '正在燃烧', 'Ignited': '被点燃', 'Scorched': '处于烧灼状态',
}
ACTIONS = {
    'Attacked': '进行过攻击', 'Blocked': '进行过格挡', 'Blocked a Spell': '格挡过法术',
    'Blocked an Attack': '格挡过攻击', 'Cast a Spell': '施放过法术', 'Crit': '造成过暴击',
    'Cursed an enemy': '诅咒过敌人', 'Detonated a Mine': '引爆过地雷',
    'Hit': '造成过击中', 'Hit Recently with Your Weapon': '用武器造成过击中',
    'Hit with a Spell': '用法术造成过击中', 'Killed': '击杀过敌人', 'Linked': '进行过链接',
    'Stunned an enemy': '晕眩过敌人', 'Summoned a Totem': '召唤过图腾',
    'Suppressed': '压制过法术伤害', 'Triggered a Trap': '触发过陷阱',
    'Chilled an enemy': '冰缓过敌人', 'Frozen an enemy': '冻结过敌人',
    'Shattered an enemy': '粉碎过敌人', 'Poisoned an enemy': '使敌人中毒',
    'Shocked an enemy': '使敌人感电', 'Ignited an enemy': '点燃过敌人',
    'been Crit': '受到过暴击', 'been Hit': '被击中过', 'been Hit by an Attack': '被攻击击中过',
    'been Stunned': '被晕眩过', 'been hit by Cold': '受到过冰霜击中',
    'been hit by Light.': '受到过闪点击中', 'been hit by Fire': '受到过火焰击中',
    'cast Dash': '施放过冲刺', 'cast a Mark Spell': '施放过印记法术',
    'caused Bleeding': '造成过流血', 'dealt a Non-Crit': '造成过非暴击',
    'stopped taking DoT': '停止受到持续伤害', 'taken Spell Damage': '受到过法术伤害',
    'taken a Savage Hit': '受到过残暴打击', 'thrown a Trap or Mine': '投掷过陷阱或地雷',
    'used a Brand Skill': '使用过烙印技能', 'used a Minion Skill': '使用过召唤生物技能',
    'used a Movement Skill': '使用过位移技能', 'used a Skill': '使用过技能',
    'used a Travel Skill': '使用过旅行技能', 'used a Vaal Skill': '使用过瓦尔技能',
    'used a Warcry': '使用过战吼', 'used a Cold Skill': '使用过冰霜技能',
    'used a Fire Skill': '使用过火焰技能',
}
ELEMENTS = {'Cold': '冰霜', 'Lightning': '闪电', 'Light.': '闪电', 'Fire': '火焰',
            'Chaos': '混沌', 'Physical': '物理'}


def compose_config(label, entries, glossary):
    body = label.rstrip(':')
    def term(s):
        if s in ALIASES:
            return ALIASES[s]
        value = glossary.get(s) or entries.get(s)
        if not value and s.endswith('s'):
            value = glossary.get(s[:-1]) or entries.get(s[:-1])
        if value:
            return re.sub(r'[（(]辅[）)]$', '', value['zh'])
    patterns = [
        (r'Is (.+) active\?', '是否拥有{}？'),
        (r'Do you have (.+)\?', '你是否拥有{}？'),
        (r'Do your [Mm]inions have (.+)\?', '你的召唤生物是否拥有{}？'),
        (r'Do you use (.+)\?', '你是否使用{}？'),
        (r'Do your [Mm]inions use (.+)\?', '你的召唤生物是否使用{}？'),
        (r'# of (.+) \(if not maximum\)', '{}数量（未达到上限时）'),
        (r'# of (.+) [Ss]tacks on enemy', '敌人身上的{}层数'),
        (r'# of (.+) [Ss]tacks', '{}层数'),
        (r'# of (.+) [Ss]tacks on you', '你身上的{}层数'),
        (r'# of (.+) lost Recently', '近期内失去的{}数量'),
        (r'(.+) Life override', '{}生命覆盖值'),
        (r'# of (.+)', '{}数量'),
        (r'(.+) self-only', '{}仅作用于自身'),
        (r'Enable (.+) Aura', '启用{}光环'),
        (r'Have you used (.+) Recently\?', '你近期内是否使用过{}？'),
        (r'Used (.+) recently\?', '近期内是否使用过{}？'),
        (r'Are you on (.+)\?', '你是否处于{}上？'),
        (r'Is the enemy on (.+)\?', '敌人是否处于{}上？'),
        (r'Minion on (.+)\?', '召唤生物是否处于{}上？'),
        (r'Have (.+)\?', '你是否拥有{}？'),
    ]
    if body in entries:
        return None
    if value := term(body):
        return value + (':' if label.endswith(':') else '')
    for prefix, zh in [('Is the enemy ', '敌人是否'), ('Are you ', '你是否')]:
        if body.startswith(prefix) and body.endswith('?') and body[len(prefix):-1] in STATES:
            return zh + STATES[body[len(prefix):-1]] + '？'
    recent = re.fullmatch(r'Have (you|your Minions|your Skills|your Herald Skills|your Totems) (.+) [Rr]ecently\??', body)
    if recent and recent[2] in ACTIONS:
        who = {'you': '你', 'your Minions': '你的召唤生物', 'your Skills': '你的技能',
               'your Herald Skills': '你的捷技能', 'your Totems': '你的图腾'}[recent[1]]
        return who + '近期内是否' + ACTIONS[recent[2]] + '？'
    for element, zh in ELEMENTS.items():
        fields = {
            f'Enemy Skill {element} Damage': f'敌人技能的{zh}伤害',
            f'Enemy Skill {element} Pen': f'敌人技能的{zh}穿透',
            f'Enemy {element} Resistance': f'敌人的{zh}抗性',
            f'Enemy was Hit by {element} Damage?': f'敌人是否被{zh}伤害击中过？',
            f'Enemy hit you with {element} Damage?': f'敌人是否以{zh}伤害击中过你？',
            f'Is the enemy Exposed to {element}?': f'敌人是否处于{zh}曝露状态？',
        }
        if body in fields:
            return fields[body] + (':' if label.endswith(':') else '')
    if match := re.fullmatch(r'(\d+%) Delirious', body):
        return match[1] + ' 惊悸迷雾'
    for pattern, fmt in patterns:
        match = re.fullmatch(pattern, body)
        if match and (value := term(match[1])):
            return fmt.format(value) + (':' if label.endswith(':') else '')
