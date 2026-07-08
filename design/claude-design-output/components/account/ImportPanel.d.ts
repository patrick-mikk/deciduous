import React from 'react';
export interface ImportPanelProps {
  tab?: 'pdf' | 'bookmarklet' | 'manual';
  onTab?: (tab: string) => void;
  onFile?: (file: File) => void;
  progress?: number;
  bookmarkletValue?: string;
  onBookmarkletChange?: (v: string) => void;
  /** The ImportPreview node (shown after parsing). */
  preview?: React.ReactNode;
}
export interface ImportPreviewProps {
  programs?: string[];
  courseCount?: number;
  cgpa?: number;
  onConfirm?: () => void;
}
