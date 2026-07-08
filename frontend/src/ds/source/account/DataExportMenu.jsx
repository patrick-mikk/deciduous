import React from 'react';
import { DropdownMenu } from '../overlay/DropdownMenu.jsx';

/** Export menu: CSV / JSON / plan PDF / ICS. */
export function DataExportMenu({ onExport }) {
  return (
    <DropdownMenu
      align="right"
      trigger={
        <button style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '9px 15px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-strong)', background: 'var(--surface)', color: 'var(--text)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' }}>
          <i data-lucide="download" style={{ width: 16, height: 16 }}></i>Export<i data-lucide="chevron-down" style={{ width: 15, height: 15 }}></i>
        </button>
      }
      items={[
        { label: 'Courses (CSV)', icon: 'table', onClick: () => onExport && onExport('csv') },
        { label: 'Full record (JSON)', icon: 'braces', onClick: () => onExport && onExport('json') },
        { label: 'Degree plan (PDF)', icon: 'file-text', onClick: () => onExport && onExport('pdf') },
        { label: 'Timetable (ICS)', icon: 'calendar', onClick: () => onExport && onExport('ics') },
      ]}
    />
  );
}
