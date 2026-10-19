"""sim_summary.json からトリガー分析ページを生成する。
usage: python3 build_analysis.py <sim_summary.json> <out_artifact.html> <out_repo.html> [posHexDark negHexDark]
"""
import json, sys, html

src, out_art, out_repo = sys.argv[1], sys.argv[2], sys.argv[3]
pos_dark = sys.argv[4] if len(sys.argv) > 4 else '#f05a97'
neg_dark = sys.argv[5] if len(sys.argv) > 5 else '#4aa3f0'
d = json.load(open(src, encoding='utf-8'))

EFF = {'みちづれのキス':'自分を脱がせた相手の手札を1枚こっそり見る（自分だけ見える）','仕返し':'自分を脱がせた相手から3♥奪う','山分け':'自分より♥の多い全員から1♥ずつもらう','値下げ':'以後、自分の「ざぁ～こ♥」は5♥で撃てる','おしおき返し':'4♥持っていたら即時払って「ざぁ～こ♥」を打つ','山札のぞき':'山札を見て1枚選び、手札と入れ替える','ダサすぎ返し':'これを持っていれば「ダサすぎ♥」をブロックできる','まるみえ':'誰か一人の手札を表にする','総入れ替え':'自分以外の全員の手札を山札に戻し、同じ枚数を引き直す','みかじめ':'全員から1♥ずつもらう','まわして':'全員手札を1枚選び、右隣に渡す','値上げ':'自分以外は「ざぁ～こ♥」が8♥になる','♥コレクター':'自分の勝利条件に「10♥集める」を追加','ルール改変':'「ダサすぎ♥」を審問（相手の手札1枚を見て山札と交換させる）に変える','ハズレ':'効果なし'}
MEMO = {"おしおき返し": "4♥に上げても最上位。発動した瞬間に相手を脱がせるので、脱落時の空撃ちでも相打ちにできる", "仕返し": "脱がせた相手から3♥取り返す。2枚入りで発動数が多く、数字は安定して上位", "値下げ": "自分だけざぁ～こ♥が5♥になる。4人戦では中立寄り、3〜6人戦では最上位と条件で揺れる", "みちづれのキス": "脱がせた相手の手札を自分だけ見る。見た相手の主張にはチャレンジしなくなるので無駄死にが減る。CPUが「知っているカード」を逆に疑う癖を直したら、マイナスからプラスに変わった", "山札のぞき": "手札の質を上げる。前回は中立だったが今回はややプラス", "みかじめ": "全員から1♥。人数が多いほど得だが、今回はやや控えめ", "まわして": "中立。全員が1枚ずつ渡すので自分の得にならない", "値上げ": "中立。自分以外のざぁ～こ♥が8♥になるが、終盤はあまり効かない", "山分け": "中立。負けているときに発動しやすいが、取れるのは1〜2♥", "ルール改変": "中立。全員に効くので自分の得にならない", "ダサすぎ返し": "中立。前回は上位だったが、2枚配りで仕込む札を選べなくなった影響か平均に戻った", "総入れ替え": "やや弱い。全員に影響する効果で自分の得は安定しない", "♥コレクター": "10♥にしても最下位。勝利条件が公開されて狙われ、残り1枚で10♥まで耐えられない。CPUに「あと3♥以内なら取りに行く」手を入れても変わらず。9♥なら中立、8♥なら上位（下の試算）", "まるみえ": "今回は0枚（山に入れていない）", "ハズレ": "基準。配られた2枚をそのまま仕込むので、ハズレも必ず場に出る"}
CANDS = [["♥コレクターを9♥に", "自分の勝利条件に「9♥集める」を追加する", "4人戦1万戦の試算でハズレ比 −1.4pt（中立）。10♥のままだと −4.8pt で最下位"], ["♥コレクターを8♥に", "自分の勝利条件に「8♥集める」を追加する", "試算で +3.8pt と最上位に入る。強すぎるならこちらは避ける"], ["道連れ", "自分を脱がせた相手はプライドを1つ失う", "脱落時に発動しても意味がある。強すぎるなら「相手が手札2枚のときだけ」"], ["遺言", "自分の♥をすべて好きな相手に渡す", "脱落後もキングメーカーになれる"], ["着替え", "残り手札1枚のとき、山札から1枚引いて手札に加える", "ライフが戻る逆転札。条件付き"]]
def rows(key):
    return [{'id':r['id'],'name':r['name'],'eff':EFF[r['name']],'held':r['held'],'heldWin':r['heldWin'],'first':r['first'],'firstWin':r['firstWin'],'last':r['last'],'memo':MEMO[r['name']]} for r in d[key]['rows']]
