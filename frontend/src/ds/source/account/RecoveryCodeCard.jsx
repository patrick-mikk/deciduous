import React from 'react';

/** Shows the encryption recovery code with copy + a can't-recover warning. */
export function RecoveryCodeCard({ code = '', onCopy, onRegenerate }) {
  const [copied, setCopied] = React.useState(false);
  const copy = () => { navigator.clipboard && navigator.clipboard.writeText(code); setCopied(true); onCopy && onCopy(); setTimeout(() => setCopied(false), 1600); };
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 18, fontFamily: 'var(--font-sans)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <i data-lucide="key-round" style={{ width: 18, height: 18, color: 'var(--primary)' }}></i>
        <span style={{ fontSize: 'var(--text-h3)', fontWeight: 'var(--weight-bold)', color: 'var(--text)' }}>Recovery code</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <code style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 'var(--text-body-lg)', letterSpacing: '0.08em', background: 'var(--surface-sunken)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '10px 12px', color: 'var(--text)' }}>{code}</code>
        <button onClick={copy} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-strong)', background: 'transparent', color: copied ? 'var(--success)' : 'var(--text)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' }}>
          <i data-lucide={copied ? 'check' : 'copy'} style={{ width: 15, height: 15 }}></i>{copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 'var(--text-body-sm)', color: 'var(--warning)' }}>
        <i data-lucide="triangle-alert" style={{ width: 15, height: 15, flexShrink: 0, marginTop: 1 }}></i>
        Store this safely. Without it, your encrypted academic data can't be recovered if you forget your password.
      </div>
      {onRegenerate && <button onClick={onRegenerate} style={{ marginTop: 12, background: 'none', border: 'none', color: 'var(--accent)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer', padding: 0 }}>Regenerate code</button>}
    </div>
  );
}
