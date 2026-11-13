// End-to-end journey integration tests for task 14.4.
//
// These drive the whole integrated journey through the real <App/> UI with the
// HTTP/JSON API client mocked at its module boundary (vi.mock). They exercise
// the wiring the design calls out (R11.1): an add in the Catalog is reflected
// in the Cart, the Checkout order summary matches the Cart, a simulated
// completion returns a confirmation derived from the cart, and starting a new
// purchase resets the state. A dedicated keyboard-only pass shows the primary
// controls are native, focusable, and operable without a pointer (R13.4).
//
// jsdom has no real layout or tab-order engine, so the keyboard pass asserts
// focusability and native-element activation rather than physical Tab order,
// and uses fireEvent per the suite's conventions.

import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CheckoutConfirmation, CheckoutRequest, Product } from "./types";

// --- Mock the API client at its module boundary -----------------------------
// The client is the single HTTP/JSON boundary; mocking it keeps these tests
// deterministic and offline while leaving every component and the shared
// journey state fully real.
vi.mock("./api/client", () => {
  return {
    // ApiError is referenced by the views' catch blocks; provide a faithful
    // stand-in so `instanceof` checks behave.
    ApiError: class ApiError extends Error {
      status: number;
      detail: unknown;
      constructor(message: string, status = 0, detail: unknown = null) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.detail = detail;
      }
    },
    API_BASE_URL: "http://localhost:8000",
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

import { apiClient } from "./api/client";
import { App } from "./App";

// A small, deterministic demonstration catalog.
const CATALOG: Product[] = [
  {
    id: "p-001",
    name: "Wireless Headphones",
    imageUrl: "https://example.test/headphones.png",
    description: "Over-ear wireless headphones.",
    price: 79.99,
    available: true,
  },
  {
    id: "p-002",
    name: "Mechanical Keyboard",
    imageUrl: "https://example.test/keyboard.png",
    description: "Compact mechanical keyboard.",
    price: 120,
    available: true,
  },
];

const CUSTOMER_ID = "cust-123";
const IDENTIFIER = "buyer@example.com";

/** Build a confirmation from the submitted cart, resolving against CATALOG. */
function confirmationFromRequest(request: CheckoutRequest): CheckoutConfirmation {
  const byId = new Map(CATALOG.map((product) => [product.id, product]));
  const items = request.items.map((item) => {
    const product = byId.get(item.productId)!;
    return {
      productId: item.productId,
      name: product.name,
      unitPrice: product.price,
      quantity: item.quantity,
      lineTotal: product.price * item.quantity,
    };
  });
  const total = items.reduce((sum, line) => sum + line.lineTotal, 0);
  return { items, total, simulated: true };
}

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  mockedClient.listProducts.mockResolvedValue(CATALOG);
  mockedClient.login.mockResolvedValue({ active: true, customerId: CUSTOMER_ID });
  mockedClient.register.mockResolvedValue({ id: CUSTOMER_ID, identifier: IDENTIFIER });
  mockedClient.logout.mockResolvedValue({ active: false, customerId: null });
  mockedClient.confirmCheckout.mockImplementation((payload: CheckoutRequest) =>
    Promise.resolve(confirmationFromRequest(payload)),
  );
});

afterEach(() => {
  vi.clearAllMocks();
});

/** Sign in through the real Account sign-in form. */
async function signInThroughUi() {
  const signInForm = screen
    .getByRole("heading", { name: "Sign in" })
    .closest("form") as HTMLFormElement;
  const scoped = within(signInForm);

  fireEvent.change(scoped.getByLabelText(/Identifier/i), {
    target: { value: IDENTIFIER },
  });
  fireEvent.change(scoped.getByLabelText(/Password/i), {
    target: { value: "s3cret-passphrase" },
  });
  fireEvent.click(scoped.getByRole("button", { name: "Sign in" }));

  await screen.findByText(`Session active — signed in as ${IDENTIFIER}.`);
}

