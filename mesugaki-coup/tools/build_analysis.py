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
_dud = int(_re.search(r"dudCount:\s*(\d+)", _idx).group(1))
PRESETS = {}
for _m in _re.finditer(r"(basic|fresh): \[([^\]]*)\]", _idx[_idx.find('const DECK_PRESETS'):_idx.find('const DECK_SIZE')]):
    PRESETS[_m.group(1)] = _re.findall(r"'(t\d+)'", _m.group(2))
_inpreset = {i for v in PRESETS.values() for i in v}
DECK = {'dud': _dud, 'presets': {k: [CNAME[i] for i in v] for k, v in PRESETS.items()}, 'bench': [CNAME[i] for i in CNAME if i not in _inpreset]}

EFF = {'みちづれのキス':'自分を脱がせた相手の手札を1枚こっそり見る（自分だけ見える）','仕返し':'自分を脱がせた相手から3♥奪う','山分け':'自分より♥の多い全員から1♥ずつもらう','値下げ':'以後、自分の「ざぁ～こ♥」は5♥で撃てる','おしおき返し':'5♥持っていたら即時払って「ざぁ～こ♥」を打つ','山札のぞき':'山札を見て1枚選び、手札と入れ替える','ダサすぎ返し':'これを持っていれば「ダサすぎ♥」をブロックできる','まるみえ':'誰か一人の手札を表にする','総入れ替え':'全員が手札を1枚伏せて出す。自分だけ全部を見て欲しい1枚をもらい、残りはランダムに1枚ずつ配り戻す','みかじめ':'全員から1♥ずつもらう','まわして':'全員手札を1枚選び、右隣に渡す','値上げ':'自分以外は「ざぁ～こ♥」が8♥になる','♥コレクター':'自分の勝利条件に「9♥集める」を追加し、自分より♥の多い全員から1♥ずつもらう','遺言':'プライドが0になったときだけ発動。自分の♥をすべて好きな相手に渡す','着替え':'プライドが0になったときだけ発動。山札から1枚引いて脱落を免れる。ただし♥は0になり、次の手番を1回飛ばす','トリガーチェック':'自分を脱がせた相手の伏せたトリガーを1枚こっそり見る（自分だけ見える）','かくれんぼ':'次の自分の手番まで、自分は「ざぁ～こ♥」「まけちゃえ～♥」の対象にならない','無敵宣言':'次の自分の手番のアクションは、チャレンジもブロックもされない','口止め料':'自分を脱がせた相手は、次の手番を1回飛ばす','おねだり':'ほかの全員は「自分に1♥渡す」か「手札1枚を自分にこっそり見せる」かを選ぶ','ボディガード':'以後、自分を対象にした ざぁ～こ♥・まけちゃえ～♥・なさけな～い♥ は、使った人が追加で2♥を自分に払う','人気者':'以後、自分の「よわ♥」はブロックされない','復讐の誓い':'以後、自分を脱がせた相手に対する自分のアクションは、チャレンジもブロックもされない','ごほうび':'以後、自分がチャレンジに成功するたびに2♥もらう','内緒話':'相手1人を選び、互いに手札1枚をこっそり見せ合う','お色直し':'自分の手札をすべて山札に戻し、同じ枚数を引き直す','道連れ':'自分を脱がせた相手もプライドを1つ失う','ルール改変':'以後、自分の「ダサすぎ♥」は通常か審問（相手の手札1枚を見て山札と交換させる）かを選べる。審問は幼馴染ガキでブロック可','ハズレ':'効果なし'}
MEMO = {"みちづれのキス": "脱がせた相手の手札を自分だけ見る。ややプラス（+0.9pt / +0.3pt）", "値下げ": "自分だけざぁ～こ♥が5♥。ややプラス（+1.2pt / +1.3pt）", "仕返し": "脱がせた相手から3♥。ややプラス（+0.9pt / +0.6pt）", "おしおき返し": "5♥。中立（+0.3pt / +0.6pt）。所持時勝率は平均より +2.7pt で、持っているだけで攻撃を抑えている", "みかじめ": "全員から1♥。ややプラス（+1.3pt / +1.0pt）", "山札のぞき": "ややプラス（+1.2pt / +0.6pt）", "ダサすぎ返し": "やや弱い（-0.6pt / -0.6pt）", "ルール改変": "自分だけに効き、通常と審問を選べる。やや弱い（-1.2pt / -1.2pt）。CPUは審問をあまり使わないので低く出る", "♥コレクター": "9♥＋公開時の山分け。中立（+0.0pt / -0.8pt）", "まわして": "2軍（0枚）。全員が1枚ずつ渡すので自分の得にならなかった", "総入れ替え": "交換会。やや弱い（-1.0pt / -0.6pt）", "遺言": "今回は0枚（外した）", "着替え": "新カードデッキに弱体版（♥0＋手番1回スキップ）で収録。1枚目は不発なので発動後勝率は低いが、所持時勝率は +7pt。復活は4人戦10万戦で25,561回", "まるみえ": "今回は0枚", "値上げ": "やや弱い（-1.0pt / -0.3pt）。自分以外のざぁ～こ♥が8♥になる", "山分け": "今回は0枚（♥コレクターの公開時効果に統合）", "ハズレ": "今回は0枚", "トリガーチェック": "やや弱い（-1.8pt / -0.9pt）。情報だけの札。見た側は次にその相手を脱がせるとき、おしおき返しや仕返しを避けられる", "道連れ": "新カードデッキの突出札。上位（+6.8pt / +5.8pt）。所持時勝率も +11pt。脱がせた側が必ず1枚失うので、持ち主は狙われにくい。「相手の手札が2枚のときだけ」などの制限候補", "ボディガード": "上位（+2.1pt / +1.4pt）。狙われると♥が入り、狙われにくくもなる", "おねだり": "ややプラス（+1.4pt / +0.9pt）。CPUは♥が3以上なら払う", "人気者": "ややプラス（+1.0pt / +0.8pt）。よわ♥が確定2♥になる地味な経済札", "かくれんぼ": "中立（+0.0pt / +0.1pt）。1周の防御。脱落時は不発", "口止め料": "中立（-0.4pt / -0.2pt）。相手の手番を1回飛ばす", "お色直し": "やや弱い（-1.2pt / -0.7pt）。手札の引き直し。CPU同士では得にならない", "ごほうび": "弱い（-1.4pt / -1.7pt）。CPUのチャレンジ成功回数が少ないので低く出る", "無敵宣言": "弱い（-1.8pt / -1.4pt）。次の1アクションがノーリスク。CPUはハッタリに合わせて使わないので低く出る。人間向け", "復讐の誓い": "弱い（-1.9pt / -1.6pt）。相手1人限定の無敵。脱落時は不発", "内緒話": "弱い（-2.5pt / -1.9pt）。相手にも情報を渡すぶん損。新カードデッキの最下位"}
CANDS = [["デッキ混成", "基本と新カードから6枚ずつ", "開始画面のカスタムで試せる。両デッキの上位札を混ぜると強い札が増えるので、下位どうしを混ぜるのも一案"], ["ハズレ1枚", "効果なしの札を1枚だけ入れる", "「脱いだのに何も起きない」場面を1割弱混ぜる。RULES.dudCount で切り替え"]]
def rows(key):
    return [{'id':r['id'],'name':r['name'],'eff':EFF[r['name']],'held':r['held'],'heldWin':r['heldWin'],'first':r['first'],'firstWin':r['firstWin'],'last':r['last'],'revive':r.get('revive',0),'reviveWin':r.get('reviveWin',0),'count':1 if r['id']!='none' else d[key].get('dud',0),'evalBy':'held' if r['name']=='着替え' else 'first','memo':MEMO[r['name']]} for r in d[key]['rows']]
