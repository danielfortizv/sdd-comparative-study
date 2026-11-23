// Property-based test for the Checkout view identification gate (task 12.2).
//
// Feature: ecommerce-stage1, Property 13: Completion is blocked while the person
// is not identified
//
// Validates: Requirements 8.2
//
// For any non-empty cart belonging to an unidentified person, the journey
// cannot complete. The Checkout view renders an identification gate instead of
// the completion control whenever no session is active, so completion simply
// cannot be triggered. The test generates random non-empty carts over a fixed
// catalog, seeds them through the shared journey state while leaving the
// session INACTIVE (never signing in), and asserts that:
//   1. the "complete-purchase" control is absent (queryByTestId returns null),
//   2. the identification gate is shown with its sign-in and register options,
//      and
//   3. apiClient.confirmCheckout was never called — completion cannot happen.

import {
  act,
  cleanup,
  render,
  screen,
} from "@testing-library/react";
import fc from "fast-check";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the API client so completion can be observed without a backend. If the
// completion control were ever reachable it would call confirmCheckout; the
// mock lets us assert it is never invoked.
vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>(
    "../api/client",
  );
  return {
    ...actual,
    apiClient: {
      register: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
      listProducts: vi.fn(),
      getProduct: vi.fn(),
      confirmCheckout: vi.fn(),
    },
  };
});

import { apiClient } from "../api/client";
import { JourneyProvider, useJourney } from "../state/JourneyState";
import type { Product } from "../types";
import { CheckoutView } from "./CheckoutView";

const mockedClient = vi.mocked(apiClient);

// A small fixed catalog. Generated carts draw their product ids from these.
const CATALOG: Product[] = [
  {
    id: "p1",
    name: "Notebook",
    imageUrl: "https://example.test/p1.png",
    description: "A ruled notebook.",
    price: 4.5,
    available: true,
  },
  {
    id: "p2",
    name: "Pen",
    imageUrl: "https://example.test/p2.png",
    description: "A blue pen.",
    price: 1.25,
    available: true,
  },
  {
    id: "p3",
    name: "Eraser",
    imageUrl: "https://example.test/p3.png",
    description: "A soft eraser.",
    price: 0.75,
    available: true,
  },
];

const CATALOG_IDS = CATALOG.map((product) => product.id);

interface SeedItem {
  productId: string;
  quantity: number;
}

// Seeds the catalog and the generated cart into the shared journey state. The
// session is deliberately left INACTIVE — this harness never signs in, which is
// the precondition under test (an unidentified person).
function GateHarness({
  seed,
  children,
}: {
  seed: SeedItem[];
  children: ReactNode;
}) {
  const { setCatalog, addToCart } = useJourney();
  useEffect(() => {
    setCatalog(CATALOG);
    for (const { productId, quantity } of seed) {
      addToCart(productId, quantity);
    }
  }, [setCatalog, addToCart, seed]);
  return <>{children}</>;
}

// A non-empty cart over the fixed catalog ids: a non-empty subset of ids, each
// with a positive quantity. Deduplicating ids keeps the seeding faithful to a
// real cart (one line per product).
const nonEmptyCartArbitrary = fc
  .uniqueArray(fc.constantFrom(...CATALOG_IDS), {
    minLength: 1,
    maxLength: CATALOG_IDS.length,
  })
  .chain((ids) =>
    fc.tuple(
      ...ids.map((productId) =>
        fc
          .integer({ min: 1, max: 5 })
          .map((quantity) => ({ productId, quantity })),
      ),
    ),
  );

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("Property 13: Completion is blocked while the person is not identified", () => {
  it("never exposes completion and always shows the gate for an unidentified non-empty cart", async () => {
    await fc.assert(
      fc.asyncProperty(nonEmptyCartArbitrary, async (seed) => {
        // Fresh render per run with the generated cart and no active session.
        await act(async () => {
          render(
            <JourneyProvider>
              <GateHarness seed={seed}>
                <CheckoutView />
              </GateHarness>
            </JourneyProvider>,
          );
        });

        // (a) The completion control must be absent — completion cannot be
        // triggered while unidentified.
        expect(screen.queryByTestId("complete-purchase")).toBeNull();

        // (b) The identification gate is shown with sign-in and register
        // options directing the person to identify themselves.
        expect(screen.getByTestId("identification-gate")).toBeInTheDocument();
        expect(
          screen.getByTestId("checkout-signin-option"),
        ).toBeInTheDocument();
        expect(
          screen.getByTestId("checkout-register-option"),
        ).toBeInTheDocument();

        // Sanity: the cart was actually seeded (non-empty), so the gate is not
        // merely the empty-cart state. The order summary is rendered.
        expect(screen.queryByTestId("checkout-empty-state")).toBeNull();

        // (c) Completion cannot happen: the confirmation call was never made.
        expect(mockedClient.confirmCheckout).not.toHaveBeenCalled();

        cleanup();
      }),
    );
  });
});
