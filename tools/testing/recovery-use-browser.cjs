// Run against dedicated sites only. QA_TOKEN is a test-environment gate, not a login.
// Config supplies literal expected URLs/hashes; no product projection builds expectations.
const { chromium } = require('playwright');
const fs = require('fs');
const crypto = require('crypto');
(async () => {
  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch({headless: true});
  const context = await browser.newContext({extraHTTPHeaders: {'X-OWR-Trial': process.env.QA_TOKEN}});
  const results = [];
  for (const site of cfg.sites) {
    const page = await context.newPage();
    const blocked = [], errors = [];
    await page.route('**/*', route => {
      if (site.forbidden.some(prefix => route.request().url().startsWith(prefix))) {
        blocked.push(route.request().url()); return route.abort();
      }
      return route.continue();
    });
    page.on('pageerror', e => errors.push(e.message));
    try {
      const response = await page.goto(site.tablePage, {waitUntil: 'networkidle'});
      if (response.status() !== 200) throw Error('Table page HTTP '+response.status());
      const table = page.locator('#tablepress-'+site.tableId);
      await page.waitForFunction(id => window.jQuery?.fn.dataTable?.isDataTable('#tablepress-'+id), site.tableId, {timeout: 15000});
      const search = page.locator('.dt-search input, .dataTables_filter input').first();
      await search.fill('Row 25');
      await page.waitForFunction(() => document.querySelectorAll('table.tablepress tbody tr').length === 1);
      if (!(await table.locator('tbody').innerText()).includes('Row 25')) throw Error('Search result mismatch');
      await search.fill('');
      await table.locator('thead th').nth(1).click();
      await table.locator('thead th').nth(1).click();
      await page.waitForFunction(() => document.querySelector('table.tablepress tbody tr')?.textContent.includes('Row 25'));
      const before = await table.locator('tbody tr').first().innerText();
      await page.locator('.dt-paging .next, .dataTables_paginate .next').first().click();
      if (await table.locator('tbody tr').first().innerText() === before) throw Error('Paging did not advance');
      if (await page.evaluate(() => Boolean(window.__owrArchivedExecuted))) throw Error('Archived script executed');
      results.push({site:site.name, test:'table-use', ok:true});
    } catch (e) { results.push({site:site.name,test:'table-use',ok:false,error:e.message}); }
    for (const doc of site.documents) {
      try {
        const r = await page.goto(doc.url, {waitUntil:'networkidle'});
        if (r.status()!==200) throw Error('Document HTTP '+r.status());
        const link = page.getByRole('link', {name:'Page',exact:true});
        if (await link.getAttribute('href') !== doc.expectedPage) throw Error('Wrong page reference: '+await link.getAttribute('href'));
        const img = page.getByRole('img', {name:'image',exact:true});
        if (await img.getAttribute('src') !== doc.expectedImage) throw Error('Wrong image reference: '+await img.getAttribute('src'));
        if (!await img.evaluate(el => el.complete && el.naturalWidth>0)) throw Error('Image not usable');
        const image = await context.request.get(doc.expectedImage);
        if (crypto.createHash('sha256').update(await image.body()).digest('hex')!==doc.imageHash) throw Error('Image bytes differ');
        if(doc.external && await page.getByRole('link',{name:'External',exact:true}).getAttribute('href')!==doc.external) throw Error('External URL changed');
        if(doc.similar && await page.getByRole('link',{name:'Similar',exact:true}).getAttribute('href')!==doc.similar) throw Error('Similar path changed');
        results.push({site:site.name,test:doc.name,ok:true});
      } catch(e) { results.push({site:site.name,test:doc.name,ok:false,error:e.message}); }
    }
    results.push({site:site.name,test:'no-old-site-access',ok:blocked.length===0,blocked});
    results.push({site:site.name,test:'no-script-errors',ok:errors.length===0,errors});
    await page.close();
  }
  await browser.close();
  console.log(JSON.stringify(results,null,2));
  process.exitCode=results.every(x=>x.ok)?0:1;
})().catch(e=>{console.error(e);process.exitCode=1});
