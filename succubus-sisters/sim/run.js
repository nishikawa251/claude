// サキュバスシスターズ：CPU同士の自動対戦で、サキュバス能力とカードの強さを集計する
//
// 使い方（Playwright が入っている環境で）
//   node sim/run.js [1キャラ×1人数あたりの試合数=40] [出力先=sim/result.json] [カード差し替えJSON]
//
// カード差し替えJSON（例：sim/patches/buff1.json）を渡すと、カードの数値や効果文を書き換えた状態で回す。
//   [{ "ids":[1,2], "face":"top", "set":{ "atk":6, "cost":"HP-3", "text":"《追撃》続けてもう1枚▲カードを出しても良い。" } }]
//
// 13キャラ＋「能力なし（比較用）」を、3〜6人それぞれで同じ試合数ずつサキュバスにして対戦させる。
// 画面の描画と待ち時間を止め、全員をCPUにして index.html のゲーム処理をそのまま動かす。
const path = require('path');
const fs = require('fs');
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node22/lib/node_modules/playwright'); }

const PER = Number(process.argv[2] || 40);
const OUT = process.argv[3] || path.join(__dirname, 'result.json');
const PATCH = process.argv[4] ? JSON.parse(fs.readFileSync(process.argv[4], 'utf8')) : [];
const PAGE = 'file://' + path.join(__dirname, '..', 'index.html');

