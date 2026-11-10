/**
 * E2E: site statique APEX (out/).
 * Vérifie que les routes principales rendent bien et que les liens
 * internes sont valides.
 */
import { test, expect } from '@playwright/test';

const ROUTES = ['/', '/agents', '/models', '/tools', '/roadmap', '/docs', '/install', '/security', '/activity', '/contribute'];

for (const route of ROUTES) {
  test(`route ${route} répond 200 et contient du contenu`, async ({ request }) => {
    const res = await request.get(route);
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body.length).toBeGreaterThan(500);
  });
}

test("la page d'accueil contient APEX et liens principaux", async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/APEX/);
  await expect(page.getByRole('link', { name: /Docs/i }).first()).toBeVisible();
  await expect(page.getByRole('link', { name: /Install/i }).first()).toBeVisible();
});

test('la page /docs charge et expose des sections', async ({ page }) => {
  await page.goto('/docs');
  await expect(page.locator('body')).toContainText(/APEX|apex|docs/i);
});

test('la page /roadmap montre les versions', async ({ page }) => {
  await page.goto('/roadmap');
  await expect(page.locator('body')).toContainText(/v1\.0\.0|v2\.0\.0/i);
});
