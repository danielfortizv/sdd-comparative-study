// Authentication view (design: Frontend Components — Authentication).
//
// Provides registration and sign-in forms using the `identifier` + `password`
// credential contract, a sign-out control, and the active/inactive session
// indicator. Password inputs are rendered obscured (R7.1) and the password is
// never rendered as readable text anywhere (R7.2). Field labels describe the
// expected input (R5.2, R6.2, R13.3). Validation surfaces errors that identify
// offending fields (R5.3, R5.4) without echoing submitted credential values
// (R5.5) or exposing unnecessary internal detail (R7.4). Visible confirmations
// are shown for sign-in and sign-out (R6.7, R6.8).

import { useState, type FormEvent } from "react";

import { ApiError, apiClient } from "../api/client";
import { useJourney } from "../state/JourneyState";
import type { Credentials } from "../types";

/**
 * Human-readable label for a credential field, used both in validation messages
 * and as the visible <label> text so a reported field name matches what the
 * person sees (R5.3, R5.4). Keys mirror the backend's field names in its
 * `emptyFields`/`nonConformingFields` lists.
 */
const FIELD_LABELS: Record<keyof Credentials, string> = {
  identifier: "Identifier",
  password: "Password",
};

/** Generic authentication-failure message with no internal detail (R7.4). */
const SIGN_IN_FAILED_MESSAGE =
  "Sign-in failed. Check your identifier and password, then try again.";

/**
 * Map an {@link ApiError} from a rejected registration onto a user-facing
 * message that names each offending field (R5.3, R5.4) and omits any submitted
 * credential value (R5.5) and internal detail (R7.4). The message is built from
 * field names only; submitted values are never interpolated.
 */
function describeRegistrationError(error: ApiError): string {
  const detail = error.detail;
  const parts: string[] = [];

  const empty = detail?.emptyFields ?? [];
  if (empty.length > 0) {
    const names = empty.map(labelFor).join(", ");
    parts.push(`The following required fields are empty: ${names}.`);
  }

  const nonConforming = detail?.nonConformingFields ?? [];
  if (nonConforming.length > 0) {
    const names = nonConforming.map(labelFor).join(", ");
    parts.push(`The following fields have an invalid format: ${names}.`);
  }

  if (parts.length > 0) {
    return parts.join(" ");
  }

  // 409 (already registered) or any other structured rejection: show the
  // backend's message when present, otherwise a safe generic fallback. The
  // backend never echoes credential values in these messages.
  if (error.status === 409) {
    return "An account with that identifier already exists. Try signing in instead.";
  }
  return "Registration failed. Please review your input and try again.";
}

/** Resolve a backend field name to its visible label; fall back to the raw name. */
function labelFor(field: string): string {
  return FIELD_LABELS[field as keyof Credentials] ?? field;
}

/** Fields missing a non-whitespace value, reported by their visible label. */
function emptyFieldLabels(credentials: Credentials): string[] {
  const missing: string[] = [];
  if (credentials.identifier.trim() === "") missing.push(FIELD_LABELS.identifier);
  if (credentials.password.trim() === "") missing.push(FIELD_LABELS.password);
  return missing;
}

