import React from 'react';

export function Card({ children, padding = 'var(--space-5)', style }) {
  return (
    <div
      style={{
        background: 'var(--surface-card)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--shadow-sm)',
        padding,
        fontFamily: 'var(--font-sans)',
        ...style,
      }}
    >
      {children}
    </div>
  );
}
