import { useState, FormEvent } from 'react';
import { useApp } from '../context/AppContext';

type Tab = 'login' | 'register';

export default function Auth() {
  const { login, register, loading } = useApp();
  const [activeTab, setActiveTab] = useState<Tab>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    // Simple completeness checks
    const trimmedUsername = username.trim();
    if (!trimmedUsername) {
      setLocalError('Username is required.');
      return;
    }
    if (!password) {
      setLocalError('Password is required.');
      return;
    }

    if (activeTab === 'login') {
      await login(trimmedUsername, password);
    } else {
      await register(trimmedUsername, password);
    }
  };

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    setLocalError(null);
  };

  return (
    <div className="auth-container">
      <div className="auth-tabs">
        <button
          className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`}
          onClick={() => handleTabChange('login')}
          type="button"
          aria-selected={activeTab === 'login'}
          role="tab"
        >
          Sign In
        </button>
        <button
          className={`auth-tab ${activeTab === 'register' ? 'active' : ''}`}
          onClick={() => handleTabChange('register')}
          type="button"
          aria-selected={activeTab === 'register'}
          role="tab"
        >
          Register
        </button>
      </div>

      <form className="auth-form" onSubmit={handleSubmit} noValidate>
        <h2 className="auth-form-title">
          {activeTab === 'login' ? 'Sign In' : 'Create an Account'}
        </h2>
        <p style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          {activeTab === 'login' 
            ? 'Identify yourself using your username and password.' 
            : 'Register a new customer account using only a username and password.'
          }
        </p>

        {localError && (
          <div className="auth-error" role="alert">
            {localError}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="username-input">Username</label>
          <input
            id="username-input"
            type="text"
            className="form-control"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading}
            autoComplete="username"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="password-input">Password</label>
          <input
            id="password-input"
            type="password"
            className="form-control"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            autoComplete={activeTab === 'login' ? 'current-password' : 'new-password'}
            required
          />
        </div>

        <button
          className="auth-submit-btn"
          type="submit"
          disabled={loading}
        >
          {loading 
            ? 'Processing...' 
            : activeTab === 'login' ? 'Sign In' : 'Register'
          }
        </button>
      </form>
    </div>
  );
}