export function AuthView() {
  const { session, signInSession, signOutSession } = useJourney();

  // Registration form state.
  const [registerIdentifier, setRegisterIdentifier] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [registerPending, setRegisterPending] = useState(false);

  // Sign-in form state.
  const [signInIdentifier, setSignInIdentifier] = useState("");
  const [signInPassword, setSignInPassword] = useState("");
  const [signInError, setSignInError] = useState<string | null>(null);
  const [signInPending, setSignInPending] = useState(false);

  // Visible action confirmation (sign-in / sign-out) (R6.7, R6.8).
  const [confirmation, setConfirmation] = useState<string | null>(null);

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const credentials: Credentials = {
      identifier: registerIdentifier,
      password: registerPassword,
    };

    // Client-side required-field check (R5.3). Values are never placed in the
    // message, only field labels.
    const missing = emptyFieldLabels(credentials);
    if (missing.length > 0) {
      setRegisterError(
        `The following required fields are empty: ${missing.join(", ")}.`,
      );
      return;
    }

    setRegisterError(null);
    setRegisterPending(true);
    try {
      const account = await apiClient.register(credentials);
      // Successful registration identifies the customer (R5.6) and establishes
      // a session using the returned identifier, never the password (R7.2).
      signInSession(account.identifier);
      setConfirmation(`Signed in as ${account.identifier}.`);
      setRegisterIdentifier("");
      setRegisterPassword("");
    } catch (error) {
      if (error instanceof ApiError) {
        setRegisterError(describeRegistrationError(error));
      } else {
        setRegisterError(
          "Registration failed. Please review your input and try again.",
        );
      }
    } finally {
      setRegisterPending(false);
    }
  }

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const credentials: Credentials = {
      identifier: signInIdentifier,
      password: signInPassword,
    };

    // Client-side required-field check: indicate which input is incomplete
    // (R6.3) without revealing the entered values.
    const missing = emptyFieldLabels(credentials);
    if (missing.length > 0) {
      setSignInError(
        `The following required fields are empty: ${missing.join(", ")}.`,
      );
      return;
    }

    setSignInError(null);
    setSignInPending(true);
    try {
      const result = await apiClient.login(credentials);
      if (!result.active) {
        // Defensive: a non-active session is treated as an auth failure.
        setSignInError(SIGN_IN_FAILED_MESSAGE);
        return;
      }
      // Establish the session using the submitted identifier for display only;
      // the password is never retained or displayed (R7.2).
      signInSession(credentials.identifier);
      setConfirmation(`Signed in as ${credentials.identifier}.`);
      setSignInIdentifier("");
      setSignInPassword("");
    } catch (error) {
      // All authentication failures surface a generic message without internal
      // detail or credential values (R7.4).
      setSignInError(SIGN_IN_FAILED_MESSAGE);
    } finally {
      setSignInPending(false);
    }
  }

  async function handleSignOut() {
    try {
      await apiClient.logout();
    } catch {
      // Even if the backend call fails, end the local session so the person is
      // not left in an ambiguous state. No internal detail is surfaced.
    } finally {
      signOutSession();
      setConfirmation("You have been signed out.");
    }
  }

  return (
    <section aria-labelledby="auth-heading">
      <h2 id="auth-heading">Account</h2>

      {/* Active/inactive session indicator (R6.4, R6.5). */}
      <p data-testid="session-indicator" aria-live="polite">
        {session.active && session.identity !== null
          ? `Session active — signed in as ${session.identity}.`
          : "No active session. Register or sign in to continue."}
      </p>

      {/* Visible sign-in / sign-out confirmation (R6.7, R6.8). */}
      <p role="status" aria-live="polite" data-testid="auth-confirmation">
        {confirmation}
      </p>

      {session.active ? (
        <button type="button" onClick={handleSignOut}>
          Sign out
        </button>
      ) : (
        <div>
          <form aria-labelledby="register-heading" onSubmit={handleRegister}>
            <h3 id="register-heading">Register</h3>

            <div>
              <label htmlFor="register-identifier">
                {FIELD_LABELS.identifier} (the name that identifies your account)
              </label>
              <input
                id="register-identifier"
                name="identifier"
                type="text"
                autoComplete="username"
                aria-describedby={
                  registerError !== null ? "register-error" : undefined
                }
                value={registerIdentifier}
                onChange={(event) => setRegisterIdentifier(event.target.value)}
              />
            </div>

            <div>
              <label htmlFor="register-password">
                {FIELD_LABELS.password} (kept secret and shown obscured)
              </label>
              <input
                id="register-password"
                name="password"
                type="password"
                autoComplete="new-password"
                aria-describedby={
                  registerError !== null ? "register-error" : undefined
                }
                value={registerPassword}
                onChange={(event) => setRegisterPassword(event.target.value)}
              />
            </div>

            {registerError !== null && (
              <p
                id="register-error"
                role="alert"
                aria-live="assertive"
                data-testid="register-error"
              >
                {registerError}
              </p>
            )}

            <button type="submit" disabled={registerPending}>
              {registerPending ? "Creating account…" : "Create account"}
            </button>

            {/* Visible loading indicator while the request is in flight
                (R12.2). */}
            {registerPending && (
              <p role="status" aria-live="polite" data-testid="register-loading">
                Creating your account… Please wait.
              </p>
            )}
          </form>

          <form aria-labelledby="signin-heading" onSubmit={handleSignIn}>
            <h3 id="signin-heading">Sign in</h3>

            <div>
              <label htmlFor="signin-identifier">
                {FIELD_LABELS.identifier} (the name that identifies your account)
              </label>
              <input
                id="signin-identifier"
                name="identifier"
                type="text"
                autoComplete="username"
                aria-describedby={
                  signInError !== null ? "signin-error" : undefined
                }
                value={signInIdentifier}
                onChange={(event) => setSignInIdentifier(event.target.value)}
              />
            </div>

            <div>
              <label htmlFor="signin-password">
                {FIELD_LABELS.password} (kept secret and shown obscured)
              </label>
              <input
                id="signin-password"
                name="password"
                type="password"
                autoComplete="current-password"
                aria-describedby={
                  signInError !== null ? "signin-error" : undefined
                }
                value={signInPassword}
                onChange={(event) => setSignInPassword(event.target.value)}
              />
            </div>

            {signInError !== null && (
              <p
                id="signin-error"
                role="alert"
                aria-live="assertive"
                data-testid="signin-error"
              >
                {signInError}
              </p>
            )}

            <button type="submit" disabled={signInPending}>
              {signInPending ? "Signing in…" : "Sign in"}
            </button>

            {/* Visible loading indicator while the request is in flight
                (R12.2). */}
            {signInPending && (
              <p role="status" aria-live="polite" data-testid="signin-loading">
                Signing you in… Please wait.
              </p>
            )}
          </form>
        </div>
      )}
    </section>
  );
}
