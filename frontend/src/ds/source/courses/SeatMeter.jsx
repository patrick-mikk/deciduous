import React from 'react';

/** Mini seat bar: "current/max". Full → danger, near-full (≥90%) → warning. */
export function SeatMeter({ current = 0, max = 0, waitlist }) {
  const pct = max ? Math.min(100, (current / max) * 100) : 0;
  const color = current >= max ? 'var(--danger)' : pct >= 90 ? 'var(--warning)' : 'var(--success)';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontFamily: 'var(--font-sans)' }}>
      <span style={{ width: 56, height: 6, borderRadius: 'var(--radius-pill)', background: 'var(--surface-sunken)', overflow: 'hidden' }}>
        <span style={{ display: 'block', width: `${pct}%`, height: '100%', background: color }}></span>
      </span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
        {current}/{max}
      </span>
      {waitlist > 0 && (
        <span style={{ fontSize: 'var(--text-caption)', color: 'var(--warning)', fontWeight: 'var(--weight-semibold)' }}>+{waitlist} wl</span>
      )}
    </span>
  );
}