s4, s3, s0 = d['sim_4p_dud5'], d['sim_235_dud5'], d['sim_4p_dud0']
DATA = {
  'conds': {
    'p4': {'label':'4人戦','sub':'ハズレ2枚・10,000戦','games':s4['games'],'rows':rows('sim_4p_dud5')},
    'p3456': {'label':'3〜6人戦','sub':'各3,000戦・ハズレ2枚・12,000戦','games':s3['games'],'rows':rows('sim_235_dud5')},
  },
  'dud': {'d5':{'label':'ハズレ2枚','games':s4['games'],'avgLog':round(s4['avgLog'],1),'winnerLostLife':round(s4['winnerLostLife'],3),'lifeLoss':round(s4['lifeLoss'],2)},
          'd0':{'label':'ハズレ0枚','games':s0['games'],'avgLog':round(s0['avgLog'],1),'winnerLostLife':round(s0['winnerLostLife'],3),'lifeLoss':round(s0['lifeLoss'],2)}},
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
  <div class="eyebrow">CPU同士の自動対戦・2026-10-19 第3版・トリガー13種16枚＋ハズレ2枚／配られた2枚をそのまま仕込む／脱がせる側は相手が選ぶ／♥コレクター10♥／おしおき返しは4♥／3〜6人</div>
  <h1><span class="nb">メスガキ・クー</span> <span class="nb">トリガー分析</span></h1>
  <p class="lede">トリガーカード13種（計16枚）＋ハズレ2枚を、どれが持ち主を勝たせているかで並べた。指標は「1枚目の脱ぎで発動したあとに勝った割合」。プライドを1つ失った状態からの勝率なので、ハズレ（何も起きない）との差で強さを見る。</p>
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
  <p>発動後勝率からハズレの発動後勝率を引いた差。右（ピンク）が持ち主の得、左（青）が損。±2ポイントは誤差の範囲。</p>
  <div class="bars" id="bars"></div>
</section>

<section aria-label="カード一覧">
  <h2>カードごとの数字 <small id="cardsub"></small></h2>
  <div id="out"></div>
</section>

<section>
  <h2>ハズレ2枚と0枚の比較 <small>4人戦・各10,000戦</small></h2>
  <div class="tbl"><table id="dudtbl"></table></div>
  <p>2枚配りになってハズレは必ず仕込まれるようになったが、2枚でも0枚でもゲームの長さ・逆転の起きやすさ・被弾回数は変わらない。ハズレはバランスには効かず、「脱いだのに何も起きない」場面を1割ほど混ぜるための札。</p>
</section>

<section>
  <h2>調整案と新カード候補</h2>
  <p>♥コレクターの目標を変えた試算（4人戦・各10,000戦）と、空撃ち（脱落時発動）でも意味がある札の案。</p>
  <div class="tbl"><table id="whatif"></table></div>
  <div class="grid" id="cands"></div>
</section>

<section>
  <h2>読み方</h2>
  <ul class="plain">
    <li>所持時勝率：そのカードを仕込んでいたプレイヤーの勝率。発動しなかった場合も含む。4人戦の平均は25%、3〜6人戦の平均は約22%。</li>
    <li>発動後勝率：1枚目の脱ぎでそのカードが発動したあと、そのプレイヤーが勝った割合。ハズレ比はこの値とハズレの差で、判定は±2ポイントを境にしている。</li>
    <li>脱落時発動率：発動のうち、2枚目の脱ぎ（脱落）で発動した割合。本人にはほぼ意味がない発動。</li>
    <li>1枚物は約2,000回、2枚物とハズレは約4,200回の発動。1枚物のハズレ比は±2ポイント程度の揺れがあるので、4人戦と3〜6人戦の両方で同じ向きに出ているかを見る。</li>
    <li>CPUは♥コレクターを持っていて目標まで3♥以内なら、ざぁ～こ♥より先に♥を集めて勝ちに行く。周りのCPUも目標が近い所持者を優先して狙う。</li>
  </ul>
  <p class="note">作成日 2026-10-19（第3版）　・　元データ：mesugaki-coup tools/sim.js（ヘッドレス自動対戦）</p>
</section>
</main>
<script>
const DATA = DATAJSON;
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct=(v,d=1)=>(v*100).toFixed(d)+'%';
const spct=(v,d=1)=>(v>=0?'+':'')+(v*100).toFixed(d)+'pt';
const fmt=n=>n.toLocaleString('ja-JP');
const state={cond:'p4',tier:'all',q:'',sort:'delta',view:'cards'};
function compute(cond){
  const rows=DATA.conds[cond].rows.map(r=>({...r}));
  const dud=rows.find(r=>r.id==='none');
  const base=dud.firstWin/dud.first;
  for(const r of rows){ r.heldp=r.heldWin/r.held; r.firstp=r.firstWin/r.first; r.delta=r.firstp-base; r.lastRate=r.last/(r.first+r.last); r.tier=r.id==='none'?'none':(r.delta>=DATA.thr?'強い':(r.delta<=-DATA.thr?'弱い':'中立')); }
  return rows;
}
const tierCls={'強い':'tS','中立':'tN','弱い':'tW','none':'tA'};
const tierLabel=t=>t==='none'?'基準':t;
function renderTotal(){
  const c4=DATA.conds.p4, c3=DATA.conds.p3456, d=DATA.dud.d5;
  $('#total').innerHTML=`<span><b>${fmt(c4.games)}</b>4人戦</span><span><b>${fmt(c3.games)}</b>3〜6人戦</span><span><b>${d.lifeLoss}回</b>1ゲームの被弾</span><span><b>${pct(d.winnerLostLife,0)}</b>勝者が途中で被弾</span><span><b>${d.avgLog}行</b>平均ログ</span>`;
}
function renderMix(){
  const r4=compute('p4'), r3=compute('p3456');
  const d3=Object.fromEntries(r3.map(r=>[r.name,r.delta]));
  const both=r4.filter(r=>r.id!=='none' && r.delta>=DATA.thr && d3[r.name]>=0).map(r=>r.name);
  const top4=both.length?both:r4.filter(r=>r.tier==='強い').map(r=>r.name);
  const weak=r4.filter(r=>r.tier==='弱い' && d3[r.name]<0).map(r=>r.name);
  const col=r4.find(r=>r.name==='♥コレクター'), col3=r3.find(r=>r.name==='♥コレクター');
  const lastAvg=r4.reduce((a,r)=>a+r.last,0)/r4.reduce((a,r)=>a+r.first+r.last,0);
  const items=[
    ['強い', top4.join('・'), `4人戦でハズレ比 +${(DATA.thr*100).toFixed(0)}pt 以上で、3〜6人戦でもプラスのカード。`],
    ['弱い', weak.join('・')||'なし', `♥コレクターは発動後勝率がハズレより ${Math.abs(col.delta*100).toFixed(1)}pt（3〜6人戦 ${Math.abs(col3.delta*100).toFixed(1)}pt）低い。勝利条件が公開されて狙われるため。`],
    ['空撃ち', pct(lastAvg,0), '発動のうち脱落時（2枚目の脱ぎ）に起きた割合。本人には意味のない発動が半分近くある。'],
    ['効果の幅', `${spct(Math.max(...r4.map(r=>r.delta)))} 〜 ${spct(Math.min(...r4.map(r=>r.delta)))}`, 'トリガーは負けかけた側に起きるので、どれも勝敗を覆すほどの力はない。'],
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
  const list=rows.filter(r=>r.id!=='none').sort((a,b)=>b.delta-a.delta);
  const max=Math.max(...list.map(r=>Math.abs(r.delta)), 0.01);
  const dud=rows.find(r=>r.id==='none');
  $('#bars').innerHTML=`<div class="barhead"><span>カード</span><span class="mid">ハズレ（発動後勝率 ${pct(dud.firstp)}）を0とした差</span><span class="r">ハズレ比</span></div>`+list.map(r=>{
    const w=Math.abs(r.delta)/max*50; const zero=Math.abs(r.delta)<0.001;
    const style=r.delta>=0?`left:50%;width:${w}%`:`right:50%;width:${w}%`;
    return `<div class="bar" title="${esc(r.name)}：発動後勝率 ${pct(r.firstp)}（ハズレ ${pct(dud.firstp)}）、発動 ${fmt(r.first)}回"><span class="bn">${esc(r.name)}</span><span class="bt"><span class="bf ${r.delta<0?'neg':''} ${zero?'zero':''}" style="${style}"></span></span><span class="bv">${spct(r.delta)} <small>${pct(r.firstp)}</small></span></div>`;
  }).join('');
}
function filtered(rows){
  let list=rows.slice();
  if(state.tier!=='all') list=list.filter(r=>r.tier===state.tier);
  if(state.q){ const q=state.q.toLowerCase(); list=list.filter(r=>(r.name+r.eff+r.memo).toLowerCase().includes(q)); }
  const s=state.sort;
  list.sort((a,b)=> s==='name'?a.name.localeCompare(b.name,'ja') : s==='heldp'?b.heldp-a.heldp : s==='first'?b.first-a.first : b.delta-a.delta);
  return list;
}
function card(r){
  return `<article class="cc"><div class="cc-top"><span class="tier ${tierCls[r.tier]}">${tierLabel(r.tier)}</span><span>発動 ${fmt(r.first)}回</span><span class="qty">所持 ${fmt(r.held)}</span></div>
  <h3 class="cc-name">${esc(r.name)}</h3><p class="txt">${esc(r.eff)}</p>
  <div class="stats"><span class="num"><b>${pct(r.firstp)}</b>発動後勝率</span><span class="num"><b>${spct(r.delta)}</b>ハズレ比</span></div>
  <div class="meta"><span>所持時勝率 <b>${pct(r.heldp)}</b></span><span>脱落時発動率 <b>${pct(r.lastRate,0)}</b></span></div>
  <p class="memo">${esc(r.memo)}</p></article>`;
}
function table(list){
  return `<div class="tbl"><table><thead><tr><th>カード</th><th>判定</th><th>効果</th><th class="n">所持回数</th><th class="n">所持時勝率</th><th class="n">発動回数</th><th class="n">発動後勝率</th><th class="n">ハズレ比</th><th class="n">脱落時発動率</th><th>メモ</th></tr></thead><tbody>`+
    list.map(r=>`<tr><td class="nm">${esc(r.name)}</td><td><span class="tier ${tierCls[r.tier]}">${tierLabel(r.tier)}</span></td><td class="tx">${esc(r.eff)}</td><td class="n">${fmt(r.held)}</td><td class="n">${pct(r.heldp)}</td><td class="n">${fmt(r.first)}</td><td class="n">${pct(r.firstp)}</td><td class="n">${spct(r.delta)}</td><td class="n">${pct(r.lastRate,0)}</td><td class="tx">${esc(r.memo)}</td></tr>`).join('')+`</tbody></table></div>`;
}
function renderCards(rows){
  const c=DATA.conds[state.cond];
  $('#cardsub').textContent=`${c.label}・${c.sub}`;
  const list=filtered(rows);
  $('#shown').textContent=`${list.length} / ${rows.length} 枚`;
  $('#out').innerHTML=list.length? (state.view==='table'?table(list):`<div class="grid">${list.map(card).join('')}</div>`) : '<div class="empty">該当するカードがない</div>';
}
function renderDud(){
  const d=DATA.dud;
  $('#dudtbl').innerHTML=`<thead><tr><th>条件</th><th class="n">ゲーム数</th><th class="n">平均ログ行数</th><th class="n">勝者が途中で被弾していた率</th><th class="n">1ゲームの被弾回数</th></tr></thead><tbody>`+['d5','d0'].map(k=>`<tr><td class="nm">${esc(d[k].label)}</td><td class="n">${fmt(d[k].games)}</td><td class="n">${d[k].avgLog}</td><td class="n">${pct(d[k].winnerLostLife)}</td><td class="n">${d[k].lifeLoss}</td></tr>`).join('')+'</tbody>';
}
function renderWhatif(){
  const w=DATA.whatif; if(!w.length){ $('#whatif').closest('.tbl').hidden=true; return; }
  $('#whatif').innerHTML='<thead><tr><th>♥コレクターの目標</th><th class="n">発動後勝率</th><th class="n">ハズレ比</th><th class="n">所持時勝率</th><th>判定</th></tr></thead><tbody>'+w.map(x=>`<tr><td class="nm">${x.goal}♥${x.goal===10?'（現行）':''}</td><td class="n">${pct(x.firstp)}</td><td class="n">${spct(x.delta)}</td><td class="n">${pct(x.heldp)}</td><td><span class="tier ${x.delta>=DATA.thr?'tS':x.delta<=-DATA.thr?'tW':'tN'}">${x.delta>=DATA.thr?'強い':x.delta<=-DATA.thr?'弱い':'中立'}</span></td></tr>`).join('')+'</tbody>';
}
function renderCands(){
  $('#cands').innerHTML=DATA.cands.map(c=>`<article class="cc"><h3 class="cc-name">${esc(c.name)}</h3><p class="txt">${esc(c.eff)}</p><p class="memo">${esc(c.aim)}</p></article>`).join('');
}
function renderAll(){
  renderChips();
  const rows=compute(state.cond);
  renderBars(rows); renderCards(rows);
}
$('#sort').onchange=e=>{ state.sort=e.target.value; renderAll(); };
$('#view').onchange=e=>{ state.view=e.target.value; renderAll(); };
$('#q').oninput=e=>{ state.q=e.target.value.trim(); renderAll(); };
renderTotal(); renderMix(); renderDud(); renderWhatif(); renderCands(); renderAll();
</script>
'''
page = page.replace('DATAJSON', json.dumps(DATA, ensure_ascii=False)).replace('POSDARK', pos_dark).replace('NEGDARK', neg_dark)
open(out_art, 'w', encoding='utf-8').write(page)
open(out_repo, 'w', encoding='utf-8').write('<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n' + page + '</body>\n</html>\n')
print('written', len(page))
