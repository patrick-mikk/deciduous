import React from 'react';

/** Generate / copy / revoke a read-only share link. Render inside a Dialog. */
export function ShareLinkDialog({ url, onGenerate, onRevoke, sharedItems = [] }) {
  const [copied, setCopied] = React.useState(false);
  const copy = () => { navigator.clipboard && navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 1600); };
  return (
    <div style={{ fontFamily: 'var(--font-sans)', display: 'flex', flexDirection: 'column', gap: 14 }}>
      <p style={{ margin: 0, fontSize: 'var(--text-body)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-body)' }}>
        Anyone with this link can view a read-only snapshot of your plan. No marks or personal data are shared.
      </p>
      {url ? (
        <div style={{ display: 'flex', gap: 8 }}>
          <input readOnly value={url} style={{ flex: 1, padding: '9px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-body-sm)', background: 'var(--surface-sunken)', color: 'var(--text)', outline: 'none' }} />
          <button onClick={copy} style={primary}><i data-lucide={copied ? 'check' : 'copy'} style={{ width: 15, height: 15 }}></i>{copied ? 'Copied' : 'Copy'}</button>
        </div>
      ) : (
        <button onClick={onGenerate} style={primary}><i data-lucide="link" style={{ width: 16, height: 16 }}></i>Generate share link</button>
      )}
      {url && onRevoke && <button onClick={onRevoke} style={{ alignSelf: 'flex-start', background: 'none', border: 'none', color: 'var(--danger)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer', padding: 0 }}>Revoke link</button>}
    </div>
  );
}
const primary = { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6, padding: '9px 16px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--primary)', color: 'var(--text-on-primary)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' };
