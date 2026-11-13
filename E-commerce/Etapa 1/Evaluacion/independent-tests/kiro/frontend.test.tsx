import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CheckoutRequest, Product } from "@kiro/types";

vi.mock("@kiro/api/client", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    detail: unknown;
    constructor(message: string, status = 0, detail: unknown = null) {
      super(message);
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
}));

import { apiClient } from "@kiro/api/client";
import { App } from "@kiro/App";

const products: Product[] = [
  {
    id: "p-001",
    name: "Independent Headphones",
    imageUrl: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>",
    description: "Representative independent product.",
    price: 40,
    available: true,
  },
  {
    id: "p-002",
    name: "Independent Monitor",
    imageUrl: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>",
    description: "Unavailable independent product.",
    price: 100,
    available: false,
  },
];

const client = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
  client.listProducts.mockResolvedValue(products);
  client.register.mockResolvedValue({ id: "customer-1", identifier: "buyer" });
  client.login.mockResolvedValue({ active: true, customerId: "customer-1" });
  client.logout.mockResolvedValue({ active: false, customerId: null });
  client.confirmCheckout.mockImplementation(async (request: CheckoutRequest) => {
    const items = request.items.map((item) => {
      const product = products.find((candidate) => candidate.id === item.productId)!;
      return {
        productId: product.id,
        name: product.name,
        unitPrice: product.price,
        quantity: item.quantity,
        lineTotal: product.price * item.quantity,
      };
    });
    return {
      items,
      total: items.reduce((sum, item) => sum + item.lineTotal, 0),
      simulated: true,
    };
  });
});

async function renderLoaded() {
  render(<App />);
  await screen.findByRole("heading", { name: products[0].name });
}

function card(name: string): HTMLElement {
  return screen.getByRole("heading", { name }).closest("li") as HTMLElement;
}

