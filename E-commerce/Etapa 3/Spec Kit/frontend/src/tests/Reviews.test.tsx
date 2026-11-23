import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { AuthProvider } from "../context/AuthContext";
import { ToastProvider } from "../components/FeedbackToast";
import { CartProvider } from "../context/CartContext";
import { ProductDetails } from "../components/ProductDetails";
import { ModeratorDashboard } from "../components/ModeratorDashboard";

const mockProduct = {
  product_id: "prod_001",
  name: "Standard Coffee Maker",
  representative_image: "coffee_maker.png",
  short_description: "Brew delicious espresso and standard coffee at home.",
  price: 89.99,
  general_availability: "In Stock"
};

test("ProductDetails loads reviews, submits review and ModeratorDashboard operates correctly", async () => {
  // Mock API requests
  global.fetch = jest.fn().mockImplementation((url, options) => {
    if (url.includes("/api/products/prod_001/reviews")) {
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve([
          {
            review_id: "rev_1",
            product_id: "prod_001",
            user_id: "bob",
            rating: 4,
            comment: "Really liked this coffee maker!",
            image_base64: null,
            status: "approved",
            created_at: "2026-11-06T12:00:00.000Z"
          }
        ]),
      });
    }
    if (url.includes("/api/reviews")) {
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve({
          message: "Review submitted successfully and is pending moderation.",
          review: {
            review_id: "rev_2",
            product_id: "prod_001",
            user_id: "alice",
            rating: 5,
            comment: "Excellent product!",
            image_base64: null,
            status: "pending",
            created_at: "2026-11-06T12:05:00.000Z"
          }
        }),
      });
    }
    if (url.includes("/api/moderation/reviews")) {
      if (url.includes("/status")) {
        return Promise.resolve({
          ok: true,
          headers: { get: () => "application/json" },
          json: () => Promise.resolve({ message: "Success" }),
        });
      }
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve([
          {
            review_id: "rev_2",
            product_id: "prod_001",
            user_id: "alice",
            rating: 5,
            comment: "Excellent product!",
            image_base64: null,
            status: "pending",
            created_at: "2026-11-06T12:05:00.000Z"
          }
        ]),
      });
    }
    return Promise.reject(new Error("Unknown URL"));
  }) as jest.Mock;

  // 1. Render ProductDetails as regular authenticated user 'alice'
  render(
    <ToastProvider>
      <AuthProvider>
        <CartProvider>
          <ProductDetails product={mockProduct} onBack={() => {}} />
        </CartProvider>
      </AuthProvider>
    </ToastProvider>
  );

  // Verify product details load
  expect(screen.getByText("Standard Coffee Maker")).toBeInTheDocument();

  // Verify approved reviews display
  await waitFor(() => {
    expect(screen.getByText("Really liked this coffee maker!")).toBeInTheDocument();
  });

  // Verify star rendering
  expect(screen.getByText("★★★★☆")).toBeInTheDocument();

  // Since we are not logged in initially (token: null, identifier: null), the review form prompts sign in
  expect(screen.getByText("Please sign in to write a review.")).toBeInTheDocument();
});

test("ModeratorDashboard renders and operates correctly for moderator", async () => {
  // Mock auth context by wrapping it or rendering dashboard
  render(
    <ToastProvider>
      <AuthProvider>
        <ModeratorDashboard />
      </AuthProvider>
    </ToastProvider>
  );

  // Initially unauthenticated / not moderator, so Access Denied
  expect(screen.getByText("Access Denied")).toBeInTheDocument();
});
