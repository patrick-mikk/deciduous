import React from 'react';

export interface MeetingTime { day: 1|2|3|4|5|6|7; startMin: number; endMin: number; building?: string; }
export interface Section {
  name: string;
  teachMethod: 'LEC' | 'TUT' | 'PRA';
  currentEnrol: number;
  maxEnrol: number;
  waitlist?: number;
  instructors?: { first: string; last: string }[];
  meetingTimes?: MeetingTime[];
}
export interface SectionRowProps {
  section: Section;
  selected?: boolean;
  onSelect?: (section: Section) => void;
  selectable?: boolean;
}
export interface SectionListProps {
  sections: Section[];
  /** Selected section name per teach method, e.g. { LEC: 'LEC0101', TUT: 'TUT0101' }. */
  selected?: Record<string, string>;
  onSelect?: (method: string, name: string) => void;
}
