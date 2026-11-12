"""Finite crafting clauses; checked terms only, no parser or save changes."""
import re
from item_completion import N


def complete_craft(text, resolve, terms):
    def term(en): return terms.get(en.casefold())
    if '\n' in text:
        parts=[resolve(line.strip()) for line in text.splitlines()]
        if all(parts): return '\n'.join(parts)
    wrappers=[
        (r'Added Small Passive Skills also grant: (.+)',lambda m,b:'增加的小天赋还提供：'+b),
        (r'While a Pinnacle Atlas Boss is in your Presence, (.+)',lambda m,b:'终极异界首领处于你的周围时，'+b),
        (r'While a Unique Enemy is in your Presence, (.+)',lambda m,b:'传奇敌人处于你的周围时，'+b),
        (r'(.+) from Melee Weapons',lambda m,b:'近战武器造成的'+b),
        (r'(.+) with Melee Weapons',lambda m,b:'使用近战武器时，'+b),
        (r'(.+) while holding a Shield',lambda m,b:'持盾时，'+b),
        (r'(.+) if no Equipped Items are Corrupted',lambda m,b:'未装备任何已腐化物品时，'+b),
        (r'(.+) per Corrupted Item Equipped',lambda m,b:'每装备一件已腐化物品，'+b),
        (r'(.+) for each Corrupted Item Equipped',lambda m,b:'每装备一件已腐化物品，'+b),
        (r'(.+) while you are affected by a Herald',lambda m,b:'你受到捷影响时，'+b),
        (r'(.+) while affected by a Herald',lambda m,b:'受到捷影响时，'+b),
        (r'(.+) against Cursed Enemies',lambda m,b:'对被诅咒的敌人，'+b),
        (r'(.+) if you have Blocked Recently',lambda m,b:'近期内格挡过时，'+b),
        (r'(.+) if you have at least '+N+r' Strength',lambda m,b:'至少有 '+m[2]+' 点力量时，'+b),
        (r'(.+) if you have Hit an Enemy Recently',lambda m,b:'近期内击中过敌人时，'+b),
        (r'(.+) if you haven\x27t Killed Recently',lambda m,b:'近期内未击败敌人时，'+b),
        (r'(.+) if you haven\x27t been Hit Recently',lambda m,b:'近期内未被击中时，'+b),
        (r'(.+) if you\x27ve Killed a Cursed Enemy Recently',lambda m,b:'近期内击败过被诅咒的敌人时，'+b),
        (r'(.+) when on Full Life',lambda m,b:'满血时，'+b),
        (r'(.+) while you have no Frenzy Charges',lambda m,b:'没有狂怒球时，'+b),
        (r'(.+) while Chilled or Frozen',lambda m,b:'被冰缓或冻结时，'+b),
        (r'(.+) while Cursed',lambda m,b:'被诅咒时，'+b),
        (r'(.+) while Shocked',lambda m,b:'被感电时，'+b),
        (r'(.+) while Leeching',lambda m,b:'偷取时，'+b),
        (r'(.+) while stationary',lambda m,b:'静止时，'+b),
        (r'(.+) while moving',lambda m,b:'移动时，'+b),
        (r'(.+) per Keystone',lambda m,b:'每个至高天赋使'+b),
        (r'(.+) per allocated Keystone',lambda m,b:'每个已分配的至高天赋使'+b),
        (r'(.+) per Chest opened Recently',lambda m,b:'近期内每打开一个箱子使'+b),
        (r'(.+) per '+N+r' Rage',lambda m,b:'每 '+m[2]+' 点怒火使'+b),
        (r'(.+) for each corpse Consumed Recently',lambda m,b:'近期内每消耗一具灵柩使'+b),
        (r'(.+) while at Maximum Frenzy Charges',lambda m,b:'狂怒球达到上限时，'+b),
    ]
    for pat,render in wrappers:
        m=re.fullmatch(pat,text)
        if m:
            base=resolve(m[1])
            if base:return render(m,base)
    m=re.fullmatch(r'Adds '+N+r' to '+N+r' (Physical|Fire|Cold|Lightning|Chaos) Damage to Attacks against you',text)
    if m:return '对你的攻击附加 '+m[1]+' - '+m[2]+' '+{'Physical':'物理','Fire':'火焰','Cold':'冰霜','Lightning':'闪电','Chaos':'混沌'}[m[3]]+'伤害'
    m=re.fullmatch(r'Skills used by this Graft (have|deal|Gain|penetrate|fire) (.+)',text)
    if m:
        prefix={'have':'','deal':'','Gain':'Gain ','penetrate':'Penetrate ','fire':'Fire '}[m[1]]
        base=resolve(prefix+m[2])
        if base:return '此嫁接施放的技能：'+base
    m=re.fullmatch(r'Minions summoned by this Graft (have|deal|gain) (.+)',text)
    if m:
        base=resolve('Minions '+m[1]+' '+m[2]) or resolve(('Gain ' if m[1]=='gain' else '')+m[2])
        if base:return '此嫁接召唤的生物：'+base
    m=re.fullmatch(r'Trigger Level '+N+r' (.+) (when you use a Socketed Skill|on Melee Hit with this Weapon|on Hit)',text)
    if m and term(m[2]):return {'when you use a Socketed Skill':'使用插槽内技能时','on Melee Hit with this Weapon':'使用此武器近战击中时','on Hit':'击中时'}[m[3]]+'触发 '+m[1]+' 级'+term(m[2])
    m=re.fullmatch(N+r'% chance to Trigger (.+) on Kill',text)
    if m and term(m[2]):return '击败敌人时有 '+m[1]+'% 的几率触发'+term(m[2])
    m=re.fullmatch(N+r'% increased Effect of Socketed (Magic|Rare) (Ghastly|Hypnotic|Murderous|Searching) Eye Jewels',text)
    if m:return '插槽内'+{'Magic':'魔法','Rare':'稀有'}[m[2]]+{'Ghastly':'苍白','Hypnotic':'催眠','Murderous':'凶残','Searching':'锐利'}[m[3]]+'之凝珠宝的效果提高 '+m[1]+'%'
    m=re.fullmatch(N+r'% of (Physical Attack|Physical|Fire|Cold|Lightning|Chaos) Damage Leeched by Enemy as (Life|Mana)',text)
    if m:return '敌人将造成的'+{'Physical Attack':'物理攻击','Physical':'物理','Fire':'火焰','Cold':'冰霜','Lightning':'闪电','Chaos':'混沌'}[m[2]]+'伤害的 '+m[1]+'% 转化为'+{'Life':'生命','Mana':'魔力'}[m[3]]+'偷取'
    return None
