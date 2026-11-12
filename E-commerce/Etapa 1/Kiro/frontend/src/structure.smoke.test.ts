// Frontend structural smoke checks for task 14.4.
//
// These assert the project's architectural boundaries and scope rather than
// runtime behavior, backing the technology/architecture/scope requirements:
//
//   * R14.1/R14.3/R14.4 — the frontend is React + TypeScript and talks to the
//     backend only through a single HTTP/JSON API client boundary (fetch +
//     API_BASE_URL + JSON), keeping presentation separate from server logic.
//   * R4.1-R4.3 — the client-side cart state wires in no durable persistence
//     (no localStorage/sessionStorage/indexedDB/cookie storage).
//   * R9.3/R9.4 — no address book or saved-address selection UI exists.
//   * R14.7 — interface text and artifacts are in English.
//
// Source files are read with Vite's `?raw` import (file contents as a string),
// so the build's type surface stays clean (no Node fs/types). Comments are
// stripped before scope greps so documentation mentioning an excluded concept
// (e.g. "no address book") does not trip a false positive — only real
// code/markup is inspected.

import { describe, expect, it } from "vitest";

import clientSource from "./api/client.ts?raw";
import appSource from "./App.tsx?raw";
import mainSource from "./main.tsx?raw";
import typesSource from "./types.ts?raw";
import cartSource from "./state/cart.ts?raw";
import journeyStateSource from "./state/JourneyState.tsx?raw";
import catalogViewSource from "./views/CatalogView.tsx?raw";
import cartViewSource from "./views/CartView.tsx?raw";
import checkoutViewSource from "./views/CheckoutView.tsx?raw";
import authViewSource from "./views/AuthView.tsx?raw";

/** Remove block and line comments so scope greps inspect code/markup only. */
function stripComments(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "") // block comments
    .replace(/^\s*\/\/.*$/gm, ""); // whole-line line comments
}

describe("API client is the HTTP/JSON boundary (R14.3, R14.4)", () => {
  it("talks to the backend over HTTP via fetch against a base URL", () => {
    expect(clientSource).toMatch(/fetch\(/);
    expect(clientSource).toMatch(/API_BASE_URL/);
    expect(clientSource).toMatch(
      /export const API_BASE_URL\s*=\s*["']https?:\/\//,
    );
  });

  it("exchanges JSON over the boundary", () => {
    expect(clientSource).toMatch(/application\/json/);
    expect(clientSource).toMatch(/JSON\.stringify/);
    expect(clientSource).toMatch(/\.json\(\)/);
  });

  it("exposes exactly the six backend endpoints and nothing more", () => {
    // Scan only the request() call sites in code (comments stripped), so
    // documentation mentioning paths like `/login` cannot inflate the surface.
    const code = stripComments(clientSource);
    const rawPaths = [
      ...code.matchAll(/request<[^>]*>\(\s*["'`](\/[a-zA-Z0-9/_${}().]*)["'`]/g),
    ].map((match) => match[1]);
    // Template-literal paths normalize to their static prefix; the single
    // product path keeps its trailing slash so it stays distinct from the list.
    const normalized = new Set(
      rawPaths.map((path) => path.replace(/\$\{[^}]*\}/g, "")),
    );

    // The six fixed endpoints are all present.
    expect(normalized.has("/products")).toBe(true); // GET /products (list)
    expect(normalized.has("/products/")).toBe(true); // GET /products/{id}
    expect(normalized.has("/auth/register")).toBe(true);
    expect(normalized.has("/auth/login")).toBe(true);
    expect(normalized.has("/auth/logout")).toBe(true);
    expect(normalized.has("/checkout/confirm")).toBe(true);

    // No stray endpoints that would widen the fixed six-endpoint contract.
    for (const path of normalized) {
      expect(path).toMatch(
        /^\/(products\/?|auth\/(register|login|logout)|checkout\/confirm)$/,
      );
    }
  });
});

describe("client-side cart has no durable persistence (R4.1-R4.3)", () => {
  const persistenceApis = /localStorage|sessionStorage|indexedDB|document\.cookie/;

  it("state modules wire in no durable storage API", () => {
    expect(cartSource).not.toMatch(persistenceApis);
    expect(journeyStateSource).not.toMatch(persistenceApis);
  });

  it("no source module anywhere wires in durable storage", () => {
    for (const source of [
      typesSource,
      appSource,
      mainSource,
      clientSource,
      catalogViewSource,
      cartViewSource,
      checkoutViewSource,
      authViewSource,
    ]) {
      expect(source).not.toMatch(persistenceApis);
    }
  });
});

describe("no address book or saved-address UI (R9.3, R9.4)", () => {
  it("the checkout view renders no address-related markup", () => {
    expect(stripComments(checkoutViewSource)).not.toMatch(/address/i);
  });

  it("no view renders address-related markup", () => {
    for (const source of [
      catalogViewSource,
      cartViewSource,
      checkoutViewSource,
      authViewSource,
    ]) {
      expect(stripComments(source)).not.toMatch(/address/i);
    }
  });
});

describe("interface text is in English (R14.7)", () => {
  it("renders recognizable English control and heading text", () => {
    expect(catalogViewSource).toMatch(/Add to cart/);
    expect(checkoutViewSource).toMatch(/Order summary/);
    expect(checkoutViewSource).toMatch(/simulated/i);
    // The app shell title is English.
    expect(appSource).toMatch(/E-Commerce Stage 1/);
  });

  it("contains only ASCII in checkout markup (allowing typographic punctuation)", () => {
    // Non-ASCII beyond the ellipsis/em-dash used in copy would hint at
    // non-English text; this is a light representative check.
    const nonAscii = checkoutViewSource
      .replace(/[\u2026\u2014]/g, "")
      .match(/[^\x00-\x7F]/g);
    expect(nonAscii).toBeNull();
  });
});
