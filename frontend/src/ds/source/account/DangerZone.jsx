import React from 'react';

/** Destructive account action with typed-confirmation gate. */
export function DangerZone({ confirmWord = 'DELETE', onDelete, title = 'Delete account', description }) {
  const [val, setVal] = React.useState('');
  const armed = val === confirmWord;
  return (
    <div style={{ border: '1px solid var(--danger)', borderRadius: 'var(--radius-lg)', padding: 18, fontFamily: 'var(--font-sans)', background: 'var(--surface)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <i data-lucide="triangle-alert" style={{ width: 18, height: 18, color: 'var(--danger)' }}></i>
        <span style={{ fontSize: 'var(--text-h3)', fontWeight: 'var(--weight-bold)', color: 'var(--danger)' }}>{title}</span>
      </div>
      <p style={{ fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)', margin: '0 0 14px', lineHeight: 'var(--leading-body)' }}>
        {description || 'This permanently deletes your account and all encrypted academic data. This cannot be undone.'}
      </p>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <input value={val} onChange={(e) => setVal(e.target.value)} placeholder={`Type ${confirmWord} to confirm`} style={{
          flex: 1, minWidth: 200, padding: '9px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body)', outline: 'none', background: 'var(--surface)', color: 'var(--text)',
        }} />
        <button onClick={() => armed && onDelete && onDelete()} disabled={!armed} style={{
          padding: '9px 16px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--danger)', color: '#fff',
          fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: armed ? 'pointer' : 'not-allowed', opacity: armed ? 1 : 0.5,
        }}>Delete account</button>
      </div>
    </div>
  );
}
