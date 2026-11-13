import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import App from "../App";

// Mock global fetch for continuous integration journey
const mockProducts = [
  {
    product_id: "prod_1",
    name: "Catalog Product Item",
    representative_image: "img.png",
    short_description: "A demonstration product",
    price: 12.5,
    general_availability: "In Stock",
  },
];

beforeEach(() => {
  global.fetch = jest.fn().mockImplementation((url, options) => {
    if (url.includes("/api/products")) {
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve(mockProducts),
      });
    }
    if (url.includes("/api/register")) {
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve({ message: "Success" }),
      });
    }
    if (url.includes("/api/signin")) {
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve({ session_token: "mock-session-uuid-token" }),
      });
    }
    if (url.includes("/api/checkout")) {
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () =>
          Promise.resolve({
            message: "Simulated checkout successful!",
            purchase_summary: {
              items: [
                {
                  product_id: "prod_1",
                  name: "Catalog Product Item",
                  quantity: 1,
                  unit_price: 12.5,
                  subtotal: 12.5,
                },
              ],
              accumulated_total: 12.5,
            },
          }),
      });
    }
    return Promise.reject(new Error("Unknown endpoint"));
  }) as jest.Mock;
});

test("Unified e2e integrated journey from catalog browsing to sign-in and checkout", async () => {
  const { container } = render(<App />);

  // 1. Catalog Browsing
  await waitFor(() => {
    expect(screen.getByText("Catalog Product Item")).toBeInTheDocument();
  });

  // 2. Add product to cart
  const addBtn = screen.getByLabelText("Add Catalog Product Item to cart");
  fireEvent.click(addBtn);
  expect(screen.getByTestId("cart")).toBeInTheDocument();
  expect(screen.getByTestId("cart-total")).toHaveTextContent("$12.50");

  // 3. Proceed to Checkout triggers Authentication overlay redirect (T026)
  const proceedBtn = screen.getByRole("button", { name: "Proceed to Checkout" });
  fireEvent.click(proceedBtn);

  // Verify authentication forms are shown
  await waitFor(() => {
    expect(screen.getByTestId("signin-form")).toBeInTheDocument();
  });

  // 4. Fill in Sign-In credentials and complete authentication
  const idInput = screen.getByPlaceholderText("Enter your registered identifier");
  const passInput = screen.getByPlaceholderText("Enter your account password");
  const signinSubmit = container.querySelector("button.auth-submit-btn") as HTMLButtonElement;

  fireEvent.change(idInput, { target: { value: "user1" } });
  fireEvent.change(passInput, { target: { value: "pass123" } });
  fireEvent.click(signinSubmit);

  // 5. Successful Sign-In automatically loads Checkout Page with cart preserved
  await waitFor(() => {
    expect(screen.getByTestId("checkout-page")).toBeInTheDocument();
  });
  expect(screen.getByTestId("checkout-total")).toHaveTextContent("$12.50");

  // 6. Complete simulated checkout
  const fieldA = screen.getByPlaceholderText("Provide detail A reference");
  const fieldB = screen.getByPlaceholderText("Provide detail B reference");
  const checkoutSubmit = screen.getByRole("button", { name: "Confirm Simulated Purchase" });

  fireEvent.change(fieldA, { target: { value: "Carol Test" } });
  fireEvent.change(fieldB, { target: { value: "carol@demo.com" } });
  fireEvent.click(checkoutSubmit);

  // Verify final purchase confirmation and summary are displayed
  await waitFor(() => {
    expect(screen.getByTestId("confirmation-panel")).toBeInTheDocument();
  });
  expect(screen.getByText("Simulated Purchase Confirmed!")).toBeInTheDocument();
});
