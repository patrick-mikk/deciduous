import React from 'react';
import { Chip } from '../feedback/Chip.jsx';

// status → {icon, color, label}. Supports spec + legacy planner values.
const STATUS = {
  completed:     { icon: 'check', color: 'var(--success)', label: 'Completed' },
  planned:       { icon: 'circle-dot', color: 'var(--accent)', label: 'Planned' },
  available:     { icon: 'circle', color: 'var(--text-tertiary)', label: 'Available' },
  blocked:       { icon: 'triangle-alert', color: 'var(--danger)', label: 'Prereq unmet' },
  'not-offered': { icon: 'clock', color: 'var(--warning)', label: 'Not offered' },
  // legacy
  open:     { icon: 'circle', color: 'var(--text-tertiary)', label: 'Open' },
  waitlist: { icon: 'clock', color: 'var(--warning)', label: 'Waitlisted' },
  full:     { icon: 'triangle-alert', color: 'var(--danger)', label: 'Full' },
  conflict: { icon: 'triangle-alert', color: 'var(--danger)', label: 'Conflict' },
};

const BR_LABEL = { BR1: 'Creative', BR2: 'Thought', BR3: 'Society', BR4: 'Living Things', BR5: 'Physical' };

function fmtCredit(c) {
  if (c == null) return null;
  return typeof c === 'number' ? `${c.toFixed(1)} FCE` : c;
}

/** Course/section card. Row `compact` variant for lists. Composes Chip. */
export function CourseCard({
  code, title, credit, breadth = [], fall, winter, status, seats,
  meetTime, location, instructor, onAdd, onDetails, compact = false, draggable, onDragStart,
}) {
  const st = status && STATUS[status];

  const AvailabilityDots = () => (
    (fall != null || winter != null) ? (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 'var(--text-caption)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-sans)' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: fall ? 'var(--leaf-amber)' : 'transparent', border: fall ? 'none' : '1px solid var(--border-strong)' }}></span>Fall
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: winter ? 'var(--br3)' : 'transparent', border: winter ? 'none' : '1px solid var(--border-strong)' }}></span>Winter
        </span>
      </span>
    ) : null
  );

  const codeEl = <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-code)', fontWeight: 'var(--weight-medium)', color: 'var(--accent)', letterSpacing: 'var(--tracking-code)' }}>{code}</span>;
  const creditEl = credit != null && <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-body-sm)', color: 'var(--text-tertiary)', fontVariantNumeric: 'tabular-nums' }}>{fmtCredit(credit)}</span>;

  if (compact) {
    return (
      <div draggable={draggable} onDragStart={onDragStart} style={{
        display: 'flex', alignItems: 'center', gap: 14, padding: '12px 16px', background: 'var(--surface)',
        border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-sans)', cursor: draggable ? 'grab' : 'default',
      }}>
        {draggable && <i data-lucide="grip-vertical" style={{ width: 16, height: 16, color: 'var(--text-tertiary)', flexShrink: 0 }}></i>}
        <div style={{ minWidth: 96 }}>{codeEl}</div>
        <div style={{ flex: 1, minWidth: 0, fontSize: 'var(--text-body)', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</div>
        {breadth.map((b) => <Chip key={b} breadth={b} dot>{b}</Chip>)}
        {creditEl}
        {st && <i data-lucide={st.icon} title={st.label} style={{ width: 16, height: 16, color: st.color }}></i>}
        {onAdd && <button onClick={onAdd} aria-label="Add" style={ghostIcon}><i data-lucide="plus" style={{ width: 16, height: 16 }}></i></button>}
        {onDetails && <button onClick={onDetails} aria-label="Details" style={ghostIcon}><i data-lucide="chevron-right" style={{ width: 16, height: 16 }}></i></button>}
      </div>
    );
  }

  return (
    <div draggable={draggable} onDragStart={onDragStart} style={{
      background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--shadow-e1)', padding: 16, fontFamily: 'var(--font-sans)', cursor: draggable ? 'grab' : 'default',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          {codeEl}
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--text-h3)', fontWeight: 'var(--weight-semibold)', color: 'var(--text)', marginTop: 2, lineHeight: 'var(--leading-heading)' }}>{title}</div>
        </div>
        {st && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: st.color, fontSize: 'var(--text-body-sm)', flexShrink: 0 }}>
            <i data-lucide={st.icon} style={{ width: 15, height: 15 }}></i>{st.label}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 10 }}>
        {creditEl}
        {breadth.map((b) => <Chip key={b} breadth={b} dot>{BR_LABEL[b] || b}</Chip>)}
        <AvailabilityDots />
      </div>

      {(meetTime || location || instructor) && (
        <div style={{ display: 'flex', gap: 14, marginTop: 8, fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', flexWrap: 'wrap' }}>
          {meetTime && <span>{meetTime}</span>}{location && <span>{location}</span>}{instructor && <span style={{ fontFamily: 'var(--font-sans)' }}>{instructor}</span>}
        </div>
      )}

      {(onAdd || onDetails) && (
        <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
          {onAdd && <button onClick={onAdd} style={btnPrimary}><i data-lucide="plus" style={{ width: 15, height: 15 }}></i>Add to plan</button>}
          {onDetails && <button onClick={onDetails} style={btnGhost}>Details</button>}
        </div>
      )}
    </div>
  );
}

const ghostIcon = { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 30, height: 30, borderRadius: 'var(--radius-sm)', border: 'none', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', flexShrink: 0 };
const btnPrimary = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--primary)', color: 'var(--text-on-primary)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' };
const btnGhost = { padding: '7px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-strong)', background: 'transparent', color: 'var(--text)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' };
