import React from 'react';
export interface DensityToggleProps {
  value?: 'comfortable' | 'compact';
  onChange?: (value: 'comfortable' | 'compact') => void;
}
