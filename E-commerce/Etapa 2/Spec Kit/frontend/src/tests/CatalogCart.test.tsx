import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { CartProvider } from "../context/CartContext";
import { ToastProvider } from "../components/FeedbackToast";
import Catalog from "../components/Catalog";
import Cart from "../components/Cart";

// Mock global fetch
const mockProducts = [
  {
    product_id: "prod_1",
    name: "Product 1 Test",
    representative_image: "img.png",
    short_description: "Short desc 1",
    price: 10.0,
    general_availability: "In Stock",
  },
  {
    product_id: "prod_2",
    name: "Product 2 Test",
    representative_image: "img2.png",
    short_description: "Short desc 2",
    price: 5.5,
    general_availability: "Low Stock",
  },
];

beforeEach(() => {
  global.fetch = jest.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      headers: {
        get: () => "application/json",
      },
      json: () => Promise.resolve(mockProducts),
    })
  ) as jest.Mock;
});

afterEach(() => {
  jest.restoreAllMocks();
});

test("Catalog displays products and adding updates the cart and totals", async () => {
  render(
    <ToastProvider>
      <CartProvider>
        <div>
          <Catalog />
          <Cart onProceedToCheckout={() => {}} />
        </div>
      </CartProvider>
    </ToastProvider>
  );

  // 1. Verify Catalog is loading and then displays items
  expect(screen.getByTestId("loading-state")).toBeInTheDocument();
  
  await waitFor(() => {
    expect(screen.getByText("Product 1 Test", { selector: "h3.product-name" })).toBeInTheDocument();
  });

  expect(screen.getByText("Product 2 Test", { selector: "h3.product-name" })).toBeInTheDocument();
  
  // Verify empty cart state is initially shown
  expect(screen.getByTestId("empty-cart-state")).toBeInTheDocument();

  // 2. Add product 1 to cart
  const addBtn = screen.getByLabelText("Add Product 1 Test to cart");
  fireEvent.click(addBtn);

  // Verify cart item is displayed
  expect(screen.getByTestId("cart")).toBeInTheDocument();
  expect(screen.getByText("Product 1 Test", { selector: "h3.cart-item-name" })).toBeInTheDocument();
  expect(screen.getByTestId("cart-total")).toHaveTextContent("$10.00");

  // 3. Increase quantity
  const increaseBtn = screen.getByLabelText("Increase quantity of Product 1 Test");
  fireEvent.click(increaseBtn);
  expect(screen.getByTestId("cart-total")).toHaveTextContent("$20.00");

  // 4. Decrease quantity
  const decreaseBtn = screen.getByLabelText("Decrease quantity of Product 1 Test");
  fireEvent.click(decreaseBtn);
  expect(screen.getByTestId("cart-total")).toHaveTextContent("$10.00");

  // 5. Remove item
  const removeBtn = screen.getByLabelText("Remove Product 1 Test from cart");
  fireEvent.click(removeBtn);
  expect(screen.getByTestId("empty-cart-state")).toBeInTheDocument();
});
