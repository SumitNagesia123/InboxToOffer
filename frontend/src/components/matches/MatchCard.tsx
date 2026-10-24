import React from 'react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Button } from '../common/Button';
import type { JobMatch } from './MatchDetailModal';
import {
  Building,
  Sparkles,
  AlertTriangle,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

interface MatchCardProps {
  match: JobMatch;
  trackingStatus?: string; // 'APPLIED' | 'NOT_APPLIED' | undefined
  onExplain: (match: JobMatch) => void;
  onLikeApply: (match: JobMatch) => void;
  onDislikeNotApply: (match: JobMatch) => void;
}

export const MatchCard: React.FC<MatchCardProps> = ({
  match,
  trackingStatus,
  onExplain,
  onLikeApply,
  onDislikeNotApply,
}) => {
  const overall = Math.round(match.overall_match_score);
  const skill = Math.round(match.skill_score);
  const exp = Math.round(match.experience_score);

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'var(--success)';
    if (score >= 65) return 'var(--accent-primary)';
    if (score >= 50) return 'var(--warning)';
    return 'var(--danger)';
  };

  const getTierBadge = (score: number) => {
    if (score >= 80) return { label: 'Top Tier Fit', variant: 'success' as const };
    if (score >= 65) return { label: 'Good Fit', variant: 'primary' as const };
    if (score >= 50) return { label: 'Moderate Fit', variant: 'warning' as const };
    return { label: 'Low Compatibility', variant: 'danger' as const };
  };

  const tier = getTierBadge(overall);

  const applyUrl =
    match.job_url && (match.job_url.startsWith('http://') || match.job_url.startsWith('https://'))
      ? match.job_url
      : `https://www.google.com/search?q=${encodeURIComponent(
          `${match.job_title} ${match.company_name} job application apply`
        )}`;

  const isApplied = trackingStatus === 'APPLIED';
  const isNotApplied = trackingStatus === 'NOT_APPLIED';

  return (
    <Card
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        height: '100%',
        cursor: 'pointer',
        transition: 'transform var(--transition-fast), border-color var(--transition-fast)',
        borderColor: isApplied
          ? 'rgba(16, 185, 129, 0.4)'
          : isNotApplied
          ? 'rgba(239, 68, 68, 0.3)'
          : undefined,
      }}
      onClick={() => onExplain(match)}
    >
      <div>
        {/* Top Header with Tier & Score Gauge */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <Badge variant={tier.variant}>{tier.label}</Badge>
            {isApplied && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--success)',
                  backgroundColor: 'rgba(16, 185, 129, 0.12)',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                }}
              >
                <CheckCircle2 size={11} /> Applied (Tracked)
              </span>
            )}
            {isNotApplied && (
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  fontWeight: 700,
                  color: 'var(--danger)',
                  backgroundColor: 'rgba(239, 68, 68, 0.12)',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                }}
              >
                <XCircle size={11} /> Not Applied (Tracked)
              </span>
            )}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: 'var(--bg-card)',
              border: `2.5px solid ${getScoreColor(overall)}`,
              boxShadow: `0 0 10px ${getScoreColor(overall)}26`,
            }}
          >
            <span style={{ fontSize: '15px', fontWeight: 800, color: getScoreColor(overall) }}>
              {overall}%
            </span>
          </div>
        </div>

        {/* Role Title & Company */}
        <div style={{ marginBottom: '14px' }}>
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
            title={match.job_title}
          >
            {match.job_title}
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
            <Building size={13} color="var(--text-muted)" />
            <span style={{ fontWeight: 500 }}>{match.company_name}</span>
          </div>
        </div>

        {/* Factor Progress Bars */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '3px' }}>
              <span>Skill Alignment</span>
              <span style={{ fontWeight: 600, color: getScoreColor(skill) }}>{skill}%</span>
            </div>
            <div style={{ width: '100%', height: '4px', backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${skill}%`, height: '100%', backgroundColor: getScoreColor(skill) }} />
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '3px' }}>
              <span>Experience Fit</span>
              <span style={{ fontWeight: 600, color: getScoreColor(exp) }}>{exp}%</span>
            </div>
            <div style={{ width: '100%', height: '4px', backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{ width: `${exp}%`, height: '100%', backgroundColor: getScoreColor(exp) }} />
            </div>
          </div>
        </div>

        {/* Matched Skills Chips */}
        {match.matched_skills && match.matched_skills.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '12px' }}>
            {match.matched_skills.slice(0, 3).map((s) => (
              <span
                key={s}
                style={{
                  padding: '2px 7px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  color: 'var(--success)',
                  fontSize: '11px',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                }}
              >
                ✓ {s}
              </span>
            ))}
            {match.matched_skills.length > 3 && (
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', padding: '2px 4px' }}>
                +{match.matched_skills.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Missing Required Warning (if any) */}
        {match.missing_required_skills && match.missing_required_skills.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11.5px', color: 'var(--danger)', marginBottom: '12px' }}>
            <AlertTriangle size={12} />
            <span>Missing: {match.missing_required_skills.slice(0, 2).join(', ')}{match.missing_required_skills.length > 2 ? '...' : ''}</span>
          </div>
        )}
      </div>

      {/* Card Actions Footer */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          paddingTop: '12px',
          borderTop: '1px solid var(--border-subtle)',
          marginTop: '8px',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Upper Action Row: Explain + Tracking Pill */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Button
            size="sm"
            variant="ghost"
            leftIcon={<Sparkles size={13} color="var(--accent-primary)" />}
            onClick={() => onExplain(match)}
          >
            Explain Fit
          </Button>

          {/* Connected Tracked Status Indicator */}
          {isApplied ? (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 10px',
                borderRadius: '14px',
                backgroundColor: 'rgba(16, 185, 129, 0.14)',
                border: '1px solid rgba(16, 185, 129, 0.35)',
                color: 'var(--success)',
                fontSize: '11.5px',
                fontWeight: 700,
              }}
              title="Job is tracked as Applied in your Applications Page"
            >
              <CheckCircle2 size={13} /> Tracked: Applied
            </div>
          ) : isNotApplied ? (
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 10px',
                borderRadius: '14px',
                backgroundColor: 'rgba(239, 68, 68, 0.14)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: 'var(--danger)',
                fontSize: '11.5px',
                fontWeight: 700,
              }}
              title="Job is tracked as Not Applied in your Applications Page"
            >
              <XCircle size={13} /> Tracked: Not Applied
            </div>
          ) : (
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Untracked
            </span>
          )}
        </div>

        {/* Lower Action Row: Quick Apply + Like / Dislike (Track Decision) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Quick Apply Button */}
          <a
            href={applyUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ flex: 1, textDecoration: 'none' }}
            onClick={(e) => e.stopPropagation()}
          >
            <Button
              size="sm"
              variant="primary"
              style={{ width: '100%', justifyContent: 'center' }}
              rightIcon={<ExternalLink size={12} />}
              title="Open actual application portal in a new tab"
            >
              Quick Apply
            </Button>
          </a>

          {/* Like Button: Marked as Applied */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onLikeApply(match);
            }}
            title={
              isApplied
                ? 'Job is marked as Applied! Click again to re-sync.'
                : 'I applied for this job! (Click to mark as Applied and track in Applications)'
            }
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '5px',
              padding: '6px 11px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              backgroundColor: isApplied ? 'rgba(16, 185, 129, 0.22)' : 'var(--bg-input)',
              border: isApplied ? '1.5px solid var(--success)' : '1px solid var(--border-subtle)',
              color: isApplied ? 'var(--success)' : 'var(--text-secondary)',
              boxShadow: isApplied ? '0 0 10px rgba(16, 185, 129, 0.3)' : 'none',
            }}
          >
            <ThumbsUp size={13} fill={isApplied ? 'currentColor' : 'none'} />
            <span>{isApplied ? 'Applied' : 'Like'}</span>
          </button>

          {/* Dislike Button: Marked as Not Applied */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDislikeNotApply(match);
            }}
            title={
              isNotApplied
                ? 'Job marked as Not Applied. Click again to re-sync.'
                : "I didn't apply / not applying for this job (Click to mark as Not Applied and track in Applications)"
            }
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '5px',
              padding: '6px 11px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              backgroundColor: isNotApplied ? 'rgba(239, 68, 68, 0.22)' : 'var(--bg-input)',
              border: isNotApplied ? '1.5px solid var(--danger)' : '1px solid var(--border-subtle)',
              color: isNotApplied ? 'var(--danger)' : 'var(--text-secondary)',
              boxShadow: isNotApplied ? '0 0 10px rgba(239, 68, 68, 0.3)' : 'none',
            }}
          >
            <ThumbsDown size={13} fill={isNotApplied ? 'currentColor' : 'none'} />
            <span>{isNotApplied ? 'Not Applied' : 'Dislike'}</span>
          </button>
        </div>
      </div>
    </Card>
  );
};
