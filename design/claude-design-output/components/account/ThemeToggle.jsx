import React from 'react';

const OPTS = [
  { value: 'light', icon: 'sun', label: 'Light' },
  { value: 'dark', icon: 'moon', label: 'Dark' },
  { value: 'system', icon: 'monitor', label: 'System' },
];

/** Segmented light / dark / system control. */
export function ThemeToggle({ value = 'light', onChange, showLabels }) {
  return (
    <div style={{ display: 'inline-flex', gap: 2, padding: 3, background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-sans)' }}>
      {OPTS.map((o) => {
        const active = o.value === value;
        return (
          <button key={o.value} onClick={() => onChange && onChange(o.value)} aria-pressed={active} title={o.label} style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, padding: showLabels ? '6px 12px' : '6px 9px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer',
            background: active ? 'var(--surface)' : 'transparent', color: active ? 'var(--text)' : 'var(--text-tertiary)', boxShadow: active ? 'var(--shadow-e1)' : 'none',
            fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)',
          }}>
            <i data-lucide={o.icon} style={{ width: 16, height: 16 }}></i>{showLabels && o.label}
          </button>
        );
      })}
    </div>
  );
}
