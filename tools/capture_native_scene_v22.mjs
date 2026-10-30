import fs from 'node:fs';
import { chromium } from 'playwright';
const out = 'output/V22-native-scene-preview';
const environment = process.argv[2] || 'CastleExterior';
const prefix = environment === 'CastleExterior' ? '' : `${environment}-`;
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
try {
  for (const source of ['scene', 'prefab']) for (const view of ['overview', 'combat', ...(environment === 'NewScene' ? ['castle'] : [])]) for (const diagnostic of ['', '-debug', '-no-grid']) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1600 } });
    const errors = []; page.on('pageerror', e => errors.push(String(e)));
    page.on('console', e => { if (e.type() === 'error' && !e.text().includes('404 (Not Found)')) errors.push(e.text()); });
    const option = diagnostic === '-debug' ? '&debugMissing=1' : diagnostic === '-no-grid' ? '&grid=0' : '';
    await page.goto(`http://127.0.0.1:5265/scene-native-v22.html?capture=1&environment=${environment}&source=${source}&view=${view}${option}`);
    await page.waitForFunction(() => window.ready || window.previewError, null, { timeout: 120000 });
    const audit = await page.evaluate(() => window.nativePreview?.audit || { error: window.previewError });
    if (errors.length || audit.error) throw Error(JSON.stringify({ errors, audit }));
    await page.locator('#view').screenshot({ path: `${out}/${prefix}${source}-${view}${diagnostic}.png` });
    fs.writeFileSync(`${out}/${prefix}${source}-${view}${diagnostic}.json`, JSON.stringify(audit, null, 2));
    console.log(`${source}-${view}${diagnostic}: ${audit.nativeObjects} native objects; ${audit.warnings.length} material warnings`);
    await page.close();
  }
} finally { await browser.close(); }
