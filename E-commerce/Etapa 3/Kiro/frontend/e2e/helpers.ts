// Shared E2E helpers (Stage 3). These drive the real UI the same way a person
// would: filling the visible forms and clicking the visible controls. No API
// request is mocked.

import { expect, type Page } from "@playwright/test";

/** The seeded demonstration moderator credentials (see backend moderator_seed). */
export const MODERATOR = { identifier: "moderator", password: "moderator123" };

/** Build a unique identifier so each run is independent of prior store state. */
export function uniqueIdentifier(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

/**
 * Register a brand-new customer account and establish a REAL backend session.
 *
 * Registration (`POST /auth/register`) only creates the account; it does not
 * establish the backend's in-process session. Because review submission and
 * moderation are authorized against that backend session, the helper then
 * signs in (`POST /auth/login`) so the backend session is the new customer.
 */
export async function registerCustomer(
  page: Page,
  identifier: string,
  password = "password123",
): Promise<void> {
  await page.locator("#register-identifier").fill(identifier);
  await page.locator("#register-password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByTestId("session-indicator")).toContainText(
    `signed in as ${identifier}`,
  );
  // Establish the backend session for this account via a real sign-in.
  await signOut(page);
  await signIn(page, identifier, password);
}

/** Sign in with existing credentials via the Account view. */
export async function signIn(
  page: Page,
  identifier: string,
  password: string,
): Promise<void> {
  await page.locator("#signin-identifier").fill(identifier);
  await page.locator("#signin-password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByTestId("session-indicator")).toContainText(
    `signed in as ${identifier}`,
  );
}

/** Sign out the current session via the Account view. */
export async function signOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByTestId("session-indicator")).toContainText(
    "No active session",
  );
}

/**
 * Ensure a product card's detail panel is expanded (idempotent). The toggle
 * button reads "View details" when collapsed and "Hide details" when expanded,
 * so this clicks only when needed and returns the card locator.
 */
export async function expandProduct(page: Page, name: string) {
  const card = page.locator(".product-card", { hasText: name });
  const toggle = card.getByRole("button", { name: /details/ });
  const expanded = await toggle.getAttribute("aria-expanded");
  if (expanded !== "true") {
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
  }
  return card;
}

/** Collapse a product card's detail panel if it is currently expanded. */
export async function collapseProduct(page: Page, name: string) {
  const card = page.locator(".product-card", { hasText: name });
  const toggle = card.getByRole("button", { name: /details/ });
  const expanded = await toggle.getAttribute("aria-expanded");
  if (expanded === "true") {
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
  }
  return card;
}

/**
 * Force a fresh reviews load for a product by collapsing then re-expanding its
 * detail panel. ProductReviews fetches on mount, so remounting re-fetches the
 * latest approved reviews (e.g. after a moderation decision).
 */
export async function reloadProductReviews(page: Page, name: string) {
  await collapseProduct(page, name);
  return expandProduct(page, name);
}
