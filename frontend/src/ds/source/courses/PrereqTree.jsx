import React from 'react';

/**
 * Visualizes prerequisite boolean logic. A node is either:
 *  { type:'course', code, credits?, met? }, { type:'credits', text, met? }, or
 *  { type:'group', op:'AND'|'OR', children:[…], met? }.
 * met true = success, false = tertiary (unmet), 'blocking' = danger.
 */
export function PrereqTree({ node, depth = 0 }) {
  if (!node) return null;

  if (node.type === 'group') {
    return (
      <div style={{ fontFamily: 'var(--font-sans)', borderLeft: depth ? '2px solid var(--border)' : 'none', paddingLeft: depth ? 14 : 0 }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-tertiary)', marginBottom: 8 }}>
          <span style={{
            padding: '1px 8px', borderRadius: 'var(--radius-pill)', background: 'var(--surface-sunken)',
            color: node.op === 'AND' ? 'var(--primary)' : 'var(--accent)', fontWeight: 'var(--weight-bold)',
          }}>{node.op === 'AND' ? 'All of' : 'One of'}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {node.children.map((c, i) => <PrereqTree key={i} node={c} depth={depth + 1} />)}
        </div>
      </div>
    );
  }

  const met = node.met;
  const color = met === true ? 'var(--success)' : met === 'blocking' ? 'var(--danger)' : 'var(--text-tertiary)';
  const icon = met === true ? 'check' : met === 'blocking' ? 'triangle-alert' : 'circle';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--font-sans)' }}>
      <i data-lucide={icon} style={{ width: 15, height: 15, color, flexShrink: 0 }}></i>
      {node.type === 'course'
        ? <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-code)', color: 'var(--text)' }}>{node.code}{node.credits ? ` (${node.credits})` : ''}</span>
        : <span style={{ fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)' }}>{node.text}</span>}
    </div>
  );
}
