"""sim_summary.json からトリガー分析ページを生成する。
usage: python3 build_analysis.py <sim_summary.json> <out_artifact.html> <out_repo.html> [posHexDark negHexDark]
"""
import json, sys, html

src, out_art, out_repo = sys.argv[1], sys.argv[2], sys.argv[3]
pos_dark = sys.argv[4] if len(sys.argv) > 4 else '#f05a97'
neg_dark = sys.argv[5] if len(sys.argv) > 5 else '#4aa3f0'
d = json.load(open(src, encoding='utf-8'))

EFF = {'おしおき返し':'5♥持っていたら即時払って「ざぁ～こ♥」を打つ','山札のぞき':'山札を見て1枚選び、手札と入れ替える','ダサすぎ返し':'これを持っていれば「ダサすぎ♥」をブロックできる','まるみえ':'誰か一人の手札を表にする','総入れ替え':'自分以外の全員の手札を山札に戻し、同じ枚数を引き直す','みかじめ':'全員から1♥ずつもらう','まわして':'全員手札を1枚選び、右隣に渡す','値上げ':'自分以外は「ざぁ～こ♥」が8♥になる','♥コレクター':'自分の勝利条件に「12♥集める」を追加','ルール改変':'「ダサすぎ♥」を審問（相手の手札1枚を見て山札と交換させる）に変える','ハズレ':'効果なし'}
MEMO = {'おしおき返し':'5♥持っている時だけ発動する。発動すれば強いが、仕込みの段階でCPUは避けがち','みかじめ':'人数が多いほど得。4人戦でも少人数戦でも上位','ダサすぎ返し':'4人戦では上位。ダサすぎ♥を止める機会が多いほど効く','値上げ':'少人数戦では効果が薄い','総入れ替え':'4人戦ではプラス、少人数戦ではマイナス。全員に影響する効果で自分の得は安定しない','ルール改変':'ほぼ中立','山札のぞき':'ほぼ中立。手札の質改善は勝率に表れにくい','まるみえ':'全員が得する情報公開で、自分の得にならない','まわして':'中立からやや弱い','♥コレクター':'CPUは12♥を狙わず7♥でざぁ～こ♥を撃つので低く出る。人間が狙えば上がる余地はあるが、所持が知られると狙われやすい','ハズレ':'基準。発動しても何も起きない'}
CANDS = [
 ('道連れ','自分を脱がせた相手は影響力を1つ失う','脱落時に発動しても意味がある。強すぎるなら「相手が手札2枚のときだけ」'),
 ('遺言','自分の♥をすべて好きな相手に渡す','脱落後もキングメーカーになれる'),
 ('仕返し','自分を脱がせた相手から3♥奪う','♥が無くても発動する、攻撃側へのお返し'),
 ('値下げ','以後、自分の「ざぁ～こ♥」は5♥で撃てる','値上げの鏡'),
 ('山分け','自分より♥の多い全員から1♥もらう','負けている側ほど得する追い上げ'),
 ('着替え','残り手札1枚のとき、山札から1枚引いて手札に加える','ライフが戻る逆転札。条件付き'),
 ('みちづれのキス','自分を脱がせた相手の手札を1枚表にする','まるみえの対象を攻撃者に固定した版'),
 ('おしおき返し（調整）','「5♥払う」を「3♥払う」に','発動機会を増やす'),
]
def rows(key):
    return [{'id':r['id'],'name':r['name'],'eff':EFF[r['name']],'held':r['held'],'heldWin':r['heldWin'],'first':r['first'],'firstWin':r['firstWin'],'last':r['last'],'memo':MEMO[r['name']]} for r in d[key]['rows']]
