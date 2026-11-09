import React from 'react';

interface NavbarProps {
  onOpenTransfer: () => void;
  isMfaLocked?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenTransfer, isMfaLocked }) => {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <div className="navbar-logo">
            <span className="logo-icon">🏦</span>
            <span className="brand-name">Shift<strong>Bank</strong></span>
          </div>
          <span className="env-badge">Stage 1 Mock</span>
        </div>

        <div className="navbar-actions">
          <button
            className="btn btn-primary"
            onClick={onOpenTransfer}
            aria-label="Transfer Money"
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
