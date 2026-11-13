import { test, expect } from '@playwright/test';

test.describe('Purchasing Journey', () => {
  test('Complete simulated purchasing journey', async ({ page }) => {
    // 1. Visit the catalog page
    await page.goto('/');
    await expect(page.locator('h1#catalog-heading')).toContainText('Product Catalog');

    // 2. Add "Premium Ergonomic Keyboard" to cart
    const addBtn = page.locator('.product-card').filter({ hasText: 'Premium Ergonomic Keyboard' }).locator('button:has-text("Add to Cart")');
    await addBtn.click();

    // Verify cart badge updates to 1
    const cartBadge = page.locator('.cart-badge');
    await expect(cartBadge).toContainText('1');

    // 3. Navigate to Cart
    const cartNavBtn = page.locator('.nav-controls button').filter({ hasText: /^Cart/ });
    await cartNavBtn.click();
    await expect(page.locator('h1')).toContainText('Your Shopping Cart');

    // 4. Click Proceed to Checkout
    const checkoutNavBtn = page.locator('button:has-text("Proceed to Checkout")');
    await checkoutNavBtn.click();

    // 5. Guided to Sign In / Register
    await expect(page.locator('.auth-form-title')).toContainText('Sign In');
    
    // Switch to Register tab
    const registerTabBtn = page.locator('button:has-text("Register")');
    await registerTabBtn.click();
    await expect(page.locator('.auth-form-title')).toContainText('Create an Account');

    // Register a dynamic user
    const username = `customer_e2e_${Date.now()}`;
    await page.fill('input#username-input', username);
    await page.fill('input#password-input', 'password123');
    await page.click('button.auth-submit-btn');

    // 6. Automatically signed in and redirected to Checkout Summary page
    await expect(page.locator('.session-status')).toContainText(`Signed in as: ${username}`);
    await expect(page.locator('h1')).toContainText('Simulated Checkout');

    // Verify Purchase Contents has our product
    await expect(page.locator('.checkout-card').filter({ hasText: 'Purchase Contents' })).toContainText('Premium Ergonomic Keyboard');

    // 7. Click Confirm Simulated Purchase
    const confirmBtn = page.locator('button:has-text("Confirm Simulated Purchase")');
    await confirmBtn.click();

    // 8. Fictitious confirmation summary displayed
    await expect(page.locator('.confirmation-title')).toContainText('Simulated Purchase Confirmed!');
    await expect(page.locator('.confirmation-msg')).toContainText('demonstration. No real charge has been made.');

    // Assert that the page contents and summary do not contain any "Order ID"
    const pageText = await page.innerText('body');
    expect(pageText.toLowerCase()).not.toContain('order id');
    expect(pageText.toLowerCase()).not.toContain('order_id');

    // 9. Click Start New Purchase -> resets and goes back to Catalog
    const startNewBtn = page.locator('button:has-text("Start New Purchase")');
    await startNewBtn.click();
    await expect(page.locator('h1#catalog-heading')).toContainText('Product Catalog');

    // Cart is empty
    await expect(page.locator('.cart-badge')).not.toBeVisible();
  });
});
