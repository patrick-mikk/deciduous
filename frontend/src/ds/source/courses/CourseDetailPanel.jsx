import React from 'react';
import { Tabs } from '../navigation/Tabs.jsx';
import { Chip } from '../feedback/Chip.jsx';
import { SectionList } from './SectionList.jsx';
import { PrereqTree } from './PrereqTree.jsx';
import { RequirementMappingList } from './RequirementMappingList.jsx';

const BR_LABEL = { BR1: 'Creative & Cultural', BR2: 'Thought & Belief', BR3: 'Society & Institutions', BR4: 'Living Things', BR5: 'Physical & Math' };

/** Full course detail: header + Overview / Sections / Satisfies tabs + footer actions. */
export function CourseDetailPanel({ course, selectedSections = {}, onSelectSection, onAddPlan, onAddTimetable }) {
  const [tab, setTab] = React.useState('overview');
  if (!course) return null;
  const c = course;

  return (
    <div style={{ fontFamily: 'var(--font-sans)', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-code)', color: 'var(--accent)', letterSpacing: 'var(--tracking-code)' }}>{c.code}</span>
        <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--text-serif-title)', fontWeight: 'var(--weight-semibold)', color: 'var(--text)', margin: '4px 0 6px', lineHeight: 'var(--leading-heading)' }}>{c.title}</h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', fontSize: 'var(--text-body-sm)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', flexWrap: 'wrap' }}>
          <span>{typeof c.credit === 'number' ? c.credit.toFixed(1) + ' FCE' : c.credit}</span>
          {c.campus && <span>{c.campus}</span>}
          {(c.breadth || []).map((b) => <Chip key={b} breadth={b} dot>{BR_LABEL[b] || b}</Chip>)}
        </div>
      </div>

      <Tabs tabs={[{ label: 'Overview', value: 'overview' }, { label: `Sections${c.sections ? ` (${c.sections.length})` : ''}`, value: 'sections' }, { label: 'Satisfies', value: 'satisfies' }]} active={tab} onChange={setTab} />

      {tab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {c.description && <p style={{ fontFamily: 'var(--font-serif)', fontSize: 'var(--text-body-lg)', lineHeight: 'var(--leading-serif)', color: 'var(--text)', margin: 0 }}>{c.description}</p>}
          {c.prereqTree && (
            <div>
              <div style={sectionLabel}>Prerequisites</div>
              <PrereqTree node={c.prereqTree} />
            </div>
          )}
          {c.exclusions && <div><div style={sectionLabel}>Exclusions</div><div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)' }}>{c.exclusions}</div></div>}
          {c.hours && <div><div style={sectionLabel}>Hours</div><div style={{ fontSize: 'var(--text-body-sm)', color: 'var(--text-secondary)' }}>{c.hours}</div></div>}
        </div>
      )}

      {tab === 'sections' && (
        c.sections && c.sections.length
          ? <SectionList sections={c.sections} selected={selectedSections} onSelect={onSelectSection} />
          : <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-body-sm)' }}>No live sections for the selected term.</div>
      )}

      {tab === 'satisfies' && <RequirementMappingList mappings={c.satisfies || []} />}

      {(onAddPlan || onAddTimetable) && (
        <div style={{ display: 'flex', gap: 10, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
          {onAddPlan && <button onClick={onAddPlan} style={footerPrimary}><i data-lucide="plus" style={{ width: 16, height: 16 }}></i>Add to plan</button>}
          {onAddTimetable && <button onClick={onAddTimetable} style={footerGhost}><i data-lucide="calendar-plus" style={{ width: 16, height: 16 }}></i>Add to timetable</button>}
        </div>
      )}
    </div>
  );
}

const sectionLabel = { fontSize: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-label)', color: 'var(--text-tertiary)', marginBottom: 8 };
const footerPrimary = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '9px 16px', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--primary)', color: 'var(--text-on-primary)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' };
const footerGhost = { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '9px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-strong)', background: 'transparent', color: 'var(--text)', fontFamily: 'var(--font-sans)', fontSize: 'var(--text-body)', fontWeight: 'var(--weight-semibold)', cursor: 'pointer' };
