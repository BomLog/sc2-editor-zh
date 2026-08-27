# -*- coding: utf-8 -*-
"""翻译引擎:官方权威短语 > 本地 proper/suffix > CamelCase token 组合。
   资产代号一律保留原文。"""
import os, re, json, sys

W = os.path.dirname(os.path.abspath(__file__))
CJK = re.compile(r'[一-鿿]')

# 不可翻译的暴雪资产代号 / 缩写(保留原文)
KEEP = {
    'AB','DOM','MC','RB','AS','CU','VO','COOP','NW','NE','SW','SE','LP','SM','LG',
    'T1','T2','T3','V1','V2','EX1','EX2','EX3','EAX','BLUR','SCV','EMP','LZ','HS',
    'PH','ULBR','ID','UI','AI','AOE','HP','MP','XP','FX','SFX','VFX','LOD','DDS',
    'XML','CSV','RGB','RGBA','UV','2D','3D','PVP','PVE','NPC','DPS','CD','GUI',
    'I','II','III','IV','V','VI','VII','VIII','IX','X','A','B','C','D','E','F','G',
    'H','J','K','L','M','N','O','P','Q','R','S','T','U','W','Y','Z',
}
KEEP.update({'AC', 'BR', 'CP', 'HOT', 'LM', 'RU', 'SG', 'SOA', 'TP'})
# 通用后缀/前缀词(补充本地 suffix 词典)
EXTRA = {
    'name':'名称','tooltip':'提示','desc':'描述','description':'描述','hint':'提示',
    'editorname':'编辑器名称','editorprefix':'编辑器前缀','editorsuffix':'编辑器后缀',
    'start':'开始','end':'结束','begin':'开始','finish':'完成','init':'初始化',
    'create':'创建','destroy':'销毁','death':'死亡','birth':'诞生','spawn':'生成',
    'attack':'攻击','defend':'防御','move':'移动','stop':'停止','hold':'保持',
    'patrol':'巡逻','follow':'跟随','build':'建造','train':'训练','research':'研究',
    'upgrade':'升级','cancel':'取消','launch':'发射','impact':'冲击','hit':'命中',
    'miss':'未命中','damage':'伤害','heal':'治疗','shield':'护盾','armor':'护甲',
    'energy':'能量','life':'生命','mana':'法力','cost':'花费','range':'射程',
    'radius':'半径','speed':'速度','duration':'持续时间','delay':'延迟',
    'cooldown':'冷却','charge':'充能','stack':'叠加','buff':'增益','debuff':'减益',
    'aura':'光环','passive':'被动','active':'主动','toggle':'切换','loop':'循环',
    'idle':'待机','walk':'行走','run':'奔跑','fly':'飞行','land':'着陆',
    'lift':'升空','burrow':'潜地','unburrow':'出地','cloak':'隐形','decloak':'显形',
    'detect':'探测','reveal':'显示','hide':'隐藏','show':'显示','flash':'闪烁',
    'glow':'发光','beam':'光束','missile':'导弹','bullet':'子弹','laser':'激光',
    'explosion':'爆炸','blast':'冲击波','wave':'波','pulse':'脉冲','ring':'环',
    'splat':'贴花','decal':'贴花','shadow':'阴影','light':'光源','sound':'音效',
    'music':'音乐','voice':'语音','ambient':'环境','portrait':'头像','icon':'图标',
    'model':'模型','texture':'贴图','animation':'动画','anim':'动画',
    'unit':'单位','structure':'建筑','building':'建筑','hero':'英雄','item':'物品',
    'weapon':'武器','ability':'技能','abil':'技能','effect':'效果','behavior':'行为',
    'validator':'验证器','actor':'演算体','mover':'移动器','turret':'炮塔',
    'requirement':'需求','upgrade':'升级','achievement':'成就','reward':'奖励',
    'terran':'人类','protoss':'星灵','zerg':'异虫','neutral':'中立',
    'player':'玩家','enemy':'敌方','ally':'友方','team':'队伍','force':'阵营',
    'small':'小型','medium':'中型','large':'大型','huge':'巨型','tiny':'微型',
    'high':'高','low':'低','fast':'快速','slow':'缓慢','normal':'普通',
    'default':'默认','custom':'自定义','test':'测试','debug':'调试','temp':'临时',
    'old':'旧','new':'新','alt':'替代','var':'变体','variant':'变体',
    'male':'男性','female':'女性','left':'左','right':'右','up':'上','down':'下',
    'front':'前','back':'后','top':'顶部','bottom':'底部','center':'中心',
    'inner':'内部','outer':'外部','main':'主','sub':'子','base':'基础',
    'level':'等级','tier':'阶','rank':'级别','stage':'阶段','phase':'阶段',
    'wave':'波次','round':'回合','mission':'任务','campaign':'战役','map':'地图',
    'lab':'实验室','tech':'科技','armory':'兵工厂','mercenary':'雇佣兵',
    'evolution':'进化','mutation':'变异','mutator':'突变因子','commander':'指挥官',
    'prestige':'威望','mastery':'精通','ascension':'扬升','veterancy':'老兵',
    'placeholder':'占位','dummy':'虚拟','helper':'辅助','search':'搜索',
    'filter':'过滤器','flag':'标记','count':'数量','total':'总计','max':'最大',
    'min':'最小','value':'值','amount':'数量','rate':'速率','ratio':'比率',
    'percent':'百分比','bonus':'加成','penalty':'惩罚','modifier':'修正',
    'target':'目标','source':'来源','caster':'施法者','owner':'所有者',
    'area':'区域','region':'区域','point':'点','path':'路径','position':'位置',
    'height':'高度','width':'宽度','depth':'深度','scale':'缩放','offset':'偏移',
    'rotation':'旋转','direction':'方向','angle':'角度','facing':'朝向',
    'color':'颜色','tint':'着色','alpha':'透明度','opacity':'不透明度',
    # —— 由 _gap_tokens.txt 高频缺口补充(只补实义词;the/you/each 等虚词
    #    一律不补,否则会拼出"英雄从风暴"这类比英文更难读的硬译)
    'instance':'实例','instace':'实例','transmission':'传输信息','wait':'等待',
    'send':'发送','shutdown':'关闭','parameter':'参数','identifier':'标识符',
    'loading':'载入','list':'列表','size':'大小','weekly':'每周','egg':'卵',
    'rally':'集结','catalog':'目录','date':'日期','datetime':'日期时间',
    'highlight':'高亮','timestamp':'时间戳','speech':'语音','integer':'整数',
    'forge':'锻炉','global':'全局','resources':'资源','activity':'活动',
    'border':'边框','prophecy':'预言','experience':'经验','labels':'标签',
    'label':'标签','supplicant':'祈求者','subselection':'子选择','dark':'黑暗',
    'replacement':'替换','skip':'跳过','contact':'联络','overwrite':'覆盖',
    'singular':'单个','bit':'位','bitmask':'位掩码','tables':'数据表',
    'table':'数据表','specified':'指定','maximum':'最大值','minimum':'最小值',
    'boss':'首领','bar':'条','progress':'进度','objective':'目标',
    'cinematic':'过场动画','cutscene':'过场动画','conversation':'对话',
    'transmissiontype':'传输类型','wave':'波次','drone':'工蜂','larva':'幼虫',
    'nexus':'星灵枢纽','pylon':'水晶塔','pod':'舱','drop':'空投',
    'reticle':'准星','attach':'附加','style':'样式','challenge':'挑战',
    'mutator':'突变因子','room':'房间','story':'剧情','archives':'档案',
    'difficulty':'难度','defeated':'已失败','died':'已死亡','skipped':'已跳过',
    'created':'已创建','sent':'已发送','finished':'已完成','clicked':'点击',
    'state':'状态','string':'字符串','text':'文本','format':'格式',
    'command':'命令','cheat':'秘籍','group':'组','version':'版本',
    'alternative':'替代','original':'原始','current':'当前','last':'最后',
    'query':'查询','options':'选项','volume':'音量','fade':'淡入淡出',
    'image':'图像','model':'模型','portrait':'头像','toast':'提示条',
    'mask':'掩码','empty':'空','split':'分割','multiple':'多个',
    'starting':'初始','allied':'联盟','commanders':'指挥官','anti':'反',
    'air':'空中','ground':'地面','melee':'近战','ranged':'远程',
    'combat':'战斗','vitality':'生命力','threshold':'阈值','sort':'排序',
    'sorting':'排序','remove':'移除','units':'单位','tactical':'战术',
    'orientation':'朝向','updates':'更新','divisions':'分区','status':'状态',
    'bearings':'方位','scope':'范围','card':'卡','default':'默认',
    'lost':'已损失','energy':'能量','solar':'太阳','mastery':'精通',
    'radius':'半径','width':'宽度','height':'高度','holograms':'全息影像',
    'infiltration':'渗透','stats':'统计','mission':'任务','map':'地图',
    'panel':'面板','button':'按钮','bottom':'底部','top':'顶部',
    'main':'主要','manager':'管理器','warning':'警告','remind':'提醒',
    'spawn':'生成','creates':'创建','sets':'设置','saves':'保存',
    'returns':'返回','moves':'移动','plays':'播放','runs':'运行',
    'treat':'对待','replace':'替换','acts':'作为','matches':'匹配',
    'awarded':'奖励','loss':'失败','functionality':'功能','respawn':'重生',
    'zergling':'跳虫','hydralisk':'刺蛇','baneling':'爆虫','roach':'蟑螂',
    'mutalisk':'飞龙','ultralisk':'雷兽','corruptor':'腐化者',
    'select':'选择','selection':'选择','item':'物品','upgrade':'升级',
    'whether':'是否','value':'值','values':'值','data':'数据',
}
EXTRA.update({
    'ab':'应用行为', 'rb':'移除行为', 'as':'动作', 'cu':'创建单位',
    'coop':'合作任务', 'aoe':'范围', 'hot':'持续治疗', 'ph':'持续效果阶段',
    'tp':'传送', 'br':'移除行为', 'lm':'发射弹道', 'cp':'创建持续效果',
    'soa':'亚顿之矛', 'fx':'特效',
    'petroleum':'石油', 'incendiary':'燃烧性', 'brotherhood':'兄弟连',
    'precursor':'前置体', 'debuffs':'减益', 'stim':'兴奋剂', 'common':'通用',
    'ultrasonic':'超声波', 'availability':'可用性', 'bombed':'被炸弹影响',
    'quickfire':'速射', 'grappling':'抓钩', 'commands':'命令',
    'shrinking':'收缩', 'behind':'后方', 'maelstromed':'被大漩涡影响',
    'artifacts':'神器', 'cyber':'控制芯体', 'shine':'光耀',
    'obscure':'遮蔽', 'pathable':'可寻路', 'reheight':'调整高度',
    'lv':'等级', 'mm':'毫米', 'op':'操作', 'site':'位置',
    'operator':'操作', 'radiance':'光辉', 'to':'至',
})


