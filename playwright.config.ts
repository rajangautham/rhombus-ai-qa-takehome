import { defineConfig, devices } from '@playwright/test';
import 'dotenv/config';

export default defineConfig({
  timeout: 180_000,
  expect: { timeout: 30_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    {
      name: 'ui',
      testDir: './ui-tests',
      use: { ...devices['Desktop Chrome'], viewport: { width: 2200, height: 1200 }, storageState: 'playwright/.auth/user.json' },
    },
    { name: 'api', testDir: './api-tests' },
  ],
});
