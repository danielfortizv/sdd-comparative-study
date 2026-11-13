import { test, expect } from '@playwright/test';

test.describe('Reviews and Moderation Lifecycle', () => {
  test('Complete reviews submission, moderation, and visibility lifecycle', async ({ page }) => {
    // 1. Visit catalog page
    await page.goto('/');

    // 2. View initial reviews for Keyboard (Product 1)
    const keyboardCard = page.locator('.product-card').filter({ hasText: 'Premium Ergonomic Keyboard' });
    const reviewsBtn = keyboardCard.locator('button:has-text("Reviews")');
    await reviewsBtn.click();

    // Verify modal is open and shows Customer Reviews
    await expect(page.locator('#modal-product-title')).toContainText('Reviews for Premium Ergonomic Keyboard');
    await expect(page.locator('.reviews-list .review-item')).toHaveCount(2);

    // Verify "Write a Product Review" is prompting to sign in
    await expect(page.locator('.auth-prompt-card')).toContainText('You must be signed in to submit a review.');
    
    // Close modal
    await page.click('button.modal-close-btn');

    // 3. Register a new reviewer user
    await page.click('button:has-text("Sign In")');
    await page.click('button:has-text("Register")');
    
    const username = `reviewer_e2e_${Date.now()}`;
    await page.fill('input#username-input', username);
    await page.fill('input#password-input', 'password123');
    await page.click('button.auth-submit-btn');

    // Automatically authenticated and redirected back to catalog
    await expect(page.locator('.session-status')).toContainText(`Signed in as: ${username}`);

    // 4. Open Reviews Modal again
    await reviewsBtn.click();

    // Fill out and submit the review
    const commentText = `E2E review comment by ${username} - outstanding!`;
    await page.fill('textarea#review-comment-input', commentText);
    await page.click('button[aria-label="Rate 5 out of 5 stars"]');
    await page.click('button.submit-review-btn');

    // Modal reloads. Verify that the pending review is HIDDEN from the list of reviews
    // The reviews count should still be exactly 2 for regular visitors
    await expect(page.locator('.reviews-list .review-item')).toHaveCount(2);
    
    // Close reviews modal
    await page.click('button.modal-close-btn');

    // 5. Sign out customer
    await page.click('button:has-text("Sign Out")');

    // 6. Log in as moderator
    await page.click('button:has-text("Sign In")');
    await page.fill('input#username-input', 'moderator');
    await page.fill('input#password-input', 'moderator');
    await page.click('button.auth-submit-btn');

    // Verify Moderator Dashboard is visible in header
    const modNavBtn = page.locator('button:has-text("Moderation Dashboard")');
    await expect(modNavBtn).toBeVisible();
    await modNavBtn.click();

    // Verify we are on Moderation Dashboard
    await expect(page.locator('h1#moderation-heading')).toContainText('Moderation Dashboard');

    // Locate our pending review card
    const reviewCard = page.locator('.moderation-card.pending').filter({ hasText: username });
    await expect(reviewCard).toBeVisible();
    await expect(reviewCard).toContainText(commentText);

    // Click Approve
    const approveBtn = reviewCard.locator('button.approve');
    await approveBtn.click();

    // Verify it is no longer in pending filter
    await expect(reviewCard).not.toBeVisible();

    // 7. Sign out moderator
    await page.click('button:has-text("Sign Out")');

    // 8. Open catalog and reviews of product again
    // Verify newly approved review is now publicly visible!
    await reviewsBtn.click();
    await expect(page.locator('.reviews-list .review-item')).toHaveCount(3);
    await expect(page.locator('.reviews-list')).toContainText(commentText);

    // Clean up modal
    await page.click('button.modal-close-btn');
  });
});