describe("independent frozen-catalog acceptance", () => {
  it("shows public catalog fields, loading state, details, availability and safe failure", async () => {
    let resolve!: (value: Product[]) => void;
    client.listProducts.mockReturnValueOnce(new Promise((done) => (resolve = done)));
    const first = render(<App />);
    expect(screen.getByTestId("catalog-loading")).toBeVisible();
    resolve(products);
    await screen.findByRole("heading", { name: products[0].name });
    const firstCard = card(products[0].name);
    expect(within(firstCard).getByRole("img", { name: products[0].name })).toBeVisible();
    expect(firstCard).toHaveTextContent(products[0].description);
    expect(firstCard).toHaveTextContent("$40.00");
    expect(firstCard).toHaveTextContent("Available");
    fireEvent.click(within(firstCard).getByRole("button", { name: "View details" }));
    expect(within(firstCard).getAllByText(products[0].description)).toHaveLength(2);
    first.unmount();

    client.listProducts.mockRejectedValueOnce(new Error("network detail"));
    render(<App />);
    expect(await screen.findByTestId("catalog-error")).toHaveTextContent("try again");
    expect(screen.queryByText("network detail")).not.toBeInTheDocument();
  });

  it("manages a local cart consistently and preserves it across navigation and sign-in", async () => {
    await renderLoaded();
    const firstCard = card(products[0].name);
    fireEvent.click(within(firstCard).getByRole("button", { name: "Add to cart" }));
    fireEvent.click(within(firstCard).getByRole("button", { name: "Add to cart" }));
    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent("added");
    expect(screen.getByTestId("cart-item-quantity")).toHaveTextContent("2");
    expect(screen.getByTestId("cart-item-line-total")).toHaveTextContent("$80.00");
    expect(screen.getByTestId("cart-total")).toHaveTextContent("$80.00");
    expect(screen.getByTestId("checkout-total")).toHaveTextContent("$80.00");
    expect(screen.getByTestId("identification-gate")).toBeVisible();

    const signIn = screen.getByRole("heading", { name: "Sign in" }).closest("form")!;
    fireEvent.change(within(signIn).getByLabelText(/Identifier/), { target: { value: "buyer" } });
    fireEvent.change(within(signIn).getByLabelText(/Password/), { target: { value: "secret" } });
    fireEvent.submit(signIn);
    await screen.findByText(/Session active/);
    expect(screen.getByTestId("cart-item-quantity")).toHaveTextContent("2");

    fireEvent.click(screen.getByRole("button", { name: /Decrease quantity/ }));
    expect(screen.getByTestId("cart-item-quantity")).toHaveTextContent("1");
    fireEvent.click(screen.getByRole("button", { name: /Remove .* from cart/ }));
    expect(screen.getByTestId("cart-empty-state")).toBeVisible();
    expect(screen.getByTestId("cart-confirmation")).toHaveTextContent("removed");
    expect(screen.getByTestId("checkout-empty-state")).toBeVisible();
  });

  it("validates authentication safely, provides session feedback, and signs out", async () => {
    await renderLoaded();
    const register = screen.getByRole("heading", { name: "Register" }).closest("form")!;
    fireEvent.submit(register);
    expect(screen.getByTestId("register-error")).toHaveTextContent("Identifier");
    expect(screen.getByTestId("register-error")).toHaveTextContent("Password");

    const signIn = screen.getByRole("heading", { name: "Sign in" }).closest("form")!;
    fireEvent.change(within(signIn).getByLabelText(/Identifier/), { target: { value: "private-id" } });
    fireEvent.change(within(signIn).getByLabelText(/Password/), { target: { value: "private-password" } });
    client.login.mockRejectedValueOnce(new Error("internal database trace"));
    fireEvent.submit(signIn);
    const error = await screen.findByTestId("signin-error");
    expect(error).not.toHaveTextContent("private-id");
    expect(error).not.toHaveTextContent("private-password");
    expect(error).not.toHaveTextContent("database");

    fireEvent.submit(signIn);
    expect(await screen.findByTestId("session-indicator")).toHaveTextContent("Session active");
    expect(screen.queryByText("private-password")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(await screen.findByTestId("session-indicator")).toHaveTextContent("No active session");
    expect(screen.getByTestId("auth-confirmation")).toHaveTextContent("signed out");
  });

  it("completes the simulated checkout with summary and resets for a new purchase", async () => {
    await renderLoaded();
    expect(screen.getByTestId("checkout-empty-state")).toBeVisible();
    expect(screen.queryByTestId("complete-purchase")).not.toBeInTheDocument();
    expect(screen.getByTestId("fictitious-payment-notice")).toHaveTextContent("No charge");
    expect(document.body.textContent).not.toMatch(/address book|saved address|card number/i);

    fireEvent.click(within(card(products[0].name)).getByRole("button", { name: "Add to cart" }));
    const signIn = screen.getByRole("heading", { name: "Sign in" }).closest("form")!;
    fireEvent.change(within(signIn).getByLabelText(/Identifier/), { target: { value: "buyer" } });
    fireEvent.change(within(signIn).getByLabelText(/Password/), { target: { value: "secret" } });
    fireEvent.submit(signIn);
    await screen.findByText(/Session active/);
    fireEvent.click(await screen.findByTestId("complete-purchase"));
    expect(await screen.findByTestId("checkout-confirmation")).toHaveTextContent("Purchase complete");
    expect(screen.getByTestId("checkout-confirmation-total")).toHaveTextContent("$40.00");
    fireEvent.click(screen.getByTestId("start-new-purchase"));
    expect(screen.getByTestId("cart-empty-state")).toBeVisible();
  });

  it("uses named native controls that are keyboard focusable", async () => {
    await renderLoaded();
    for (const linkName of ["Catalog", "Cart", "Account", "Checkout"]) {
      const link = screen.getByRole("link", { name: linkName });
      link.focus();
      expect(link).toHaveFocus();
    }
    const add = within(card(products[0].name)).getByRole("button", { name: "Add to cart" });
    add.focus();
    expect(add).toHaveFocus();
    fireEvent.keyDown(add, { key: "Enter" });
    fireEvent.click(add);
    expect(await screen.findByTestId("cart-item-p-001")).toBeVisible();
  });
});
