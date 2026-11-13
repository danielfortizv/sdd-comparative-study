import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { ToastProvider } from "../components/FeedbackToast";
import CheckoutPage from "../pages/CheckoutPage";

// Initial state mocks
let mockCartValue = {
  items: [] as any[],
  accumulated_total: 0,
  addItem: jest.fn(),
  updateQuantity: jest.fn(),
  removeItem: jest.fn(),
  clearCart: jest.fn(),
};

let mockAuthValue = {
  token: null as string | null,
  identifier: null as string | null,
  isAuthenticated: false,
  register: jest.fn(),
  signIn: jest.fn(),
  signOut: jest.fn(),
};

// Mock contexts
jest.mock("../context/CartContext", () => ({
  useCart: () => mockCartValue,
}));

jest.mock("../context/AuthContext", () => ({
  useAuth: () => mockAuthValue,
}));

test("Checkout blocks on empty cart, summary display, form submissions, and disclaimer", async () => {
  // 1. Render empty cart checkout (blocked)
  mockCartValue.items = [];
  mockCartValue.accumulated_total = 0;
  mockAuthValue.token = null;
  mockAuthValue.isAuthenticated = false;

  const { rerender } = render(
    <ToastProvider>
      <CheckoutPage onBackToCatalog={() => {}} />
    </ToastProvider>
  );

  expect(screen.getByTestId("empty-checkout-state")).toBeInTheDocument();
  expect(screen.getByText("Your shopping cart is empty. Checkout cannot proceed.")).toBeInTheDocument();

  // 2. Pre-populate items and active session token
  mockCartValue.items = [
    {
      product_id: "prod_1",
      name: "Product Test Item",
      unit_price: 15.0,
      quantity: 1,
      subtotal: 15.0,
    },
  ];
  mockCartValue.accumulated_total = 15.0;
  mockAuthValue.token = "token-123";
  mockAuthValue.identifier = "user1";
  mockAuthValue.isAuthenticated = true;

  // Mock global fetch for API simulated checkout response
  global.fetch = jest.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      headers: { get: () => "application/json" },
      json: () =>
        Promise.resolve({
          message: "Simulated purchase confirmed!",
          purchase_summary: {
            items: [
              {
                product_id: "prod_1",
                name: "Product Test Item",
                quantity: 1,
                unit_price: 15.0,
                subtotal: 15.0,
              },
            ],
            accumulated_total: 15.0,
          },
        }),
    })
  ) as jest.Mock;

  rerender(
    <ToastProvider>
      <CheckoutPage onBackToCatalog={() => {}} />
    </ToastProvider>
  );

  // Verify pre-confirmation summary values
  expect(screen.getByTestId("checkout-summary")).toBeInTheDocument();
  expect(screen.getByText("Product Test Item")).toBeInTheDocument();
  expect(screen.getByTestId("checkout-total")).toHaveTextContent("$15.00");

  // 3. Submit form with opaque details
  const fieldA = screen.getByPlaceholderText("Provide detail A reference");
  const fieldB = screen.getByPlaceholderText("Provide detail B reference");
  const submitBtn = screen.getByRole("button", { name: "Confirm Simulated Purchase" });

  fireEvent.change(fieldA, { target: { value: "Test Name" } });
  fireEvent.change(fieldB, { target: { value: "Test Contact" } });
  fireEvent.click(submitBtn);

  // 4. Verify unambiguous simulated confirmation panel and disclaimers
  await waitFor(() => {
    expect(screen.getByTestId("confirmation-panel")).toBeInTheDocument();
  });
  expect(screen.getByText("Simulated Purchase Confirmed!")).toBeInTheDocument();
  expect(screen.getByText(/No real payment gateway was contacted/)).toBeInTheDocument();
  expect(screen.getByText("Simulated Grand Total:")).toBeInTheDocument();
});
