import React from 'react';

interface NavbarProps {
  onOpenTransfer: () => void;
  onOpenConversion?: () => void;
  onOpenRecurring?: () => void;
  onOpenLimits?: () => void;
  isMfaLocked?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenTransfer,
  onOpenConversion,
  onOpenRecurring,
  onOpenLimits,
  isMfaLocked,
}) => {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <div className="navbar-logo">
            <span className="logo-icon">🏦</span>
            <span className="brand-name">Shift<strong>Bank</strong></span>
          </div>
          <span className="env-badge">Stage 4 Live</span>
        </div>

        <div className="navbar-actions">
          {onOpenLimits && (
            <button
              className="btn btn-secondary"
              onClick={onOpenLimits}
              aria-label="Transfer Limits"
              data-testid="nav-limits-btn"
            >
              <span className="btn-icon">⚙️</span>
              Limits
            </button>
          )}

          {onOpenRecurring && (
            <button
              className="btn btn-secondary"
              onClick={onOpenRecurring}
              aria-label="Recurring Payments"
              data-testid="nav-recurring-btn"
            >
              <span className="btn-icon">🔄</span>
              Recurring
            </button>
          )}

          {onOpenConversion && (
            <button
              className="btn btn-secondary"
              onClick={onOpenConversion}
              aria-label="Convert Currency"
              data-testid="nav-convert-btn"
            >
              <span className="btn-icon">💱</span>
              Convert Currency
            </button>
          )}

          <button
            className="btn btn-primary"
            onClick={onOpenTransfer}
            aria-label="Transfer Money"
            data-testid="nav-transfer-btn"
          >
            <span className="btn-icon">⇄</span>
            Transfer Money
          </button>

          <div className="user-profile">
            <div className="user-avatar" title="Alex Morgan">AM</div>
            <div className="user-info">
              <span className="user-name">Alex Morgan</span>
              <span className="user-role">
                {isMfaLocked ? (
                  <span className="badge badge-danger">MFA Locked</span>
                ) : (
                  <span className="badge badge-success">Verified</span>
                )}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
