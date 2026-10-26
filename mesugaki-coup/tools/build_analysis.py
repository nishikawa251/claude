"""sim_summary.json からトリガー分析ページを生成する。
usage: python3 build_analysis.py <sim_summary.json> <out_artifact.html> <out_repo.html> [posHexDark negHexDark]
"""
import json, sys, html

src, out_art, out_repo = sys.argv[1], sys.argv[2], sys.argv[3]
pos_dark = sys.argv[4] if len(sys.argv) > 4 else '#f05a97'
neg_dark = sys.argv[5] if len(sys.argv) > 5 else '#4aa3f0'
d = json.load(open(src, encoding='utf-8'))
# 山の枚数は index.html の TRIGGERS 定義（count）から読む
import os, re as _re
_idx = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.html'), encoding='utf-8').read()
CNAME = {}
for _m in _re.finditer(r"\{ id:'(t\d+)',\s*name:'([^']+)'", _idx):
    CNAME[_m.group(1)] = _m.group(2)
RETIRED = [_m.group(1) for _m in _re.finditer(r"\{ id:'(t\d+)',[^\n]*retired:true", _idx)]
_rules = {k: v for k, v in _re.findall(r"(\w+):\s*(\d+),", _idx[_idx.find('const RULES = {'):_idx.find('};', _idx.find('const RULES = {'))])}
TEXT = {}
for _m in _re.finditer(r"\{ id:'(t\d+)',\s*name:'([^']+)',\s*text:(?:'([^']*)'|`([^`]*)`)", _idx):
    _t = _m.group(3) if _m.group(3) is not None else _m.group(4)
    TEXT[_m.group(1)] = _re.sub(r'\$\{RULES\.(\w+)\}', lambda mm: _rules.get(mm.group(1), '?'), _t)
_dud = int(_re.search(r"dudCount:\s*(\d+)", _idx).group(1))
PRESETS = {}
for _m in _re.finditer(r"(basic|fresh|mix):\s*\[([^\]]*)\]", _idx[_idx.find('const DECK_PRESETS'):_idx.find('const DECK_SIZE')]):
    PRESETS[_m.group(1)] = _re.findall(r"'(t\d+)'", _m.group(2))
SETS = {}
for _m in _re.finditer(r"(basic|fresh):\s*\[([^\]]*)\]", _idx[_idx.find('const SETS = {'):_idx.find('};', _idx.find('const SETS = {'))]):
    SETS[_m.group(1)] = _re.findall(r"'(t\d+)'", _m.group(2))
_inpreset = {i for v in SETS.values() for i in v}
PERSIST = {_m.group(1) for _m in _re.finditer(r"\{ id:'(t\d+)',[^\n]*persistent:true", _idx)}
DECK = {'dud': _dud, 'presets': {k: [CNAME[i] for i in v] for k, v in PRESETS.items()}, 'bench': [CNAME[i] for i in CNAME if i not in _inpreset and i not in RETIRED], 'retired': [CNAME[i] for i in RETIRED]}
# 物理版の枚数（index.html の定義から数える）
_chars = _re.findall(r"\{ id:'([a-z]+)',\s*name:'([^']+)' \}", _idx[_idx.find('const CHARS'):_idx.find('const CHARS')+2000])
N_CHARS = len(_chars); N_ROLES = 5; N_TRIG = len(CNAME); N_PRESET = sum(len(v) for v in PRESETS.values())

EFF = TEXT   # id -> カードの文言（index.html から）

CANDS = [["デッキ混成", "基本と新カードから6枚ずつ", "開始画面のカスタムで試せる。両デッキの上位札を混ぜると強い札が増えるので、下位どうしを混ぜるのも一案"], ["ハズレ1枚", "効果なしの札を1枚だけ入れる", "「脱いだのに何も起きない」場面を1割弱混ぜる。RULES.dudCount で切り替え"]]
# 「使っておもしろいか」の主観点（1〜5）。決断・駆け引き・派手さ・巻き込みで採点
FUN = {'t41':3,'t29':5,'t30':4,'t31':3,'t32':2,'t33':4,'t34':4,'t35':4,'t36':2,'t37':3,'t38':3,'t39':3,'t40':3,'t1':5,'t2':2,'t3':2,'t5':5,'t6':3,'t8':3,'t9':4,'t10':3,'t11':3,'t12':3,'t14':3,'t17':4,'t18':3,'t19':5,'t20':3,'t21':5,'t22':4,'t23':2,'t24':4,'t25':3,'t26':3,'t27':2,'t28':5,'t16':5,'t4':2,'t7':3,'t13':2,'t15':3}
FUN_WHY = {'t41':'まけちゃえ～♥を封じる保険。公開後は狙われなくなる','t29':'ばいば～い♥が跳ね返る大逆転','t30':'第三者を巻き込む','t31':'狙われるほど儲かる','t32':'自分へのばいば～い♥だけ2♥高くなる地味な守り','t33':'安いが精度が落ちる駆け引き','t34':'2連撃の爆発力','t35':'貯め込み勢を一斉に動かす','t36':'貯め込み用','t37':'ざぁ～こ♥に税金','t38':'気軽にダウトできる','t39':'ざぁ～こ♥にブロックが生える','t40':'自分だけ得する税','t1':'即時ばいば～い♥で相打ちのドラマ','t2':'地味で本人にしか見えない','t3':'出番が少ない条件ブロック','t5':'全員を巻き込む交換会。選ぶ楽しさ','t6':'単純だが全員から取る','t8':'全体への縛り','t9':'勝利条件が増えて狙われる緊張','t10':'みせて♥は面白いが機会が少ない','t11':'こっそり情報','t12':'単純な取り返し','t14':'地味だが強い','t17':'トリガーを覗いて脱がせ方を考える','t18':'消極的な防御','t19':'ハッタリを1回通し放題','t20':'相手の手番を飛ばす','t21':'全員に選択を迫る','t22':'狙われたら儲かる駆け引き','t23':'地味','t24':'因縁の対人ドラマ','t25':'ダウトを誘発','t26':'見せ合い','t27':'地味な引き直し','t28':'相打ちのドラマ','t16':'復活のドラマ','t4':'全員が得する公開','t7':'全員が1枚渡す','t13':'地味','t15':'キングメーカー'}
def balance_pt(a):
    a=abs(a); return 5 if a<=1 else 4 if a<=2 else 3 if a<=3 else 2 if a<=5 else 1
