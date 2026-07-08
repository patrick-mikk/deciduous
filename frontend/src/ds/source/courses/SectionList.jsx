import React from 'react';
import { SeatMeter } from './SeatMeter.jsx';

const METHOD = { LEC: 'var(--primary)', TUT: 'var(--accent)', PRA: 'var(--br4)' };

function fmtMin(m) {
  const h = Math.floor(m / 60), mm = String(m % 60).padStart(2, '0');
  return `${String(h).padStart(2, '0')}:${mm}`;
}
const DAYS = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

/** One selectable section row. */
export function SectionRow({ section, selected, onSelect, selectable = true }) {
  const s = section;
  return (
    <div onClick={() => selectable && onSelect && onSelect(s)} style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', fontFamily: 'var(--font-sans)',
      borderRadius: 'var(--radius-md)', cursor: selectable ? 'pointer' : 'default',
      border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
      background: selected ? 'var(--info-bg)' : 'var(--surface)',
    }}>
      {selectable && (
        <span style={{
          width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
          border: `1px solid ${selected ? 'var(--accent)' : 'var(--border-strong)'}`,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {selected && <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'var(--accent)' }}></span>}
        </span>
      )}
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-code)', color: 'var(--text)', minWidth: 68 }}>{s.name}</span>
      <span style={{
        fontSize: 11, fontWeight: 'var(--weight-bold)', color: '#fff', background: METHOD[s.teachMethod] || 'var(--text-tertiary)',
        borderRadius: 'var(--radius-sm)', padding: '2px 6px', letterSpacing: '.03em',
      }}>{s.teachMethod}</span>
      <span style={{ flex: 1, minWidth: 120, fontFamily: 'var(--font-mono)', fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)' }}>
        {(s.meetingTimes || []).map((m, i) => `${DAYS[m.day]} ${fmtMin(m.startMin)}–${fmtMin(m.endMin)}`).join(' · ') || 'TBA'}
      </span>
      <span style={{ fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)', minWidth: 90 }}>
        {(s.instructors || []).map((i) => i.last).join(', ') || '—'}
      </span>
      <SeatMeter current={s.currentEnrol} max={s.maxEnrol} waitlist={s.waitlist} />
    </div>
  );
}

/** List of sections grouped by teach method; one selection per method. */
export function SectionList({ sections = [], selected = {}, onSelect }) {
  const groups = {};
  sections.forEach((s) => { (groups[s.teachMethod] = groups[s.teachMethod] || []).push(s); });
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, fontFamily: 'var(--font-sans)' }}>
      {Object.entries(groups).map(([method, secs]) => (
        <div key={method}>
          <div style={{ fontSize: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-tertiary)', marginBottom: 8 }}>
            {method === 'LEC' ? 'Lecture' : method === 'TUT' ? 'Tutorial' : 'Practical'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {secs.map((s) => (
              <SectionRow key={s.name} section={s} selected={selected[method] === s.name} onSelect={() => onSelect && onSelect(method, s.name)} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
