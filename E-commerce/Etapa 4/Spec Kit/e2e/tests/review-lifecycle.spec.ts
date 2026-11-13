import { test, expect } from '@playwright/test';

test.describe('E-Commerce Reviews and Moderation Lifecycle', () => {
  test('should submit a review, verify it is pending, approve as moderator, and check public visibility', async ({ page }) => {
    // 1. Visit homepage
    await page.goto('/');

    // 2. Add product to cart and proceed to trigger login
    const productCard = page.locator('[data-testid="product-card"]').first();
    const productName = await productCard.locator('.product-name').textContent();
    await productCard.locator('.add-to-cart-btn').click();
    await page.locator('.checkout-proceed-btn').click();

    // 3. Register a new user
    await page.getByRole('button', { name: 'Register', exact: true }).click();
    const uniqueUser = `reviewer_${Date.now()}`;
    await page.locator('#register-identifier').fill(uniqueUser);
    await page.locator('#register-password').fill('testpassword');
    await page.getByRole('button', { name: 'Register Account' }).click();

    // 4. Sign in with the registered user
    await page.locator('#signin-identifier').fill(uniqueUser);
    await page.locator('#signin-password').fill('testpassword');
    await page.locator('[data-testid="signin-form"]').locator('.auth-submit-btn').click();

    // Automatically redirected to Checkout page since there's an item in the cart.
    // Wait for Checkout view to stabilize
    await expect(page.locator('[data-testid="checkout-form"]')).toBeVisible();

    // 5. Navigate back to Catalog to write a review
    await page.locator('.header-title').click();

    // 6. View reviews for the product
    await productCard.locator('.view-details-btn').click();
    await expect(page.locator('[data-testid="product-details-page"]')).toBeVisible();

    // 7. Fill out and submit review
    const uniqueComment = `This is a spectacular review comment written by ${uniqueUser}! Code: ${Date.now()}`;
    await page.locator('#review-rating').selectOption('5');
    await page.locator('#review-comment').fill(uniqueComment);
    await page.getByRole('button', { name: 'Submit Review', exact: true }).click();

    // Verify submission success toast/message is shown
    await expect(page.locator('.toast-success', { hasText: 'Your review has been submitted and is pending moderation.' })).toBeVisible();

    // Verify the review is NOT visible in the public reviews list (still pending)
    await expect(page.locator(`text=${uniqueComment}`)).not.toBeVisible();

    // 8. Sign out of reviewer session
    await page.locator('.sign-out-btn').click();
    await expect(page.locator('text=Guest Visitor')).toBeVisible();

    // 9. Sign in as Moderator
    // Since there's still an item in the cart, click Proceed to Checkout to trigger login
    await page.locator('.checkout-proceed-btn').click();
    await page.locator('#signin-identifier').fill('moderator');
    await page.locator('#signin-password').fill('moderator');
    await page.locator('[data-testid="signin-form"]').locator('.auth-submit-btn').click();

    // 10. Navigate to Moderation Dashboard (visible only for moderator)
    await expect(page.locator('.moderator-dashboard-nav-btn')).toBeVisible();
    await page.locator('.moderator-dashboard-nav-btn').click();
    await expect(page.locator('[data-testid="moderator-dashboard"]')).toBeVisible();

    // Locate our pending review and approve it
    const moderationCard = page.locator('[data-testid="moderation-card"]').filter({ hasText: uniqueComment });
    await expect(moderationCard).toBeVisible();
    await moderationCard.locator('.approve-btn').click();

    // 11. Sign out moderator session
    await page.locator('.sign-out-btn').click();
    await expect(page.locator('text=Guest Visitor')).toBeVisible();

    // 12. View product details as a Guest Visitor to verify immediate visibility (cache invalidated and bypassed)
    await page.locator('.header-title').click();
    await productCard.locator('.view-details-btn').click();
    await expect(page.locator('[data-testid="product-details-page"]')).toBeVisible();

    // Verify the review is now visible to the public
    await expect(page.locator(`text=${uniqueComment}`)).toBeVisible();
  });
});