def rating_rows(d, keys):
    acc={}
    for key in keys:
        c=d.get(key)
        if not c: continue
        for r in c['rows']:
            if r['id']=='none': continue
            v = r['delta'] if r['id']!='t16' else 100*(r['heldWin']/r['held']-c['heldBase'])
            acc.setdefault(r['id'],{'id':r['id'],'name':CNAME.get(r['id'],r['name']),'d':[]})['d'].append(v)
    out=[]
    for id,v in acc.items():
        avg=sum(v['d'])/len(v['d']); b=balance_pt(avg); f=FUN.get(id,3)
        out.append({'id':id,'name':v['name'],'fun':f,'why':FUN_WHY.get(id,''),'avg':avg,'bal':b,'total':f+b})
    out.sort(key=lambda r:(-r['total'],-r['fun'],abs(r['avg'])))
    return out
def rows(key):
    return [{'id':r['id'],'name':CNAME.get(r['id'],r['name']),'eff':EFF.get(r['id'],''),'held':r['held'],'heldWin':r['heldWin'],'first':r['first'],'firstWin':r['firstWin'],'last':r['last'],'revive':r.get('revive',0),'reviveWin':r.get('reviveWin',0),'count':1 if r['id']!='none' else d[key].get('dud',0),'evalBy':'held' if r['id']=='t16' else 'first','memo':''} for r in d[key]['rows']]
s4, s3, s0 = d['basic_p4'], d['basic_p3456'], d.get('basic_p4_dud0')
f4, f3 = d.get('fresh_p4'), d.get('fresh_p3456')
m4, m3 = d.get('mix_p4'), d.get('mix_p3456')
n4, n3 = d.get('bench_p4'), d.get('bench_p3456')
RATING = rating_rows(d, ['basic_p4','basic_p3456','fresh_p4','fresh_p3456','bench_p4','bench_p3456'])
MIX_IDS = PRESETS.get('mix', [])
# 物理版のトリガー：基本デッキ＋おすすめデッキの和集合（18枚）
_t20 = list(PRESETS.get('basic', []))
TRIG20 = [CNAME[i] for i in _t20]
_notin = [CNAME[i] for i in PRESETS.get('fresh', []) if i not in _t20]
N_PRINT_CHARS = 6
PHYS = {
  'chars': [n for _, n in _chars],
  'rows': [
    ['ガキカード（役職）', N_ROLES*3, f'{N_ROLES}種×3枚。メスガキ・後輩ガキ・幼馴染ガキ・サキュガキ・わからせおじさん', '裏面は共通の裏柄。表に「できる／ブロック」を印刷しておくと早見表が要らない'],
    ['キャラカード（キャラ）', N_PRINT_CHARS*2, f'{N_PRINT_CHARS}キャラ×上半身・下半身の2枚。表＝通常絵、裏＝ボロ絵の両面印刷', '基本形はモモコ・グリムアロエ・アクア・パイン・シロ・クロ。横長（名刺91×55mm）で、上下を縦に並べると全身'],
    ['トリガーカード', len(TRIG20), f'{len(TRIG20)}種×1枚：' + '・'.join(TRIG20), f'基本デッキ18枚（旧基本12枚＋おすすめに入っている新カード6枚）。ハズレは入れない。新カードデッキを丸ごと遊ぶには {"・".join(_notin)} も要る'],
    ['♥トークン', 50, '1♥×40、5♥×10 くらい', '6人戦でも50あれば足りる（クーのコイン50枚と同じ）'],
    ['早見表', 6, 'アクション7種と「は？」ブロック・ダウトの表。1人1枚', 'ゲーム画面の「ルール」の①〜③をそのまま'],
    ['タイトルカード', 1, 'ゲーム名と人数・時間。裏に内容物一覧', '合計を52枚にそろえる1枚'],
  ],
  'rulebook': 'ルールブック：別紙（準備・手番・プライド喪失とトリガー・勝利条件・トリガー一覧）。カード枚数には含めない',
  'per_player': '1人ぶん：キャラカード2枚（上・下）、ガキカード2枚（伏せ）、トリガー2枚（伏せて上下に1枚ずつ）、2♥',
  'min4': f'4人戦の最小セット：ガキ{N_ROLES*3}＋キャラ8＋トリガー12＋早見表4 ＝ {N_ROLES*3+8+12+4}枚と♥トークン',
}
hasDud = bool(s4.get('hasDud', True))
BASELBL = 'ハズレ比' if hasDud else '平均比'
BASENAME = 'ハズレ' if hasDud else '全カード平均'
def all_rows():
    acc = {}
    for key, c in d.items():
        if key == 'whatif' or not isinstance(c, dict) or 'rows' not in c: continue
        for r in c['rows']:
            if r['id'] == 'none': continue
            a = acc.setdefault(r['id'], {'id': r['id'], 'held': 0, 'heldWin': 0, 'first': 0, 'firstWin': 0, 'last': 0, 'revive': 0, 'reviveWin': 0})
            for k in ('held', 'heldWin', 'first', 'firstWin', 'last'): a[k] += r[k]
            a['revive'] += r.get('revive', 0); a['reviveWin'] += r.get('reviveWin', 0)
    rows = []
    for a in acc.values():
        rows.append({'id': a['id'], 'name': CNAME.get(a['id'], a['id']), 'eff': EFF.get(a['id'], ''), 'held': a['held'], 'heldWin': a['heldWin'], 'first': a['first'], 'firstWin': a['firstWin'], 'last': a['last'], 'revive': a['revive'], 'reviveWin': a['reviveWin'], 'count': 1, 'evalBy': 'held' if a['id'] == 't16' else 'first', 'memo': ''})
    base = sum(r['firstWin'] for r in rows) / max(1, sum(r['first'] for r in rows))
    hbase = sum(r['heldWin'] for r in rows) / max(1, sum(r['held'] for r in rows))
    return rows, base, hbase
