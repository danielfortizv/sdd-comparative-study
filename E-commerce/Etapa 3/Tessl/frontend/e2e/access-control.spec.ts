import { test, expect } from '@playwright/test';

test.describe('Access Control Checks', () => {
  test('Regular customer denied access to moderation dashboard and APIs', async ({ page }) => {
    // 1. Visit home page
    await page.goto('/');

    // 2. Sign in as a standard registered customer
    await page.click('button:has-text("Sign In")');
    await page.click('button:has-text("Register")');
    
    const username = `customer_ac_${Date.now()}`;
    await page.fill('input#username-input', username);
    await page.fill('input#password-input', 'password123');
    await page.click('button.auth-submit-btn');

    // Verify successfully signed in
    await expect(page.locator('.session-status')).toContainText(`Signed in as: ${username}`);

    // 3. Verify "Moderation Dashboard" button is NOT visible in the header controls
    const modNavBtn = page.locator('button:has-text("Moderation Dashboard")');
    await expect(modNavBtn).not.toBeVisible();

    // 4. Retrieve user token from localState/context or perform fetch call inside browser with user's token
    // Since AppContext manages the state, we can simulate an direct API request to /api/moderation/reviews
    // using the token to verify the server correctly returns 403 Forbidden.
    const apiResponseStatus = await page.evaluate(async (username) => {
      // Let's locate the token from localStorage if stored there, or attempt to fetch directly
      // Standard customers hitting moderation APIs should get 403 Forbidden even if they forge requests.
      // Let's first register another token or extract active context if possible,
      // or simply make a request with standard customer authorization (which we can fake or fetch).
      // Let's forge a request with a fake session token to verify 401,
      // and with the actual user token to verify 403.
      // We can grab the token from the React context by mocking or we can fetch login again.
      const loginRes = await fetch('http://127.0.0.1:8000/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password: 'password123' })
      });
      const loginData = await loginRes.json();
      const token = loginData.token;

      // Make a request to the restricted moderation endpoint using the standard user token
      const modRes = await fetch('http://127.0.0.1:8000/api/moderation/reviews', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      return modRes.status;
    }, username);

    // Assert that the server returns 403 Forbidden for a regular customer
    expect(apiResponseStatus).toBe(403);
  });
});