s4, s3, s0 = d['basic_p4'], d['basic_p3456'], d.get('basic_p4_dud0')
f4, f3 = d.get('fresh_p4'), d.get('fresh_p3456')
hasDud = bool(s4.get('hasDud', True))
BASELBL = 'ハズレ比' if hasDud else '平均比'
BASENAME = 'ハズレ' if hasDud else '全カード平均'
DATA = {
  'conds': {
    'basic_p4': {'label':'基本・4人戦','deck':'basic','sub':f"基本デッキ・{s4['games']:,}戦",'games':s4['games'],'rows':rows('basic_p4'),'base':s4.get('base'),'heldBase':s4.get('heldBase'),'avgLog':round(s4['avgLog'],1),'winnerLostLife':round(s4['winnerLostLife'],3),'lifeLoss':round(s4['lifeLoss'],2)},
    'basic_p3456': {'label':'基本・3〜6人戦','deck':'basic','sub':f"基本デッキ・各{s3['games']//4:,}戦・{s3['games']:,}戦",'games':s3['games'],'rows':rows('basic_p3456'),'base':s3.get('base'),'heldBase':s3.get('heldBase')},
    **({'fresh_p4': {'label':'新カード・4人戦','deck':'fresh','sub':f"新カードデッキ・{f4['games']:,}戦",'games':f4['games'],'rows':rows('fresh_p4'),'base':f4.get('base'),'heldBase':f4.get('heldBase'),'avgLog':round(f4['avgLog'],1),'winnerLostLife':round(f4['winnerLostLife'],3),'lifeLoss':round(f4['lifeLoss'],2)},
        'fresh_p3456': {'label':'新カード・3〜6人戦','deck':'fresh','sub':f"新カードデッキ・各{f3['games']//4:,}戦・{f3['games']:,}戦",'games':f3['games'],'rows':rows('fresh_p3456'),'base':f3.get('base'),'heldBase':f3.get('heldBase')}} if f4 and f3 else {}),
  },
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
  <div class="eyebrow">CPU同士の自動対戦・2026-10-19 第11版・基本デッキ12枚と新カードデッキ12枚（各1枚・ハズレなし）／配られた2枚をそのまま仕込む／♥コレクター9♥＋公開時に山分け／おしおき返しは5♥／3〜6人・各デッキ20万戦</div>
  <h1><span class="nb">メスガキ・クー</span> <span class="nb">トリガー分析</span></h1>
  <p class="lede">基本デッキ12枚と新カードデッキ12枚を、どれが持ち主を勝たせているかで並べた。条件チップでデッキと人数を切り替えられる。指標は「1枚目の脱ぎで発動したあとに勝った割合」。プライドを1つ失った状態からの勝率なので、BASENAMEとの差で強さを見る。DUDNOTE</p>
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

<section>
  <h2>調整案と新カード案</h2>
  <p>数値を変えた試算（基本デッキ・4人戦・各WHATIFN戦）と、今後の案。</p>
  <div id="whatif"></div>
  <div class="grid" id="cands"></div>
</section>

<section>
  <h2>読み方</h2>
  <ul class="plain">
    <li>所持時勝率：そのカードを仕込んでいたプレイヤーの勝率。発動しなかった場合も含む。4人戦の平均は25%、3〜6人戦の平均は約22%。</li>
    <li>発動後勝率：1枚目の脱ぎでそのカードが発動したあと、そのプレイヤーが勝った割合。BASELBLはこの値とBASENAMEの差で、判定は±2ポイントを境にしている。</li>
    <li>脱落時発動率：発動のうち、2枚目の脱ぎ（脱落）で発動した割合。着替え以外は本人にほぼ意味がない発動。</li>
    HELDLI    <li>NOISENOTE 4人戦と3〜6人戦の両方で同じ向きに出ているかも見る。</li>
    <li>CPUは♥コレクターを持っていて目標まで3♥以内なら、ざぁ～こ♥より先に♥を集めて勝ちに行く。周りのCPUも目標が近い所持者を優先して狙う。</li>
  </ul>
  <p class="note">作成日 2026-10-20（第11版）　・　元データ：mesugaki-coup tools/sim.js（ヘッドレス自動対戦）</p>
</section>
</main>
<script>
const DATA = DATAJSON;
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct=(v,d=1)=>(v*100).toFixed(d)+'%';
const spct=(v,d=1)=>(v>=0?'+':'')+(v*100).toFixed(d)+'pt';
const fmt=n=>n.toLocaleString('ja-JP');
const state={cond:'basic_p4',tier:'all',q:'',sort:'delta',view:'cards'};
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
  if(k.bench.length) lines.push(`2軍（どちらにも入っていない）：${esc(k.bench.join('・'))}`);
  $('#deckline').innerHTML=lines.join('<br>')+'<br>開始画面でどちらかのデッキ、または好きな12枚を選べる。各プレイヤーに2枚配り、そのまま上半身・下半身に仕込む。';
}
function renderTotal(){
  const c4=DATA.conds.basic_p4, d=c4;
  const tot=Object.values(DATA.conds).reduce((a,c)=>a+c.games,0);
  $('#total').innerHTML=`<span><b>${fmt(tot)}</b>総対戦数</span><span><b>${d.lifeLoss}回</b>1ゲームの被弾</span><span><b>${pct(d.winnerLostLife,0)}</b>勝者が途中で被弾</span><span><b>${d.avgLog}行</b>平均ログ</span>`;
}
function renderMix(){
  const dk=DATA.conds[state.cond].deck||'basic'; const r4=compute(dk+'_p4'), r3=compute(dk+'_p3456');
  const d3=Object.fromEntries(r3.map(r=>[r.name,r.score]));
  const both=r4.filter(r=>r.id!=='none' && r.score>=DATA.thr && d3[r.name]>=0).map(r=>r.name);
  const top4=both.length?both:r4.filter(r=>r.tier==='強い').map(r=>r.name);
  const weak=r4.filter(r=>r.tier==='弱い' && d3[r.name]<0).map(r=>r.name);
  const col=r4.find(r=>r.name==='♥コレクター'), col3=r3.find(r=>r.name==='♥コレクター');
  const lastAvg=r4.reduce((a,r)=>a+r.last,0)/r4.reduce((a,r)=>a+r.first+r.last,0);
  const items=[
    [(DATA.conds[state.cond].deck==='fresh'?'新カード・':'基本・')+'強い', top4.join('・')||'なし', top4.length?`4人戦でBASELBL +${(DATA.thr*100).toFixed(0)}pt 以上で、3〜6人戦でもプラスのカード。`:`+2pt を超えるカードはない。いちばん高い${r4[0].name}でも ${spct(r4[0].score)} で、かなり平ら。`],
    ['弱い', weak.join('・')||'なし', weak.length?'両条件でマイナスのカード。':`両条件で −2pt を下回るカードはない。いちばん低い${r4[r4.length-1].name}でも ${spct(r4[r4.length-1].score)} で、不発（何も起きない）とほぼ同じ。`],
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
renderDeck(); renderTotal(); renderDud(); renderWhatif(); renderCands(); renderAll();
</script>
'''
import math
_r4=[r for r in d['basic_p4']['rows'] if r['id']!='none']
_n1=min(r['first'] for r in _r4); _pbar=d['basic_p4']['base']
_se=2*math.sqrt(_pbar*(1-_pbar)/_n1)*100
NOISENOTE=f"1枚物は約{_n1:,}回、2枚物はその2倍の発動。BASELBLの揺れは1枚物で±{_se:.1f}ポイント程度。判定の±2ポイントは誤差ではなく「効果の大きさ」の線引き。"
WHATIFN=f"{d['whatif'][0]['rows'][0]['first']*4:,}" if d.get('whatif') else ''
_held=any(r.get('evalBy')=='held' for c in DATA['conds'].values() for r in c['rows'])
HELDNOTE='着替えだけは脱落時にしか効かないので、所持時勝率の差（◆）で見る。' if _held else ''
HELDLI='    <li>着替えは発動後勝率ではなく所持時勝率の差で判定している（復活回数と復活後の勝率はカードに併記）。</li>\n' if _held else ''
page = page.replace('HELDNOTE', HELDNOTE).replace('HELDLI', HELDLI).replace('NOISENOTE', NOISENOTE).replace('WHATIFN', WHATIFN).replace('ハズレ比','BASELBL').replace('DUDNOTE', '' if hasDud else '不発（着替え・遺言が1枚目でめくれたとき）は −2ポイント前後に出るので、それが「何も起きない」の目安。').replace('BASELBL', BASELBL).replace('BASENAME', BASENAME).replace('DATAJSON', json.dumps(DATA, ensure_ascii=False)).replace('POSDARK', pos_dark).replace('NEGDARK', neg_dark)
open(out_art, 'w', encoding='utf-8').write(page)
open(out_repo, 'w', encoding='utf-8').write('<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n' + page + '</body>\n</html>\n')
print('written', len(page))
