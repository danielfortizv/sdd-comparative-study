// Property-based test for the Checkout view's reset-to-new-purchase behavior
// (task 12.5; design: Frontend Components — Checkout; Testing Strategy —
// Property-Based Tests).
//
// Feature: ecommerce-stage1, Property 17: Completion resets to a state that
// allows a new purchase
//
// Validates: Requirements 10.3
//
// For any successfully completed simulated purchase, the resulting application
// state permits the person to start a new purchase. With the session held
// ACTIVE and a generated non-empty cart, the test completes a purchase (the
// mocked confirmCheckout resolves to a valid confirmation derived from the
// generated cart), awaits the confirmation, then clicks "start-new-purchase".
// It asserts the resulting state permits a new purchase:
//   1. the confirmation is gone (queryByTestId checkout-confirmation is null),
//   2. the cart is reset (the "checkout-empty-state" indication is shown), and
//   3. the fictitious-payment notice is present again — the pre-purchase
//      checkout surface from which a new purchase can start.

import {
  act,
  cleanup,
  fireEvent,
  render,
  waitFor,
  within,
} from "@testing-library/react";
import fc from "fast-check";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the API client so completion resolves without a backend. The resolved
// value is set per run to a valid confirmation derived from the generated cart.
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
import type {
  CheckoutConfirmation,
  CheckoutRequest,
  Product,
} from "../types";
import { CheckoutView } from "./CheckoutView";

const mockedClient = vi.mocked(apiClient);

// A fixed, small catalog the generated carts reference. The property holds for
// any catalog, so a representative fixed set keeps the input space focused.
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
const PRODUCT_BY_ID = new Map(CATALOG.map((product) => [product.id, product]));

interface SeedItem {
  productId: string;
  quantity: number;
}

// Seeds the catalog and the generated cart into the shared journey state, and
// signs the session in on mount so the identification gate is satisfied and the
// completion control is reachable.
function ResetHarness({
  seed,
  children,
}: {
  seed: SeedItem[];
  children: ReactNode;
}) {
  const { setCatalog, addToCart, signInSession } = useJourney();
  useEffect(() => {
    setCatalog(CATALOG);
    signInSession("buyer@example.test");
    for (const { productId, quantity } of seed) {
      addToCart(productId, quantity);
    }
  }, [setCatalog, addToCart, signInSession, seed]);
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

/** Build a valid confirmation derived from the submitted cart and catalog. */
function confirmationFor(payload: CheckoutRequest): CheckoutConfirmation {
  const items = payload.items.map((item) => {
    const product = PRODUCT_BY_ID.get(item.productId)!;
    return {
      productId: product.id,
      name: product.name,
      unitPrice: product.price,
      quantity: item.quantity,
      lineTotal: product.price * item.quantity,
    };
  });
  const total = items.reduce((sum, line) => sum + line.lineTotal, 0);
  return { items, total, simulated: true };
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("Property 17: Completion resets to a state that allows a new purchase", () => {
  it("returns to a new-purchase-ready state after completing a simulated purchase", async () => {
    await fc.assert(
      fc.asyncProperty(nonEmptyCartArbitrary, async (seed) => {
        // Clean up any prior render so queries are scoped to a single tree,
        // and reset the mock so its call count is local to this run.
        cleanup();
        mockedClient.confirmCheckout.mockReset();

        // Each run: the confirmation resolves to a value derived from the
        // actual submitted cart contents.
        mockedClient.confirmCheckout.mockImplementation(
          async (payload: CheckoutRequest) => confirmationFor(payload),
        );

        // Scope all queries to this render's container so leftover DOM from any
        // other run can never satisfy a query.
        let container!: HTMLElement;
        await act(async () => {
          ({ container } = render(
            <JourneyProvider>
              <ResetHarness seed={seed}>
                <CheckoutView />
              </ResetHarness>
            </JourneyProvider>,
          ));
        });
        const view = within(container);

        // Precondition: an identified person with a non-empty cart sees the
        // completion control and no confirmation yet.
        const completeControl = await view.findByTestId("complete-purchase");
        expect(view.queryByTestId("checkout-confirmation")).toBeNull();

        // Complete the simulated purchase and await the confirmation.
        await act(async () => {
          fireEvent.click(completeControl);
        });
        await waitFor(() => {
          expect(view.getByTestId("checkout-confirmation")).toBeInTheDocument();
        });
        expect(mockedClient.confirmCheckout).toHaveBeenCalledTimes(1);

        // Start a new purchase from the confirmed state.
        const startNew = view.getByTestId("start-new-purchase");
        await act(async () => {
          fireEvent.click(startNew);
        });

        // The resulting state permits a new purchase:
        // (a) the confirmation is gone,
        await waitFor(() => {
          expect(view.queryByTestId("checkout-confirmation")).toBeNull();
        });
        // (b) the cart is reset to the empty state, and
        expect(view.getByTestId("checkout-empty-state")).toBeInTheDocument();
        // (c) the fictitious-payment notice is present again — the pre-purchase
        // checkout surface from which a new purchase can start.
        expect(
          view.getByTestId("fictitious-payment-notice"),
        ).toBeInTheDocument();

        cleanup();
      }),
    );
  });
});
