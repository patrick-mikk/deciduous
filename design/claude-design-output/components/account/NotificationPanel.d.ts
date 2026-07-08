import React from 'react';
export interface NotificationItem {
  id: string;
  kind: 'deadline' | 'prereq' | 'seat' | 'info';
  title: string;
  time?: string;
  read?: boolean;
}
export interface NotificationPanelProps {
  items: NotificationItem[];
  onMarkRead?: (id: string) => void;
  onMarkAllRead?: () => void;
}