s4, s3, s0 = d['sim_4p_dud5'], d['sim_235_dud5'], d['sim_4p_dud0']
DATA = {
  'conds': {
    'p4': {'label':'4人戦','sub':'ハズレ5枚・10,000戦','games':s4['games'],'rows':rows('sim_4p_dud5')},
    'p235': {'label':'2〜5人戦','sub':'各3,000戦・ハズレ5枚・9,000戦','games':s3['games'],'rows':rows('sim_235_dud5')},
  },
  'dud': {'d5':{'label':'ハズレ5枚','games':s4['games'],'avgLog':round(s4['avgLog'],1),'winnerLostLife':round(s4['winnerLostLife'],3),'lifeLoss':round(s4['lifeLoss'],2)},
          'd0':{'label':'ハズレ0枚','games':s0['games'],'avgLog':round(s0['avgLog'],1),'winnerLostLife':round(s0['winnerLostLife'],3),'lifeLoss':round(s0['lifeLoss'],2)}},
  'cands': [{'name':a,'eff':b,'aim':c} for a,b,c in CANDS],
  'thr': 0.015,
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
  <div class="eyebrow">CPU同士の自動対戦・2026-10-19・トリガーは自分だけ見える／3枚から2枚を仕込む／脱がせる側は相手が選ぶ／♥コレクター12♥</div>
  <h1><span class="nb">メスガキ・クー</span> <span class="nb">トリガー分析</span></h1>
  <p class="lede">トリガーカード10種＋ハズレを、どれが持ち主を勝たせているかで並べた。指標は「1枚目の脱ぎで発動したあとに勝った割合」。ライフを1つ失った状態からの勝率なので、ハズレ（何も起きない）との差で強さを見る。</p>
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
  <p>発動後勝率からハズレの発動後勝率を引いた差。右（ピンク）が持ち主の得、左（青）が損。±1ポイントは誤差の範囲。</p>
  <div class="bars" id="bars"></div>
</section>

<section aria-label="カード一覧">
  <h2>カードごとの数字 <small id="cardsub"></small></h2>
  <div id="out"></div>
</section>

<section>
  <h2>ハズレは要るか <small>4人戦・各10,000戦</small></h2>
  <div class="tbl"><table id="dudtbl"></table></div>
  <p>ハズレを0枚にしても、ゲームの長さ・逆転の起きやすさ・被弾回数は変わらない。バランスには効かず、純粋に「脱いだのに何も起きない」場面を入れるかどうかの好みで決めてよい。入れるなら、ハズレの枠を「1♥もらう」程度の小さい効果に置き換える案もある。</p>
</section>

<section>
  <h2>新カード候補</h2>
  <p>空撃ち（脱落時発動）でも意味がある札、攻撃側へのお返し、損な引きになっている札の差し替えを中心に。</p>
  <div class="grid" id="cands"></div>
</section>

<section>
  <h2>読み方</h2>
  <ul class="plain">
    <li>所持時勝率：そのカードを仕込んでいたプレイヤーの勝率。発動しなかった場合も含む。4人戦の平均は25%。</li>
    <li>発動後勝率：1枚目の脱ぎでそのカードが発動したあと、そのプレイヤーが勝った割合。ハズレ比はこの値とハズレの差で、判定は±1.5ポイントを境にしている。</li>
    <li>脱落時発動率：発動のうち、2枚目の脱ぎ（脱落）で発動した割合。本人にはほぼ意味がない発動。</li>
    <li>各カード約2,000〜4,000回の発動なので、±1ポイント程度は誤差。</li>
    <li>CPUは7♥でざぁ～こ♥を撃ち、12♥を狙わない。♥コレクターの数字はその前提で低く出ている。</li>
    <li>同じ数字は <a href="https://docs.google.com/spreadsheets/d/1rPmmPNhjmtu2PtSg7NSGkMvegFs8LFiNDSzIKj6yhLU/edit#gid=20261019" target="_blank" rel="noopener">GFカードシートの「トリガー分析」タブ</a> にもある。</li>
  </ul>
  <p class="note">作成日 2026-10-19　・　元データ：mesugaki-coup tools/sim.js（ヘッドレス自動対戦）</p>
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
  const c4=DATA.conds.p4, c3=DATA.conds.p235, d=DATA.dud.d5;
  $('#total').innerHTML=`<span><b>${fmt(c4.games)}</b>4人戦</span><span><b>${fmt(c3.games)}</b>2〜5人戦</span><span><b>${d.lifeLoss}回</b>1ゲームの被弾</span><span><b>${pct(d.winnerLostLife,0)}</b>勝者が途中で被弾</span><span><b>${d.avgLog}行</b>平均ログ</span>`;
}
function renderMix(){
  const r4=compute('p4'), r3=compute('p235');
  const top4=r4.filter(r=>r.tier==='強い').map(r=>r.name);
  const weak=r4.filter(r=>r.tier==='弱い').map(r=>r.name);
  const lastAvg=r4.reduce((a,r)=>a+r.last,0)/r4.reduce((a,r)=>a+r.first+r.last,0);
  const items=[
    ['強い', top4.join('・'), `4人戦でハズレ比 +${(DATA.thr*100).toFixed(1)}pt 以上。2〜5人戦でも上位は みかじめ・ダサすぎ返し・おしおき返し。`],
    ['弱い', weak.join('・')||'なし', '♥コレクターは所持しているだけで勝率が3ポイント下がる。まるみえは少人数戦でマイナス。'],
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
renderTotal(); renderMix(); renderDud(); renderCands(); renderAll();
</script>
'''
page = page.replace('DATAJSON', json.dumps(DATA, ensure_ascii=False)).replace('POSDARK', pos_dark).replace('NEGDARK', neg_dark)
open(out_art, 'w', encoding='utf-8').write(page)
open(out_repo, 'w', encoding='utf-8').write('<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n' + page + '</body>\n</html>\n')
print('written', len(page))
