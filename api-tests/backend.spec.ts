/**
 * Backend API tests. The endpoint and credentials come from a request captured
 * in DevTools (Network > Copy as cURL) and are read from .env — never committed.
 */
import { test, expect, APIRequestContext, request } from '@playwright/test';

const URL = process.env.API_URL!;
const TOKEN = process.env.API_TOKEN || '';
const COOKIE = process.env.API_COOKIE || '';
const EXPECT = process.env.API_EXPECT_IN_BODY || '';

test.beforeAll(() => {
  if (!URL || (!TOKEN && !COOKIE)) throw new Error('Set API_URL and API_TOKEN or API_COOKIE in .env (see .env.example)');
});

const authHeaders = (): Record<string, string> => ({
  accept: 'application/json',
  ...(TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}),
  ...(COOKIE ? { cookie: COOKIE } : {}),
});

async function bare(): Promise<APIRequestContext> {
  return request.newContext(); // no stored cookies, no headers
}

test('authenticated request returns 200 and the workflow data', async () => {
  const ctx = await bare();
  const res = await ctx.get(URL, { headers: authHeaders() });
  expect(res.status()).toBe(200);
  expect(res.headers()['content-type']).toContain('application/json');
  const body = await res.text();
  expect(() => JSON.parse(body)).not.toThrow();
  if (EXPECT) expect(body).toContain(EXPECT);
});

test('NEGATIVE: unauthenticated request is rejected and leaks no data', async () => {
  const ctx = await bare();
  const res = await ctx.get(URL, { headers: { accept: 'application/json' } });
  expect([401, 403]).toContain(res.status());
  if (EXPECT) expect(await res.text()).not.toContain(EXPECT);
});

test('NEGATIVE: invalid token is rejected', async () => {
  const ctx = await bare();
  const res = await ctx.get(URL, { headers: { accept: 'application/json', authorization: 'Bearer invalid.token.value' } });
  expect([401, 403]).toContain(res.status());
});

test('NEGATIVE: non-existent resource id returns 403/404, not 200 or 5xx', async () => {
  const fake = URL.replace(/\/(\d+)(?=[/?]|$)/, '/999999999');
  test.skip(fake === URL, 'API_URL has no numeric id to replace');
  const ctx = await bare();
  const res = await ctx.get(fake, { headers: authHeaders() });
  expect([403, 404]).toContain(res.status());
});
