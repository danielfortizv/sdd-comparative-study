import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { AuthProvider } from "../context/AuthContext";
import { ToastProvider } from "../components/FeedbackToast";
import RegisterForm from "../components/RegisterForm";
import SignInForm from "../components/SignInForm";
import AuthStatus from "../components/AuthStatus";

test("Registration and Sign-in forms validate inputs and update status", async () => {
  // Mock registration and signin fetch responses
  global.fetch = jest.fn().mockImplementation((url, options) => {
    const body = options?.body ? JSON.parse(options.body) : {};
    if (url.includes("/api/register")) {
      if (body.identifier === "taken") {
        return Promise.resolve({
          ok: false,
          headers: { get: () => "application/json" },
          json: () => Promise.resolve({ error: "The username is already registered." }),
        });
      }
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve({ message: "Success" }),
      });
    }
    if (url.includes("/api/signin")) {
      if (body.password === "wrong") {
        return Promise.resolve({
          ok: false,
          headers: { get: () => "application/json" },
          json: () => Promise.resolve({ error: "Invalid password" }),
        });
      }
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve({ session_token: "mock-token-123" }),
      });
    }
    if (url.includes("/api/signout")) {
      return Promise.resolve({
        ok: true,
        headers: { get: () => "application/json" },
        json: () => Promise.resolve({ message: "Terminated" }),
      });
    }
    return Promise.reject(new Error("Unknown URL"));
  }) as jest.Mock;

  render(
    <ToastProvider>
      <AuthProvider>
        <div>
          <AuthStatus />
          <RegisterForm />
          <SignInForm />
        </div>
      </AuthProvider>
    </ToastProvider>
  );

  // 1. Initial Guest indicator
  expect(screen.getByTestId("unauthenticated-status")).toBeInTheDocument();
  expect(screen.getByText("Guest Visitor")).toBeInTheDocument();

  // 2. Submit Register with empty fields (Incomplete Input)
  const regBtn = screen.getByRole("button", { name: "Register Account" });
  fireEvent.click(regBtn);
  await waitFor(() => {
    expect(screen.getByText("Please fill in all expected information.")).toBeInTheDocument();
  });

  // 3. Submit Register with valid fields
  const regIdInput = screen.getByPlaceholderText("Enter your customer identifier");
  const regPassInput = screen.getByPlaceholderText("Enter a secure password");
  fireEvent.change(regIdInput, { target: { value: "customer1" } });
  fireEvent.change(regPassInput, { target: { value: "password" } });
  fireEvent.click(regBtn);

  // 4. Submit Sign-in with wrong password
  const signIdInput = screen.getByPlaceholderText("Enter your registered identifier");
  const signPassInput = screen.getByPlaceholderText("Enter your account password");
  const signBtn = screen.getByRole("button", { name: "Sign In" });

  fireEvent.change(signIdInput, { target: { value: "customer1" } });
  fireEvent.change(signPassInput, { target: { value: "wrong" } });
  fireEvent.click(signBtn);
  await waitFor(() => {
    expect(screen.getByText("Invalid password")).toBeInTheDocument();
  });

  // 5. Submit Sign-in with correct credentials
  fireEvent.change(signPassInput, { target: { value: "correct" } });
  fireEvent.click(signBtn);
  await waitFor(() => {
    expect(screen.getByTestId("authenticated-status")).toBeInTheDocument();
  });
  expect(screen.getByText("customer1")).toBeInTheDocument();

  // 6. Sign-out click
  const signoutBtn = screen.getByRole("button", { name: "Sign Out" });
  fireEvent.click(signoutBtn);
  await waitFor(() => {
    expect(screen.getByTestId("unauthenticated-status")).toBeInTheDocument();
  });
});
