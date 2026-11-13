// Cross-cutting feedback and system-state tests (Task 14.1; design: Frontend
// Components; Testing Strategy — Unit and Example Tests).
//
// Requirement 12 asks the application to present four consistent states across
// the catalog, authentication, cart, and checkout surfaces:
//   - R12.1 invalid-data: a visible message identifying the invalid data.
//   - R12.2 loading: a visible loading indicator while a request is in flight.
//   - R12.3 empty-state: a visible indication of what is happening and what the
//           person can do next when there is nothing to display.
//   - R12.4 request-failure: a visible error indication describing what happened
//           and what the person can do next.
//
// These tests exercise the four states together so the behaviour stays
// consistent across the views. The API client is mocked so requests can be held
// pending (to observe the loading indicator) or rejected (to observe the
// request-failure message), and every render is wrapped in the real
// JourneyProvider so the views consume the shared journey state exactly as the
// app does.

import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { JourneyProvider, useJourney } from "../state/JourneyState";
import type { Product } from "../types";
import { AuthView } from "./AuthView";
import { CartView } from "./CartView";
import { CatalogView } from "./CatalogView";
import { CheckoutView } from "./CheckoutView";

// Mock the API client so no real network request is made. Each method is a mock
// whose resolution can be controlled per test (pending vs. rejected).
vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    apiClient: {
      listProducts: vi.fn(),
      getProduct: vi.fn(),
      register: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
      confirmCheckout: vi.fn(),
    },
  };
});

import { apiClient } from "../api/client";

const mocked = vi.mocked(apiClient);

const PRODUCTS: Product[] = [
  {
    id: "p1",
    name: "Notebook",
    imageUrl: "https://example.test/p1.png",
    description: "A ruled notebook.",
    price: 4.5,
    available: true,
  },
];

/** A never-resolving promise so a request can be observed while in flight. */
function pending<T>(): Promise<T> {
  return new Promise<T>(() => {
    /* intentionally never settles */
  });
}

/** Seed the catalog and (optionally) an active session, plus add buttons. */
function Harness({
  signedIn = false,
  children,
}: {
  signedIn?: boolean;
  children: ReactNode;
}) {
  const { setCatalog, addToCart, signInSession } = useJourney();
  useEffect(() => {
    setCatalog(PRODUCTS);
    if (signedIn) {
      signInSession("buyer@example.test");
    }
  }, [setCatalog, signInSession, signedIn]);
  return (
    <>
      {PRODUCTS.map((product) => (
        <button
          key={product.id}
          type="button"
          onClick={() => addToCart(product.id, 1)}
        >
          {`Add ${product.name}`}
        </button>
      ))}
      {children}
    </>
  );
}

function renderWithJourney(ui: ReactNode, options?: { signedIn?: boolean }) {
  return render(
    <JourneyProvider>
      <Harness signedIn={options?.signedIn}>{ui}</Harness>
    </JourneyProvider>,
  );
}

function typeInto(input: HTMLElement, value: string) {
  fireEvent.change(input, { target: { value } });
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("R12.2 — a visible loading indicator while a request is in flight", () => {
  it("shows a catalog loading indicator while products are loading", () => {
    mocked.listProducts.mockReturnValue(pending<Product[]>());

    render(
      <JourneyProvider>
        <CatalogView />
      </JourneyProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent(/loading/i);
  });

  it("shows a sign-in loading indicator while the login request is in flight", async () => {
    mocked.login.mockReturnValue(pending());

    renderWithJourney(<AuthView />);

    typeInto(screen.getByLabelText(/identifier/i, { selector: "#signin-identifier" }), "buyer");
    typeInto(screen.getByLabelText(/password/i, { selector: "#signin-password" }), "secret1");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(
      await screen.findByTestId("signin-loading"),
    ).toHaveTextContent(/signing you in/i);
  });

  it("shows a register loading indicator while the register request is in flight", async () => {
    mocked.register.mockReturnValue(pending());

    renderWithJourney(<AuthView />);

    typeInto(
      screen.getByLabelText(/identifier/i, { selector: "#register-identifier" }),
      "buyer",
    );
    typeInto(
      screen.getByLabelText(/password/i, { selector: "#register-password" }),
      "secret1",
    );
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByTestId("register-loading"),
    ).toHaveTextContent(/creating your account/i);
  });

  it("shows a checkout loading indicator while the purchase request is in flight", async () => {
    mocked.confirmCheckout.mockReturnValue(pending());

    renderWithJourney(<CheckoutView />, { signedIn: true });
    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));

    fireEvent.click(screen.getByTestId("complete-purchase"));

    expect(
      await screen.findByTestId("checkout-loading"),
    ).toHaveTextContent(/completing your purchase/i);
  });
});

describe("R12.4 — a request-failure message that describes the next step", () => {
  it("catalog failure tells the person they can try again later", async () => {
    mocked.listProducts.mockRejectedValue(new ApiError("boom", 500));

    render(
      <JourneyProvider>
        <CatalogView />
      </JourneyProvider>,
    );

    const error = await screen.findByTestId("catalog-error");
    expect(error).toHaveTextContent(/try again/i);
  });

  it("sign-in failure tells the person what to do next", async () => {
    mocked.login.mockRejectedValue(new ApiError("nope", 401));

    renderWithJourney(<AuthView />);

    typeInto(screen.getByLabelText(/identifier/i, { selector: "#signin-identifier" }), "buyer");
    typeInto(screen.getByLabelText(/password/i, { selector: "#signin-password" }), "secret1");
    fireEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    const error = await screen.findByTestId("signin-error");
    expect(error).toHaveTextContent(/try again/i);
  });

  it("checkout failure tells the person they can try again", async () => {
    mocked.confirmCheckout.mockRejectedValue(
      new ApiError("The request to /checkout/confirm failed.", 400),
    );

    renderWithJourney(<CheckoutView />, { signedIn: true });
    fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));

    fireEvent.click(screen.getByTestId("complete-purchase"));

    const error = await screen.findByTestId("checkout-error");
    expect(error).toHaveTextContent(/try again/i);
  });
});

describe("R12.1 — a visible message identifies invalid data", () => {
  it("register surfaces an invalid-data message naming the empty fields", () => {
    renderWithJourney(<AuthView />);

    // Submit the registration form with empty inputs: the message must name the
    // offending fields without echoing any submitted value.
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(screen.getByTestId("register-error")).toHaveTextContent(
      /required fields are empty/i,
    );
    expect(mocked.register).not.toHaveBeenCalled();
  });
});

describe("R12.3 — an empty-state indication describes the next step", () => {
  it("the cart empty-state points the person to the catalog", () => {
    renderWithJourney(<CartView />);

    const empty = screen.getByTestId("cart-empty-state");
    expect(empty).toHaveTextContent(/empty/i);
    expect(empty).toHaveTextContent(/catalog/i);
  });

  it("the checkout empty-state points the person to the catalog", () => {
    renderWithJourney(<CheckoutView />, { signedIn: true });

    const empty = screen.getByTestId("checkout-empty-state");
    expect(empty).toHaveTextContent(/empty/i);
    expect(empty).toHaveTextContent(/catalog/i);
  });

  it("the catalog empty-state describes what is happening and the next step", async () => {
    mocked.listProducts.mockResolvedValue([]);

    render(
      <JourneyProvider>
        <CatalogView />
      </JourneyProvider>,
    );

    const empty = await screen.findByTestId("catalog-empty-state");
    expect(empty).toHaveTextContent(/no products are available/i);
    expect(empty).toHaveTextContent(/check back later/i);
  });
});
