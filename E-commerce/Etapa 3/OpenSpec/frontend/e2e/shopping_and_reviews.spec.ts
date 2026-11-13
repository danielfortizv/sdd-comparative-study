import { test, expect } from '@playwright/test';

test.describe('E-Commerce Stage 3 End-to-End Test Suite', () => {
  const randomId = Math.floor(Math.random() * 1000000);
  const customerUsername = `e2e_customer_${randomId}`;
  const customerPassword = 'password123';

  test('should complete the entire purchasing, reviews, moderation, and access control journey', async ({ page }) => {
    // -------------------------------------------------------------
    // 1. PURCHASING JOURNEY
    // -------------------------------------------------------------
    // Go to catalog home
    await page.goto('/');
    await expect(page).toHaveTitle(/Academic Ecommerce Store/i);

    // Verify catalog has items and add the first available item to cart
    const addToCartButton = page.locator('button:has-text("Add to Cart")').first();
    await expect(addToCartButton).toBeVisible();
    await addToCartButton.click();

    // Verify feedback or cart badge update
    await expect(page.locator('button:has-text("Added!")')).toBeVisible();

    // Go to Cart page
    await page.click('a[href="/cart"]');
    await expect(page).toHaveURL(/\/cart/);
    
    // Check item is present in cart
    await expect(page.locator('h1:has-text("Shopping Cart")')).toBeVisible();
    
    // Proceed to checkout (guided authentication)
    await page.click('button:has-text("Proceed to Checkout")');
    await expect(page).toHaveURL(/\/login/);

    // Toggle registration mode on Login page
    await page.click('button:has-text("Create Account")');
    await expect(page.locator('h1:has-text("Create Academic Account")')).toBeVisible();

    // Fill registration details
    await page.fill('input#account_identifier', customerUsername);
    await page.fill('input#password', customerPassword);
    await page.click('button[type="submit"]');

    // Registering should switch back to Sign In automatically and show success
    await expect(page.locator('div[role="status"]:has-text("Registration successful!")')).toBeVisible();
    await expect(page.locator('h1:has-text("Sign In")')).toBeVisible();

    // Sign in with the newly created customer account
    await page.fill('input#account_identifier', customerUsername);
    await page.fill('input#password', customerPassword);
    await page.click('button[type="submit"]');

    // Should redirect to Checkout Page as guided state is preserved
    await expect(page).toHaveURL(/\/checkout/);
    await expect(page.locator('h1:has-text("Simulated Checkout Summary")')).toBeVisible();

    // Confirm Simulated Purchase
    await page.click('button:has-text("Confirm Purchase")');
    
    // Check confirmation screen
    await expect(page).toHaveURL(/\/confirmation/);
    await expect(page.locator('h1:has-text("Simulated Purchase Confirmed!")')).toBeVisible();

    // Receipt should display correctly in English
    await expect(page.locator('h2:has-text("Simulated Receipt")')).toBeVisible();

    // Click "Start New Purchase" to return to catalog
    await page.click('a:has-text("Start New Purchase")');
    await expect(page).toHaveURL(/\//);

    // -------------------------------------------------------------
    // 2. REVIEW SUBMISSION AND MODERATION lifecycle
    // -------------------------------------------------------------
    // Navigate to the first product page (id=1) by clicking its catalog link to preserve in-memory auth state
    await page.locator('a[href="/product/1"]').first().click();
    await expect(page.locator('h1')).toBeVisible();

    // Ensure we can write a review because we are already logged in
    await expect(page.locator('h2:has-text("Write a Review")')).toBeVisible();
    await expect(page.locator('textarea#comment')).toBeVisible();

    // Rate 4 stars
    await page.click('button[aria-label="Rate 4 out of 5 stars"]');
    
    // Enter review comments
    const testReviewComment = `Excellent quality product, tested under automated E2E workflow id ${randomId}.`;
    await page.fill('textarea#comment', testReviewComment);
    
    // Submit the review
    await page.click('button:has-text("Submit Review")');

    // Check submit success notice (pending moderator approval)
    await expect(page.locator('span:has-text("Review submitted successfully!")')).toBeVisible();

    // Verify the newly submitted review is HIDDEN (not present) on the public product page
    await expect(page.locator(`p:has-text("${testReviewComment}")`)).not.toBeVisible();

    // Sign out to switch roles to Moderator
    await page.click('button:has-text("Sign Out")');

    // Go to login page
    await page.goto('/login');
    await page.fill('input#account_identifier', 'moderator');
    await page.fill('input#password', 'modpassword');
    await page.click('button[type="submit"]');

    // Since we are moderator, "Moderation" link should be in Header
    const moderationHeaderLink = page.locator('a[href="/moderation"]');
    await expect(moderationHeaderLink).toBeVisible();
    await moderationHeaderLink.click();

    // We are on moderation page
    await expect(page).toHaveURL(/\/moderation/);
    await expect(page.locator('h1:has-text("Moderation Dashboard")')).toBeVisible();

    // Find our pending review card and click Approve
    const pendingReviewCard = page.locator('div.bg-white.rounded-xl', {
      has: page.locator('p', { hasText: testReviewComment })
    });
    await expect(pendingReviewCard).toBeVisible();
    
    // Click checkmark / approve button within that review card
    const approveButton = pendingReviewCard.getByRole('button', { name: 'Approve' });
    await approveButton.click();

    // Review card should be removed from the pending list
    await expect(pendingReviewCard).not.toBeVisible();

    // Sign Out as moderator
    await page.click('button:has-text("Sign Out")');

    // Visit the product detail page as a public guest
    await page.goto('/product/1');
    
    // Verify the newly approved review is now publicly visible
    const approvedReviewText = page.locator(`p:has-text("${testReviewComment}")`);
    await expect(approvedReviewText).toBeVisible();

    // -------------------------------------------------------------
    // 3. ACCESS CONTROL (Denial for normal customer attempting moderation)
    // -------------------------------------------------------------
    // Log back in as standard customer
    await page.goto('/login');
    await page.fill('input#account_identifier', customerUsername);
    await page.fill('input#password', customerPassword);
    await page.click('button[type="submit"]');

    // Header MUST NOT contain "Moderation" dashboard link
    await expect(page.locator('a[href="/moderation"]')).not.toBeVisible();

    // Attempting direct URL access to /moderation MUST trigger the redirect to home (/)
    await page.goto('/moderation');
    await page.waitForURL('**/');
    await expect(page).toHaveURL(/\/$/); // Ended up at catalog root page
  });
});
