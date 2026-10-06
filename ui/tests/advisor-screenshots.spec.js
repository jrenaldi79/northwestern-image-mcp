import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { openAdvisor, result } from './fixtures/advisor-host.js';

test('capture real demo reply with provider logo, rich text and reviewed return controls', async ({ page }) => {
  const data = JSON.parse(await readFile(new URL('../../.venv/codex-install/real-advisor-demo.json', import.meta.url), 'utf8').catch(error => {
    if (error.code !== 'ENOENT') throw error;
    return JSON.stringify({ model: 'google/gemini-example', title: 'Classroom activity', answer: '# Compare two advisors\n\n1. **Frame** a product idea.\n2. Ask two models for advice.\n3. Discuss the differences.' });
  }));
  const { viewer } = await openAdvisor(page, { responses: { 'get_advisor_result:result-1': [result(data)] } });
  await expect(viewer.locator('#answer')).not.toBeEmpty();
  await expect(viewer.locator('#model-logo img')).toBeVisible();
  for (const width of [360, 900]) {
    await page.evaluate(width => document.querySelector('iframe').style.width = `${width}px`, width);
    await page.waitForTimeout(150);
    await page.setViewportSize({ width: 1000, height: Math.ceil(await viewer.locator('body').evaluate(body => body.getBoundingClientRect().height)) + 32 });
    await page.locator('iframe').screenshot({ path: `../.venv/codex-install/advisor-chat-${width}.png` });
  }
  await viewer.getByRole('button', { name: 'Review full answer', exact: true }).click();
  await expect(viewer.locator('#preview-section')).toBeVisible();
  await page.waitForTimeout(150);
  await page.setViewportSize({ width: 1000, height: Math.ceil(await viewer.locator('body').evaluate(body => body.getBoundingClientRect().height)) + 32 });
  await page.locator('iframe').screenshot({ path: '../.venv/codex-install/advisor-chat-return-900.png' });
});
