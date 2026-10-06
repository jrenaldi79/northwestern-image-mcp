import { test, expect } from '@playwright/test';
import { openSettings } from './fixtures/settings-host.js';

test('capture onboarding for review without restarting the MCP server', async ({ page }) => {
  const { viewer } = await openSettings(page);
  await expect(viewer.locator('#workspace')).toContainText('workshop');
  for (const width of [360, 900]) {
    await page.evaluate(width => document.querySelector('iframe').style.width = `${width}px`, width);
    for (const [name, label] of [['setup', 'Setup'], ['models', 'Models'], ['advisor', 'How it works'], ['images', 'Images'], ['finish', 'Finish']]) {
      await viewer.getByRole('button', { name: label, exact: true }).click();
      await viewer.locator('main').evaluate(main => { main.closest('html').scrollTop = 0; });
      // Fullscreen host context lets the capture show the full page, including below-fold content.
      await page.evaluate(() => window.notify('ui/notifications/host-context-changed', { displayMode: 'fullscreen' }));
      await expect.poll(() => page.locator('iframe').evaluate(frame => parseFloat(frame.style.height))).toBeGreaterThan(100);
      await page.waitForTimeout(150);
      await viewer.locator('body').evaluate(body => { body.scrollTop = 0; document.documentElement.scrollTop = 0; });
      await page.evaluate(height => document.querySelector('iframe').style.height = `${Math.ceil(height) + 1}px`, await viewer.locator('main').evaluate(main => main.getBoundingClientRect().height));
      await page.setViewportSize({ width: 1000, height: Math.ceil(await viewer.locator('main').evaluate(main => main.getBoundingClientRect().height)) + 32 });
      await page.locator('iframe').screenshot({ path: `../.venv/codex-install/onboarding-${name}-${width}.png` });
      if (name === 'images') {
        await page.locator('iframe').screenshot({ path: `../.venv/codex-install/onboarding-create-${width}.png` });
        await viewer.getByRole('tab', { name: 'Edit', exact: true }).click();
        await page.waitForTimeout(150);
        await page.evaluate(height => document.querySelector('iframe').style.height = `${Math.ceil(height) + 1}px`, await viewer.locator('main').evaluate(main => main.getBoundingClientRect().height));
        await page.setViewportSize({ width: 1000, height: Math.ceil(await viewer.locator('main').evaluate(main => main.getBoundingClientRect().height)) + 32 });
        await page.locator('iframe').screenshot({ path: `../.venv/codex-install/onboarding-edit-${width}.png` });
        await viewer.locator('#image-compare').focus();
        await viewer.locator('#image-compare').press('End');
        await page.waitForTimeout(150);
        await viewer.locator('body').evaluate(body => { body.scrollTop = 0; document.documentElement.scrollTop = 0; });
        await page.evaluate(height => document.querySelector('iframe').style.height = `${Math.ceil(height) + 1}px`, await viewer.locator('main').evaluate(main => main.getBoundingClientRect().height));
        await page.setViewportSize({ width: 1000, height: Math.ceil(await viewer.locator('main').evaluate(main => main.getBoundingClientRect().height)) + 32 });
        await page.locator('iframe').screenshot({ path: `../.venv/codex-install/onboarding-edited-${width}.png` });
        await viewer.locator('#image-compare').press('Home');
        await page.locator('iframe').screenshot({ path: `../.venv/codex-install/onboarding-original-${width}.png` });
        await viewer.locator('#image-compare').evaluate(slider => { slider.value = '50'; slider.dispatchEvent(new Event('input')); });
        await viewer.getByRole('tab', { name: 'Create', exact: true }).click();
      }
    }
  }
});
