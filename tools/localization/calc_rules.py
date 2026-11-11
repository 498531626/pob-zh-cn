"""Reviewed, finite label composition for the actual calculation-page schema."""
RESOURCE = {'Life': '生命', 'Mana': '魔力', 'ES': '能量护盾', 'Energy Shield': '能量护盾', 'Rage': '怒火'}
RESOURCE_FIELDS = {
    '% Cost': '百分比消耗', '% per second': '每秒百分比变化', 'per second': '每秒变化',
    'Cost': '消耗', 'Gain Rate': '获取速率', 'Gain on Kill': '击杀获取', 'Gain per Hit': '击中获取',
    'Leech Cap': '偷取上限', 'Leech Rate': '偷取速率', 'Leech per Hit': '每次击中偷取',
    'on Block': '格挡获取', 'on Spell Block': '法术格挡获取', 'on Suppression': '压制时获取',
    'Reserve Mod': '保留倍率', 'Flask Charges/s': '药剂每秒充能', 'Flask Recovery Rate': '药剂回复速率',
    'Bypass %': '穿透比例'
}
AILMENTS = {'Brittle': '脆弱', 'Chill': '冰缓', 'Sap': '力竭', 'Scorch': '烧灼', 'Shock': '感电',
            'Bleed': '流血', 'Blind': '致盲', 'Freeze': '冻结', 'Ignite': '点燃', 'Impale': '穿刺',
            'Poison': '中毒', 'Curse': '诅咒', 'Silence': '沉默', 'Interrupt': '打断'}
AILMENT_FIELDS = {'Avoid Ch.': '避免几率', 'Duration': '持续时间', 'Effect': '效果', 'Effect Mod': '效果倍率'}
ELEMENTS = {'Physical': '物理', 'Phys': '物理', 'Chaos': '混沌', 'Cold': '冰霜', 'Fire': '火焰',
            'Lightning': '闪电', 'Light': '闪电', 'Light.': '闪电'}


def compose(label, translations):
    for prefix, zh in [('MH ', '主手'), ('OH ', '副手')]:
        if label.startswith(prefix) and label[len(prefix):] in translations:
            return zh + translations[label[len(prefix):]]
    for resource, zh in RESOURCE.items():
        if label.startswith(resource + ' ') and label[len(resource)+1:] in RESOURCE_FIELDS:
            return zh + RESOURCE_FIELDS[label[len(resource)+1:]]
        if label == f'Increased {resource} Regeneration Rate': return zh + '再生速度提高'
        if label == f'More {resource} Regeneration Rate': return zh + '再生速度总增'
    for ailment, zh in AILMENTS.items():
        for suffix, field in AILMENT_FIELDS.items():
            if label == ailment + ' ' + suffix: return zh + field
        for prefix, field in [('Configured', '设定'), ('Current', '当前'), ('Maximum', '最大'), ('Total', '合计')]:
            if label == prefix + ' ' + ailment: return field + zh
        if label == 'Chance to ' + ailment: return '施加' + zh + '几率'
        if label == 'Guaranteed ' + {'Brittle':'Brittles','Chill':'Chills','Sap':'Saps','Scorch':'Scorches','Shock':'Shocks'}.get(ailment, ''):
            return '保底' + zh
    for element, zh in ELEMENTS.items():
        if label == element + ' Recoup': return zh + '伤害损伤补偿'
        if label == element + ' Taken as': return zh + '承伤转化'
        if label == 'Taken as ' + element: return '转为' + zh + '承伤'
        if label == element + ' Dmg. Reduct': return zh + '伤害减免'
    return None
