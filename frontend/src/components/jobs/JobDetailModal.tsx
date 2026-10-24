import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { api } from '../../api/client';
import {
  MapPin,
  ExternalLink,
  CheckCircle,
  Layers,
  Sparkles,
  Building,
} from 'lucide-react';

import { getApplicationStatusConfig } from './statusUtils';

export interface Job {
  id: string;
  user_id: string;
  source_email_id?: string;
  company_id?: string;
  company_name: string;
  title: string;
  normalized_title: string;
  location?: string;
  work_mode: string;
  employment_type: string;
  salary_currency?: string;
  salary_min?: number;
  salary_max?: number;
  min_experience_years?: number;
  max_experience_years?: number;
  job_description?: string;
  job_url?: string;
  platform_source: string;
  posted_date?: string;
  application_deadline?: string;
  is_duplicate: boolean;
  canonical_job_id?: string;
  required_skills: string[];
  preferred_skills: string[];
  created_at: string;
}

interface JobDetailModalProps {
  job: Job | null;
  isOpen: boolean;
  onClose: () => void;
  onApplicationCreated?: () => void;
  applicationStatus?: string;
  matchScore?: number;
}

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  job,
  isOpen,
  onClose,
  onApplicationCreated,
  applicationStatus,
  matchScore,
}) => {
  const [isTracking, setIsTracking] = useState(false);
  const [trackedSuccess, setTrackedSuccess] = useState(false);

  if (!job) return null;

  const appStatusConfig = getApplicationStatusConfig(applicationStatus);

  const handleTrackApplication = async () => {
    setIsTracking(true);
    try {
      await api.post('/applications', {
        job_id: job.id,
        status: 'APPLIED',
        applied_date: new Date().toISOString(),
        notes: `Application initiated from Job Intelligence Hub (${job.platform_source})`,
      });
      setTrackedSuccess(true);
      if (onApplicationCreated) {
        onApplicationCreated();
      }
    } catch (err: any) {
      alert(`Could not track application: ${err.message}`);
    } finally {
      setIsTracking(false);
    }
  };

  const formatSalary = () => {
    if (!job.salary_min && !job.salary_max) return 'Salary Undisclosed';
    const curr = job.salary_currency || '$';
    if (job.salary_min && job.salary_max) {
      return `${curr}${job.salary_min.toLocaleString()} - ${curr}${job.salary_max.toLocaleString()}`;
    }
    if (job.salary_min) return `From ${curr}${job.salary_min.toLocaleString()}`;
    return `Up to ${curr}${job.salary_max?.toLocaleString()}`;
  };

  const formatExperience = () => {
    if (job.min_experience_years === undefined || job.min_experience_years === null) {
      return 'Not Specified';
    }
    if (job.max_experience_years) {
      return `${job.min_experience_years} - ${job.max_experience_years} years`;
    }
    return `${job.min_experience_years}+ years`;
  };

  const getWorkModeVariant = (mode: string): 'primary' | 'danger' | 'success' | 'warning' | 'info' | 'neutral' => {
    const m = mode.toUpperCase();
    if (m === 'REMOTE') return 'success';
    if (m === 'HYBRID') return 'primary';
    if (m === 'ON_SITE') return 'warning';
    return 'neutral';
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Structured Job Opportunity"
      maxWidth="760px"
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Badge variant="info">{job.platform_source}</Badge>
            {job.is_duplicate && <Badge variant="warning">Duplicate Posting</Badge>}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            {job.job_url && (
              <a href={job.job_url} target="_blank" rel="noopener noreferrer">
                <Button
                  variant="outline"
                  size="md"
                  rightIcon={<ExternalLink size={15} />}
                >
                  Direct Job URL
                </Button>
              </a>
            )}

            {trackedSuccess || applicationStatus === 'APPLIED' ? (
              <Button variant="outline" size="md" disabled leftIcon={<CheckCircle size={15} color="var(--success)" />}>
                {applicationStatus === 'APPLIED' ? 'Already in Pipeline (Applied)' : 'Added to Pipeline'}
              </Button>
            ) : (
              <Button
                variant="primary"
                size="md"
                isLoading={isTracking}
                leftIcon={<Layers size={15} />}
                onClick={handleTrackApplication}
              >
                Track as Applied
              </Button>
            )}
          </div>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
        {/* Header Section */}
        <div
          style={{
            padding: '20px',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '14px', flexWrap: 'wrap' }}>
            <div>
              <h2 style={{ fontSize: '20px', fontWeight: 700, margin: '0 0 6px 0', color: 'var(--text-primary)' }}>
                {job.title}
              </h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '15px' }}>
                <Building size={16} color="var(--accent-primary)" />
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{job.company_name}</span>
                {job.location && (
                  <>
                    <span>•</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <MapPin size={14} color="var(--text-muted)" />
                      {job.location}
                    </span>
                  </>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <Badge variant={getWorkModeVariant(job.work_mode)}>
                {job.work_mode}
              </Badge>
              {typeof matchScore === 'number' && matchScore > 0 ? (
                <Badge score={matchScore} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <Sparkles size={12} /> {Math.round(matchScore)}% match
                </Badge>
              ) : (
                <Badge variant="neutral">Not scored</Badge>
              )}
              {appStatusConfig && (
                <Badge variant={appStatusConfig.variant} title={`Pipeline Stage: ${appStatusConfig.label}`}>
                  {appStatusConfig.label}
                </Badge>
              )}
            </div>
          </div>

          {/* Quick Specifications Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: '12px',
              marginTop: '16px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Salary Range
              </div>
              <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--success)', marginTop: '2px' }}>
                {formatSalary()}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Experience Req.
              </div>
              <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {formatExperience()}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Employment Type
              </div>
              <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                {job.employment_type.replace('_', ' ')}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Extracted On
              </div>
              <div style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                {new Date(job.created_at).toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>

        {/* Required & Preferred Skills */}
        {((job.required_skills && job.required_skills.length > 0) ||
          (job.preferred_skills && job.preferred_skills.length > 0)) && (
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sparkles size={16} color="var(--accent-primary)" />
              Extracted Skill Requirements
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {job.required_skills && job.required_skills.length > 0 && (
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Required Qualifications:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {job.required_skills.map((skill, idx) => (
                      <span
                        key={idx}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '6px',
                          backgroundColor: 'rgba(99, 102, 241, 0.12)',
                          border: '1px solid rgba(99, 102, 241, 0.25)',
                          color: 'var(--accent-primary)',
                          fontSize: '12px',
                          fontWeight: 500,
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {job.preferred_skills && job.preferred_skills.length > 0 && (
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    Preferred / Nice-to-Have:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {job.preferred_skills.map((skill, idx) => (
                      <span
                        key={idx}
                        style={{
                          padding: '4px 10px',
                          borderRadius: '6px',
                          backgroundColor: 'rgba(255, 255, 255, 0.05)',
                          border: '1px solid var(--border-subtle)',
                          color: 'var(--text-secondary)',
                          fontSize: '12px',
                        }}
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Full Job Description */}
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 10px 0', color: 'var(--text-primary)' }}>
            Job Description & Overview
          </h4>
          <div
            style={{
              padding: '16px',
              backgroundColor: 'var(--bg-card)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              fontSize: '13.5px',
              lineHeight: 1.6,
              color: 'var(--text-secondary)',
              maxHeight: '260px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
            }}
          >
            {job.job_description || 'No detailed description extracted for this role.'}
          </div>
        </div>
      </div>
    </Modal>
  );
};
