import { test, expect } from '@playwright/test';
import { openSettings } from './fixtures/settings-host.js';

test('Models settles without a repeated host resize feedback loop', async ({ page }) => {
  const { viewer } = await openSettings(page);
  await expect(viewer.locator('#workspace')).toContainText('workshop');
  await viewer.getByRole('button', { name: 'Models', exact: true }).click();
  await page.waitForTimeout(250);
  const start = await page.evaluate(() => window.hostMessages.filter(m => m.method === 'ui/notifications/size-changed').length);
  await page.waitForTimeout(500);
  const heights = await page.evaluate(index => window.hostMessages.filter(m => m.method === 'ui/notifications/size-changed').slice(index).map(m => m.params.height), start);
  expect(heights, 'The host height should settle, rather than resize on every frame').toHaveLength(0);
});

test('changing steps measures content without mutating the document root height', async ({ page }) => {
  const { viewer } = await openSettings(page);
  await expect(viewer.locator('#workspace')).toContainText('workshop');
  await viewer.locator('html').evaluate(root => {
    window.rootHeightMutations = 0;
    const observer = new MutationObserver(records => { window.rootHeightMutations += records.length; });
    observer.observe(root, { attributes: true, attributeFilter: ['style'] });
  });
  await viewer.getByRole('button', { name: 'Models', exact: true }).click();
  await page.waitForTimeout(300);
  expect(await viewer.locator('html').evaluate(() => window.rootHeightMutations)).toBe(0);
});

test('size reports leave host width alone when selecting Models', async ({ page }) => {
  const { viewer } = await openSettings(page);
  await expect(viewer.locator('#workspace')).toContainText('workshop');
  await viewer.getByRole('button', { name: 'Models', exact: true }).click();
  await page.waitForTimeout(200);
  const reports = await page.evaluate(() => window.hostMessages.filter(m => m.method === 'ui/notifications/size-changed').map(m => m.params));
  expect(reports.length).toBeGreaterThan(0);
  expect(reports.every(report => !Object.hasOwn(report, 'width'))).toBe(true);
});

for (const width of [320, 700]) test(`resizing settles under a constrained host at ${width}px`, async ({ page }) => {
  const { viewer } = await openSettings(page, { maxHeight: 360 });
  await expect(viewer.locator('#workspace')).toContainText('workshop');
  await page.evaluate(width => { document.querySelector('iframe').style.width = `${width}px`; }, width);
  for (const name of ['Models', 'Setup', 'Models']) {
    await viewer.getByRole('button', { name, exact: true }).click();
    await page.waitForTimeout(200);
    const start = await page.evaluate(() => window.hostMessages.filter(m => m.method === 'ui/notifications/size-changed').length);
    await page.waitForTimeout(400);
    expect(await page.evaluate(index => window.hostMessages.filter(m => m.method === 'ui/notifications/size-changed').slice(index).length, start)).toBe(0);
  }
  expect(await viewer.locator('body').evaluate(body => body.scrollWidth <= body.clientWidth)).toBe(true);
});
