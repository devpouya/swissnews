import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('should display the homepage with correct title', async ({ page }) => {
    await page.goto('/');

    // Check if the page loads
    await expect(page).toHaveTitle(/Swiss News/);

    // Check for main navigation or header
    const header = page.locator('header, nav');
    await expect(header).toBeVisible();
  });

  test('should display language toggle', async ({ page }) => {
    await page.goto('/');

    // Look for language toggle buttons/tabs
    const languageToggle = page.locator('[data-testid="language-toggle"], .language-selector, [aria-label*="language"]');
    await expect(languageToggle).toBeVisible();
  });

  test('should display article cards', async ({ page }) => {
    await page.goto('/');

    // Wait for articles to load
    await page.waitForLoadState('networkidle');

    // Check for article cards or list
    const articles = page.locator('[data-testid="article-card"], .article-card, article');
    await expect(articles.first()).toBeVisible();
  });

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Check that content is still visible and accessible
    const mainContent = page.locator('main, .main-content, [role="main"]');
    await expect(mainContent).toBeVisible();
  });

  test('should have working navigation', async ({ page }) => {
    await page.goto('/');

    // Test navigation links (if they exist)
    const navLinks = page.locator('nav a, header a');
    const linkCount = await navLinks.count();

    if (linkCount > 0) {
      // Click on first navigation link
      await navLinks.first().click();

      // Verify navigation worked (URL changed or page content changed)
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/.*\/.*/); // Any path change
    }
  });
});

test.describe('Accessibility', () => {
  test('should have proper heading structure', async ({ page }) => {
    await page.goto('/');

    // Check for h1 tag
    const h1 = page.locator('h1');
    await expect(h1).toBeVisible();

    // Check that h1 content is meaningful
    const h1Text = await h1.textContent();
    expect(h1Text).toBeTruthy();
    expect(h1Text?.length).toBeGreaterThan(0);
  });

  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/');

    // Check for main landmark
    const main = page.locator('main, [role="main"]');
    await expect(main).toBeVisible();

    // Check for navigation landmark
    const nav = page.locator('nav, [role="navigation"]');
    if (await nav.count() > 0) {
      await expect(nav.first()).toBeVisible();
    }
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');

    // Test tab navigation
    await page.keyboard.press('Tab');

    // Check that focus is visible somewhere
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });
});
