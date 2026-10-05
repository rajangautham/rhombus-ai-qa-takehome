// Google blocks OAuth in automated browsers, so log in with real Chrome
// (started with --remote-debugging-port=9222) and copy its session here.
import { chromium } from '@playwright/test';
const browser = await chromium.connectOverCDP('http://localhost:9222');
await browser.contexts()[0].storageState({ path: 'playwright/.auth/user.json' });
console.log('Session saved to playwright/.auth/user.json');
await browser.close();