_arows, _abase, _ahbase = all_rows()
_agames = sum(c['games'] for k, c in d.items() if isinstance(c, dict) and 'games' in c)
_never = [CNAME[i] for i in CNAME if i not in RETIRED and i not in {r['id'] for r in _arows}]   # 山に入れたが一度も仕込まれなかった札
_nevernote = f"。{'・'.join(_never)}は3枚から2枚を選ぶときCPUが一度も残さなかったので数字がない" if _never else ''
DATA = {
  'conds': {
    'all': {'label':'全カード・全条件','deck':'all','sub':f"回した全条件（3デッキ×4人戦・3〜6人戦＋2軍）を合算・{_agames:,}戦。基準は全カード平均{_nevernote}",'games':_agames,'rows':_arows,'base':_abase,'heldBase':_ahbase},
    'basic_p4': {'label':'基本・4人戦','deck':'basic','sub':f"基本デッキ・{s4['games']:,}戦",'games':s4['games'],'rows':rows('basic_p4'),'base':s4.get('base'),'heldBase':s4.get('heldBase'),'avgLog':round(s4['avgLog'],1),'winnerLostLife':round(s4['winnerLostLife'],3),'lifeLoss':round(s4['lifeLoss'],2)},
    'basic_p3456': {'label':'基本・3〜6人戦','deck':'basic','sub':f"基本デッキ・各{s3['games']//4:,}戦・{s3['games']:,}戦",'games':s3['games'],'rows':rows('basic_p3456'),'base':s3.get('base'),'heldBase':s3.get('heldBase')},
    **({'fresh_p4': {'label':'新カード・4人戦','deck':'fresh','sub':f"新カードデッキ・{f4['games']:,}戦",'games':f4['games'],'rows':rows('fresh_p4'),'base':f4.get('base'),'heldBase':f4.get('heldBase'),'avgLog':round(f4['avgLog'],1),'winnerLostLife':round(f4['winnerLostLife'],3),'lifeLoss':round(f4['lifeLoss'],2)},
        'fresh_p3456': {'label':'新カード・3〜6人戦','deck':'fresh','sub':f"新カードデッキ・各{f3['games']//4:,}戦・{f3['games']:,}戦",'games':f3['games'],'rows':rows('fresh_p3456'),'base':f3.get('base'),'heldBase':f3.get('heldBase')}} if f4 and f3 else {}),
    **({'mix_p4': {'label':'おすすめ・4人戦','deck':'mix','sub':f"おすすめデッキ・{m4['games']:,}戦",'games':m4['games'],'rows':rows('mix_p4'),'base':m4.get('base'),'heldBase':m4.get('heldBase')},
        'mix_p3456': {'label':'おすすめ・3〜6人戦','deck':'mix','sub':f"おすすめデッキ・各{m3['games']//4:,}戦・{m3['games']:,}戦",'games':m3['games'],'rows':rows('mix_p3456'),'base':m3.get('base'),'heldBase':m3.get('heldBase')}} if m4 and m3 else {}),
    **({'bench_p4': {'label':'2軍・4人戦','deck':'bench','sub':f"2軍10枚＋おすすめ8枚の18枚・{n4['games']:,}戦",'games':n4['games'],'rows':rows('bench_p4'),'base':n4.get('base'),'heldBase':n4.get('heldBase')},
        'bench_p3456': {'label':'2軍・3〜6人戦','deck':'bench','sub':f"2軍10枚＋おすすめ8枚の18枚・各{n3['games']//4:,}戦・{n3['games']:,}戦",'games':n3['games'],'rows':rows('bench_p3456'),'base':n3.get('base'),'heldBase':n3.get('heldBase')}} if n4 and n3 else {}),
  },
  'rating': RATING,
  'allcards': [{'id':i,'name':CNAME[i],'text':TEXT.get(i,''),'family':'見送り' if i in RETIRED else '基本' if i in SETS.get('basic',[]) else '新カード' if i in SETS.get('fresh',[]) else '2軍',
                'kind':'常時' if i in PERSIST else '発動時','decks':[k for k,v in PRESETS.items() if i in v],'retired':i in RETIRED,'fun':FUN.get(i),'why':FUN_WHY.get(i,'')} for i in CNAME],
  'phys': PHYS,
  'mixIds': MIX_IDS,
  'hasDud': hasDud,
  'deck': DECK,
  'dud': ({'d5':{'label':'ハズレ2枚','games':s4['games'],'avgLog':round(s4['avgLog'],1),'winnerLostLife':round(s4['winnerLostLife'],3),'lifeLoss':round(s4['lifeLoss'],2)},
          'd0':{'label':'ハズレ0枚','games':s0['games'],'avgLog':round(s0['avgLog'],1),'winnerLostLife':round(s0['winnerLostLife'],3),'lifeLoss':round(s0['lifeLoss'],2)}} if s0 else None),
  'cands': [{'name':a,'eff':b,'aim':c} for a,b,c in CANDS],
  'thr': 0.02,
  'whatif': d.get('whatif', []),
}
page = r'''<title>メスガキ・クー トリガー分析</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Zen+Kaku+Gothic+New:wght@400;700&display=swap">
<style>
/* カードリストと同じ色と書体。上に結論、中にハズレ比の棒、下にカードごとの数字 */
:root{
  --bg:#faf6f8; --surface:#ffffff; --ink:#1f1522; --ink2:#4f4252; --muted:#7a6c7d; --line:#eadfe7; --band:#f6eef3;
  --accent:#b8306a; --accent-soft:#f6dbe7; --pos:#b8306a; --neg:#246fb8; --zero:#9a8d9c;
  --tS:#8f1d4f; --tA:#b8306a; --tN:#d9d2d8; --tW:#e9e3ea; --onS:#ffffff; --onA:#ffffff; --onN:#1f1522; --onW:#4f4252;
  --display:"Dela Gothic One","Hiragino Sans","Yu Gothic",sans-serif;
  --body:"Zen Kaku Gothic New","Hiragino Sans","Yu Gothic",system-ui,sans-serif;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  color-scheme:dark; --bg:#141015; --surface:#1d171f; --ink:#f6ecf2; --ink2:#d3c4cf; --muted:#a896a6; --line:#382c3a; --band:#241c26;
  --accent:#ff74aa; --accent-soft:#44202f; --pos:POSDARK; --neg:NEGDARK; --zero:#6e606f;
  --tS:#ff74aa; --tA:#e0558f; --tN:#3a323c; --tW:#2b242d; --onS:#1f0a14; --onA:#1f0a14; --onN:#d3c4cf; --onW:#a896a6;
}}
:root[data-theme="dark"]{
  color-scheme:dark; --bg:#141015; --surface:#1d171f; --ink:#f6ecf2; --ink2:#d3c4cf; --muted:#a896a6; --line:#382c3a; --band:#241c26;
  --accent:#ff74aa; --accent-soft:#44202f; --pos:POSDARK; --neg:NEGDARK; --zero:#6e606f;
  --tS:#ff74aa; --tA:#e0558f; --tN:#3a323c; --tW:#2b242d; --onS:#1f0a14; --onA:#1f0a14; --onN:#d3c4cf; --onW:#a896a6;
}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.7}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg)}
main{max-width:1120px;margin:0 auto;padding-block:28px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:32px}
.eyebrow{font-size:12px;letter-spacing:.25em;color:var(--accent);font-weight:700}
.nb{display:inline-block}
h1{font-family:var(--display);font-weight:400;font-size:clamp(28px,6vw,44px);line-height:1.15;margin:6px 0 10px;text-wrap:balance}
h2{font-family:var(--display);font-weight:400;font-size:22px;margin:0;text-wrap:balance;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
h2 small{font-family:var(--body);font-size:13px;color:var(--muted);font-weight:400}
p{margin:0 0 10px;max-width:68ch;color:var(--ink2)}
.lede{font-size:16px}
#deckline{font-size:14px;color:var(--ink2)} #deckline b{color:var(--ink)}
section{display:flex;flex-direction:column;gap:12px}
.total{display:flex;gap:22px;flex-wrap:wrap;font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px}
.total b{display:block;font-size:22px;color:var(--ink);font-family:var(--display);font-weight:400}

/* 読み取り */
.mix{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}
.mixbox{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.mixbox h3{margin:0 0 6px;font-size:12px;letter-spacing:.15em;color:var(--muted)}
.mixbox .big{font-family:var(--display);font-weight:400;font-size:26px;line-height:1.2;color:var(--ink);margin-bottom:4px}
.mixbox p{font-size:13px;margin:0}

/* 絞り込み */
.filters{background:var(--bg);padding-block:10px;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:8px}
.frow{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.frow .lab{font-size:12px;color:var(--muted);min-width:3.5em}
.chip{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--surface);color:var(--ink2);border-radius:999px;padding:2px 12px;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--surface)}
.chip:focus-visible,.search:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.search{font:inherit;font-size:14px;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:6px 12px;flex:1 1 200px;min-width:0;max-width:360px}
select{font:inherit;font-size:13px;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:5px 8px}
.shown{font-size:13px;color:var(--muted);margin-left:auto;font-variant-numeric:tabular-nums}

/* ハズレ比の棒 */
.bars{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:4px;font-variant-numeric:tabular-nums}
.bar{display:grid;grid-template-columns:7.5em 1fr 5.5em;align-items:center;gap:10px;min-height:28px;border-radius:6px;padding:0 4px}
.bar:hover{background:var(--band)}
.bar .bn{font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar .bt{position:relative;height:14px}
.bar .bt::before{content:"";position:absolute;left:50%;top:-5px;bottom:-5px;width:1px;background:var(--line)}
.bar .bf{position:absolute;top:1px;height:12px;border-radius:0 4px 4px 0;background:var(--pos)}
.bar .bf.neg{border-radius:4px 0 0 4px;background:var(--neg)}
.bar .bf.zero{background:var(--zero)}
.bar .bv{font-size:13px;color:var(--ink);text-align:right;white-space:nowrap}
.bar .bv small{color:var(--muted);font-size:11px}
.barhead{display:grid;grid-template-columns:7.5em 1fr 5.5em;gap:10px;font-size:11px;color:var(--muted);padding:0 4px 4px}
.barhead .mid{text-align:center}
.barhead .r{text-align:right}

/* カード */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.cc{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:6px;min-width:0;position:relative}
.cc-top{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.qty{margin-left:auto;font-weight:700;color:var(--ink2)}
.cc-name{margin:0;font-size:18px;line-height:1.35;font-weight:700;overflow-wrap:anywhere}
.txt{margin:0;font-size:13px;color:var(--ink2);line-height:1.6}
.stats{display:flex;align-items:baseline;flex-wrap:wrap;gap:4px 16px;font-variant-numeric:tabular-nums}
.num{display:inline-flex;align-items:baseline;gap:4px;font-size:12px;color:var(--muted)}
.num b{font-family:var(--display);font-weight:400;font-size:26px;line-height:1;color:var(--ink)}
.meta{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--ink2);font-variant-numeric:tabular-nums}
.meta b{font-weight:700;color:var(--ink)}
.memo{margin:0;font-size:12px;color:var(--muted);border-top:1px dashed var(--line);padding-top:6px}
.tier{display:inline-block;min-width:3.2em;text-align:center;border-radius:6px;padding:0 8px;font-weight:700;font-size:12px;white-space:nowrap}
.tS{background:var(--tS);color:var(--onS)} .tA{background:var(--tA);color:var(--onA)} .tN{background:var(--tN);color:var(--onN)} .tW{background:var(--tW);color:var(--onW)}
.empty{color:var(--muted);font-size:14px;padding:12px 0}

/* 表 */
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-size:12px;color:var(--muted);white-space:nowrap;position:sticky;top:0;background:var(--surface)}
td.n,th.n{text-align:right;white-space:nowrap}
td.nm{font-weight:700;white-space:nowrap}
td.tx{min-width:16em;color:var(--ink2)}
tbody tr:hover td{background:var(--band)}
tr.mixrow td{background:var(--accent-soft)}

ul.plain{margin:0;padding-left:1.2em;color:var(--ink2);max-width:72ch} ul.plain li{margin-bottom:6px}
ul.plain a,p a{color:var(--accent);font-weight:700}
.note{font-size:13px;color:var(--muted)}
@media (min-width:700px){ .filters{position:sticky;top:env(safe-area-inset-top,0px);z-index:5} }
@media (max-width:699px){
  .filters .frow:not(:first-child){flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
  .filters .frow .lab{min-width:auto;flex:none}
  .chip{flex:none}
  .grid{grid-template-columns:1fr}
  .bar{grid-template-columns:6em 1fr 4.5em}
  .barhead{grid-template-columns:6em 1fr 4.5em}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<main>
<header>
  <div class="eyebrow">CPU同士の自動対戦・2026-10-26 第17版（18枚デッキ・3枚配り）・基本／新カード／おすすめ の3デッキ（各18枚・ハズレなし）＋2軍10枚におすすめ8枚を足した18枚／総合評価＝おもしろさ＋バランス／3枚配って2枚を選んで仕込む（5〜6人戦は山が足りないので2枚配り）／メンヘラ9♥＋公開時に山分け／わからせ返しは5♥／3〜6人・各デッキ20万戦</div>
  <h1><span class="nb">メスガキに「は？」って言うゲーム</span> <span class="nb">トリガー分析</span></h1>
  <p class="lede">基本・新カード・おすすめの3デッキを、どれが持ち主を勝たせているかで並べた。条件チップでデッキと人数を切り替えられる。下の「総合評価」では、使っておもしろいかの点を足して18枚を選んでいる。指標は「1枚目の脱ぎで発動したあとに勝った割合」。プライドを1つ失った状態からの勝率なので、BASENAMEとの差で強さを見る。DUDNOTE</p>
  <p class="lede" id="deckline"></p>
  <div class="total" id="total"></div>
</header>

<section>
  <h2>読み取り</h2>
  <div class="mix" id="mix"></div>
</section>

<section aria-label="絞り込み">
  <div class="filters" role="search">
    <div class="frow"><span class="lab">条件</span><span id="fCond"></span>
      <select id="sort" aria-label="並べ方"><option value="delta">ハズレ比が大きい順</option><option value="heldp">所持時勝率が高い順</option><option value="first">発動回数が多い順</option><option value="name">名前順</option></select>
      <select id="view" aria-label="表示"><option value="cards">カードで見る</option><option value="table">表で見る</option></select>
      <span class="shown" id="shown"></span></div>
    <div class="frow" id="fTier"><span class="lab">判定</span></div>
    <div class="frow"><input class="search" id="q" type="search" placeholder="名前・効果で探す（例：♥、手札）" aria-label="名前・効果で探す"></div>
  </div>
</section>

<section>
  <h2>ハズレ比 <small id="barsub"></small></h2>
  <p>発動後勝率からBASENAMEの発動後勝率を引いた差。右（ピンク）が持ち主の得、左（青）が損。±2ポイントは誤差の範囲。HELDNOTE</p>
  <div class="bars" id="bars"></div>
</section>

<section aria-label="カード一覧">
  <h2>カードごとの数字 <small id="cardsub"></small></h2>
  <div id="out"></div>
</section>

<section id="dudsec">
  <h2>ハズレ2枚と0枚の比較 <small>4人戦・各10,000戦</small></h2>
  <div class="tbl"><table id="dudtbl"></table></div>
  <p>2枚配りになってハズレは必ず仕込まれるようになったが、2枚でも0枚でもゲームの長さ・逆転の起きやすさ・被弾回数は変わらない。ハズレはバランスには効かず、「脱いだのに何も起きない」場面を1割ほど混ぜるための札。</p>
</section>

<section aria-label="全カード一覧">
  <h2>全カード一覧 <small id="allsub"></small></h2>
  <p>ゲームに定義してある全トリガー。系統（基本・新カード・2軍・見送り）とどのデッキに入っているか、BASELBLの平均（回した条件の平均。見送り札は回していない）を並べた。</p>
  <div class="frow"><input class="search" id="qall" type="search" placeholder="名前・効果で探す" aria-label="全カードから探す"> <select id="fam" aria-label="系統"><option value="all">すべての系統</option><option>基本</option><option>新カード</option><option>2軍</option><option>見送り</option></select> <select id="sortall" aria-label="並べ方"><option value="family">系統順</option><option value="name">名前順</option><option value="avg">BASELBLが大きい順</option><option value="total">総合評価順</option></select></div>
  <div class="tbl"><table id="alltbl"></table></div>
</section>

<section>
  <h2>総合評価 <small>おもしろさ ＋ バランス</small></h2>
  <p>「使っておもしろいか」を5点満点で採点し（決断・駆け引き・派手さ・巻き込みがあるほど高い）、BASELBLの近さをバランス点（±1pt以内＝5、±2＝4、±3＝3、±5＝2、それ以上＝1。おきがえしま～す！は所持時勝率）にして足した。上位18枚が「おすすめデッキ」。同点はおもしろさ、次にBASELBLの小ささで並べている。</p>
  <div class="tbl"><table id="rating"></table></div>
</section>

<section>
  <h2>調整案と新カード案</h2>
  <p>数値を変えた試算（基本デッキ・4人戦・各WHATIFN戦）と、今後の案。</p>
  <div id="whatif"></div>
  <div class="grid" id="cands"></div>
</section>

<section>
  <h2>物理版にするときの枚数</h2>
  <p>紙で作るときの内訳。数字はゲームの定義から数えている。</p>
  <div class="tbl"><table id="phys"></table></div>
  <p class="note" id="physnote"></p>
</section>

<section>
  <h2>読み方</h2>
  <ul class="plain">
    <li>所持時勝率：そのカードを仕込んでいたプレイヤーの勝率。発動しなかった場合も含む。4人戦の平均は25%、3〜6人戦の平均は約22%。</li>
    <li>発動後勝率：1枚目の脱ぎでそのカードが発動したあと、そのプレイヤーが勝った割合。BASELBLはこの値とBASENAMEの差で、判定は±2ポイントを境にしている。</li>
    <li>脱落時発動率：発動のうち、2枚目の脱ぎ（脱落）で発動した割合。おきがえしま～す！以外は本人にほぼ意味がない発動。</li>
    HELDLI    <li>NOISENOTE 4人戦と3〜6人戦の両方で同じ向きに出ているかも見る。</li>
    <li>CPUはメンヘラを持っていて目標まで3♥以内なら、ばいば～い♥より先に♥を集めて勝ちに行く。周りのCPUも目標が近い所持者を優先して狙う。</li>
  </ul>
  <p class="note">作成日 2026-10-26（第17版）　・　元データ：mesugaki-coup tools/sim.js（ヘッドレス自動対戦）</p>
</section>
</main>
<script>
const DATA = DATAJSON;
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct=(v,d=1)=>(v*100).toFixed(d)+'%';
const spct=(v,d=1)=>(v>=0?'+':'')+(v*100).toFixed(d)+'pt';
const fmt=n=>n.toLocaleString('ja-JP');
const state={cond:'all',tier:'all',q:'',sort:'delta',view:'cards'};
function compute(cond){
  const rows=DATA.conds[cond].rows.map(r=>({...r}));
  const dud=rows.find(r=>r.id==='none'); const C=DATA.conds[cond];
  const base=dud?dud.firstWin/dud.first:C.base;
  const hbase=dud?dud.heldWin/dud.held:C.heldBase;
  rows.base=base; rows.hbase=hbase;
  for(const r of rows){ r.heldp=r.heldWin/r.held; r.firstp=r.firstWin/r.first; r.delta=r.firstp-base; r.heldDelta=r.heldp-hbase; r.score=r.evalBy==='held'?r.heldDelta:r.delta; r.lastRate=r.last/(r.first+r.last); r.revivep=r.revive?r.reviveWin/r.revive:0; r.tier=r.id==='none'?'none':(r.score>=DATA.thr?'強い':(r.score<=-DATA.thr?'弱い':'中立')); }
  return rows;
}
const tierCls={'強い':'tS','中立':'tN','弱い':'tW','none':'tA'};
const tierLabel=t=>t==='none'?'基準':t;
function renderDeck(){
  const k=DATA.deck; if(!k) return;
  const lines=[];
  if(k.presets.basic) lines.push(`<b>基本デッキ</b>（${k.presets.basic.length}枚・各1枚）：${esc(k.presets.basic.join('・'))}`);
  if(k.presets.fresh) lines.push(`<b>新カードデッキ</b>（${k.presets.fresh.length}枚・各1枚）：${esc(k.presets.fresh.join('・'))}`);
  if(k.presets.mix) lines.push(`<b>おすすめデッキ</b>（総合評価の上位${k.presets.mix.length}枚）：${esc(k.presets.mix.join('・'))}`);
  if(k.bench.length) lines.push(`2軍（デッキ外。カスタムで使える）：${esc(k.bench.join('・'))}`);
  if(k.retired&&k.retired.length) lines.push(`見送り（ゲーム・印刷から外した）：${esc(k.retired.join('・'))}`);
  $('#deckline').innerHTML=lines.join('<br>')+'<br>開始画面でいずれかのデッキ、または好きな18枚を選べる。各プレイヤーに3枚配り、2枚を選んで上半身・下半身に仕込む（残りは山へ）。';
}
function renderTotal(){
  const c4=DATA.conds.basic_p4, d=c4;
  const tot=Object.values(DATA.conds).reduce((a,c)=>a+c.games,0);
  $('#total').innerHTML=`<span><b>${fmt(tot)}</b>総対戦数</span><span><b>${d.lifeLoss}回</b>1ゲームの被弾</span><span><b>${pct(d.winnerLostLife,0)}</b>勝者が途中で被弾</span><span><b>${d.avgLog}行</b>平均ログ</span>`;
}
function renderMix(){
  const dk=DATA.conds[state.cond].deck||'basic'; const r4=compute(dk==='all'?'all':dk+'_p4'), r3=compute(dk==='all'?'all':dk+'_p3456');
  const d3=Object.fromEntries(r3.map(r=>[r.name,r.score]));
  const both=r4.filter(r=>r.id!=='none' && r.score>=DATA.thr && d3[r.name]>=0).map(r=>r.name);
  const top4=both.length?both:r4.filter(r=>r.tier==='強い').map(r=>r.name);
  const weak=r4.filter(r=>r.tier==='弱い' && d3[r.name]<0).map(r=>r.name);
  const col=r4.find(r=>r.id==='t9'), col3=r3.find(r=>r.id==='t9');
  const lastAvg=r4.reduce((a,r)=>a+r.last,0)/r4.reduce((a,r)=>a+r.first+r.last,0);
  const items=[
    [({fresh:'新カード・',mix:'おすすめ・',bench:'2軍・',all:'全カード・'}[DATA.conds[state.cond].deck]||'基本・')+'強い', top4.join('・')||'なし', top4.length?(dk==='all'?`全条件の合算でBASELBL +${(DATA.thr*100).toFixed(0)}pt 以上のカード。`:`4人戦でBASELBL +${(DATA.thr*100).toFixed(0)}pt 以上で、3〜6人戦でもプラスのカード。`):`+2pt を超えるカードはない。いちばん高い${r4[0].name}でも ${spct(r4[0].score)} で、かなり平ら。`],
    ['弱い', weak.join('・')||'なし', weak.length?(dk==='all'?'全条件の合算で −2pt を下回るカード。':'両条件でマイナスのカード。'):`両条件で −2pt を下回るカードはない。いちばん低い${r4[r4.length-1].name}でも ${spct(r4[r4.length-1].score)} で、不発（何も起きない）とほぼ同じ。`],
    ['空撃ち', pct(lastAvg,0), '発動のうち脱落時（2枚目の脱ぎ）に起きた割合。本人には意味のない発動が半分近くある。'],
    ['効果の幅', `${spct(Math.max(...r4.map(r=>r.score)))} 〜 ${spct(Math.min(...r4.map(r=>r.score)))}`, 'トリガーは負けかけた側に起きるので、どれも勝敗を覆すほどの力はない。'],
  ];
  $('#mix').innerHTML=items.map(([h,b,p])=>`<div class="mixbox"><h3>${esc(h)}</h3><div class="big">${esc(b)}</div><p>${esc(p)}</p></div>`).join('');
}
function renderChips(){
  $('#fCond').innerHTML=Object.entries(DATA.conds).map(([k,c])=>`<button class="chip" data-cond="${k}" aria-pressed="${state.cond===k}">${esc(c.label)}</button>`).join('');
  const tiers=['all','強い','中立','弱い'];
  $('#fTier').innerHTML='<span class="lab">判定</span>'+tiers.map(t=>`<button class="chip" data-tier="${t}" aria-pressed="${state.tier===t}">${t==='all'?'すべて':esc(t)}</button>`).join('');
  document.querySelectorAll('[data-cond]').forEach(b=>b.onclick=()=>{ state.cond=b.dataset.cond; renderAll(); });
  document.querySelectorAll('[data-tier]').forEach(b=>b.onclick=()=>{ state.tier=b.dataset.tier; renderAll(); });
}
function renderBars(rows){
  const c=DATA.conds[state.cond];
  $('#barsub').textContent=`${c.label}・${c.sub}`;
  const list=rows.filter(r=>r.id!=='none').sort((a,b)=>b.score-a.score);
  const max=Math.max(...list.map(r=>Math.abs(r.score)), 0.01);
  const dud={firstp:rows.base, heldp:rows.hbase};
  $('#bars').innerHTML=`<div class="barhead"><span>カード</span><span class="mid">BASENAME（発動後勝率 ${pct(dud.firstp)}）を0とした差</span><span class="r">BASELBL</span></div>`+list.map(r=>{
    const v=r.score; const w=Math.abs(v)/max*50; const zero=Math.abs(v)<0.001; const held=r.evalBy==='held';
    const style=v>=0?`left:50%;width:${w}%`:`right:50%;width:${w}%`;
    const title=held?`${r.name}：所持時勝率 ${pct(r.heldp)}（BASENAME ${pct(dud.heldp)}）、復活 ${fmt(r.revive)}回`:`${r.name}：発動後勝率 ${pct(r.firstp)}（BASENAME ${pct(dud.firstp)}）、発動 ${fmt(r.first)}回`;
    return `<div class="bar" title="${esc(title)}"><span class="bn">${esc(r.name)}${r.count>1?' ×'+r.count:''}${held?' ◆':''}</span><span class="bt"><span class="bf ${v<0?'neg':''} ${zero?'zero':''}" style="${style}"></span></span><span class="bv">${spct(v)} <small>${pct(held?r.heldp:r.firstp)}</small></span></div>`;
  }).join('');
}
function filtered(rows){
  let list=rows.slice();
  if(state.tier!=='all') list=list.filter(r=>r.tier===state.tier);
  if(state.q){ const q=state.q.toLowerCase(); list=list.filter(r=>(r.name+r.eff+r.memo).toLowerCase().includes(q)); }
  const s=state.sort;
  list.sort((a,b)=> s==='name'?a.name.localeCompare(b.name,'ja') : s==='heldp'?b.heldp-a.heldp : s==='first'?b.first-a.first : b.score-a.score);
  return list;
}
function card(r){
  return `<article class="cc"><div class="cc-top"><span class="tier ${tierCls[r.tier]}">${tierLabel(r.tier)}</span><span>山に <b>${r.count}枚</b></span><span>発動 ${fmt(r.first)}回</span><span class="qty">所持 ${fmt(r.held)}</span></div>
  <h3 class="cc-name">${esc(r.name)}</h3><p class="txt">${esc(r.eff)}</p>
  <div class="stats">${r.evalBy==='held'?`<span class="num"><b>${pct(r.heldp)}</b>所持時勝率</span><span class="num"><b>${spct(r.heldDelta)}</b>ハズレ比（所持時）</span>`:`<span class="num"><b>${pct(r.firstp)}</b>発動後勝率</span><span class="num"><b>${spct(r.delta)}</b>ハズレ比</span>`}</div>
  <div class="meta">${r.evalBy==='held'?`<span>発動後勝率 <b>${pct(r.firstp)}</b>（1枚目では不発）</span><span>復活 <b>${fmt(r.revive)}回</b></span><span>復活後勝率 <b>${pct(r.revivep)}</b></span>`:`<span>所持時勝率 <b>${pct(r.heldp)}</b></span><span>脱落時発動率 <b>${pct(r.lastRate,0)}</b></span>`}</div>
  <p class="memo">${esc(r.memo)}</p></article>`;
}
function table(list){
  return `<div class="tbl"><table><thead><tr><th>カード</th><th class="n">枚数</th><th>判定</th><th>効果</th><th class="n">所持回数</th><th class="n">所持時勝率</th><th class="n">発動回数</th><th class="n">発動後勝率</th><th class="n">ハズレ比</th><th class="n">脱落時発動率</th><th>メモ</th></tr></thead><tbody>`+
    list.map(r=>`<tr><td class="nm">${esc(r.name)}</td><td class="n">${r.count}</td><td><span class="tier ${tierCls[r.tier]}">${tierLabel(r.tier)}</span></td><td class="tx">${esc(r.eff)}</td><td class="n">${fmt(r.held)}</td><td class="n">${pct(r.heldp)}</td><td class="n">${fmt(r.first)}</td><td class="n">${pct(r.firstp)}</td><td class="n">${spct(r.delta)}</td><td class="n">${pct(r.lastRate,0)}</td><td class="tx">${esc(r.memo)}</td></tr>`).join('')+`</tbody></table></div>`;
}
function renderCards(rows){
  const c=DATA.conds[state.cond];
  $('#cardsub').textContent=`${c.label}・${c.sub}`;
  const list=filtered(rows);
  $('#shown').textContent=`${list.length} / ${rows.length} 枚`;
  $('#out').innerHTML=list.length? (state.view==='table'?table(list):`<div class="grid">${list.map(card).join('')}</div>`) : '<div class="empty">該当するカードがない</div>';
}
function renderDud(){
  const d=DATA.dud; if(!d){ $('#dudsec').hidden=true; return; }
  $('#dudtbl').innerHTML=`<thead><tr><th>条件</th><th class="n">ゲーム数</th><th class="n">平均ログ行数</th><th class="n">勝者が途中で被弾していた率</th><th class="n">1ゲームの被弾回数</th></tr></thead><tbody>`+['d5','d0'].map(k=>`<tr><td class="nm">${esc(d[k].label)}</td><td class="n">${fmt(d[k].games)}</td><td class="n">${d[k].avgLog}</td><td class="n">${pct(d[k].winnerLostLife)}</td><td class="n">${d[k].lifeLoss}</td></tr>`).join('')+'</tbody>';
}
function renderWhatif(){
  const w=DATA.whatif; if(!w.length){ $('#whatif').hidden=true; return; }
  $('#whatif').innerHTML=w.map(t=>`<div class="tbl"><table><thead><tr><th>${esc(t.title)}</th><th class="n">発動後勝率</th><th class="n">ハズレ比</th><th class="n">所持時勝率</th><th>判定</th></tr></thead><tbody>`+t.rows.map(x=>`<tr><td class="nm">${esc(x.label)}${x.current?'（現行）':''}</td><td class="n">${pct(x.firstp)}</td><td class="n">${spct(x.delta)}</td><td class="n">${pct(x.heldp)}</td><td><span class="tier ${x.delta>=DATA.thr?'tS':x.delta<=-DATA.thr?'tW':'tN'}">${x.delta>=DATA.thr?'強い':x.delta<=-DATA.thr?'弱い':'中立'}</span></td></tr>`).join('')+'</tbody></table></div>').join('');
}
function renderRating(){
  const rows=DATA.rating||[]; if(!rows.length){ $('#rating').closest('section').hidden=true; return; }
  const inMix=new Set(DATA.mixIds||[]);
  const star=n=>'★'.repeat(n)+'☆'.repeat(5-n);
  $('#rating').innerHTML='<thead><tr><th class="n">#</th><th>カード</th><th>おもしろさ</th><th>理由</th><th class="n">BASELBL（平均）</th><th>バランス</th><th class="n">総合</th><th>おすすめ</th></tr></thead><tbody>'+rows.map((r,i)=>`<tr${inMix.has(r.id)?' class="mixrow"':''}><td class="n">${i+1}</td><td class="nm">${esc(r.name)}</td><td title="${r.fun}/5">${star(r.fun)}</td><td class="tx">${esc(r.why)}</td><td class="n">${spct(r.avg/100)}</td><td title="${r.bal}/5">${star(r.bal)}</td><td class="n"><b>${r.total}</b></td><td>${inMix.has(r.id)?'<span class="tier tS">採用</span>':''}</td></tr>`).join('')+'</tbody>';
}
const allState={q:'',fam:'all',sort:'family'};
function renderAllCards(){
  const rows=DATA.allcards||[]; if(!rows.length) return;
  const rate=Object.fromEntries((DATA.rating||[]).map(r=>[r.id,r]));
  const deckName={basic:'基本',fresh:'新カード',mix:'おすすめ'};
  const famOrder={'基本':0,'新カード':1,'2軍':2,'見送り':3};
  let list=rows.map(r=>({...r,avg:rate[r.id]?rate[r.id].avg/100:null,total:rate[r.id]?rate[r.id].total:null}));
  if(allState.fam!=='all') list=list.filter(r=>r.family===allState.fam);
  if(allState.q){ const q=allState.q.toLowerCase(); list=list.filter(r=>(r.name+r.text).toLowerCase().includes(q)); }
  const s=allState.sort;
  list.sort((a,b)=> s==='name'?a.name.localeCompare(b.name,'ja') : s==='avg'?((b.avg??-9)-(a.avg??-9)) : s==='total'?((b.total??-1)-(a.total??-1))||((b.fun??0)-(a.fun??0)) : (famOrder[a.family]-famOrder[b.family])||(parseInt(a.id.slice(1))-parseInt(b.id.slice(1))));
  $('#allsub').textContent=`${list.length} / ${rows.length} 枚`;
  const star=n=>n==null?'－':'★'.repeat(n)+'☆'.repeat(5-n);
  $('#alltbl').innerHTML='<thead><tr><th>カード</th><th>系統</th><th>種類</th><th>デッキ</th><th>効果</th><th>おもしろさ</th><th class="n">BASELBL（平均）</th><th class="n">総合</th></tr></thead><tbody>'+list.map(r=>`<tr${r.retired?' style="opacity:.6"':''}><td class="nm">${esc(r.name)}</td><td>${esc(r.family)}</td><td>${esc(r.kind)}</td><td>${r.decks.map(k=>deckName[k]||k).join('・')||'－'}</td><td class="tx">${esc(r.text)}</td><td title="${r.why?esc(r.why):''}">${star(r.fun)}</td><td class="n">${r.avg==null?'－':spct(r.avg)}</td><td class="n">${r.total==null?'－':r.total+'/10'}</td></tr>`).join('')+'</tbody>';
}
function renderPhys(){
  const k=DATA.phys; if(!k){ return; }
  // 枚数はゲーム定義から。キャラは6種に絞った印刷想定
  const total=k.rows.filter(r=>r[0]!=='♥トークン').reduce((a,r)=>a+r[1],0);
  $('#phys').innerHTML='<thead><tr><th>種類</th><th class="n">枚数</th><th>内訳</th><th>備考</th></tr></thead><tbody>'+k.rows.map(r=>`<tr><td class="nm">${esc(r[0])}</td><td class="n">${fmt(r[1])}${r[0]==='♥トークン'?'個':'枚'}</td><td class="tx">${esc(r[2])}</td><td class="tx">${esc(r[3])}</td></tr>`).join('')+`<tr><td class="nm">カード合計</td><td class="n">${fmt(total)}枚</td><td class="tx" colspan="2">トランプ1組と同じ52枚。ルールブックは別紙で付けるので数えない。54枚仕様（ジョーカー2枚つき）で刷るなら余り2枚はハズレ2枚に。♥トークンは別</td></tr></tbody>`;
  $('#physnote').textContent=`${k.rulebook}。${k.per_player}。${k.min4}。キャラは基本形の6人（モモコ・グリムアロエ・アクア・パイン・シロ・クロ）。ほかの候補：${k.chars.filter(n=>!['モモコ','グリムアロエ','アクア','パイン','シロ','クロ'].includes(n)).join('・')}。キャラ画像の分割と印刷用シート（A4両面）は tools/split_cards.py が出力する。`;
}
function renderCands(){
  $('#cands').innerHTML=DATA.cands.map(c=>`<article class="cc"><h3 class="cc-name">${esc(c.name)}</h3><p class="txt">${esc(c.eff)}</p><p class="memo">${esc(c.aim)}</p></article>`).join('');
}
function renderAll(){
  renderChips(); renderMix();
  const rows=compute(state.cond);
  renderBars(rows); renderCards(rows);
}
$('#sort').onchange=e=>{ state.sort=e.target.value; renderAll(); };
$('#view').onchange=e=>{ state.view=e.target.value; renderAll(); };
$('#q').oninput=e=>{ state.q=e.target.value.trim(); renderAll(); };
$('#qall').oninput=e=>{ allState.q=e.target.value.trim(); renderAllCards(); };
$('#fam').onchange=e=>{ allState.fam=e.target.value; renderAllCards(); };
$('#sortall').onchange=e=>{ allState.sort=e.target.value; renderAllCards(); };
renderDeck(); renderTotal(); renderDud(); renderWhatif(); renderRating(); renderAllCards(); renderPhys(); renderCands(); renderAll();
</script>
'''
import math
_r4=[r for r in d['basic_p4']['rows'] if r['id']!='none']
_n1=min(r['first'] for r in _r4); _pbar=d['basic_p4']['base']
_se=2*math.sqrt(_pbar*(1-_pbar)/_n1)*100
NOISENOTE=f"1枚物は約{_n1:,}回、2枚物はその2倍の発動。BASELBLの揺れは1枚物で±{_se:.1f}ポイント程度。判定の±2ポイントは誤差ではなく「効果の大きさ」の線引き。"
WHATIFN=f"{d['whatif'][0]['rows'][0]['first']*4:,}" if d.get('whatif') else ''
_held=any(r.get('evalBy')=='held' for c in DATA['conds'].values() for r in c['rows'])
HELDNOTE='おきがえしま～す！だけは脱落時にしか効かないので、所持時勝率の差（◆）で見る。' if _held else ''
HELDLI='    <li>おきがえしま～す！は発動後勝率ではなく所持時勝率の差で判定している（復活回数と復活後の勝率はカードに併記）。</li>\n' if _held else ''
page = page.replace('HELDNOTE', HELDNOTE).replace('HELDLI', HELDLI).replace('NOISENOTE', NOISENOTE).replace('WHATIFN', WHATIFN).replace('ハズレ比','BASELBL').replace('DUDNOTE', '' if hasDud else '不発（おきがえしま～す！・花束が1枚目でめくれたとき）は −2ポイント前後に出るので、それが「何も起きない」の目安。').replace('BASELBL', BASELBL).replace('BASENAME', BASENAME).replace('DATAJSON', json.dumps(DATA, ensure_ascii=False)).replace('POSDARK', pos_dark).replace('NEGDARK', neg_dark)
open(out_art, 'w', encoding='utf-8').write(page)
open(out_repo, 'w', encoding='utf-8').write('<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n' + page + '</body>\n</html>\n')
print('written', len(page))
