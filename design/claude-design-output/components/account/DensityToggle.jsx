import React from 'react';

/** Segmented comfortable / compact density control. */
export function DensityToggle({ value = 'comfortable', onChange }) {
  const opts = [{ value: 'comfortable', label: 'Comfortable' }, { value: 'compact', label: 'Compact' }];
  return (
    <div style={{ display: 'inline-flex', gap: 2, padding: 3, background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-sans)' }}>
      {opts.map((o) => {
        const active = o.value === value;
        return (
          <button key={o.value} onClick={() => onChange && onChange(o.value)} aria-pressed={active} style={{
            padding: '6px 14px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer',
            background: active ? 'var(--surface)' : 'transparent', color: active ? 'var(--text)' : 'var(--text-tertiary)', boxShadow: active ? 'var(--shadow-e1)' : 'none',
            fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)',
          }}>{o.label}</button>
        );
      })}
    </div>
  );
}
