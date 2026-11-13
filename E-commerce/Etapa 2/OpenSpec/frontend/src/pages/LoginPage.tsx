import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FormInput } from '../components/FormInput';
import { UserPlus, LogIn, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, isAuthLoading, setIsAuthLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Determine if user was guided here from checkout
  const wasGuided = location.state?.fromCheckout;

  // Form toggling state
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // Common Form States
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');

  // Validation / Feedback states
  const [localErrors, setLocalErrors] = useState<{ id?: string; pw?: string }>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const validateForm = (): boolean => {
    const errors: { id?: string; pw?: string } = {};
    if (!identifier.trim()) {
      errors.id = 'Account identifier is required.';
    }
    if (!password.trim()) {
      errors.pw = 'Password is required.';
    }
    setLocalErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    setSuccessMessage(null);

    if (!validateForm()) return;

    setIsAuthLoading(true);

    const endpoint = isRegisterMode ? 'register' : 'login';
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_identifier: identifier.trim(),
          password: password.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'An error occurred during authentication.');
      }

      if (isRegisterMode) {
        setSuccessMessage('Registration successful! You can now log in.');
        setIsRegisterMode(false);
        setPassword(''); // Clear password for login transition
      } else {
        login(data.account_identifier, data.access_token);
        // On successful login, check if guided from checkout and redirect there, else go to Catalog
        if (wasGuided) {
          navigate('/checkout');
        } else {
          navigate('/');
        }
      }
    } catch (err: any) {
      setApiError(err.message || 'Server connection failed.');
    } finally {
      setIsAuthLoading(false);
    }
  };

  return (
    <main className="max-w-md mx-auto px-4 py-12 flex-1 flex flex-col justify-center w-full">
      <div className="bg-white p-8 rounded-xl shadow-md border border-gray-100">
        {/* Guided Authentication Header Notice */}
        {wasGuided && (
          <div
            className="mb-6 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800 flex items-start gap-2"
            role="status"
          >
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <p>
              Please sign in or register to complete your purchase. Your active shopping cart has been preserved!
            </p>
          </div>
        )}

        {/* Title */}
        <div className="text-center mb-6">
          <h1 className="text-2xl font-extrabold text-gray-900 flex items-center justify-center gap-2">
            {isRegisterMode ? (
              <>
                <UserPlus className="h-6 w-6 text-indigo-600" />
                <span>Create Academic Account</span>
              </>
            ) : (
              <>
                <LogIn className="h-6 w-6 text-indigo-600" />
                <span>Sign In</span>
              </>
            )}
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {isRegisterMode
              ? 'Enter an account identifier and password'
              : 'Sign in with your academic identifier'}
          </p>
        </div>

        {/* Feedback Messages */}
        {apiError && (
          <div
            className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800 flex items-center gap-2"
            role="alert"
          >
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />
            <span>{apiError}</span>
          </div>
        )}

        {successMessage && (
          <div
            className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md text-sm text-green-800 flex items-center gap-2"
            role="status"
          >
            <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleAuthSubmit} noValidate aria-label="Academic authentication form">
          <FormInput
            id="account_identifier"
            label="Account Identifier"
            value={identifier}
            onChange={setIdentifier}
            error={localErrors.id}
            placeholder="e.g. student_id, email, or nickname"
            required
          />

          <FormInput
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            error={localErrors.pw}
            placeholder="Your account password"
            required
          />

          <button
            type="submit"
            disabled={isAuthLoading}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white font-bold py-2.5 px-4 rounded-md hover:bg-indigo-700 transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            aria-label={isRegisterMode ? 'Submit Registration' : 'Submit Sign In'}
          >
            {isAuthLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Authenticating...</span>
              </>
            ) : (
              <span>{isRegisterMode ? 'Register' : 'Sign In'}</span>
            )}
          </button>
        </form>

        {/* Toggle between Login and Registration */}
        <div className="mt-6 pt-4 border-t border-gray-100 text-center text-sm">
          {isRegisterMode ? (
            <p className="text-gray-600">
              Already have an account?{' '}
              <button
                onClick={() => {
                  setIsRegisterMode(false);
                  setLocalErrors({});
                  setApiError(null);
                }}
                className="text-indigo-600 font-bold hover:underline cursor-pointer"
                aria-label="Switch to Sign In mode"
              >
                Sign In
              </button>
            </p>
          ) : (
            <p className="text-gray-600">
              New visitor?{' '}
              <button
                onClick={() => {
                  setIsRegisterMode(true);
                  setLocalErrors({});
                  setApiError(null);
                }}
                className="text-indigo-600 font-bold hover:underline cursor-pointer"
                aria-label="Switch to Register account mode"
              >
                Create Account
              </button>
            </p>
          )}
        </div>
      </div>
    </main>
  );
};
