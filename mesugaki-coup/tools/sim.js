const { chromium } = require('playwright');
const url = 'file:///home/user/claude/mesugaki-coup/index.html';
const N = parseInt(process.argv[2] || '100', 10);
const PLAYERS = (process.argv[3] || '4').split(',').map(Number);
const DUD = parseInt(process.argv[4] || '5', 10);
// 任意：RULES の上書き（例 collectorGoal=8,coupCost=6）
const OVR = {}; for (const kv of (process.argv[5] || '').split(',').filter(Boolean)) { const [k, v] = kv.split('='); OVR[k] = isNaN(Number(v)) ? (v === 'true' ? true : v === 'false' ? false : v) : Number(v); }
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto(url); await page.waitForTimeout(300);
  const t0 = Date.now();
  const res = await page.evaluate(async ({ N, PLAYERS, DUD, OVR }) => {
    S.headless = true; RULES.dudCount = DUD; Object.assign(RULES, OVR);
    const ids = [...TRIGGERS.map(t => t.id), 'none'];
    const st = {}; for (const id of ids) st[id] = { held: 0, heldWin: 0, first: 0, firstWin: 0, last: 0, firstByWin: 0, firstBy: 0 };
    const out = { games: 0, turns: 0, winnerLostLife: 0, winnerHearts: 0, lifeLossTotal: 0, errors: 0, winBySeat: {}, firstTurnWin: 0 };
    for (let g = 0; g < N; g++) {
      const n = PLAYERS[g % PLAYERS.length];
      let first;
      try { await newGame(n, Math.floor(Math.random() * CHARS.length), { auto: true }); } catch (e) { out.errors++; continue; }
      if (!S.winner) { out.errors++; continue; }
      out.games++; out.turns += S.log.length; out.winnerHearts += S.winner.hearts;
      const w = S.winner;
      for (const p of S.players) {
        const win = p === w ? 1 : 0;
        for (const k of ['top', 'bottom']) { const id = p.triggers[k].card.id; st[id].held++; st[id].heldWin += win; }
      }
      const lostLife = {};
      for (const a of S.acts) {
        lostLife[a.i] = (lostLife[a.i] || 0) + 1; out.lifeLossTotal++;
        const win = S.players[a.i] === w ? 1 : 0;
        if (a.left === 1) { st[a.id].first++; st[a.id].firstWin += win; if (a.by >= 0 && a.by !== a.i) { st[a.id].firstBy++; st[a.id].firstByWin += (S.players[a.by] === w ? 1 : 0); } }
        else st[a.id].last++;
      }
      if (lostLife[w.i]) out.winnerLostLife++;
    }
    return { st, out };
  }, { N, PLAYERS, DUD, OVR });
  res.ms = Date.now() - t0; res.errors = errors.slice(0, 3); res.cfg = { N, PLAYERS, DUD, OVR };
  console.log(JSON.stringify(res));
  await browser.close();
})();
