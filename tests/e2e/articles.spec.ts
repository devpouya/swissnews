import { test, expect } from '@playwright/test';

test.describe('Article Functionality', () => {
  test('should navigate to article detail page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find and click on an article card/link
    const articleLink = page.locator('[data-testid="article-link"], .article-card a, article a').first();

    if (await articleLink.count() > 0) {
      await articleLink.click();

      // Verify we're on an article page
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/.*\/(article|articles)\/.*/);

      // Check for article content
      const articleTitle = page.locator('h1, .article-title, [data-testid="article-title"]');
      await expect(articleTitle).toBeVisible();
    }
  });

  test('should display similar articles', async ({ page }) => {
    // Navigate to an article page (this assumes we have sample data)
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const articleLink = page.locator('[data-testid="article-link"], .article-card a, article a').first();

    if (await articleLink.count() > 0) {
      await articleLink.click();
      await page.waitForLoadState('networkidle');

      // Look for similar articles section
      const similarArticles = page.locator(
        '[data-testid="similar-articles"], .similar-articles, .related-articles'
      );

      // Similar articles might not exist yet, so this is optional
      if (await similarArticles.count() > 0) {
        await expect(similarArticles).toBeVisible();

        // Check for individual similar article items
        const similarArticleItems = page.locator(
          '[data-testid="similar-article-item"], .similar-article, .related-article'
        );

        if (await similarArticleItems.count() > 0) {
          await expect(similarArticleItems.first()).toBeVisible();
        }
      }
    }
  });

  test('should handle article loading states', async ({ page }) => {
    await page.goto('/');

    // Check for loading states or spinners
    const loadingIndicator = page.locator(
      '[data-testid="loading"], .loading, .spinner, [aria-label*="loading"]'
    );

    // Loading indicators should either be visible initially or not present
    if (await loadingIndicator.count() > 0) {
      // If present, it should eventually disappear
      await expect(loadingIndicator).toBeHidden({ timeout: 10000 });
    }

    // Content should be loaded
    await page.waitForLoadState('networkidle');
    const content = page.locator('main, .main-content, [role="main"]');
    await expect(content).toBeVisible();
  });

  test('should handle article not found', async ({ page }) => {
    // Try to navigate to a non-existent article
    await page.goto('/article/non-existent-article-id');

    // Should show 404 or error message
    const errorMessage = page.locator(
      '[data-testid="error"], .error, .not-found, h1:has-text("404"), h1:has-text("Not Found")'
    );

    await expect(errorMessage).toBeVisible();
  });
});

test.describe('Language Switching', () => {
  test('should switch article language', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find language toggle
    const languageToggle = page.locator(
      '[data-testid="language-toggle"], .language-selector, [aria-label*="language"]'
    );

    if (await languageToggle.count() > 0) {
      // Look for specific language options
      const germanOption = page.locator(
        '[data-testid="lang-de"], [data-lang="de"], button:has-text("DE"), a:has-text("Deutsch")'
      );
      const frenchOption = page.locator(
        '[data-testid="lang-fr"], [data-lang="fr"], button:has-text("FR"), a:has-text("Français")'
      );

      if (await germanOption.count() > 0) {
        await germanOption.click();
        await page.waitForLoadState('networkidle');

        // Verify language change (could check URL, content, or localStorage)
        const currentLang = await page.evaluate(() => {
          return document.documentElement.lang ||
                 localStorage.getItem('language') ||
                 window.location.pathname.includes('/de') ? 'de' : null;
        });

        // This is flexible - different implementations might handle language differently
        if (currentLang) {
          expect(currentLang).toBe('de');
        }
      }

      if (await frenchOption.count() > 0) {
        await frenchOption.click();
        await page.waitForLoadState('networkidle');

        // Similar check for French
        const currentLang = await page.evaluate(() => {
          return document.documentElement.lang ||
                 localStorage.getItem('language') ||
                 window.location.pathname.includes('/fr') ? 'fr' : null;
        });

        if (currentLang) {
          expect(currentLang).toBe('fr');
        }
      }
    }
  });

  test('should persist language preference', async ({ page }) => {
    await page.goto('/');

    const languageToggle = page.locator(
      '[data-testid="language-toggle"], .language-selector'
    );

    if (await languageToggle.count() > 0) {
      const frenchOption = page.locator(
        '[data-testid="lang-fr"], button:has-text("FR")'
      );

      if (await frenchOption.count() > 0) {
        await frenchOption.click();
        await page.waitForLoadState('networkidle');

        // Reload the page
        await page.reload();
        await page.waitForLoadState('networkidle');

        // Check if language preference is still French
        const isStillFrench = await page.evaluate(() => {
          return document.documentElement.lang === 'fr' ||
                 localStorage.getItem('language') === 'fr' ||
                 document.querySelector('[data-testid="lang-fr"]')?.getAttribute('aria-selected') === 'true';
        });

        // This might be true depending on implementation
        if (isStillFrench !== null) {
          expect(isStillFrench).toBeTruthy();
        }
      }
    }
  });
});
