import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  /** CSS padding value. Default 'var(--space-5)'. */
  padding?: string;
  style?: React.CSSProperties;
}
