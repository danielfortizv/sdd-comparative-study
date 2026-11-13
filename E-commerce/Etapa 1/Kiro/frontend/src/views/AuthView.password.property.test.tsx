// Property-based test for the Authentication view (task 11.2).
//
// Feature: ecommerce-stage1, Property 11: Passwords never appear as readable
// plain text in outputs
//
// Validates: Requirements 7.2
//
// For any password entered through the sign-in flow, no rendered interface view
// contains that password as readable plain text. The test generates random
// non-empty printable passwords, types each into the sign-in password field,
// submits the form against a mocked API client whose login resolves to an
// active session, and asserts that:
//   1. the password input is rendered obscured (type="password") (R7.1 masking
//      is the mechanism that keeps the entered value out of readable output),
//   2. the generated password never appears as readable text in the rendered
//      DOM (document.body.textContent) before or after submit (R7.2), and
//   3. the mocked login was invoked with the submitted password, proving the
//      value reached the credential boundary yet still does not surface as
//      readable rendered text.
//
// A type="password" input's VALUE is not readable plain text in textContent;
// the stronger absence assertion on document.body.textContent guards against
// the password leaking into any label, confirmation, or error message.

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import fc from "fast-check";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the API client so the view's behavior is tested without a backend. The
// mocked login resolves to an active session; register/logout are stubbed.
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

// Import the mocked client and view after vi.mock so we get the mocked instance.
import { apiClient } from "../api/client";
import { JourneyProvider } from "../state/JourneyState";
import { AuthView } from "./AuthView";

const mockedClient = vi.mocked(apiClient);

function renderAuthView() {
  return render(
    <JourneyProvider>
      <AuthView />
    </JourneyProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("Property 11: Passwords never appear as readable plain text in outputs", () => {
  it("never renders a submitted sign-in password as readable text in any view", async () => {
    await fc.assert(
      fc.asyncProperty(
        // A non-empty, printable password. A fixed sentinel prefix that never
        // occurs in the view's static text (labels, headings, button captions,
        // confirmations) is prepended so that finding the password string in
        // the rendered DOM unambiguously means the entered value leaked — not
        // that a short random string happened to be a substring of unrelated UI
        // copy such as "Password" or "signed in as alice". The random suffix
        // ranges over printable ASCII to exercise the credential input space.
        fc
          .string({
            minLength: 1,
            maxLength: 40,
            unit: fc.constantFrom(
              ..."abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}".split(
                "",
              ),
            ),
          })
          .map((suffix) => `pw-sentinel-\u2764-${suffix}`),
        async (password) => {
          // Each run renders a fresh component against a mocked active session.
          mockedClient.login.mockResolvedValue({
            active: true,
            customerId: "c-1",
          });

          renderAuthView();

          const signInForm = screen.getByRole("form", { name: /sign in/i });
          const identifierInput =
            within(signInForm).getByLabelText(/identifier/i);
          const passwordInput =
            within(signInForm).getByLabelText(/password/i);

          // The password field must be rendered obscured (not readable).
          expect(passwordInput).toHaveAttribute("type", "password");

          fireEvent.change(identifierInput, { target: { value: "alice" } });
          fireEvent.change(passwordInput, { target: { value: password } });

          // Before submit, the entered password must not appear as readable
          // text anywhere in the rendered output.
          expect(document.body.textContent ?? "").not.toContain(password);

          fireEvent.click(
            within(signInForm).getByRole("button", { name: /sign in/i }),
          );

          // After the sign-in resolves and the confirmation renders, the
          // password still must not appear as readable text in any view.
          // ``findByTestId`` resolves as soon as the confirmation appears, so
          // each run spends no longer than the confirmation actually takes to
          // render.
          expect(
            await screen.findByTestId("auth-confirmation"),
          ).toHaveTextContent(/signed in as alice/i);

          // The value reached the credential boundary (login was called with
          // it) yet never surfaces as readable rendered text (R7.2).
          expect(mockedClient.login).toHaveBeenCalledWith({
            identifier: "alice",
            password,
          });
          expect(document.body.textContent ?? "").not.toContain(password);

          // Release this run's render immediately so DOM and timers do not
          // accumulate across the generated cases, keeping the whole property
          // within the test runner's default timeout under the unmodified
          // default generated-case count.
          cleanup();
        },
      ),
    );
  });
});
