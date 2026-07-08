import React from 'react';
export interface ThemeToggleProps {
  value?: 'light' | 'dark' | 'system';
  onChange?: (value: 'light' | 'dark' | 'system') => void;
  showLabels?: boolean;
}
