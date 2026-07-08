import React from 'react';
import { PrereqNode } from './PrereqTree';
import { Section } from './SectionList';
import { RequirementMapping } from './RequirementMappingList';

export interface CourseDetail {
  code: string;
  title: string;
  credit?: number | string;
  campus?: string;
  description?: string;
  breadth?: ('BR1' | 'BR2' | 'BR3' | 'BR4' | 'BR5')[];
  prereqTree?: PrereqNode;
  exclusions?: string;
  hours?: string;
  sections?: Section[];
  satisfies?: RequirementMapping[];
}
export interface CourseDetailPanelProps {
  course: CourseDetail;
  /** Selected section name per teach method. */
  selectedSections?: Record<string, string>;
  onSelectSection?: (method: string, name: string) => void;
  onAddPlan?: () => void;
  onAddTimetable?: () => void;
}