def split_ident(s):
    """CamelCase / snake / 数字 拆 token,并把 3D/T1 这类数字-字母组合重新合并"""
    # 先剥标点:(Campaign) / "Set / value, / unit" 都要还原成裸词
    s = s.replace('AoEHoTHeal', 'AOE HOT')
    s = s.replace('AoEHoT', 'AOE HOT')
    s = s.replace('AoE', 'AOE').replace('HoT', 'HOT').replace('DoT', 'DOT')
    s = s.replace('BandofBrothers', 'Brotherhood')
    s = s.replace('DarkShine', 'DarkRadiance')
    s = s.replace('Healto', 'HealTo')
    s = s.replace('SOp', 'SiteOperator')
    s = re.sub(r'[()\[\]{}"\'`,;:!?]+', ' ', s)
    s = re.sub(r'[_\-\.]+', ' ', s)
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', s)
    s = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', s)
    s = re.sub(r'(?<=[A-Za-z])(?=\d)', ' ', s)
    s = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', s)
    toks = [t for t in s.split() if t]
    # 合并 数字+单字母(3D) 与 单字母+数字(T1)
    merged = []
    for t in toks:
        if merged and len(t) == 1 and t.isalpha() and merged[-1].isdigit():
            merged[-1] += t; continue
        if merged and t.isdigit() and len(merged[-1]) == 1 and merged[-1].isalpha():
            merged[-1] += t; continue
        merged.append(t)
    return merged


