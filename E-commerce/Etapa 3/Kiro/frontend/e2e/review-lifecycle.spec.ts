// E2E: Stage 2 review + moderation lifecycle against the real stack
// (Requirement 2). A customer submits a review; it is hidden while pending; a
// moderator approves it; it becomes publicly visible with an updated summary.
// No API boundary is mocked.

import { expect, test } from "@playwright/test";

import {
  MODERATOR,
  expandProduct,
  registerCustomer,
  reloadProductReviews,
  signIn,
  signOut,
  uniqueIdentifier,
} from "./helpers";

// Use a stable product; the review is uniquely authored so the one-review-per-
// author-per-product rule is never hit across runs (fresh account each run).
const PRODUCT_NAME = "Mechanical Keyboard";

test("a submitted review is hidden until a moderator approves it, then becomes public", async ({
  page,
}) => {
  await page.goto("/");

  // 1. A fresh customer signs in and submits a review.
  const customer = uniqueIdentifier("reviewer");
  await registerCustomer(page, customer);

  const uniqueText = `Great keyboard ${customer}`;
  const card = await expandProduct(page, PRODUCT_NAME);
  await card.getByLabel("Rating (1 to 5)").selectOption("5");
  await card.getByLabel("Your review").fill(uniqueText);
  await card.getByTestId("submit-review").click();

  // Submission accepted: the author's own-review state reflects the persisted
  // pending status after the reviews list reloads (the transient "submitted"
  // banner is replaced by the reloaded list).
  await expect(card.getByTestId("own-review-state")).toContainText("pending");

  // 2. The review is NOT publicly visible while pending.
  //    Reload as a visitor (sign out) and confirm the text is absent.
  await signOut(page);
  const visitorCard = await reloadProductReviews(page, PRODUCT_NAME);
  await expect(visitorCard.getByTestId("reviews-loading")).toHaveCount(0);
  await expect(page.getByText(uniqueText)).toHaveCount(0);

  // 3. A moderator signs in and approves the pending review.
  await signIn(page, MODERATOR.identifier, MODERATOR.password);
  const moderation = page.locator("#moderation");
  await expect(moderation.getByRole("heading", { name: "Moderation" })).toBeVisible();
  const queueItem = moderation.locator("li", { hasText: uniqueText });
  await expect(queueItem).toBeVisible();
  await queueItem.getByRole("button", { name: "Approve" }).click();
  await expect(moderation.getByTestId("moderation-confirmation")).toContainText(
    "approved",
  );

  // 4. The approved review is now publicly visible with an updated summary.
  await signOut(page);
  const publicCard = await reloadProductReviews(page, PRODUCT_NAME);
  await expect(publicCard.getByText(uniqueText)).toBeVisible();
  await expect(publicCard.getByTestId("rating-summary")).toContainText("review");
});
