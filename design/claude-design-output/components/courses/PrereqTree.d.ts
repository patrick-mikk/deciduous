import React from 'react';

export type PrereqNode =
  | { type: 'course'; code: string; credits?: number; met?: boolean | 'blocking' }
  | { type: 'credits'; text: string; met?: boolean | 'blocking' }
  | { type: 'group'; op: 'AND' | 'OR'; children: PrereqNode[]; met?: boolean | 'blocking' };

export interface PrereqTreeProps {
  node: PrereqNode;
  depth?: number;
}
