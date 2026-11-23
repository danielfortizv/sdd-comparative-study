// Unit tests for the Authentication view (task 11.1).
//
// Verify the registration/sign-in field sets and labels (R5.1, R5.2, R6.1,
// R6.2), password masking (R7.1), that a successful sign-in shows a visible
// confirmation and an active session indicator without rendering the password
// (R6.4, R6.7, R7.2), that sign-out shows a confirmation and the inactive
// indicator (R6.5, R6.8), and that a rejected registration surfaces the
// offending-field messages without echoing the submitted password (R5.3, R5.5).

import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { JourneyProvider } from "../state/JourneyState";
import { AuthView } from "./AuthView";

// Mock the API client so the view's behavior is tested without a backend.
vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>(
    "../api/client",
  );
  return {
    ...actual,
    apiClient: {
      register: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
      listProducts: vi.fn(),
      getProduct: vi.fn(),
      confirmCheckout: vi.fn(),
    },
  };
});

// Import the mocked client after vi.mock so we get the mocked instance.
import { apiClient } from "../api/client";

const mockedClient = vi.mocked(apiClient);

function renderAuthView() {
  return render(
    <JourneyProvider>
      <AuthView />
    </JourneyProvider>,
  );
}

/** Type a value into an input via a native change event. */
function typeInto(input: HTMLElement, value: string) {
  fireEvent.change(input, { target: { value } });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AuthView fields and labels", () => {
  it("renders identifier and password fields with descriptive labels in both forms", () => {
    renderAuthView();

    const registerForm = screen.getByRole("form", { name: /register/i });
    expect(
      within(registerForm).getByLabelText(/identifier/i),
    ).toBeInTheDocument();
    expect(within(registerForm).getByLabelText(/password/i)).toBeInTheDocument();

    const signInForm = screen.getByRole("form", { name: /sign in/i });
    expect(
      within(signInForm).getByLabelText(/identifier/i),
    ).toBeInTheDocument();
    expect(within(signInForm).getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("renders password inputs as obscured (type=password)", () => {
    renderAuthView();

    const passwordInputs = screen.getAllByLabelText(/password/i);
    expect(passwordInputs.length).toBeGreaterThan(0);
    for (const input of passwordInputs) {
      expect(input).toHaveAttribute("type", "password");
    }
  });

  it("shows the inactive session indicator before signing in", () => {
    renderAuthView();
    expect(screen.getByTestId("session-indicator")).toHaveTextContent(
      /no active session/i,
    );
  });
});

describe("AuthView sign-in", () => {
  it("shows a confirmation and the active indicator on a successful sign-in without rendering the password", async () => {
    const secretPassword = "sup3r-secret-pass";
    mockedClient.login.mockResolvedValue({ active: true, customerId: "c-1" });

    renderAuthView();

    const signInForm = screen.getByRole("form", { name: /sign in/i });
    typeInto(within(signInForm).getByLabelText(/identifier/i), "alice");
    typeInto(within(signInForm).getByLabelText(/password/i), secretPassword);
    fireEvent.click(
      within(signInForm).getByRole("button", { name: /sign in/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-confirmation")).toHaveTextContent(
        /signed in as alice/i,
      );
    });

    expect(screen.getByTestId("session-indicator")).toHaveTextContent(
      /session active/i,
    );
    expect(mockedClient.login).toHaveBeenCalledWith({
      identifier: "alice",
      password: secretPassword,
    });
    // The password must never appear as readable text anywhere in the output.
    expect(document.body.textContent).not.toContain(secretPassword);
  });

  it("shows a generic authentication error without internal detail on a rejected sign-in", async () => {
    mockedClient.login.mockRejectedValue(
      new ApiError("Invalid credentials", 401, { error: "unauthorized" }),
    );

    renderAuthView();

    const signInForm = screen.getByRole("form", { name: /sign in/i });
    typeInto(within(signInForm).getByLabelText(/identifier/i), "bob");
    typeInto(within(signInForm).getByLabelText(/password/i), "wrongpass");
    fireEvent.click(
      within(signInForm).getByRole("button", { name: /sign in/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("signin-error")).toHaveTextContent(
        /sign-in failed/i,
      );
    });
    // No echoed credential value and no internal/status detail.
    expect(screen.getByTestId("signin-error")).not.toHaveTextContent(
      "wrongpass",
    );
    expect(screen.getByTestId("signin-error")).not.toHaveTextContent(/401/);
  });
});

describe("AuthView sign-out", () => {
  it("shows a confirmation and the inactive indicator after signing out", async () => {
    mockedClient.login.mockResolvedValue({ active: true, customerId: "c-1" });
    mockedClient.logout.mockResolvedValue({ active: false, customerId: null });

    renderAuthView();

    const signInForm = screen.getByRole("form", { name: /sign in/i });
    typeInto(within(signInForm).getByLabelText(/identifier/i), "alice");
    typeInto(within(signInForm).getByLabelText(/password/i), "pw");
    fireEvent.click(
      within(signInForm).getByRole("button", { name: /sign in/i }),
    );

    const signOutButton = await screen.findByRole("button", {
      name: /sign out/i,
    });
    fireEvent.click(signOutButton);

    await waitFor(() => {
      expect(screen.getByTestId("auth-confirmation")).toHaveTextContent(
        /signed out/i,
      );
    });
    expect(screen.getByTestId("session-indicator")).toHaveTextContent(
      /no active session/i,
    );
    expect(mockedClient.logout).toHaveBeenCalledTimes(1);
  });
});

describe("AuthView registration validation", () => {
  it("surfaces offending-field messages on a rejected registration without echoing the submitted password", async () => {
    const secretPassword = "my-weak-pw";
    mockedClient.register.mockRejectedValue(
      new ApiError("Validation failed", 422, {
        emptyFields: [],
        nonConformingFields: ["identifier", "password"],
      }),
    );

    renderAuthView();

    const registerForm = screen.getByRole("form", { name: /register/i });
    typeInto(within(registerForm).getByLabelText(/identifier/i), "ab");
    typeInto(within(registerForm).getByLabelText(/password/i), secretPassword);
    fireEvent.click(
      within(registerForm).getByRole("button", { name: /create account/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("register-error")).toHaveTextContent(
        /invalid format/i,
      );
    });
    const errorText = screen.getByTestId("register-error").textContent ?? "";
    expect(errorText).toMatch(/Identifier/);
    expect(errorText).toMatch(/Password/);
    // The submitted password value must never be echoed back (R5.5).
    expect(errorText).not.toContain(secretPassword);
    expect(document.body.textContent).not.toContain(secretPassword);
  });

  it("rejects an empty registration client-side and names the empty fields", () => {
    renderAuthView();

    const registerForm = screen.getByRole("form", { name: /register/i });
    fireEvent.click(
      within(registerForm).getByRole("button", { name: /create account/i }),
    );

    expect(screen.getByTestId("register-error")).toHaveTextContent(
      /required fields are empty/i,
    );
    expect(mockedClient.register).not.toHaveBeenCalled();
  });
});
