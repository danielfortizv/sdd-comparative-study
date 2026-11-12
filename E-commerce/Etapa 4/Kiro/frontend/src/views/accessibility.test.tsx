// Cross-view accessibility tests (task 14.2 — Requirement 13).
//
// These verify that Requirement 13 is met consistently across the four views:
// - R13.2: each primary control exposes an understandable accessible name that
//   identifies the action it performs (asserted via getByRole with a name).
// - R13.3: form inputs are associated with their visible labels (getByLabelText
//   resolves them) and, when present, their validation messages are associated
//   via aria-describedby.
// - R13.4: the controls used along the main journey are native, keyboard-
//   focusable elements with no positive tabindex, so keyboard navigation never
//   prevents completing the journey.
//
// The API client is mocked so views render without a backend, and every render
// is wrapped in the real JourneyProvider so the views consume shared state
// exactly as they do in the app.

import { useEffect } from "react";
import {
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { JourneyProvider, useJourney } from "../state/JourneyState";
import type { Product } from "../types";
import { AuthView } from "./AuthView";
import { CartView } from "./CartView";
import { CatalogView } from "./CatalogView";
import { CheckoutView } from "./CheckoutView";

// Mock the API client module so no real network request is made.
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

// Import the mocked client after vi.mock so the typed mock is available.
import { apiClient } from "../api/client";

const listProductsMock = vi.mocked(apiClient.listProducts);

const PRODUCTS: Product[] = [
  {
    id: "p1",
    name: "Ceramic Mug",
    imageUrl: "http://img/mug.png",
    description: "A sturdy ceramic mug.",
    price: 12.5,
    available: true,
  },
];

/** True when an element is a native, keyboard-focusable control with no
 *  positive tabindex (which would distort the natural tab order, R13.4). */
function isKeyboardOperable(element: HTMLElement): boolean {
  const nativelyFocusable = ["A", "BUTTON", "INPUT", "SELECT", "TEXTAREA"];
  const isNative = nativelyFocusable.includes(element.tagName);
  // tabIndex of a native control defaults to 0 (focusable). A value greater
  // than 0 is a positive tabindex and is disallowed.
  const noPositiveTabIndex = element.tabIndex <= 0;
  return isNative && noPositiveTabIndex;
}

/** Seed the shared catalog and cart with one product on mount so the Cart and
 *  Checkout views render their primary controls. The catalog must be populated
 *  because the cart view resolves line items against it. */
function CartSeeder({ productId }: { productId: string }) {
  const { setCatalog, addToCart } = useJourney();
  useEffect(() => {
    setCatalog(PRODUCTS);
    addToCart(productId);
    // Seed exactly once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
}

beforeEach(() => {
  vi.clearAllMocks();
  listProductsMock.mockResolvedValue(PRODUCTS);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("Accessibility — primary controls have accessible names (R13.2)", () => {
  it("Catalog primary controls expose action-identifying names", async () => {
    render(
      <JourneyProvider>
        <CatalogView />
      </JourneyProvider>,
    );

    // Wait for the catalog to load.
    await screen.findByRole("heading", { name: "Ceramic Mug" });

    expect(
      screen.getByRole("button", { name: /add to cart/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /view details/i }),
    ).toBeInTheDocument();
  });

  it("Cart primary controls expose action-identifying names", () => {
    render(
      <JourneyProvider>
        <CartSeeder productId="p1" />
        <CartView />
      </JourneyProvider>,
    );

    // Each quantity/removal control names the product and action it affects.
    expect(
      screen.getByRole("button", { name: /increase quantity of/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /decrease quantity of/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /remove .* from cart/i }),
    ).toBeInTheDocument();
  });

  it("Account primary controls expose action-identifying names", () => {
    render(
      <JourneyProvider>
        <AuthView />
      </JourneyProvider>,
    );

    expect(
      screen.getByRole("button", { name: /create account/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("Checkout primary controls expose action-identifying names", () => {
    render(
      <JourneyProvider>
        <CartSeeder productId="p1" />
        <CheckoutView />
      </JourneyProvider>,
    );

    // With a cart but no session, the gate's sign-in/register links are the
    // primary controls and both name their action.
    expect(
      screen.getByRole("link", { name: /sign in to your account/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /register a new account/i }),
    ).toBeInTheDocument();
  });
});

describe("Accessibility — form inputs associated with labels and messages (R13.3)", () => {
  it("Account inputs resolve by their visible labels in both forms", () => {
    render(
      <JourneyProvider>
        <AuthView />
      </JourneyProvider>,
    );

    const registerForm = screen.getByRole("form", { name: /register/i });
    expect(
      within(registerForm).getByLabelText(/identifier/i),
    ).toBeInTheDocument();
    expect(
      within(registerForm).getByLabelText(/password/i),
    ).toBeInTheDocument();

    const signInForm = screen.getByRole("form", { name: /sign in/i });
    expect(
      within(signInForm).getByLabelText(/identifier/i),
    ).toBeInTheDocument();
    expect(
      within(signInForm).getByLabelText(/password/i),
    ).toBeInTheDocument();
  });

  it("associates a validation message with its inputs via aria-describedby", () => {
    render(
      <JourneyProvider>
        <AuthView />
      </JourneyProvider>,
    );

    const registerForm = screen.getByRole("form", { name: /register/i });
    // Submitting empty surfaces the required-fields error (R5.3).
    fireEvent.submit(registerForm);

    const error = screen.getByTestId("register-error");
    expect(error).toHaveAttribute("id", "register-error");

    const identifier = within(registerForm).getByLabelText(/identifier/i);
    const password = within(registerForm).getByLabelText(/password/i);
    expect(identifier).toHaveAttribute("aria-describedby", "register-error");
    expect(password).toHaveAttribute("aria-describedby", "register-error");
  });
});

describe("Accessibility — controls are keyboard-operable (R13.4)", () => {
  it("Account controls are native and carry no positive tabindex", () => {
    render(
      <JourneyProvider>
        <AuthView />
      </JourneyProvider>,
    );

    const controls: HTMLElement[] = [
      ...screen.getAllByRole("textbox"),
      ...screen.getAllByRole("button"),
      // Password inputs are not exposed as a role; collect them by label.
      ...screen.getAllByLabelText(/password/i),
    ];

    expect(controls.length).toBeGreaterThan(0);
    for (const control of controls) {
      expect(isKeyboardOperable(control)).toBe(true);
    }
  });

  it("Cart controls are native and carry no positive tabindex", () => {
    render(
      <JourneyProvider>
        <CartSeeder productId="p1" />
        <CartView />
      </JourneyProvider>,
    );

    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
    for (const button of buttons) {
      expect(isKeyboardOperable(button)).toBe(true);
    }
  });

  it("Catalog controls are native and carry no positive tabindex", async () => {
    render(
      <JourneyProvider>
        <CatalogView />
      </JourneyProvider>,
    );

    await screen.findByRole("heading", { name: "Ceramic Mug" });

    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
    for (const button of buttons) {
      expect(isKeyboardOperable(button)).toBe(true);
    }
  });

  it("Checkout gate links are native and carry no positive tabindex", () => {
    render(
      <JourneyProvider>
        <CartSeeder productId="p1" />
        <CheckoutView />
      </JourneyProvider>,
    );

    const links = screen.getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);
    for (const link of links) {
      expect(isKeyboardOperable(link)).toBe(true);
    }
  });
});
