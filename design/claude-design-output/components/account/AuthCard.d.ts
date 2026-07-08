import React from 'react';
export interface AuthCardProps {
  title: string;
  subtitle?: string;
  /** Form fields + submit button. */
  children: React.ReactNode;
  /** Alt-action line (e.g. "New here? Create an account"). */
  footer?: React.ReactNode;
  width?: number;
}
