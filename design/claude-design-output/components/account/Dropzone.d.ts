import React from 'react';
export interface DropzoneProps {
  label?: string;
  hint?: string;
  accept?: string;
  onFile?: (file: File) => void;
  /** 0–100 upload/parse progress. */
  progress?: number;
}
