import React from 'react';
export interface RequirementMapping {
  programCode: string;
  programName: string;
  group: string;
  breadth?: 'BR1' | 'BR2' | 'BR3' | 'BR4' | 'BR5';
}
export interface RequirementMappingListProps {
  mappings: RequirementMapping[];
}
