// E2E: moderation access is denied to a regular customer (Requirement 2.3).
// A signed-in non-moderator customer sees the moderator-access-required prompt
// and has no moderation queue or Approve/Reject controls. The check is also
// confirmed at the real API boundary: the backend denies the moderation queue.

import { expect, test } from "@playwright/test";

import { registerCustomer, uniqueIdentifier } from "./helpers";

test("a regular customer cannot access the moderation queue or actions", async ({
  page,
}) => {
  await page.goto("/");

  // Sign in as a regular (non-moderator) customer.
  const customer = uniqueIdentifier("customer");
  await registerCustomer(page, customer);

  // The moderation view shows the access-required prompt, not a queue.
  const moderation = page.locator("#moderation");
  await expect(moderation.getByTestId("moderation-access-required")).toBeVisible();
  await expect(moderation.getByRole("button", { name: "Approve" })).toHaveCount(0);
  await expect(moderation.getByRole("button", { name: "Reject" })).toHaveCount(0);

  // Confirm the backend itself denies the moderation queue for this session.
  const response = await page.request.get("http://localhost:8000/moderation/reviews");
  expect(response.status()).toBe(403);
  const body = await response.json();
  expect(body.error).toBe("moderator_required");
});
