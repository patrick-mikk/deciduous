import React from 'react';

/** Drag-drop file area with browse fallback + progress. */
export function Dropzone({ label = 'Drop your file here', hint, accept, onFile, progress }) {
  const [over, setOver] = React.useState(false);
  const inputRef = React.useRef(null);
  const pick = (files) => { if (files && files[0] && onFile) onFile(files[0]); };
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files); }}
      onClick={() => inputRef.current && inputRef.current.click()}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: '32px 24px', cursor: 'pointer', textAlign: 'center',
        border: `1.5px dashed ${over ? 'var(--accent)' : 'var(--border-strong)'}`, borderRadius: 'var(--radius-lg)',
        background: over ? 'var(--info-bg)' : 'var(--surface-sunken)', fontFamily: 'var(--font-sans)',
      }}
    >
      <i data-lucide="upload-cloud" style={{ width: 30, height: 30, color: 'var(--accent)' }}></i>
      <div style={{ fontSize: 'var(--text-body)', color: 'var(--text)', fontWeight: 'var(--weight-semibold)' }}>{label}</div>
      {hint && <div style={{ fontSize: 'var(--text-body-sm)', color: 'var(--text-tertiary)' }}>{hint}</div>}
      {progress != null && (
        <div style={{ width: '100%', height: 6, borderRadius: 'var(--radius-pill)', background: 'var(--surface-hover)', overflow: 'hidden', marginTop: 8 }}>
          <div style={{ width: `${progress}%`, height: '100%', background: 'var(--accent)', transition: 'width var(--duration-base) var(--ease-standard)' }}></div>
        </div>
      )}
      <input ref={inputRef} type="file" accept={accept} onChange={(e) => pick(e.target.files)} style={{ display: 'none' }} />
    </div>
  );
}
