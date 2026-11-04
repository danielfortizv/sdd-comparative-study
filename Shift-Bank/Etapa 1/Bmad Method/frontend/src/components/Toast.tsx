import React from 'react';

interface ToastProps {
  message: string | null;
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ message, onClose }) => {
  if (!message) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        top: '24px',
        right: '24px',
        zIndex: 1000,
        backgroundColor: 'var(--color-success-surface)',
        border: '1px solid var(--color-success)',
        color: 'var(--color-success-foreground)',
        borderRadius: 'var(--rounded-md)',
        padding: '12px 18px',
        boxShadow: 'var(--shadow-md)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        maxWidth: '480px',
        animation: 'slideIn 0.3s ease-out',
      }}
      data-testid="confirmation-toast"
    >
      <span
        style={{
          width: '20px',
          height: '20px',
          borderRadius: 'var(--rounded-full)',
          backgroundColor: 'var(--color-success)',
          color: '#FFFFFF',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          fontSize: '12px',
          flexShrink: 0,
        }}
        aria-hidden="true"
      >
        ✓
      </span>
      <span style={{ fontSize: '13px', fontWeight: 500, flex: 1 }}>{message}</span>
      <button
        onClick={onClose}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--color-success-foreground)',
          fontSize: '16px',
          fontWeight: 'bold',
          cursor: 'pointer',
          padding: '0 4px',
          lineHeight: 1,
        }}
        aria-label="Close notification"
      >
        ×
      </button>
    </div>
  );
};
