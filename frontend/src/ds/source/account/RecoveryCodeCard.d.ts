import React from 'react';
export interface RecoveryCodeCardProps {
  code: string;
  onCopy?: () => void;
  onRegenerate?: () => void;
}
