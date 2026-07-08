import React from 'react';
export interface DataExportMenuProps {
  onExport?: (format: 'csv' | 'json' | 'pdf' | 'ics') => void;
}