describe("integrated journey end to end (R11.1)", () => {
  it("flows catalog -> cart -> checkout -> completion -> reset consistently", async () => {
    render(<App />);

    // Catalog loads from the mocked client.
    await screen.findByRole("heading", { name: "Wireless Headphones" });
    expect(mockedClient.listProducts).toHaveBeenCalledTimes(1);

    // Add the first product from the catalog.
    const headphonesCard = screen
      .getByRole("heading", { name: "Wireless Headphones" })
      .closest("li") as HTMLElement;
    fireEvent.click(
      within(headphonesCard).getByRole("button", { name: "Add to cart" }),
    );

    // Cart reflects the add: the item appears and the total matches.
    const cartItem = await screen.findByTestId("cart-item-p-001");
    expect(within(cartItem).getByTestId("cart-item-name")).toHaveTextContent(
      "Wireless Headphones",
    );
    expect(within(cartItem).getByTestId("cart-item-quantity")).toHaveTextContent(
      "Quantity: 1",
    );
    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent(
      "Product added to your cart.",
    );
    expect(screen.getByTestId("cart-total")).toHaveTextContent("Total: $79.99");

    // Checkout order summary matches the cart (same product, quantity, total).
    const checkoutItem = screen.getByTestId("checkout-item-p-001");
    expect(within(checkoutItem).getByTestId("checkout-item-name")).toHaveTextContent(
      "Wireless Headphones",
    );
    expect(
      within(checkoutItem).getByTestId("checkout-item-quantity"),
    ).toHaveTextContent("Quantity: 1");
    expect(screen.getByTestId("checkout-total")).toHaveTextContent("Total: $79.99");

    // Before identification the completion control is gated.
    expect(screen.getByTestId("identification-gate")).toBeInTheDocument();
    expect(screen.queryByTestId("complete-purchase")).not.toBeInTheDocument();

    // Sign in through the Account form; the cart is preserved across sign-in.
    await signInThroughUi();
    expect(screen.getByTestId("cart-item-p-001")).toBeInTheDocument();

    // Complete the simulated purchase.
    const completeButton = await screen.findByTestId("complete-purchase");
    fireEvent.click(completeButton);

    // A confirmation derived from the cart appears.
    const confirmation = await screen.findByTestId("checkout-confirmation");
    expect(within(confirmation).getByTestId("checkout-finished")).toBeInTheDocument();
    expect(mockedClient.confirmCheckout).toHaveBeenCalledWith({
      items: [{ productId: "p-001", quantity: 1 }],
    });
    expect(screen.getByTestId("checkout-purchased-p-001")).toBeInTheDocument();
    expect(screen.getByTestId("checkout-confirmation-total")).toHaveTextContent(
      "Total: $79.99",
    );

    // Start a new purchase: state resets to the empty-cart checkout state.
    fireEvent.click(screen.getByTestId("start-new-purchase"));
    await screen.findByTestId("checkout-empty-state");
    expect(screen.getByTestId("cart-empty-state")).toBeInTheDocument();
    expect(screen.queryByTestId("checkout-confirmation")).not.toBeInTheDocument();
  });

  it("keeps per-product quantity and totals consistent across cart and checkout", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Mechanical Keyboard" });

    const keyboardCard = screen
      .getByRole("heading", { name: "Mechanical Keyboard" })
      .closest("li") as HTMLElement;
    // Add the keyboard twice -> quantity 2.
    fireEvent.click(within(keyboardCard).getByRole("button", { name: "Add to cart" }));
    fireEvent.click(within(keyboardCard).getByRole("button", { name: "Add to cart" }));

    const cartItem = await screen.findByTestId("cart-item-p-002");
    expect(within(cartItem).getByTestId("cart-item-quantity")).toHaveTextContent(
      "Quantity: 2",
    );
    // $120 * 2 = $240 in both cart and checkout.
    expect(screen.getByTestId("cart-total")).toHaveTextContent("Total: $240.00");
    const checkoutItem = screen.getByTestId("checkout-item-p-002");
    expect(
      within(checkoutItem).getByTestId("checkout-item-quantity"),
    ).toHaveTextContent("Quantity: 2");
    expect(screen.getByTestId("checkout-total")).toHaveTextContent("Total: $240.00");
  });
});

describe("keyboard-only pass through the main journey (R13.4)", () => {
  it("drives the journey using native, focusable controls operable by keyboard", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Wireless Headphones" });

    // The in-page navigation uses native anchors (focusable, keyboard-operable).
    const nav = screen.getByRole("navigation", { name: "Journey navigation" });
    for (const label of ["Catalog", "Cart", "Account", "Checkout"]) {
      const link = within(nav).getByRole("link", { name: label });
      expect(link.tagName).toBe("A");
      link.focus();
      expect(link).toHaveFocus();
    }

    // Add-to-cart is a native <button>: focus it and activate it from the
    // keyboard. jsdom does not synthesize a click from Enter on a button, so
    // we focus (proving reachability) then activate via the native path.
    const headphonesCard = screen
      .getByRole("heading", { name: "Wireless Headphones" })
      .closest("li") as HTMLElement;
    const addButton = within(headphonesCard).getByRole("button", {
      name: "Add to cart",
    });
    expect(addButton.tagName).toBe("BUTTON");
    addButton.focus();
    expect(addButton).toHaveFocus();
    fireEvent.keyDown(addButton, { key: "Enter", code: "Enter" });
    fireEvent.click(addButton); // native activation of a focused button
    await screen.findByTestId("cart-item-p-001");

    // Sign-in form inputs are native and focusable, each tied to a visible
    // label so a keyboard user can target them (R13.3 backs R13.4).
    const signInForm = screen
      .getByRole("heading", { name: "Sign in" })
      .closest("form") as HTMLFormElement;
    const scoped = within(signInForm);
    const identifierInput = scoped.getByLabelText(/Identifier/i) as HTMLInputElement;
    const passwordInput = scoped.getByLabelText(/Password/i) as HTMLInputElement;
    expect(identifierInput.tagName).toBe("INPUT");
    expect(passwordInput).toHaveAttribute("type", "password");
    identifierInput.focus();
    expect(identifierInput).toHaveFocus();
    fireEvent.change(identifierInput, { target: { value: IDENTIFIER } });
    passwordInput.focus();
    expect(passwordInput).toHaveFocus();
    fireEvent.change(passwordInput, { target: { value: "s3cret-passphrase" } });

    const signInButton = scoped.getByRole("button", { name: "Sign in" });
    signInButton.focus();
    expect(signInButton).toHaveFocus();
    fireEvent.keyDown(signInButton, { key: "Enter", code: "Enter" });
    fireEvent.click(signInButton);
    await screen.findByText(`Session active — signed in as ${IDENTIFIER}.`);

    // Complete the purchase via the native completion button.
    const completeButton = await screen.findByTestId("complete-purchase");
    expect(completeButton.tagName).toBe("BUTTON");
    completeButton.focus();
    expect(completeButton).toHaveFocus();
    fireEvent.keyDown(completeButton, { key: "Enter", code: "Enter" });
    fireEvent.click(completeButton);

    // The journey completes without any pointer-only interaction (R13.4).
    await screen.findByTestId("checkout-confirmation");
    const startNew = screen.getByTestId("start-new-purchase");
    expect(startNew.tagName).toBe("BUTTON");
    startNew.focus();
    expect(startNew).toHaveFocus();
  });
});
