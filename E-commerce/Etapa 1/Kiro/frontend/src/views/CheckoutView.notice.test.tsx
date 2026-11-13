// Example-based unit tests for the Checkout view, task 12.7 (design: Frontend
// Components — Checkout; Testing Strategy — Unit and Example Tests).
//
// This file is intentionally separate from CheckoutView.test.tsx (task 12.1)
// and focuses on the enumerated checks for task 12.7:
//   - R10.1: the fictitious-payment notice is present and states both that no
//     charge is made and that no real payment gateway is contacted.
//   - R8.1: when the person is unidentified, the identification gate offers
//     BOTH a sign-in option and a register option.
//   - R9.2: only the minimum demonstration information is requested — the view
//     collects no extra data-entry inputs.
//   - R9.3, R9.4: no address book and no saved-address selection UI is present.
//   - R10.4: on successful completion, visible finished feedback is shown.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

import { apiClient } from "../api/client";

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

beforeEach(() => {
  confirmCheckout.mockReset();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("CheckoutView — notice, gate, and minimum information (task 12.7)", () => {
  it("shows a fictitious-payment notice stating no charge and no real payment gateway (R10.1)", () => {
    renderCheckout({ signedIn: true });

    const notice = screen.getByTestId("fictitious-payment-notice");
    expect(notice).toBeInTheDocument();
    // Both claims required by R10.1 must be present in the notice text.
    expect(notice).toHaveTextContent(/no charge is made/i);
    expect(notice).toHaveTextContent(/no real payment gateway/i);
  });

  it("keeps the fictitious-payment notice visible when the cart is empty (R10.1)", () => {
    renderCheckout({ signedIn: true });

    // The notice is a standing statement about the checkout and does not
    // depend on cart contents.
    expect(
      screen.getByTestId("fictitious-payment-notice"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("checkout-empty-state")).toBeInTheDocument();
  });

  it("offers both a sign-in option and a register option when unidentified (R8.1)", () => {
    renderCheckout({ signedIn: false });
    addNotebookAndPen();

    const gate = screen.getByTestId("identification-gate");
    expect(gate).toBeInTheDocument();

    const signIn = screen.getByTestId("checkout-signin-option");
    const register = screen.getByTestId("checkout-register-option");
    // Two distinct options are presented: one to sign in, one to register.
    expect(signIn).toBeInTheDocument();
    expect(register).toBeInTheDocument();
    expect(signIn).toHaveTextContent(/sign in/i);
    expect(register).toHaveTextContent(/register/i);

    // No completion action is offered while the person is unidentified.
    expect(
      screen.queryByTestId("complete-purchase"),
    ).not.toBeInTheDocument();
  });

  it("requests only minimum demonstration information with no extra data-entry inputs (R9.2)", () => {
    renderCheckout({ signedIn: true });
    addNotebookAndPen();

    // The checkout collects no demonstration-information inputs: no text
    // fields, textareas, comboboxes, spinbuttons, or checkboxes beyond the
    // single completion action. Confirming the purchase requires no data entry.
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();

    // The only interactive control inside the checkout section is the
    // completion button (plus the harness add-buttons that live outside it).
    const section = screen
      .getByTestId("fictitious-payment-notice")
      .closest("section");
    expect(section).not.toBeNull();
    const sectionButtons = section!.querySelectorAll("button");
    expect(sectionButtons).toHaveLength(1);
    expect(sectionButtons[0]).toHaveAttribute(
      "data-testid",
      "complete-purchase",
    );
  });

  it("renders no address book and no saved-address selection UI (R9.3, R9.4)", () => {
    renderCheckout({ signedIn: true });
    addNotebookAndPen();

    // No address-related text, labels, or inputs are present anywhere in the
    // checkout: no address book (R9.3) and no saved-address selection (R9.4).
    expect(screen.queryByText(/address book/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/saved address/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/address/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/address/i)).not.toBeInTheDocument();
  });

  it("displays visible finished feedback when the simulated purchase completes (R10.4)", async () => {
    confirmCheckout.mockResolvedValue(CONFIRMATION);
    renderCheckout({ signedIn: true });
    addNotebookAndPen();

    fireEvent.click(screen.getByTestId("complete-purchase"));

    // Visible, finished feedback is surfaced on successful completion.
    await waitFor(() =>
      expect(screen.getByTestId("checkout-finished")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("checkout-finished")).toHaveTextContent(
      /finished/i,
    );
  });
});
