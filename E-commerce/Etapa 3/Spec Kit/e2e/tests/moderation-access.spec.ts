import { test, expect } from '@playwright/test';

test.describe('Moderation Access Control Safeguards', () => {
  test('should deny moderation access to a standard customer', async ({ page }) => {
    // 1. Visit homepage
    await page.goto('/');

    // 2. Guest Visitor: verify "Moderation Dashboard" nav button is NOT visible
    await expect(page.locator('.moderator-dashboard-nav-btn')).not.toBeVisible();

    // 3. Log in as a regular customer
    // Add product to cart and click proceed to trigger login
    const productCard = page.locator('[data-testid="product-card"]').first();
    await productCard.locator('.add-to-cart-btn').click();
    await page.locator('.checkout-proceed-btn').click();

    // Register standard customer
    await page.getByRole('button', { name: 'Register', exact: true }).click();
    const uniqueUser = `standard_cust_${Date.now()}`;
    await page.locator('#register-identifier').fill(uniqueUser);
    await page.locator('#register-password').fill('testpassword');
    await page.getByRole('button', { name: 'Register Account' }).click();

    // Sign in as standard customer
    await page.locator('#signin-identifier').fill(uniqueUser);
    await page.locator('#signin-password').fill('testpassword');
    await page.locator('[data-testid="signin-form"]').locator('.auth-submit-btn').click();

    // Automatically redirected to Checkout page
    // 4. Verify that standard customer does NOT see "Moderation Dashboard" nav button
    await expect(page.locator('.moderator-dashboard-nav-btn')).not.toBeVisible();

    // 5. Navigate back to Catalog and verify button is still not visible
    await page.getByRole('heading', { name: '🛒 Demonstration Store' }).click();
    await expect(page.locator('.moderator-dashboard-nav-btn')).not.toBeVisible();
  });
});
