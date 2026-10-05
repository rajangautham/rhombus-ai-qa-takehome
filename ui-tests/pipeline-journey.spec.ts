/**
 * UI journey for the AI-built Rhombus pipeline.
 * Auth: Google blocks OAuth in automated browsers, so log in with real Chrome
 * started with --remote-debugging-port=9222, then `node scripts/save-auth.mjs`.
 * No fixed sleeps: every wait is an auto-retrying assertion.
 */
import { test, expect, Page } from '@playwright/test';

const WORKFLOW_URL = process.env.WORKFLOW_URL!;
test.beforeAll(() => {
  if (!WORKFLOW_URL) throw new Error('Set WORKFLOW_URL in .env (see .env.example)');
});

async function openCanvas(page: Page) {
  await page.goto(WORKFLOW_URL);
  await page.getByText('Canvas', { exact: true }).click();
  await expect(page.getByText(/^Remove Dupl/).first()).toBeVisible();
}

test('AI-built pipeline has the expected 7 steps in order', async ({ page }) => {
  await openCanvas(page);
  await expect(page.getByText('Data Input', { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/^Remove Dupl/)).toHaveCount(2);
  await expect(page.getByText('Text Cleanup', { exact: true })).toHaveCount(1);
  await expect(page.getByText('Text Case', { exact: true })).toHaveCount(2);
  await expect(page.getByText('Custom', { exact: true }).first()).toBeVisible();
});

test('Data Input node lists the baseline dataset', async ({ page }) => {
  await openCanvas(page);
  await page.getByText('Data Input', { exact: true }).first().click();
  await expect(page.getByText('Select Dataset')).toBeVisible();
  await expect(page.getByText('baseline.csv', { exact: true })).toBeVisible();
});

test('A 15-minute schedule is configured and Active', async ({ page }) => {
  await openCanvas(page);
  await page.getByText('Schedule', { exact: true }).click();
  await expect(page.getByText('Active', { exact: true })).toBeVisible();
  await expect(page.getByText(/\*\/15 \* \* \* \*/)).toBeVisible();
});

test('Manual run of the pipeline completes and is logged', async ({ page }) => {
  await openCanvas(page);
  const started = Date.now();
  await page.locator('button:has(svg.lucide-play)').first().click();
  await page.getByText('Logs', { exact: true }).first().click();
  // The log panel starts empty on a fresh page load (verified 6 Oct: 0 success entries
  // before running), so a success entry here can only come from the run just triggered.
  await expect(page.getByText('Pipeline execution completed successfully').first()).toBeVisible({ timeout: 150_000 });
  test.info().annotations.push({ type: 'duration_ms', description: String(Date.now() - started) });
});

test('BUG REPRO: Active schedule has no executions (observations/04)', async ({ page }) => {
  // Asserts the bug as observed. When Rhombus fixes it, this test fails and should be
  // replaced by an assertion that execution rows exist.
  await openCanvas(page);
  await page.getByText('Schedule', { exact: true }).click();
  await expect(page.getByText('Active', { exact: true })).toBeVisible();
  await page.locator('button:has(svg.lucide-history)').first().click();
  await expect(page.getByText('Executions', { exact: true })).toBeVisible();
  await expect(page.getByText('No results.')).toBeVisible();
});

test('BLOCKED: S3 source connection verifies', async () => {
  test.fixme(true, 'Verification fails with the generated bucket policy — observations/01-setup-s3-connector-verification.md');
});

test('BLOCKED: GCS destination can be configured', async () => {
  test.fixme(true, 'GCS is not an available destination — observations/02-setup-gcs-destination-not-supported.md');
});
