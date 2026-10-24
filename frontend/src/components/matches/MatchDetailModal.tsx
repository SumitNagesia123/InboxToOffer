import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { api } from '../../api/client';
import {
  Sparkles,
  Building,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  XCircle,
} from 'lucide-react';

export interface JobMatch {
  id: string;
  user_id: string;
  job_id: string;
  resume_id: string;
  job_title: string;
  company_name: string;
  overall_match_score: number;
  skill_score: number;
  experience_score: number;
  semantic_score: number;
  matched_skills: string[];
  missing_required_skills: string[];
  missing_preferred_skills: string[];
  explanation_summary: string;
  job_url?: string;
  source_email_id?: string;
  created_at: string;
}

interface MatchDetailModalProps {
  match: JobMatch | null;
  isOpen: boolean;
  trackingStatus?: string; // 'APPLIED' | 'NOT_APPLIED' | undefined
  onClose: () => void;
  onApplicationCreated?: () => void;
  onLikeApply?: (match: JobMatch) => void;
  onDislikeNotApply?: (match: JobMatch) => void;
}

export const MatchDetailModal: React.FC<MatchDetailModalProps> = ({
  match,
  isOpen,
  trackingStatus,
  onClose,
  onApplicationCreated,
  onLikeApply,
  onDislikeNotApply,
}) => {
  const [isTracking, setIsTracking] = useState(false);

  if (!match) return null;

  const isApplied = trackingStatus === 'APPLIED';
  const isNotApplied = trackingStatus === 'NOT_APPLIED';

  const applyUrl =
    match.job_url && (match.job_url.startsWith('http://') || match.job_url.startsWith('https://'))
      ? match.job_url
      : `https://www.google.com/search?q=${encodeURIComponent(
          `${match.job_title} ${match.company_name} job application apply`
        )}`;

  const handleTrackApplication = async (status: 'APPLIED' | 'NOT_APPLIED') => {
    setIsTracking(true);
    try {
      await api.post('/applications', {
        job_id: match.job_id,
        status,
        applied_date: status === 'APPLIED' ? new Date().toISOString() : null,
        notes:
          status === 'APPLIED'
            ? `Applied via Quick Apply (${Math.round(match.overall_match_score)}% match)`
            : `Marked as Not Applied (${Math.round(match.overall_match_score)}% match)`,
      });
      if (onApplicationCreated) {
        onApplicationCreated();
      }
      window.dispatchEvent(new CustomEvent('app:refresh-data'));
      onClose();
    } catch (err: any) {
      alert(`Could not update application status: ${err.message}`);
    } finally {
      setIsTracking(false);
    }
  };

  const overall = Math.round(match.overall_match_score);
  const skill = Math.round(match.skill_score);
  const exp = Math.round(match.experience_score);
  const sem = Math.round(match.semantic_score);

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'var(--success)';
    if (score >= 65) return 'var(--accent-primary)';
    if (score >= 50) return 'var(--warning)';
    return 'var(--danger)';
  };

  const getTierBadge = (score: number) => {
    if (score >= 80) return { label: 'Strong Fit (Top Tier)', variant: 'success' as const };
    if (score >= 65) return { label: 'Good Match', variant: 'primary' as const };
    if (score >= 50) return { label: 'Moderate Fit', variant: 'warning' as const };
    return { label: 'Low Compatibility', variant: 'danger' as const };
  };

  const tier = getTierBadge(overall);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Candidate Match Breakdown"
      maxWidth="720px"
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Status:</span>
            {isApplied ? (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '12px',
                  fontWeight: 700,
                  color: 'var(--success)',
                  backgroundColor: 'rgba(16, 185, 129, 0.12)',
                  padding: '3px 9px',
                  borderRadius: '12px',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                }}
              >
                <CheckCircle2 size={12} /> Tracked: Applied
              </span>
            ) : isNotApplied ? (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '12px',
                  fontWeight: 700,
                  color: 'var(--danger)',
                  backgroundColor: 'rgba(239, 68, 68, 0.12)',
                  padding: '3px 9px',
                  borderRadius: '12px',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                }}
              >
                <XCircle size={12} /> Tracked: Not Applied
              </span>
            ) : (
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Untracked</span>
            )}
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <a
              href={applyUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ textDecoration: 'none' }}
            >
              <Button
                size="sm"
                variant="primary"
                rightIcon={<ExternalLink size={13} />}
                title="Open actual application portal in a new tab"
              >
                Quick Apply
              </Button>
            </a>

            <Button
              variant="outline"
              size="sm"
              isLoading={isTracking}
              leftIcon={<ThumbsUp size={13} fill={isApplied ? 'currentColor' : 'none'} />}
              onClick={() => {
                if (onLikeApply) onLikeApply(match);
                else handleTrackApplication('APPLIED');
              }}
              style={{
                borderColor: isApplied ? 'var(--success)' : undefined,
                color: isApplied ? 'var(--success)' : undefined,
                backgroundColor: isApplied ? 'rgba(16, 185, 129, 0.12)' : undefined,
              }}
              title="Mark as Applied (Tracked in Applications)"
            >
              {isApplied ? 'Applied ✓' : 'Like (Applied)'}
            </Button>

            <Button
              variant="outline"
              size="sm"
              isLoading={isTracking}
              leftIcon={<ThumbsDown size={13} fill={isNotApplied ? 'currentColor' : 'none'} />}
              onClick={() => {
                if (onDislikeNotApply) onDislikeNotApply(match);
                else handleTrackApplication('NOT_APPLIED');
              }}
              style={{
                borderColor: isNotApplied ? 'var(--danger)' : undefined,
                color: isNotApplied ? 'var(--danger)' : undefined,
                backgroundColor: isNotApplied ? 'rgba(239, 68, 68, 0.12)' : undefined,
              }}
              title="Mark as Not Applied (Tracked in Applications)"
            >
              {isNotApplied ? 'Not Applied ✕' : 'Dislike (Skip)'}
            </Button>

            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
        {/* Role & Score Header Banner */}
        <div
          style={{
            padding: '20px',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <Badge variant={tier.variant}>{tier.label}</Badge>
            </div>
            <h2 style={{ fontSize: '20px', fontWeight: 700, margin: '4px 0', color: 'var(--text-primary)' }}>
              {match.job_title}
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '14px' }}>
              <Building size={14} color="var(--text-muted)" />
              <span style={{ fontWeight: 600 }}>{match.company_name}</span>
            </div>
          </div>

          {/* Radial / Percentage Badge */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              width: '90px',
              height: '90px',
              borderRadius: '50%',
              backgroundColor: 'var(--bg-card)',
              border: `3px solid ${getScoreColor(overall)}`,
              boxShadow: `0 0 16px ${getScoreColor(overall)}33`,
            }}
          >
            <div style={{ fontSize: '24px', fontWeight: 800, color: getScoreColor(overall), lineHeight: 1 }}>
              {overall}%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '3px' }}>
              Match
            </div>
          </div>
        </div>

        {/* Explainable Factor Weights Grid */}
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
            Score Attribution Breakdown
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            {/* Skill Alignment */}
            <div
              style={{
                padding: '14px',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Skills (40%)</span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: getScoreColor(skill) }}>{skill}%</span>
              </div>
              <div style={{ width: '100%', height: '5px', backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${skill}%`, height: '100%', backgroundColor: getScoreColor(skill) }} />
              </div>
            </div>

            {/* Experience Alignment */}
            <div
              style={{
                padding: '14px',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Experience (30%)</span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: getScoreColor(exp) }}>{exp}%</span>
              </div>
              <div style={{ width: '100%', height: '5px', backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${exp}%`, height: '100%', backgroundColor: getScoreColor(exp) }} />
              </div>
            </div>

            {/* Semantic Relevance */}
            <div
              style={{
                padding: '14px',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Domain Fit (30%)</span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: getScoreColor(sem) }}>{sem}%</span>
              </div>
              <div style={{ width: '100%', height: '5px', backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${sem}%`, height: '100%', backgroundColor: getScoreColor(sem) }} />
              </div>
            </div>
          </div>
        </div>

        {/* AI Explanatory Narrative */}
        <div
          style={{
            padding: '16px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'rgba(99, 102, 241, 0.06)',
            border: '1px solid rgba(99, 102, 241, 0.2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Sparkles size={16} color="var(--accent-primary)" />
            <h4 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
              AI Compatibility Rationale
            </h4>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0 }}>
            {match.explanation_summary}
          </p>
        </div>

        {/* Detailed Skills Diagnostics */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Matched Skills */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
              <CheckCircle2 size={15} color="var(--success)" />
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Matched Skills ({match.matched_skills.length})
              </span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {match.matched_skills.map((s) => (
                <span
                  key={s}
                  style={{
                    padding: '3px 9px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    color: 'var(--success)',
                    fontSize: '12px',
                    fontWeight: 500,
                  }}
                >
                  ✓ {s}
                </span>
              ))}
            </div>
          </div>

          {/* Missing Required Skills */}
          {match.missing_required_skills && match.missing_required_skills.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <AlertTriangle size={15} color="var(--danger)" />
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Missing Required Qualifications ({match.missing_required_skills.length})
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {match.missing_required_skills.map((s) => (
                  <span
                    key={s}
                    style={{
                      padding: '3px 9px',
                      borderRadius: '4px',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.25)',
                      color: 'var(--danger)',
                      fontSize: '12px',
                      fontWeight: 500,
                    }}
                  >
                    ✕ {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Missing Preferred Skills */}
          {match.missing_preferred_skills && match.missing_preferred_skills.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
                  Missing Preferred / Nice-to-Have ({match.missing_preferred_skills.length})
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {match.missing_preferred_skills.map((s) => (
                  <span
                    key={s}
                    style={{
                      padding: '3px 9px',
                      borderRadius: '4px',
                      backgroundColor: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--text-muted)',
                      fontSize: '12px',
                    }}
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};
