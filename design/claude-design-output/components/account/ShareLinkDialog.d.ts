import React from 'react';
export interface ShareLinkDialogProps {
  /** The share URL once generated; empty shows the Generate button. */
  url?: string;
  onGenerate?: () => void;
  onRevoke?: () => void;
  sharedItems?: string[];
}
