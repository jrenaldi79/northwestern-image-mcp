import { test, expect } from '@playwright/test';
import { openSettings, calls } from './fixtures/settings-host.js';

test('image editing teaches preservation with an accessible free comparison', async ({ page }) => {
  const { viewer } = await openSettings(page);
  await viewer.getByRole('button', { name: 'Images', exact: true }).click();
  await viewer.getByRole('tab', { name: 'Edit', exact: true }).click();
  const panel = viewer.locator('[data-panel="3"]');
  await expect(panel).toContainText('Change one part. Keep the rest.');
  await expect(panel).not.toContainText(/mask|feather|white changes|black keeps|rerender/i);
  await expect(viewer.locator('#image-edit-panel img')).toHaveCount(2);
  const slider = viewer.getByRole('slider', { name: 'Compare original and edited image' });
  await slider.focus();
  await slider.press('End');
  await expect(panel.locator('.edit-comparison')).toHaveCSS('--reveal', '100%');
  await slider.press('ArrowLeft');
  await expect(slider).toHaveValue('99');
  for (const name of ['generate_image', 'edit_image', 'remask_image', 'run_sidecar_demo']) expect(await calls(page, name)).toEqual([]);
});

test('onboarding keeps essential guidance short with sharing detail on demand', async ({ page }) => {
  const { viewer } = await openSettings(page);
  for (const name of ['Setup', 'How it works', 'Images', 'Finish']) {
    await viewer.getByRole('button', { name, exact: true }).click();
    const words = await viewer.locator('[data-panel]:visible').evaluate(panel => panel.innerText.trim().split(/\s+/).length);
    expect(words).toBeLessThan(95);
  }
  await viewer.getByRole('button', { name: 'How it works', exact: true }).click();
  await expect(viewer.locator('#sharing-details')).not.toHaveAttribute('open', '');
  await viewer.locator('#sharing-details summary').click();
  await expect(viewer.locator('#sharing-details')).toContainText('not automatically');
});