class Engine:
    def __init__(self):
        d = json.load(open(os.path.join(W, 'l10n_dict.json'), encoding='utf-8'))
        self.proper = {k.lower(): v for k, v in d.get('proper', {}).items()}
        self.suffix = {k.lower(): v for k, v in d.get('suffix', {}).items()}
        o = json.load(open(os.path.join(W, 'l10n_dict_official.json'), encoding='utf-8'))
        self.phrase = {k.lower(): v for k, v in o.get('phrase', {}).items()}
        self.otok = {k.lower(): v for k, v in o.get('token', {}).items()}
        # token 查表优先级: 官方 token > EXTRA > 本地 suffix > 本地 proper
        self.tokmap = {}
        for src in (self.proper, self.suffix, EXTRA, self.otok):
            for k, v in src.items():
                if v and v != k:
                    self.tokmap[k] = v

    def tr_token(self, t):
        """-> (译文, 是否命中, 是否是"字母代号原样保留")"""
        tl = t.lower()
        if re.fullmatch(r'\d+', t):
            return t, True, False               # 纯数字:合法后缀
        if re.fullmatch(r'(?:[A-Za-z]+\d+[A-Za-z]*|\d+[A-Za-z]+)', t):
            return t, True, False
        v = self.tokmap.get(tl)
        if v:
            return v, True, False
        if t.upper() in KEEP:
            # 纯字母缩写被原样保留 => 强烈暗示这是资产哈希代号
            # 含数字的组合(3D / T1 / Ex1)是合法后缀,不算代号
            return t, True, False
        return t, False, False

    def translate(self, en, allow_token=True):
        """返回 (译文, 是否全部命中)。
        allow_token=False 用于句子类(Grammar/Hint):只接受整句权威命中,
        禁止 token 逐词拼接 —— 逐词硬译("设置时间的日至")比英文更难读。"""
        en = en.strip()
        if not en or CJK.search(en):
            return en, bool(CJK.search(en))
        # 1) 整句短语命中
        v = self.phrase.get(en.lower())
        if v:
            return v, True
        # 2) 去空格后整体命中(PascalCase 形式)
        flat = re.sub(r'\s+', '', en)
        v = self.phrase.get(flat.lower()) or self.proper.get(flat.lower())
        if v and v.lower() != flat.lower():
            return v, True
        if not allow_token:
            return en, False
        # 3) token 组合
        toks = split_ident(en)
        if not toks:
            return en, False
        outs, hit, code = [], 0, 0
        for t in toks:
            tv, ok, is_code = self.tr_token(t)
            outs.append(tv)
            if ok:
                hit += 1
            if is_code:
                code += 1
        # 资产哈希代号(AHer / OTip / XOk1 / DOchChains)一律拒译:
        # 多 token 组合里只要出现"字母代号被原样保留",整条不可信
        if code and len(toks) > 1:
            return en, False
        # 短标识符(nef0 / cVc2 / ATg3)是 4~5 字符资产哈希,禁止 token 拼接,
        # 只有整体词典命中(上面第 1/2 步)才可信
        if len(flat) <= 5 and len(toks) > 1:
            return en, False
        # 没有任何实义词被译成中文 -> 拒
        if not any(CJK.search(o) for o in outs):
            return en, False
        return ''.join(outs), hit == len(toks)