(async () => {
  const browser = await playwright.chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.route('**fonts.g**', r => r.abort());
  await page.goto(PAGE);

  const result = await page.evaluate(async ([PER, PATCH]) => {
    // カードの差し替え（面ごと）
    for (const pt of PATCH){
      for (const d of CARD_DEFS.filter(d => pt.ids.includes(d.id))){
        const f = d[pt.face || 'top'];
        if (!f) continue;
        const st = pt.set;
        if ('atk' in st) f.atk = st.atk;
        if ('def' in st) f.def = st.def;
        if ('el' in st) f.el = EL_KEY[st.el] || st.el;
        if ('range' in st) f.range = parseRange(st.range);
        if ('cost' in st) f.cost = parseCost(st.cost);
        if ('text' in st){ f.text = st.text; f.kw = parseKw(st.text); }
        f.isDef = f.marks.includes('○') || f.def !== null;
      }
    }
    // 描画と待ち時間を止める
    window.render = () => {};
    window.fx = () => {};
    window.wait = async () => {};
    window.ask = async () => true;

    const CONTROL = { key:'control', name:'能力なし（比較用）', short:'比較', glyph:'無', gem:'#888', text:'共通のサキュバス能力（手札上限＋1・《吸収》）だけ。' };
    const SUCC_CHARS = [...CHARACTERS, CONTROL];

    const chars = {};   // サキュバスのキャラ別
    const cards = {};   // カードの面ごと
    const baseline = { sister:[0, 0], succubus:[0, 0], fallen:[0, 0] };   // [勝ち点合計, 回数]
    const byCount = {};
    let pendingUses = [];

    const cardKey = f => f.name;
    const C = f => cards[cardKey(f)] || (cards[cardKey(f)] = {
      name:f.name, marks:f.marks.join(''), el:f.el, atk:f.atk, def:f.def, text:f.text,
      ids:new Set(), uses:0, atkUses:0, defUses:0, cost:0, triggers:0, dealt:0, kills:0, prevented:0, heal:0, counter:0, reflect:0, winSum:0, expSum:0,
    });
    CARD_DEFS.forEach(d => { C(d.top).ids.add(d.id); if (d.heart) C(d.heart).ids.add(d.id); });
    const use = (f, p, kind) => { const c = C(f); c.uses++; if (kind === 'atk') c.atkUses++; if (kind === 'def') c.defUses++; pendingUses.push({ c, role:p.role }); };

    window.onGameEvent = (type, d) => {
      if (type === 'play') d.faces.forEach(f => use(f, d.p, f.isAtk ? 'atk' : 'sup'));
      if (type === 'strike'){
        const { atk, t, faces } = d;
        faces.forEach(f => use(f, t, 'def'));
        if (atk.reflectedBy){ C(atk.reflectedBy).reflect += d.dmg; }
        else if (atk.faces && atk.faces.length){
          const tot = atk.faces.reduce((s, f) => s + (f.atk || 0), 0) || atk.faces.length;
          atk.faces.forEach(f => { const w = (f.atk || (tot === atk.faces.length ? 1 : 0)) / tot; C(f).dealt += d.dmg * w; if (d.killed) C(f).kills += w; });
        }
        if (d.by){ C(d.by).prevented += atk.instakill ? t.hp : atk.power; return; }
        if (!faces.length) return;
        if (d.nullified){ const nf = faces.find(f => f.kw.nullify && f.kw.nullify.includes(d.el)); if (nf) C(nf).prevented += atk.instakill ? t.hp : atk.power; return; }
        const valid = faces.filter(f => f.def && validDef(f, atk, d.el));
        const sum = valid.reduce((s, f) => s + f.def, 0);
        const saved = atk.instakill && d.dmg === 0 ? t.hp : Math.min(atk.power, d.defSum || 0);
        valid.forEach(f => { C(f).prevented += sum ? saved * f.def / sum : 0; });
      }
      if (type === 'heal') C(d.face).heal += d.amount;
      if (type === 'cost') C(d.face).cost += d.hp;
      if (type === 'amulet'){ use(d.face, d.p, 'sup'); C(d.face).triggers++; C(d.face).heal += 10; }
      if (type === 'bowfire'){ use(d.face, d.p, 'atk'); C(d.face).triggers++; }
      if (type === 'counter') C(d.face).counter += d.dmg;
    };

    const games = [];
    const stuck = [];
    const runOne = (n, sc) => new Promise(resolve => {
      pendingUses = [];
      const pool = shuffle(CHARACTERS.slice());
      M = { game:GAMES - 1, players:Array.from({ length:n }, (_, k) => ({ i:k, human:false, char:pool[k % pool.length], name:`P${k}`, vp:0, history:[] })) };
      const prevEmit = window.onGameEvent;
      let manifested = false;
      window.onGameEvent = (type, d) => {
        prevEmit(type, d);
        if (type === 'manifest' && d.p.role === 'succubus') manifested = true;
        if (type === 'end'){
          window.onGameEvent = prevEmit;
          const succ = G.players.find(p => p.role === 'succubus');
          const out = { sister:0, succubus:0, fallen:0 };
          if (d.reason === 'last'){ out.succubus = out.fallen = 1; }
          else if (d.reason === 'succubus'){ out.sister = 1; }
          else if (d.reason === 'deck'){ out.sister = out.succubus = out.fallen = 0.5; }
          else { out.sister = out.succubus = out.fallen = 0.5; }
          const vp = d.gain.get(succ).reduce((s, x) => s + x.v, 0);
          games.push({ n, sc:sc.key, reason:d.reason, rounds:G.round, manifested, vp, alive:succ.alive });
          ['sister', 'succubus', 'fallen'].forEach(r => { if (G.players.some(p => p.role === r)){ baseline[r][0] += out[r]; baseline[r][1]++; } });
          for (const u of pendingUses){ u.c.winSum += out[u.role]; u.c._roles = u.c._roles || []; u.c._roles.push(u.role); }
          setTimeout(resolve, 0);
        }
      };
      nextGame();
      const succ = G.players.find(p => p.role === 'succubus');
      succ.char = sc;
      // 止まったゲームは記録して次へ進む
      const gid = gameId;
      setTimeout(() => { if (gameId === gid && window.onGameEvent !== prevEmit){ window.onGameEvent = prevEmit; stuck.push({ n, sc:sc.key, round:G.round, log:G.log.slice(-12).map(l => l.text) }); resolve(); } }, 3000);
    });

    const t0 = performance.now();
    for (let n = 3; n <= 6; n++)
      for (const sc of SUCC_CHARS)
        for (let k = 0; k < PER; k++) await runOne(n, sc);
    const ms = performance.now() - t0;

    // 期待勝率（役職ごとの平均）でカードの「使った側の勝率の上振れ」を出す
    const base = r => baseline[r][1] ? baseline[r][0] / baseline[r][1] : 0.5;
    for (const c of Object.values(cards)){ c.expSum = (c._roles || []).reduce((s, r) => s + base(r), 0); delete c._roles; c.ids = [...c.ids].sort((a, b) => a - b); }

    return { per:PER, ms, games, stuck, cards:Object.values(cards), baseline:{ sister:base('sister'), succubus:base('succubus'), fallen:base('fallen') },
      chars:SUCC_CHARS.map(c => ({ key:c.key, name:c.name, text:c.text, common:c.common || COMMON_SUCC })) };
  }, [PER, PATCH]);

  fs.writeFileSync(OUT, JSON.stringify({ ...result, errors }, null, 1));
  console.log(`games=${result.games.length} time=${(result.ms / 1000).toFixed(1)}s errors=${errors.length} -> ${OUT}`);
  await browser.close();
})();
