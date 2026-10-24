import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import type { Job } from './JobDetailModal';
import {
  MapPin,
  Building,
  DollarSign,
  Briefcase,
  ExternalLink,
  Eye,
  Sparkles,
} from 'lucide-react';
import { getApplicationStatusConfig } from './statusUtils';

export interface JobCardProps {
  job: Job;
  onInspect: (job: Job) => void;
  applicationStatus?: string;
  matchScore?: number;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  onInspect,
  applicationStatus,
  matchScore,
}) => {
  const initial = job.company_name ? job.company_name.charAt(0).toUpperCase() : '?';
  const appStatusConfig = getApplicationStatusConfig(applicationStatus);

  const formatSalary = () => {
    if (!job.salary_min && !job.salary_max) return null;
    const curr = job.salary_currency || '$';
    if (job.salary_min && job.salary_max) {
      return `${curr}${Math.round(job.salary_min / 1000)}k - ${curr}${Math.round(job.salary_max / 1000)}k`;
    }
    if (job.salary_min) return `From ${curr}${Math.round(job.salary_min / 1000)}k`;
    return `Up to ${curr}${Math.round((job.salary_max || 0) / 1000)}k`;
  };

  const getWorkModeVariant = (mode: string): 'primary' | 'danger' | 'success' | 'warning' | 'info' | 'neutral' => {
    const m = mode.toUpperCase();
    if (m === 'REMOTE') return 'success';
    if (m === 'HYBRID') return 'primary';
    if (m === 'ON_SITE') return 'warning';
    return 'neutral';
  };

  return (
    <Card
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100%',
        transition: 'transform var(--transition-fast), border-color var(--transition-fast)',
        cursor: 'pointer',
      }}
      onClick={() => onInspect(job)}
    >
      <div>
        {/* Top Badges: Work Mode, Source, Match Score, Live Status & Duplicate */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '14px',
            flexWrap: 'wrap',
            gap: '6px',
          }}
        >
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
            <Badge variant={getWorkModeVariant(job.work_mode)}>{job.work_mode}</Badge>
            <Badge variant="info">{job.platform_source}</Badge>
            {typeof matchScore === 'number' && matchScore > 0 ? (
              <Badge score={matchScore} style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                <Sparkles size={11} /> {Math.round(matchScore)}% match
              </Badge>
            ) : (
              <Badge variant="neutral">Not scored</Badge>
            )}
          </div>
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            {appStatusConfig && (
              <Badge variant={appStatusConfig.variant} title={`Pipeline Stage: ${appStatusConfig.label}`}>
                {appStatusConfig.label}
              </Badge>
            )}
            {job.is_duplicate && (
              <Badge variant="warning">Duplicate</Badge>
            )}
          </div>
        </div>

        {/* Company Avatar & Title */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', marginBottom: '12px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              color: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '17px',
              flexShrink: 0,
            }}
          >
            {initial}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <h3
              style={{
                fontSize: '16px',
                fontWeight: 600,
                margin: '0 0 4px 0',
                color: 'var(--text-primary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={job.title}
            >
              {job.title}
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <Building size={13} color="var(--text-muted)" />
              <span style={{ fontWeight: 500 }}>{job.company_name}</span>
            </div>
          </div>
        </div>

        {/* Location & Salary */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '14px', fontSize: '12.5px', color: 'var(--text-secondary)' }}>
          {job.location && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <MapPin size={13} color="var(--text-muted)" />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {job.location}
              </span>
            </div>
          )}

          {formatSalary() && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--success)', fontWeight: 600 }}>
              <DollarSign size={13} />
              <span>{formatSalary()}</span>
            </div>
          )}

          {job.employment_type && job.employment_type !== 'UNKNOWN' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
              <Briefcase size={13} />
              <span>{job.employment_type.replace('_', ' ')}</span>
            </div>
          )}
        </div>

        {/* Skills Pills */}
        {job.required_skills && job.required_skills.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '16px' }}>
            {job.required_skills.slice(0, 3).map((skill, idx) => (
              <span
                key={idx}
                style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  fontSize: '11px',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                {skill}
              </span>
            ))}
            {job.required_skills.length > 3 && (
              <span
                style={{
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                }}
              >
                +{job.required_skills.length - 3}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Card Footer Actions */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: '14px',
          borderTop: '1px solid var(--border-subtle)',
          marginTop: '8px',
        }}
      >
        <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
          {new Date(job.created_at).toLocaleDateString()}
        </span>

        <div style={{ display: 'flex', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
          {job.job_url && (
            <a href={job.job_url} target="_blank" rel="noopener noreferrer">
              <Button size="sm" variant="ghost" rightIcon={<ExternalLink size={13} />} title="Open external job link">
                Link
              </Button>
            </a>
          )}
          <Button
            size="sm"
            variant="outline"
            leftIcon={<Eye size={13} />}
            onClick={() => onInspect(job)}
          >
            Inspect
          </Button>
        </div>
      </div>
    </Card>
  );
};
