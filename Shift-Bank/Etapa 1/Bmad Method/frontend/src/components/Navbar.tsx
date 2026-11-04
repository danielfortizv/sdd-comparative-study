import React from 'react';

export const Navbar: React.FC = () => {
  return (
    <header
      style={{
        height: '64px',
        backgroundColor: 'var(--color-surface)',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 var(--spacing-lg)',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
        <div
          style={{
            width: '32px',
            height: '32px',
            backgroundColor: 'var(--color-primary)',
            color: 'var(--color-accent)',
            borderRadius: 'var(--rounded-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '18px',
          }}
          aria-hidden="true"
        >
          S
        </div>
        <span style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary)' }}>
          Shift Bank
        </span>
        <span
          style={{
            fontSize: '11px',
            fontWeight: 600,
            backgroundColor: 'var(--color-muted-surface)',
            color: 'var(--color-muted)',
            padding: '2px 8px',
            borderRadius: 'var(--rounded-sm)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          Stage 1 Sandbox
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
        <div style={{ textAlign: 'right', lineHeight: 1.2 }}>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-foreground)' }}>
            Alex Morgan
          </div>
          <div
            style={{
              fontSize: '11px',
              color: 'var(--color-muted)',
              fontFamily: 'var(--font-family-mono)',
            }}
          >
            cust_mock_001
          </div>
        </div>
        <div
          style={{
            width: '36px',
            height: '36px',
            borderRadius: 'var(--rounded-full)',
            backgroundColor: 'var(--color-muted-surface)',
            color: 'var(--color-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 600,
            fontSize: '13px',
            border: '1px solid var(--color-border)',
          }}
          aria-hidden="true"
        >
          AM
        </div>
      </div>
    </header>
  );
};
