import { test, expect } from '@playwright/test';

test.describe('E-Commerce Purchasing Journey', () => {
  test('should complete the full purchasing journey for a visitor', async ({ page }) => {
    // 1. Visit homepage
    await page.goto('/');

    // Verify catalog title
    await expect(page.getByRole('heading', { name: 'Product Catalog' })).toBeVisible();

    // 2. Add first product to cart
    const productCard = page.locator('[data-testid="product-card"]').first();
    await productCard.locator('.add-to-cart-btn').click();

    // Verify product is in cart and proceed button is active
    await expect(page.locator('[data-testid="cart"]')).toBeVisible();
    await expect(page.locator('[data-testid="cart-item"]')).toBeVisible();

    // 3. Click proceed to checkout (triggers authentication request)
    await page.locator('.checkout-proceed-btn').click();

    // Verify auth form overlay is displayed
    await expect(page.locator('[data-testid="signin-form"]')).toBeVisible();

    // 4. Switch to register tab
    await page.getByRole('button', { name: 'Register', exact: true }).click();
    await expect(page.locator('[data-testid="register-form"]')).toBeVisible();

    // 5. Fill registration details (unique identifier to avoid conflicts)
    const uniqueUser = `customer_${Date.now()}`;
    await page.locator('#register-identifier').fill(uniqueUser);
    await page.locator('#register-password').fill('testpassword');
    await page.getByRole('button', { name: 'Register Account' }).click();

    // Success triggers switch back to sign-in form
    await expect(page.locator('[data-testid="signin-form"]')).toBeVisible();

    // 6. Sign in with newly created customer account
    await page.locator('#signin-identifier').fill(uniqueUser);
    await page.locator('#signin-password').fill('testpassword');
    await page.locator('[data-testid="signin-form"]').locator('.auth-submit-btn').click();

    // Success transitions automatically to Checkout view
    await expect(page.locator('[data-testid="checkout-form"]')).toBeVisible();

    // 7. Complete Checkout Form
    await page.locator('#checkout-field-a').fill('John Doe');
    await page.locator('#checkout-field-b').fill('john.doe@example.com');
    await page.locator('.checkout-submit-btn').click();

    // 8. Verify confirmation screen with disclaimers
    await expect(page.locator('[data-testid="confirmation-panel"]')).toBeVisible();
    await expect(page.locator('h2:has-text("Simulated Purchase Confirmed!")')).toBeVisible();
    await expect(page.locator('text=Fictitious Gateway Disclaimer')).toBeVisible();
  });
});
