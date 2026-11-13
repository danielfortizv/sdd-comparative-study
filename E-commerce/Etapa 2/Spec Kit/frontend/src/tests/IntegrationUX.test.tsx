import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import { ToastProvider, useToast } from "../components/FeedbackToast";
import { LoadingFallback, EmptyCatalogFallback, ErrorFallback } from "../components/StateFallbacks";

// Helper to trigger toasts
const ToastTriggerButton: React.FC = () => {
  const { showToast } = useToast();
  return (
    <div>
      <button onClick={() => showToast("Success notification text", "success")}>
        Trigger Success Toast
      </button>
      <button onClick={() => showToast("Error message text", "error")}>
        Trigger Error Toast
      </button>
    </div>
  );
};

test("Visible toast notifications and fallback state presentations render correctly", () => {
  render(
    <ToastProvider>
      <ToastTriggerButton />
    </ToastProvider>
  );

  // 1. Verify success toast trigger
  const successBtn = screen.getByText("Trigger Success Toast");
  fireEvent.click(successBtn);
  expect(screen.getByTestId("feedback-toast")).toBeInTheDocument();
  expect(screen.getByText("Success notification text")).toBeInTheDocument();

  // 2. Verify error toast trigger
  const errorBtn = screen.getByText("Trigger Error Toast");
  fireEvent.click(errorBtn);
  expect(screen.getAllByTestId("feedback-toast")).toHaveLength(2);
});

test("Loading, empty, and error fallback components show understandable info", () => {
  const { rerender } = render(<LoadingFallback />);
  expect(screen.getByTestId("loading-state")).toBeInTheDocument();
  expect(screen.getByText("Loading products, please wait...")).toBeInTheDocument();

  rerender(<EmptyCatalogFallback />);
  expect(screen.getByTestId("empty-catalog-state")).toBeInTheDocument();
  expect(screen.getByText(/No products are currently available/)).toBeInTheDocument();

  rerender(<ErrorFallback message="Test server error detail" />);
  expect(screen.getByTestId("error-state")).toBeInTheDocument();
  expect(screen.getByText("Test server error detail")).toBeInTheDocument();
});
