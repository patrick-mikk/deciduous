import React from 'react';
import { Wordmark } from '../layout/Wordmark.jsx';

/** Centered auth card (sign in / sign up / reset). Brand mark + title + form + alt-action. */
export function AuthCard({ title, subtitle, children, footer, width = 380 }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface-sunken)', padding: 24, fontFamily: 'var(--font-sans)' }}>
      <div style={{ width, maxWidth: '100%', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-e2)', padding: '32px 30px' }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 18 }}><Wordmark size={24} /></div>
        <h1 style={{ textAlign: 'center', fontSize: 'var(--text-h2)', fontWeight: 'var(--weight-bold)', color: 'var(--text)', margin: 0 }}>{title}</h1>
        {subtitle && <p style={{ textAlign: 'center', fontSize: 'var(--text-body)', color: 'var(--text-secondary)', margin: '6px 0 0' }}>{subtitle}</p>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 24 }}>{children}</div>
        {footer && <div style={{ marginTop: 20, textAlign: 'center', fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)' }}>{footer}</div>}
      </div>
    </div>
  );
}
