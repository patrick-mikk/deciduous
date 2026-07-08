import React from 'react';
import { Chip } from '../feedback/Chip.jsx';

/**
 * For a course, the requirement groups (across enrolled programs) it can satisfy.
 * `mappings`: [{ programCode, programName, group, breadth? }].
 */
export function RequirementMappingList({ mappings = [] }) {
  if (!mappings.length) {
    return <div style={{ fontFamily: 'var(--font-sans)', color: 'var(--text-tertiary)', fontSize: 'var(--text-body-sm)' }}>Doesn't map to a requirement in your enrolled programs.</div>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontFamily: 'var(--font-sans)' }}>
      {mappings.map((m, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)' }}>
          <i data-lucide="git-branch" style={{ width: 16, height: 16, color: 'var(--text-tertiary)', flexShrink: 0 }}></i>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 'var(--text-body)', color: 'var(--text)' }}>{m.programName}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-caption)', color: 'var(--text-tertiary)' }}>{m.programCode}</div>
          </div>
          {m.breadth ? <Chip breadth={m.breadth} dot>{m.group}</Chip> : <Chip tone="info">{m.group}</Chip>}
        </div>
      ))}
    </div>
  );
}
