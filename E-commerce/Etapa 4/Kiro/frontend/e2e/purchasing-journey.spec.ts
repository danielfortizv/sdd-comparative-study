// E2E: Stage 1 purchasing journey against the real stack (Requirement 1).
//
// Browse the catalog -> add a product to the cart -> register and sign in ->
// confirm a simulated checkout -> assert the confirmation and the reset to a
// new-purchase state. No API boundary is mocked.

import { expect, test } from "@playwright/test";

import { registerCustomer, uniqueIdentifier } from "./helpers";

test("a visitor can browse, cart, authenticate, and complete a simulated checkout", async ({
  page,
}) => {
  await page.goto("/");

  // The catalog is the initial view and loads from the real backend.
  await expect(page.getByRole("heading", { name: "Catalog" })).toBeVisible();
  const product = page.locator(".product-card", { hasText: "Wireless Headphones" });
  await expect(product).toBeVisible();

  // Add the product to the local cart.
  await product.getByRole("button", { name: "Add to cart" }).click();
  await expect(page.getByTestId("cart-item-p-001")).toBeVisible();
  await expect(page.getByTestId("cart-total")).toContainText("$79.99");

  // Checkout requires identification; the gate is shown until we sign in.
  await expect(page.getByTestId("identification-gate")).toBeVisible();

  // Register a fresh account (also establishes the session).
  const identifier = uniqueIdentifier("buyer");
  await registerCustomer(page, identifier);

  // Now checkout can complete.
  await expect(page.getByTestId("complete-purchase")).toBeEnabled();
  await page.getByTestId("complete-purchase").click();

  // Unambiguous confirmation with the purchased-items summary.
  await expect(page.getByTestId("checkout-confirmation")).toBeVisible();
  await expect(page.getByTestId("checkout-finished")).toContainText(
    "Purchase complete",
  );
  await expect(page.getByTestId("checkout-purchased-p-001")).toBeVisible();

  // Reset to a comprehensible new-purchase state empties the cart.
  await page.getByTestId("start-new-purchase").click();
  await expect(page.getByTestId("checkout-empty-state")).toBeVisible();
  await expect(page.getByTestId("cart-empty-state")).toBeVisible();
});
