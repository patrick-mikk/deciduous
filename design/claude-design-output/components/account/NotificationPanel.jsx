import React from 'react';

const KIND = {
  deadline: { icon: 'calendar-clock', color: 'var(--info)' },
  prereq: { icon: 'triangle-alert', color: 'var(--danger)' },
  seat: { icon: 'circle-check', color: 'var(--success)' },
  info: { icon: 'info', color: 'var(--text-tertiary)' },
};

/** Notification list with read state. `items`: [{ id, kind, title, time, read }]. */
export function NotificationPanel({ items = [], onMarkRead, onMarkAllRead }) {
  const unread = items.filter((i) => !i.read).length;
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', fontFamily: 'var(--font-sans)', width: 320 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
        <span style={{ fontWeight: 'var(--weight-bold)', color: 'var(--text)' }}>Notifications{unread > 0 ? ` (${unread})` : ''}</span>
        {unread > 0 && onMarkAllRead && <button onClick={onMarkAllRead} style={{ background: 'none', border: 'none', color: 'var(--accent)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' }}>Mark all read</button>}
      </div>
      <div style={{ maxHeight: 360, overflowY: 'auto' }}>
        {items.map((n) => {
          const k = KIND[n.kind] || KIND.info;
          return (
            <div key={n.id} onClick={() => onMarkRead && onMarkRead(n.id)} style={{
              display: 'flex', gap: 10, padding: '12px 14px', borderBottom: '1px solid var(--border)', cursor: 'pointer',
              background: n.read ? 'var(--surface)' : 'var(--info-bg)',
            }}>
              <i data-lucide={k.icon} style={{ width: 17, height: 17, color: k.color, flexShrink: 0, marginTop: 1 }}></i>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 'var(--text-body-sm)', color: 'var(--text)', fontWeight: n.read ? 'var(--weight-regular)' : 'var(--weight-semibold)' }}>{n.title}</div>
                {n.time && <div style={{ fontSize: 'var(--text-caption)', color: 'var(--text-tertiary)', marginTop: 2 }}>{n.time}</div>}
              </div>
              {!n.read && <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)', flexShrink: 0, marginTop: 4 }}></span>}
            </div>
          );
        })}
        {items.length === 0 && <div style={{ padding: 28, textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 'var(--text-body-sm)' }}>You're all caught up.</div>}
      </div>
    </div>
  );
}
