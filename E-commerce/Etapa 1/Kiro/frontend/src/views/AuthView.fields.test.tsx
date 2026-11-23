// Unit tests for the Authentication view (task 11.3).
//
// These tests complement AuthView.test.tsx (task 11.1) and focus on the
// enumerated checks for task 11.3: the registration/sign-in field sets and
// descriptive labels in both forms (R5.1, R5.2, R6.1, R6.2), password field
// masking (R7.1), authentication error message content being generic and free
// of internal detail or credential values (R7.4), the active/inactive session
// indicator text (R6.4, R6.5), and the visible sign-in/sign-out confirmations
// (R6.7, R6.8).

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

// Mock the API client so the view's behavior is tested without a backend. The
// login/logout mocks resolve with the Session shape returned by the real client.
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

/** Sign in through the sign-in form with the given credentials. */
function signInAs(identifier: string, password: string) {
  const signInForm = screen.getByRole("form", { name: /sign in/i });
  typeInto(within(signInForm).getByLabelText(/identifier/i), identifier);
  typeInto(within(signInForm).getByLabelText(/password/i), password);
  fireEvent.click(within(signInForm).getByRole("button", { name: /sign in/i }));
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AuthView field sets and labels (R5.1, R5.2, R6.1, R6.2)", () => {
  it("renders exactly the identifier and password fields in the registration form", () => {
    renderAuthView();

    const registerForm = screen.getByRole("form", { name: /register/i });
    // Field set is limited to identifier + password (minimum to identify a
    // Customer): exactly two labeled inputs, one of each (R5.1).
    const inputs = within(registerForm).getAllByRole("textbox");
    const passwordInput = within(registerForm).getByLabelText(/password/i);
    // getAllByRole("textbox") excludes password inputs, so there is exactly one
    // text input (identifier) plus the single password input.
    expect(inputs).toHaveLength(1);
    expect(within(registerForm).getByLabelText(/identifier/i)).toBe(inputs[0]);
    expect(passwordInput).toBeInTheDocument();
  });

  it("renders exactly the identifier and password fields in the sign-in form", () => {
    renderAuthView();

    const signInForm = screen.getByRole("form", { name: /sign in/i });
    const inputs = within(signInForm).getAllByRole("textbox");
    const passwordInput = within(signInForm).getByLabelText(/password/i);
    expect(inputs).toHaveLength(1);
    expect(within(signInForm).getByLabelText(/identifier/i)).toBe(inputs[0]);
    expect(passwordInput).toBeInTheDocument();
  });

  it("gives each registration field a descriptive label associated with its input (R5.2)", () => {
    renderAuthView();

    const registerForm = screen.getByRole("form", { name: /register/i });
    const identifier = within(registerForm).getByLabelText(/identifier/i);
    const password = within(registerForm).getByLabelText(/password/i);

    // Labels describe the expected information, not just a bare field name.
    expect(identifier).toHaveAccessibleName(/name that identifies your account/i);
    expect(password).toHaveAccessibleName(/kept secret and shown obscured/i);
  });

  it("gives each sign-in field a descriptive label associated with its input (R6.2)", () => {
    renderAuthView();

    const signInForm = screen.getByRole("form", { name: /sign in/i });
    const identifier = within(signInForm).getByLabelText(/identifier/i);
    const password = within(signInForm).getByLabelText(/password/i);

    expect(identifier).toHaveAccessibleName(/name that identifies your account/i);
    expect(password).toHaveAccessibleName(/kept secret and shown obscured/i);
  });
});

describe("AuthView password masking (R7.1)", () => {
  it("renders the registration password input obscured as type=password", () => {
    renderAuthView();

    const registerForm = screen.getByRole("form", { name: /register/i });
    expect(within(registerForm).getByLabelText(/password/i)).toHaveAttribute(
      "type",
      "password",
    );
  });

  it("renders the sign-in password input obscured as type=password", () => {
    renderAuthView();

    const signInForm = screen.getByRole("form", { name: /sign in/i });
    expect(within(signInForm).getByLabelText(/password/i)).toHaveAttribute(
      "type",
      "password",
    );
  });
});

describe("AuthView authentication error message content (R7.4)", () => {
  it("presents a generic failure message that leaks no status code, hash, or credential value", async () => {
    const submittedPassword = "pa55word-secret";
    // A realistic rejection carrying internal detail that must not leak.
    mockedClient.login.mockRejectedValue(
      new ApiError("Internal failure", 401, {
        error: "invalid_credentials",
        // The internal hash sentinel rides along in a real detail field so the
        // "never leaks into the rendered message" assertion below stays honest.
        message: "Internal failure deadbeefcafed00d",
      }),
    );

    renderAuthView();
    signInAs("charlie", submittedPassword);

    const error = await screen.findByTestId("signin-error");
    // Indicates the authentication failure to the user (R7.4).
    expect(error).toHaveTextContent(/sign-in failed/i);
    // No submitted credential values.
    expect(error).not.toHaveTextContent("charlie");
    expect(error).not.toHaveTextContent(submittedPassword);
    // No unnecessary internal detail (status code, raw error key, hash).
    expect(error).not.toHaveTextContent(/401/);
    expect(error).not.toHaveTextContent(/invalid_credentials/i);
    expect(error).not.toHaveTextContent(/deadbeefcafed00d/i);
  });

  it("shows the same generic failure message when the login resolves as inactive", async () => {
    mockedClient.login.mockResolvedValue({ active: false, customerId: null });

    renderAuthView();
    signInAs("dana", "whatever-pw");

    const error = await screen.findByTestId("signin-error");
    expect(error).toHaveTextContent(/sign-in failed/i);
    expect(error).not.toHaveTextContent(/null/i);
  });
});

describe("AuthView session indicators (R6.4, R6.5)", () => {
  it("shows the inactive-session indicator while no session is active (R6.5)", () => {
    renderAuthView();

    expect(screen.getByTestId("session-indicator")).toHaveTextContent(
      /no active session/i,
    );
  });

  it("shows the active-session indicator naming the signed-in identity (R6.4)", async () => {
    mockedClient.login.mockResolvedValue({ active: true, customerId: "c-7" });

    renderAuthView();
    signInAs("erin", "pw-erin");

    await waitFor(() => {
      expect(screen.getByTestId("session-indicator")).toHaveTextContent(
        /session active/i,
      );
    });
    expect(screen.getByTestId("session-indicator")).toHaveTextContent(/erin/);
  });
});

describe("AuthView sign-in and sign-out confirmations (R6.7, R6.8)", () => {
  it("displays a visible sign-in confirmation after a successful sign-in (R6.7)", async () => {
    mockedClient.login.mockResolvedValue({ active: true, customerId: "c-9" });

    renderAuthView();
    signInAs("frank", "pw-frank");

    await waitFor(() => {
      expect(screen.getByTestId("auth-confirmation")).toHaveTextContent(
        /signed in as frank/i,
      );
    });
  });

  it("displays a visible sign-out confirmation and clears the identity after signing out (R6.8)", async () => {
    mockedClient.login.mockResolvedValue({ active: true, customerId: "c-9" });
    mockedClient.logout.mockResolvedValue({ active: false, customerId: null });

    renderAuthView();
    signInAs("grace", "pw-grace");

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
  });
});
