import { test, expect } from '@playwright/test';
import { openSettings, calls, settings, view, failure } from './fixtures/settings-host.js';

test('model selection autosaves once and exposes prices per million below the choice', async ({ page }) => {
  const { viewer } = await openSettings(page);
  await viewer.getByRole('button', { name: 'Models', exact: true }).click();
  await expect(viewer.locator('#general-info')).toBeVisible();
  await expect(viewer.locator('#general-info')).toContainText('$1 input');
  await expect(viewer.locator('#general-info')).toContainText('$2 output');
  await expect(viewer.locator('#general-info')).toContainText('/ 1M tokens');
  await viewer.getByLabel('General advisor default').selectOption('openai/example');
  await expect(viewer.locator('#save-status')).toContainText('Saved');
  expect(await calls(page, 'set_sidecar_preferences')).toEqual([{ settings_id: 'settings-1', expected_revision: 1, general_default: 'openai/example' }]);
  await expect(viewer.getByRole('button', { name: 'Save defaults (free)' })).toHaveCount(0);
});

test('missing general model marks Models as an action and prevents completion', async ({ page }) => {
  const { viewer } = await openSettings(page, { responses: { get_sidecar_settings: [settings({ general_default: null })] } });
  await expect(viewer.locator('[data-step="1"]')).toHaveClass(/needs-choice/);
  await expect(viewer.locator('#model-task')).toHaveText('Choose a model');
  await viewer.getByRole('button', { name: 'Finish', exact: true }).click();
  await expect(viewer.locator('#finish')).toBeDisabled();
});

test('batch variants are absent from every model choice', async ({ page }) => {
  const base = view().models[1];
  const { viewer } = await openSettings(page, { responses: { get_sidecar_settings: [settings({ models: [...view().models, { ...base, id: 'openai/test:batch', name: 'Batch model' }, { ...base, id: 'openai/special', name: 'GPT (Batch)' }] })] } });
  await viewer.getByRole('button', { name: 'Models', exact: true }).click();
  await expect(viewer.locator('#general')).not.toContainText('Batch');
  await expect(viewer.locator('#openai')).not.toContainText('Batch');
});

test('failed autosave requires deliberate retry and uses the refreshed revision', async ({ page }) => {
  const { viewer } = await openSettings(page, { responses: {
    get_sidecar_settings: [settings(), settings({ revision: 2 })],
    set_sidecar_preferences: [failure('Conflict'), { content: [], structuredContent: view({ revision: 3, general_default: 'openai/example' }) }],
  } });
  await viewer.getByRole('button', { name: 'Models', exact: true }).click();
  await viewer.getByLabel('General advisor default').selectOption('openai/example');
  await expect(viewer.locator('#retry-save')).toBeVisible();
  expect(await calls(page, 'set_sidecar_preferences')).toHaveLength(1);
  await viewer.getByRole('button', { name: 'Retry save', exact: true }).click();
  await expect(viewer.locator('#save-status')).toContainText('Saved');
  expect((await calls(page, 'set_sidecar_preferences'))[1].expected_revision).toBe(2);
});
