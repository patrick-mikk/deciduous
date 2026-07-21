import React from 'react';

export interface CourseCardProps {
  /** e.g. "POL208H1" */
  code: string;
  title: string;
  /** number (FCE, e.g. 0.5) or preformatted string. */
  credit?: number | string;
  /** Breadth categories, e.g. ["BR3"]. */
  breadth?: ('BR1' | 'BR2' | 'BR3' | 'BR4' | 'BR5')[];
  /** Plain-language "Counts toward X" line (e.g. "Economics and Public Policy"). */
  countsToward?: string;
  /** Term availability dots. */
  fall?: boolean;
  winter?: boolean;
  status?: 'completed' | 'planned' | 'available' | 'blocked' | 'not-offered' | 'open' | 'waitlist' | 'full' | 'conflict';
  seats?: { current: number; max: number };
  /** Legacy inline meeting info (optional). */
  meetTime?: string;
  location?: string;
  instructor?: string;
  onAdd?: () => void;
  onDetails?: () => void;
  /** Dense single-row variant for lists. */
  compact?: boolean;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent) => void;
}
