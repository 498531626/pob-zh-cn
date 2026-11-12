"""Reviewed descriptive affix names, enabled only for source display names."""
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent


def build_names(rows):
    words=dict(line.split('\t') for line in (HERE/'craft-affix-words.tsv').read_text('utf8').splitlines()
               if line and not line.startswith('//'))
    categories={'Ailment':'异常状态','Attribute':'属性','Caster Damage':'施法伤害','Chaos':'混沌',
                'Cold':'冰霜','Critical':'暴击','Damage':'伤害','Defence':'防御','Fire':'火焰',
                'Life':'生命','Lightning':'闪电','Mana':'魔力','Physical':'物理',
                'Resistance':'抗性','Speed':'速度'}
    components={'Additional Crafted Modifier':'额外制作词缀','Additional Crafting Modifier':'额外制作词缀',
                'Attribute Requirement':'属性需求','Attribute Requirements':'属性需求',
                'Attribute Requirement Penalty':'属性需求惩罚','Attribute Requirements Penalty':'属性需求惩罚',
                'Socket Penalty':'插槽数量惩罚','Sockets Are Linked':'插槽相连',
                'White Socket':'白色插槽','White Sockets':'白色插槽',
                'Decaying Capacity':'递减容量','Decaying Duration':'递减持续时间',
                'Decaying Effect':'递减效果','Decaying Efficiency':'递减效能'}
    for en,zh in categories.items():
        components[en+' Modifier Effect']=zh+'词缀效果'
        components[en+' Modifier Effect Penalty']=zh+'词缀效果惩罚'
    for en,zh in [('Blue','蓝色'),('Green','绿色'),('Red','红色')]:
        components['No '+en+' Sockets']='无'+zh+'插槽'
        components['Only '+en+' Sockets']='仅有'+zh+'插槽'
    result={}
    for row in rows:
        if row['kind']!='affix-name':continue
        en=row['english'].strip()
        if en.startswith('Enchantment '):
            parts=en.removeprefix('Enchantment ').split(' and ')
            if all(p in components for p in parts):result[en]='附魔：'+'与'.join(components[p] for p in parts)
            continue
        if en.startswith('[UNUSED]'):
            tail=en.removeprefix('[UNUSED]').strip()
            if not tail:result[en]='（未使用）'
            for english,chinese in [('Bleed duration','流血持续时间'),('Ignite duration','点燃持续时间'),('Poison duration','中毒持续时间')]:
                if tail.startswith(english):result[en]='（未使用）'+tail.replace(english,chinese)
            continue
        base=en.removesuffix(' FIX ME')
        root=re.sub(r'^of (?:the )?','',base)
        root=root[:-2] if root.endswith("'s") else root[:-1] if root.endswith("'") else root
        if root in words:
            zh=words[root]
            if re.search(r"(?:'s|s')$",base):zh+='的'
            if en.endswith(' FIX ME'):zh+='（待修正）'
            result[en]=zh
    return result
