import React from 'react';
import { Card } from '../common/Card';
import { Input } from '../common/Input';
import { Button } from '../common/Button';
import {
  Search,
  LayoutGrid,
  List,
  Sparkles,
  GitMerge,
  Filter,
} from 'lucide-react';

interface JobFilterBarProps {
  search: string;
  onSearchChange: (search: string) => void;
  workMode: string;
  onWorkModeChange: (mode: string) => void;
  includeDuplicates: boolean;
  onIncludeDuplicatesChange: (include: boolean) => void;
  viewMode: 'grid' | 'table';
  onViewModeChange: (mode: 'grid' | 'table') => void;
  onExtractAll: () => void;
  isExtracting: boolean;
  onDeduplicate: () => void;
  isDeduplicating: boolean;
  hideApplied?: boolean;
  onHideAppliedChange?: (hide: boolean) => void;
  sortByMatch?: boolean;
  onSortByMatchChange?: (sortByMatch: boolean) => void;
}

const WORK_MODES = [
  { id: 'ALL', label: 'All Modes' },
  { id: 'REMOTE', label: 'Remote' },
  { id: 'HYBRID', label: 'Hybrid' },
  { id: 'ON_SITE', label: 'On-Site' },
];

export const JobFilterBar: React.FC<JobFilterBarProps> = ({
  search,
  onSearchChange,
  workMode,
  onWorkModeChange,
  includeDuplicates,
  onIncludeDuplicatesChange,
  viewMode,
  onViewModeChange,
  onExtractAll,
  isExtracting,
  onDeduplicate,
  isDeduplicating,
  hideApplied,
  onHideAppliedChange,
  sortByMatch,
  onSortByMatchChange,
}) => {
  return (
    <Card style={{ padding: '18px 20px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Main Search & Pipeline Action Buttons */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ flex: 1, minWidth: '260px' }}>
            <Input
              placeholder="Search by role title, hiring company, or keywords..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              leftIcon={<Search size={16} />}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Button
              variant="outline"
              size="md"
              isLoading={isDeduplicating}
              leftIcon={<GitMerge size={15} />}
              onClick={onDeduplicate}
              title="Detect and cluster cross-platform duplicate job postings"
            >
              Sweep Duplicates
            </Button>

            <Button
              variant="primary"
              size="md"
              isLoading={isExtracting}
              leftIcon={<Sparkles size={15} />}
              onClick={onExtractAll}
              title="Parse structured jobs from all classified job emails"
            >
              Extract All Jobs
            </Button>
          </div>
        </div>

        {/* Filter Pills, Duplicate Toggle, and View Mode Switcher */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            paddingTop: '6px',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          {/* Work Mode Filters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '12.5px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Filter size={13} /> Work Mode:
            </span>
            {WORK_MODES.map((mode) => (
              <button
                key={mode.id}
                type="button"
                onClick={() => onWorkModeChange(mode.id)}
                style={{
                  padding: '5px 12px',
                  borderRadius: '20px',
                  fontSize: '12.5px',
                  fontWeight: workMode === mode.id ? 600 : 400,
                  border:
                    workMode === mode.id
                      ? '1px solid var(--accent-primary)'
                      : '1px solid var(--border-subtle)',
                  backgroundColor:
                    workMode === mode.id
                      ? 'rgba(99, 102, 241, 0.15)'
                      : 'var(--bg-card)',
                  color:
                    workMode === mode.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {mode.label}
              </button>
            ))}
          </div>

          {/* Right Controls: Filter Toggles, Duplicate Checkbox and View Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            {onHideAppliedChange && (
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12.5px',
                  color: hideApplied ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  fontWeight: hideApplied ? 600 : 400,
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
                title="Hide jobs you have already applied to"
              >
                <input
                  type="checkbox"
                  checked={!!hideApplied}
                  onChange={(e) => onHideAppliedChange(e.target.checked)}
                  style={{ accentColor: 'var(--accent-primary)', width: '15px', height: '15px', cursor: 'pointer' }}
                />
                Hide Applied
              </label>
            )}

            {onSortByMatchChange && (
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12.5px',
                  color: sortByMatch ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  fontWeight: sortByMatch ? 600 : 400,
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
                title="Sort jobs with highest resume match score first"
              >
                <input
                  type="checkbox"
                  checked={!!sortByMatch}
                  onChange={(e) => onSortByMatchChange(e.target.checked)}
                  style={{ accentColor: 'var(--accent-primary)', width: '15px', height: '15px', cursor: 'pointer' }}
                />
                Sort by Match %
              </label>
            )}

            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '12.5px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              <input
                type="checkbox"
                checked={includeDuplicates}
                onChange={(e) => onIncludeDuplicatesChange(e.target.checked)}
                style={{ accentColor: 'var(--accent-primary)', width: '15px', height: '15px', cursor: 'pointer' }}
              />
              Include Duplicates
            </label>

            {/* Layout Toggle (Grid vs Table) */}
            <div
              style={{
                display: 'flex',
                backgroundColor: 'var(--bg-input)',
                padding: '3px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <button
                type="button"
                onClick={() => onViewModeChange('grid')}
                title="Grid View"
                style={{
                  background: viewMode === 'grid' ? 'var(--accent-primary)' : 'transparent',
                  border: 'none',
                  color: viewMode === 'grid' ? '#fff' : 'var(--text-muted)',
                  padding: '5px 8px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <LayoutGrid size={15} />
              </button>
              <button
                type="button"
                onClick={() => onViewModeChange('table')}
                title="Table View"
                style={{
                  background: viewMode === 'table' ? 'var(--accent-primary)' : 'transparent',
                  border: 'none',
                  color: viewMode === 'table' ? '#fff' : 'var(--text-muted)',
                  padding: '5px 8px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <List size={15} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
