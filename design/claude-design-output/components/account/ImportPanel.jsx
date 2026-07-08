import React from 'react';
import { Tabs } from '../navigation/Tabs.jsx';
import { Dropzone } from './Dropzone.jsx';

/** Onboarding import: Upload PDF / Bookmarklet / Manual tabs; shows preview when provided. */
export function ImportPanel({ tab = 'pdf', onTab, onFile, progress, bookmarkletValue, onBookmarkletChange, preview }) {
  return (
    <div style={{ fontFamily: 'var(--font-sans)', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Tabs tabs={[{ label: 'Upload PDF', value: 'pdf' }, { label: 'Bookmarklet', value: 'bookmarklet' }, { label: 'Start blank', value: 'manual' }]} active={tab} onChange={onTab} />

      {tab === 'pdf' && <Dropzone label="Drop your Degree Explorer PDF here" hint="or click to browse · parsed locally & encrypted" accept="application/pdf" onFile={onFile} progress={progress} />}

      {tab === 'bookmarklet' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ol style={{ margin: 0, paddingLeft: 20, fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)', lineHeight: 'var(--leading-body)' }}>
            <li>Drag the bookmarklet to your bookmarks bar.</li>
            <li>Open Degree Explorer and click it.</li>
            <li>Paste the copied capture below.</li>
          </ol>
          <textarea value={bookmarkletValue} onChange={(e) => onBookmarkletChange && onBookmarkletChange(e.target.value)} rows={4}
            placeholder="<degree-explorer-capture>…</degree-explorer-capture>" style={{
              width: '100%', boxSizing: 'border-box', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
              fontFamily: 'var(--font-mono)', fontSize: 'var(--text-body-sm)', resize: 'vertical', outline: 'none', background: 'var(--surface)', color: 'var(--text)',
            }} />
        </div>
      )}

      {tab === 'manual' && (
        <div style={{ padding: '20px', background: 'var(--surface-sunken)', borderRadius: 'var(--radius-lg)', fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)', textAlign: 'center' }}>
          Start with an empty record — add programs and courses by hand.
        </div>
      )}

      {preview}
    </div>
  );
}

/** Detected-programs + transcript-diff preview shown before applying an import. */
export function ImportPreview({ programs = [], courseCount, cgpa, onConfirm }) {
  return (
    <div style={{ background: 'var(--surface-sunken)', borderRadius: 'var(--radius-lg)', padding: 16, fontFamily: 'var(--font-sans)' }}>
      <div style={{ fontSize: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-tertiary)', marginBottom: 10 }}>Detected</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {programs.map((p, i) => (
          <span key={i} style={{ padding: '4px 10px', borderRadius: 'var(--radius-pill)', background: 'var(--primary-bg)', color: 'var(--primary)', fontSize: 'var(--text-body-sm)', fontWeight: 'var(--weight-semibold)' }}>{p}</span>
        ))}
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)' }}>
        {courseCount} courses{cgpa != null ? ` · CGPA ${cgpa.toFixed(2)}` : ''}
      </div>
      {onConfirm && (
        <button onClick={onConfirm} style={{ marginTop: 14, padding: '9px 16px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--primary)', color: 'var(--text-on-primary)', fontFamily: 'var(--font-sans)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' }}>Looks right → Next</button>
      )}
    </div>
  );
}
