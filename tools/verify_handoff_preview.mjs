// Verify that the committed preview loads without external local asset folders.
import {createServer} from 'vite';
import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const option = (key, fallback) => {
  const index = process.argv.indexOf(key);
  return index < 0 ? fallback : process.argv[index + 1];
};
const out = path.resolve(option('--out', path.join(root, 'output/handoff-verification')));
const variant = option('--variant', 'V22R-topfield-T1');
const installedChrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const browserPath = option('--browser', process.env.PVE_BROWSER_PATH ||
  (fs.existsSync(installedChrome) ? installedChrome : undefined));
const report = {variant, root, nodeVersion: process.version, pageErrors: [],
  failedResponses: [], networkFailures: [], states: []};
let server, browser;
fs.mkdirSync(out, {recursive: true});
try {
  server = await createServer({root, configFile: false, logLevel: 'silent',
    server: {host: '127.0.0.1', port: 0,
      watch: {ignored: ['**/output/**', '**/variants/**', '**/assets/**']}}});
  await server.listen();
  browser = await chromium.launch({headless: true,
    ...(browserPath ? {executablePath: browserPath} : {}),
    args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
  const page = await browser.newPage({viewport: {width: 720, height: 1080}});
  page.on('pageerror', error => report.pageErrors.push(error.message));
  page.on('response', response => {
    if (response.status() >= 400) report.failedResponses.push({
      url: new URL(response.url()).pathname, status: response.status()});
  });
  page.on('requestfailed', request => report.networkFailures.push({
    url: request.url(), error: request.failure()?.errorText}));
  await page.route('**/favicon.ico', route => route.fulfill({status: 204, body: ''}));
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/v22.html?` +
    `capture=1&variant=${encodeURIComponent(variant)}&presentation=approved-castle`);
  await page.waitForFunction(() => window.ready === true, null, {timeout: 180000});
  await page.evaluate(() => window.sceneRuntime.renderer.setSize(720, 1080));
  report.nativeScene = await page.evaluate(() => ({
    objects: window.environmentAudit.audit.objects.length,
    units: window.sceneRuntime.simulation.units.length,
    duration: window.sceneRuntime.config.duration,
    models: Object.keys(window.assetAudit), camera: window.cameraState}));
  for (const time of [0, 1, 2.65, 4, report.nativeScene.duration - 1 / 60]) {
    if (time >= report.nativeScene.duration) continue;
    report.states.push(await page.evaluate(time => {
      window.renderAt(time);
      window.sceneRuntime.renderer.getContext().finish();
      return window.lastState;
    }, time));
    if (time === 0) await page.locator('#view').screenshot({path: path.join(out, 'opening.png')});
  }
  report.success = !report.pageErrors.length && !report.failedResponses.length &&
    !report.networkFailures.length;
  console.log(JSON.stringify({success: report.success, units: report.nativeScene.units,
    nativeObjects: report.nativeScene.objects, sampledTimes: report.states.map(s => s.time), out}));
  if (!report.success) process.exitCode = 1;
} catch (error) {
  report.success = false;
  report.error = String(error);
  process.exitCode = 1;
  console.error(report.error);
} finally {
  fs.writeFileSync(path.join(out, 'audit.json'), JSON.stringify(report, null, 2) + '\n');
  if (browser) await browser.close();
  if (server) await server.close();
}
