// Example-based unit tests for the Checkout view (design: Frontend Components —
// Checkout; Testing Strategy — Unit and Example Tests).
//
// These cover: the pre-confirmation summary of products/quantities/total
// (R9.1); the empty-cart guard that blocks completion and shows an empty-state
// (R9.5); the absence of any address book or saved-address UI (R9.3, R9.4); the
// identification gate that blocks completion and surfaces sign-in and register
// options when unidentified (R8.1, R8.2); cart preservation across the gate
// (R8.3, R8.4); the always-visible fictitious-payment notice (R10.1);
// successful completion showing an unambiguous confirmation + purchased-items
// summary + finished feedback (R10.2, R10.4); and returning to a new-purchase
// state (R10.3).

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useEffect } from "react";

import type { CheckoutConfirmation, Product } from "../types";
import { JourneyProvider, useJourney } from "../state/JourneyState";
import { CheckoutView } from "./CheckoutView";

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>(
    "../api/client",
  );
  return {
    ...actual,
    apiClient: {
      confirmCheckout: vi.fn(),
    },
  };
});

import { ApiError, apiClient } from "../api/client";

const confirmCheckout = apiClient.confirmCheckout as unknown as ReturnType<
  typeof vi.fn
>;

const PRODUCTS: Product[] = [
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
];

// Seeds the catalog so cart items resolve, exposes add controls, and can
// toggle an active session on mount.
function Harness({
  signedIn,
  children,
}: {
  signedIn: boolean;
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

function renderCheckout({ signedIn = false }: { signedIn?: boolean } = {}) {
  return render(
    <JourneyProvider>
      <Harness signedIn={signedIn}>
        <CheckoutView />
      </Harness>
    </JourneyProvider>,
  );
}

function addNotebookAndPen() {
  fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));
  fireEvent.click(screen.getByRole("button", { name: "Add Notebook" }));
  fireEvent.click(screen.getByRole("button", { name: "Add Pen" }));
}

const CONFIRMATION: CheckoutConfirmation = {
  items: [
    {
      productId: "p1",
      name: "Notebook",
      unitPrice: 4.5,
      quantity: 2,
      lineTotal: 9.0,
    },
    {
      productId: "p2",
      name: "Pen",
      unitPrice: 1.25,
      quantity: 1,
      lineTotal: 1.25,
    },
  ],
  total: 10.25,
  simulated: true,
};

