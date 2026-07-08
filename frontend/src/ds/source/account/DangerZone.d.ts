import React from 'react';
export interface DangerZoneProps {
  /** Word the user must type to arm the action. Default "DELETE". */
  confirmWord?: string;
  onDelete?: () => void;
  title?: string;
  description?: string;
}
