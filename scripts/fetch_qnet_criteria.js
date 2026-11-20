const { chromium } = require('playwright');
(async () => {
  const out = process.argv[2];
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1100, height: 1500 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  await p.goto('https://www.q-net.or.kr/cst006.do?id=cst00601&code=1202&gSite=Q&gId=', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForTimeout(3000);
  const [pop] = await Promise.all([
    ctx.waitForEvent('page', { timeout: 30000 }),
    p.evaluate(() => { cst006Report('1910', '1018'); }),
  ]);
  await pop.waitForLoadState('domcontentloaded');
  await pop.waitForTimeout(15000);
  const pages=[];
  for (let i=0;i<12;i++){
    const t = await pop.evaluate(() => document.querySelector('#m2soft-crownix-page').innerText);
    if (pages.length && pages[pages.length-1]===t) break;
    pages.push(t);
    const dis = await pop.evaluate(() => document.querySelector('#crownix-toolbar-next').className.includes('disable'));
    if (dis) break;
    await pop.click('#crownix-toolbar-next button');
    await pop.waitForTimeout(4000);
  }
  require('fs').writeFileSync(out + '/criteria_2026.txt', pages.map((t,i)=>`=== 쪽 ${i+1} ===\n${t}`).join('\n'));
  console.log(pages.length);
  await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