beforeEach(() => {
  confirmCheckout.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("CheckoutView", () => {
  it("always displays the fictitious-payment notice (R10.1)", () => {
    renderCheckout({ signedIn: true });
    expect(
      screen.getByTestId("fictitious-payment-notice"),
    ).toHaveTextContent(/no charge is made/i);
    expect(
      screen.getByTestId("fictitious-payment-notice"),
    ).toHaveTextContent(/no real payment gateway/i);
  });

  it("presents the pre-confirmation summary of each product, quantity, and total (R9.1)", () => {
    renderCheckout({ signedIn: true });
    addNotebookAndPen();

    const notebook = within(screen.getByTestId("checkout-item-p1"));
    expect(notebook.getByTestId("checkout-item-name")).toHaveTextContent(
      "Notebook",
    );
    expect(notebook.getByTestId("checkout-item-quantity")).toHaveTextContent(
      "2",
    );

    const pen = within(screen.getByTestId("checkout-item-p2"));
    expect(pen.getByTestId("checkout-item-name")).toHaveTextContent("Pen");
    expect(pen.getByTestId("checkout-item-quantity")).toHaveTextContent("1");

    // Total from the single source of totals: 9.00 + 1.25 = 10.25.
    expect(screen.getByTestId("checkout-total")).toHaveTextContent("$10.25");
  });

  it("blocks completion and shows an empty-state when the cart is empty (R9.5)", () => {
    renderCheckout({ signedIn: true });

    expect(screen.getByTestId("checkout-empty-state")).toBeInTheDocument();
    // No completion action is available while the cart is empty.
    expect(
      screen.queryByTestId("complete-purchase"),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("checkout-total")).not.toBeInTheDocument();
  });

  it("blocks completion and surfaces sign-in and register options when unidentified (R8.1, R8.2)", () => {
    renderCheckout({ signedIn: false });
    addNotebookAndPen();

    // Completion is blocked for an unidentified person.
    expect(
      screen.queryByTestId("complete-purchase"),
    ).not.toBeInTheDocument();
    // Both identification options are presented.
    expect(screen.getByTestId("identification-gate")).toBeInTheDocument();
    expect(screen.getByTestId("checkout-signin-option")).toBeInTheDocument();
    expect(screen.getByTestId("checkout-register-option")).toBeInTheDocument();
  });

  it("preserves cart items while the identification gate is shown (R8.3, R8.4)", () => {
    renderCheckout({ signedIn: false });
    addNotebookAndPen();

    // The summary still lists the products while the gate blocks completion;
    // the cart is not cleared by the gate.
    expect(screen.getByTestId("checkout-item-p1")).toBeInTheDocument();
    expect(screen.getByTestId("checkout-item-p2")).toBeInTheDocument();
    expect(screen.getByTestId("checkout-total")).toHaveTextContent("$10.25");
  });

  it("renders no address book or saved-address selection UI (R9.3, R9.4)", () => {
    renderCheckout({ signedIn: true });
    addNotebookAndPen();

    expect(screen.queryByText(/address book/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/saved address/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/address/i)).not.toBeInTheDocument();
  });

  it("shows an unambiguous confirmation, purchased items, and finished feedback on success (R10.2, R10.4)", async () => {
    confirmCheckout.mockResolvedValue(CONFIRMATION);
    renderCheckout({ signedIn: true });
    addNotebookAndPen();

    fireEvent.click(screen.getByTestId("complete-purchase"));

    await waitFor(() =>
      expect(screen.getByTestId("checkout-confirmation")).toBeInTheDocument(),
    );

    expect(confirmCheckout).toHaveBeenCalledWith({
      items: [
        { productId: "p1", quantity: 2 },
        { productId: "p2", quantity: 1 },
      ],
    });

    // Visible finished feedback (R10.4).
    expect(screen.getByTestId("checkout-finished")).toHaveTextContent(
      /finished/i,
    );
    // Purchased-items summary from the response (R10.2).
    const notebook = within(screen.getByTestId("checkout-purchased-p1"));
    expect(notebook.getByTestId("purchased-name")).toHaveTextContent(
      "Notebook",
    );
    expect(notebook.getByTestId("purchased-quantity")).toHaveTextContent("2");
    expect(
      screen.getByTestId("checkout-confirmation-total"),
    ).toHaveTextContent("$10.25");
  });

  it("returns to a comprehensible new-purchase state after completion (R10.3)", async () => {
    confirmCheckout.mockResolvedValue(CONFIRMATION);
    renderCheckout({ signedIn: true });
    addNotebookAndPen();

    fireEvent.click(screen.getByTestId("complete-purchase"));
    await waitFor(() =>
      expect(screen.getByTestId("start-new-purchase")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("start-new-purchase"));

    // Confirmation is cleared and the cart is reset to the empty-state from
    // which a new purchase can start.
    expect(
      screen.queryByTestId("checkout-confirmation"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("checkout-empty-state")).toBeInTheDocument();
    // The fictitious-payment notice remains visible in the fresh state.
    expect(
      screen.getByTestId("fictitious-payment-notice"),
    ).toBeInTheDocument();
  });

  it("surfaces a request-failure message when completion fails", async () => {
    confirmCheckout.mockRejectedValue(
      new ApiError("The request to /checkout/confirm failed.", 400),
    );
    renderCheckout({ signedIn: true });
    addNotebookAndPen();

    fireEvent.click(screen.getByTestId("complete-purchase"));

    await waitFor(() =>
      expect(screen.getByTestId("checkout-error")).toBeInTheDocument(),
    );
    // The summary is still shown so the person can retry.
    expect(screen.getByTestId("complete-purchase")).toBeInTheDocument();
  });
});
