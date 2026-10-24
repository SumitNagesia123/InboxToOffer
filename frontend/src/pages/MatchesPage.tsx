import React, { useEffect, useState, useCallback } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Table, type Column } from '../components/common/Table';
import { Input } from '../components/common/Input';
import { MatchCard } from '../components/matches/MatchCard';
import { MatchDetailModal, type JobMatch } from '../components/matches/MatchDetailModal';
import { api } from '../api/client';
import {
  Sparkles,
  Search,
  RotateCw,
  LayoutGrid,
  List,
  CheckCircle2,
  TrendingUp,
  Award,
  Filter,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  XCircle,
  Undo2,
  X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface MatchListResponse {
  items: JobMatch[];
  total: number;
  skip: number;
  limit: number;
}

interface BatchMatchResponse {
  total_jobs_evaluated: number;
  total_matches_created: number;
  average_match_score: number;
  high_match_count: number;
  message: string;
}

interface ActionToast {
  message: string;
  decision: 'APPLIED' | 'NOT_APPLIED';
  match: JobMatch;
  appId?: string;
}

const SCORE_FILTERS = [
  { id: '65', label: 'Best Fits (65%+)', minScore: 65 },
  { id: '80', label: 'Top Tier (80%+)', minScore: 80 },
  { id: '50', label: 'Moderate (50%+)', minScore: 50 },
  { id: 'ALL', label: 'All Jobs', minScore: 0 },
];

export const MatchesPage: React.FC = () => {
  const navigate = useNavigate();
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [search, setSearch] = useState<string>('');
  // Default to 65% so only jobs that fit better with the candidate's resume appear first!
  const [selectedScoreFilter, setSelectedScoreFilter] = useState<string>('65');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isComputing, setIsComputing] = useState<boolean>(false);

  // Selected match for detail modal
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);

  // Map of job_id -> { id, status: 'APPLIED' | 'NOT_APPLIED' | etc }
  const [trackedMap, setTrackedMap] = useState<Record<string, { id?: string; status: string }>>({});

  // Floating confirmation toast for rapid multi-job reviewing
  const [actionToast, setActionToast] = useState<ActionToast | null>(null);

  // Auto-dismiss toast after 5s
  useEffect(() => {
    if (actionToast) {
      const timer = setTimeout(() => {
        setActionToast(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [actionToast]);

  const fetchMatches = useCallback(async () => {
    setIsLoading(true);
    try {
      const activeFilter = SCORE_FILTERS.find((f) => f.id === selectedScoreFilter);
      const params = new URLSearchParams();
      params.append('limit', '100');
      if (activeFilter && activeFilter.minScore > 0) {
        params.append('min_score', activeFilter.minScore.toString());
      }

      const [matchesRes, appsRes] = await Promise.allSettled([
        api.get<MatchListResponse>(`/matches?${params.toString()}`),
        api.get<{ items: { id?: string; job_id?: string; status?: string }[] }>('/applications?limit=100'),
      ]);

      let trackedDecidedJobIds = new Set<string>();
      if (appsRes.status === 'fulfilled') {
        const map: Record<string, { id?: string; status: string }> = {};
        (appsRes.value.items || []).forEach((a) => {
          if (a.job_id) {
            // Store all applications in the map for tracking status display
            map[a.job_id] = { id: a.id, status: a.status || 'DISCOVERED' };
            // Any decision (APPLIED, NOT_APPLIED, INTERVIEWING, OFFER, REJECTED, etc.)
            // means the candidate has already reviewed and filed this job.
            // Only uncreated jobs or DISCOVERED jobs remain in the pending queue.
            if (a.status && a.status !== 'DISCOVERED') {
              trackedDecidedJobIds.add(a.job_id);
            }
          }
        });
        setTrackedMap(map);
      }

      if (matchesRes.status === 'fulfilled') {
        const rawItems = matchesRes.value.items || [];
        // Only show pending matches that have not been acted on (Applied or Not Applied)
        const unreviewedMatches = rawItems.filter((m) => !trackedDecidedJobIds.has(m.job_id));
        setMatches(unreviewedMatches);
      }
    } catch (err) {
      console.error('Failed to load matches:', err);
      setMatches([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedScoreFilter]);

  useEffect(() => {
    fetchMatches();
  }, [fetchMatches]);

  useEffect(() => {
    const handleGlobalRefresh = () => {
      fetchMatches();
    };
    window.addEventListener('app:refresh-data', handleGlobalRefresh);
    return () => {
      window.removeEventListener('app:refresh-data', handleGlobalRefresh);
    };
  }, [fetchMatches]);

  const handleComputeAll = async () => {
    setIsComputing(true);
    try {
      const res = await api.post<BatchMatchResponse>('/matches/compute-all');
      alert(
        `Batch Matching Complete:\n• Jobs Evaluated: ${res.total_jobs_evaluated}\n• Matches Computed: ${res.total_matches_created}\n• High Matches (70%+): ${res.high_match_count}\n• Average Score: ${Math.round(res.average_match_score)}%`
      );
      fetchMatches();
    } catch (err: any) {
      alert(`Matching evaluation failed: ${err.message}. If you have not uploaded a resume, please upload one first.`);
    } finally {
      setIsComputing(false);
    }
  };

  // Undo tracking decision - brings job back into the matches queue
  const handleUndoTrack = async (match: JobMatch, appId?: string) => {
    // Re-insert job at top of matches list
    setMatches((prev) => [match, ...prev.filter((m) => m.job_id !== match.job_id)]);
    setTrackedMap((prev) => {
      const next = { ...prev };
      delete next[match.job_id];
      return next;
    });
    setActionToast(null);

    const targetAppId = appId || trackedMap[match.job_id]?.id;
    if (targetAppId) {
      try {
        await api.delete(`/applications/${targetAppId}`);
        window.dispatchEvent(new CustomEvent('app:refresh-data'));
      } catch (err: any) {
        console.error('Failed to revert application:', err);
      }
    }
  };

  // Like button clicked -> user applied for this job -> erase immediately from matches feed
  const handleLikeApply = async (match: JobMatch) => {
    const existingId = trackedMap[match.job_id]?.id;

    // Erase immediately from matches list so the next job (#2) slides into place instantly
    setMatches((prev) => prev.filter((m) => m.job_id !== match.job_id));
    setTrackedMap((prev) => ({
      ...prev,
      [match.job_id]: { id: existingId, status: 'APPLIED' },
    }));

    setActionToast({
      message: `"${match.job_title}" marked as Applied and moved to Applications.`,
      decision: 'APPLIED',
      match,
      appId: existingId,
    });

    try {
      const res = await api.post<{ id: string }>('/applications', {
        job_id: match.job_id,
        status: 'APPLIED',
        applied_date: new Date().toISOString(),
        notes: `Applied via Quick Apply (${Math.round(match.overall_match_score)}% match)`,
      });
      if (res?.id) {
        setTrackedMap((prev) => ({
          ...prev,
          [match.job_id]: { id: res.id, status: 'APPLIED' },
        }));
        setActionToast((prev) =>
          prev && prev.match.job_id === match.job_id ? { ...prev, appId: res.id } : prev
        );
      }
      window.dispatchEvent(new CustomEvent('app:refresh-data'));
    } catch (err: any) {
      alert(`Could not track application: ${err.message}`);
      fetchMatches();
    }
  };

  // Dislike button clicked -> user skips/doesn't apply -> erase immediately from matches feed
  const handleDislikeNotApply = async (match: JobMatch) => {
    const existingId = trackedMap[match.job_id]?.id;

    // Erase immediately from matches list so the next job slides into place instantly
    setMatches((prev) => prev.filter((m) => m.job_id !== match.job_id));
    setTrackedMap((prev) => ({
      ...prev,
      [match.job_id]: { id: existingId, status: 'NOT_APPLIED' },
    }));

    setActionToast({
      message: `"${match.job_title}" marked as Not Applied and removed from Matches feed.`,
      decision: 'NOT_APPLIED',
      match,
      appId: existingId,
    });

    try {
      const res = await api.post<{ id: string }>('/applications', {
        job_id: match.job_id,
        status: 'NOT_APPLIED',
        applied_date: null,
        notes: `Marked as Not Applied (${Math.round(match.overall_match_score)}% match)`,
      });
      if (res?.id) {
        setTrackedMap((prev) => ({
          ...prev,
          [match.job_id]: { id: res.id, status: 'NOT_APPLIED' },
        }));
        setActionToast((prev) =>
          prev && prev.match.job_id === match.job_id ? { ...prev, appId: res.id } : prev
        );
      }
      window.dispatchEvent(new CustomEvent('app:refresh-data'));
    } catch (err: any) {
      alert(`Could not track application status: ${err.message}`);
      fetchMatches();
    }
  };

  // Filter client-side search across role title and company name
  const filteredMatches = matches.filter(
    (m) =>
      m.job_title.toLowerCase().includes(search.toLowerCase()) ||
      m.company_name.toLowerCase().includes(search.toLowerCase())
  );

  // KPI Calculations on available unapplied jobs
  const topCount = matches.filter((m) => m.overall_match_score >= 80).length;
  const goodCount = matches.filter(
    (m) => m.overall_match_score >= 65 && m.overall_match_score < 80
  ).length;
  const moderateCount = matches.filter(
    (m) => m.overall_match_score >= 50 && m.overall_match_score < 65
  ).length;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'var(--success)';
    if (score >= 65) return 'var(--accent-primary)';
    if (score >= 50) return 'var(--warning)';
    return 'var(--danger)';
  };

  const getApplyUrl = (match: JobMatch) => {
    if (match.job_url && (match.job_url.startsWith('http://') || match.job_url.startsWith('https://'))) {
      return match.job_url;
    }
    return `https://www.google.com/search?q=${encodeURIComponent(
      `${match.job_title} ${match.company_name} job application apply`
    )}`;
  };

  const columns: Column<JobMatch>[] = [
    {
      key: 'job_title',
      header: 'Role & Organization',
      render: (m) => (
        <div>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '13.5px' }}>
            {m.job_title}
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
            {m.company_name}
          </div>
        </div>
      ),
    },
    {
      key: 'overall_match_score',
      header: 'Compatibility',
      render: (m) => {
        const score = Math.round(m.overall_match_score);
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Badge score={score}>{score}% Match</Badge>
          </div>
        );
      },
    },
    {
      key: 'factors',
      header: 'Skill / Exp Fit',
      render: (m) => (
        <div style={{ display: 'flex', gap: '8px', fontSize: '12px' }}>
          <span style={{ color: getScoreColor(m.skill_score), fontWeight: 600 }}>
            Skills: {Math.round(m.skill_score)}%
          </span>
          <span style={{ color: 'var(--text-muted)' }}>•</span>
          <span style={{ color: getScoreColor(m.experience_score), fontWeight: 600 }}>
            Exp: {Math.round(m.experience_score)}%
          </span>
        </div>
      ),
    },
    {
      key: 'matched_skills',
      header: 'Matched Skills',
      render: (m) => (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxWidth: '240px' }}>
          {m.matched_skills.slice(0, 3).map((s) => (
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
              {s}
            </span>
          ))}
          {m.matched_skills.length > 3 && (
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', alignSelf: 'center' }}>
              +{m.matched_skills.length - 3}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'tracking',
      header: 'Tracking State',
      render: (m) => {
        const tracking = trackedMap[m.job_id]?.status;
        if (tracking === 'APPLIED') {
          return (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11.5px',
                fontWeight: 700,
                color: 'var(--success)',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                padding: '3px 8px',
                borderRadius: '12px',
                border: '1px solid rgba(16, 185, 129, 0.3)',
              }}
            >
              <CheckCircle2 size={12} /> Applied
            </span>
          );
        }
        if (tracking === 'NOT_APPLIED') {
          return (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11.5px',
                fontWeight: 700,
                color: 'var(--danger)',
                backgroundColor: 'rgba(239, 68, 68, 0.12)',
                padding: '3px 8px',
                borderRadius: '12px',
                border: '1px solid rgba(239, 68, 68, 0.3)',
              }}
            >
              <XCircle size={12} /> Not Applied
            </span>
          );
        }
        return <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>Untracked</span>;
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (m) => {
        const tracking = trackedMap[m.job_id]?.status;
        const isApplied = tracking === 'APPLIED';
        const isNotApplied = tracking === 'NOT_APPLIED';
        const applyUrl = getApplyUrl(m);

        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
            <Button
              size="sm"
              variant="outline"
              leftIcon={<Sparkles size={13} color="var(--accent-primary)" />}
              onClick={() => setSelectedMatch(m)}
            >
              Explain
            </Button>

            <a
              href={applyUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ textDecoration: 'none' }}
            >
              <Button
                size="sm"
                variant="primary"
                rightIcon={<ExternalLink size={12} />}
                title="Quick Apply on official job portal"
              >
                Apply
              </Button>
            </a>

            <button
              type="button"
              onClick={() => handleLikeApply(m)}
              title="I applied for this job (Mark Applied)"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '5px 8px',
                borderRadius: '4px',
                fontSize: '11.5px',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: isApplied ? 'rgba(16, 185, 129, 0.2)' : 'var(--bg-card)',
                border: isApplied ? '1.5px solid var(--success)' : '1px solid var(--border-subtle)',
                color: isApplied ? 'var(--success)' : 'var(--text-secondary)',
              }}
            >
              <ThumbsUp size={12} fill={isApplied ? 'currentColor' : 'none'} />
              <span>Applied</span>
            </button>

            <button
              type="button"
              onClick={() => handleDislikeNotApply(m)}
              title="I haven't applied / skip this job (Mark Not Applied)"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '5px 8px',
                borderRadius: '4px',
                fontSize: '11.5px',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: isNotApplied ? 'rgba(239, 68, 68, 0.2)' : 'var(--bg-card)',
                border: isNotApplied ? '1.5px solid var(--danger)' : '1px solid var(--border-subtle)',
                color: isNotApplied ? 'var(--danger)' : 'var(--text-secondary)',
              }}
            >
              <ThumbsDown size={12} fill={isNotApplied ? 'currentColor' : 'none'} />
              <span>Skip</span>
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <AppLayout
      title="Explainable Match Intelligence"
      onRefresh={fetchMatches}
      isRefreshing={isLoading}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* KPI Metrics Summary */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '16px',
          }}
        >
          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Top Tier (80%+)</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--success)', marginTop: '4px' }}>
                  {topCount}
                </div>
              </div>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(16, 185, 129, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Award size={22} color="var(--success)" />
              </div>
            </div>
          </Card>

          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Good Fits (65-79%)</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '4px' }}>
                  {goodCount}
                </div>
              </div>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(99, 102, 241, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <TrendingUp size={22} color="var(--accent-primary)" />
              </div>
            </div>
          </Card>

          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Moderate Fits (50-64%)</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--warning)', marginTop: '4px' }}>
                  {moderateCount}
                </div>
              </div>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(245, 158, 11, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <CheckCircle2 size={22} color="var(--warning)" />
              </div>
            </div>
          </Card>

          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Available Matches</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                  {matches.length}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Ready to evaluate
                </div>
              </div>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Sparkles size={22} color="var(--text-secondary)" />
              </div>
            </div>
          </Card>
        </div>

        {/* User Guidance Banner */}
        <div
          style={{
            padding: '14px 18px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'rgba(99, 102, 241, 0.08)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Sparkles size={18} color="var(--accent-primary)" />
            <span style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
              <strong>Pending Matches Queue:</strong> Review jobs aligned with your resume. Click <strong>Quick Apply</strong>, then mark <strong>Like (👍 Applied)</strong> or <strong>Dislike (👎 Not Applied)</strong> to file them to your Applications pipeline and clear them from this feed.
            </span>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => navigate('/applications')}
            title="View personal application pipeline"
          >
            View Applications Pipeline →
          </Button>
        </div>

        {/* Control and Search Bar */}
        <Card style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
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
                  placeholder="Search matches by role or company..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  leftIcon={<Search size={16} />}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Button
                  variant="outline"
                  size="md"
                  isLoading={isLoading}
                  leftIcon={<RotateCw size={15} className={isLoading ? 'animate-spin' : ''} />}
                  onClick={fetchMatches}
                  title="Reload match intelligence"
                >
                  Refresh
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  isLoading={isComputing}
                  leftIcon={<Sparkles size={16} />}
                  onClick={handleComputeAll}
                >
                  Re-evaluate All Jobs
                </Button>
              </div>
            </div>

            {/* Score Filters & View Mode */}
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '12.5px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Filter size={13} /> Showing:
                </span>
                {SCORE_FILTERS.map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setSelectedScoreFilter(f.id)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: '20px',
                      fontSize: '12.5px',
                      fontWeight: selectedScoreFilter === f.id ? 600 : 400,
                      border:
                        selectedScoreFilter === f.id
                          ? '1px solid var(--accent-primary)'
                          : '1px solid var(--border-subtle)',
                      backgroundColor:
                        selectedScoreFilter === f.id
                          ? 'rgba(99, 102, 241, 0.15)'
                          : 'var(--bg-card)',
                      color:
                        selectedScoreFilter === f.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* View Switcher */}
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
                  onClick={() => setViewMode('grid')}
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
                  onClick={() => setViewMode('table')}
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
        </Card>

        {/* Presentation Area */}
        {viewMode === 'grid' ? (
          isLoading ? (
            <Card style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Evaluating resume compatibility across job postings...
            </Card>
          ) : filteredMatches.length === 0 ? (
            <Card style={{ padding: '48px', textAlign: 'center' }}>
              <div style={{ maxWidth: '440px', margin: '0 auto' }}>
                <Sparkles size={40} color="var(--accent-primary)" style={{ margin: '0 auto 16px', display: 'block' }} />
                <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
                  All Matching Jobs Evaluated! 🎉
                </h3>
                <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginBottom: '20px', lineHeight: 1.5 }}>
                  You have applied or decided on all available job matches in this queue. Track your application stages in the Applications Pipeline, or view other score tiers!
                </p>
                <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                  {selectedScoreFilter !== 'ALL' && (
                    <Button
                      variant="outline"
                      size="md"
                      onClick={() => setSelectedScoreFilter('ALL')}
                    >
                      View All Jobs
                    </Button>
                  )}
                  <Button
                    variant="primary"
                    size="md"
                    onClick={() => navigate('/applications')}
                  >
                    Go to Applications Pipeline →
                  </Button>
                </div>
              </div>
            </Card>
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
                gap: '18px',
              }}
            >
              {filteredMatches.map((match) => (
                <MatchCard
                  key={match.id}
                  match={match}
                  trackingStatus={trackedMap[match.job_id]?.status}
                  onExplain={(m) => setSelectedMatch(m)}
                  onLikeApply={handleLikeApply}
                  onDislikeNotApply={handleDislikeNotApply}
                />
              ))}
            </div>
          )
        ) : (
          <Card style={{ padding: '0px', overflow: 'hidden' }}>
            <Table<JobMatch>
              columns={columns}
              data={filteredMatches}
              keyExtractor={(m) => m.id}
              isLoading={isLoading}
              onRowClick={(m) => setSelectedMatch(m)}
              emptyMessage="No match evaluations match your criteria."
            />
          </Card>
        )}
      </div>

      {/* Match Explainability Modal */}
      <MatchDetailModal
        match={selectedMatch}
        isOpen={!!selectedMatch}
        trackingStatus={selectedMatch ? trackedMap[selectedMatch.job_id]?.status : undefined}
        onClose={() => setSelectedMatch(null)}
        onApplicationCreated={() => fetchMatches()}
        onLikeApply={handleLikeApply}
        onDislikeNotApply={handleDislikeNotApply}
      />

      {/* Floating Action Toast for Rapid Reviewing */}
      {actionToast && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 9999,
            backgroundColor: 'var(--bg-card)',
            border:
              actionToast.decision === 'APPLIED'
                ? '1px solid rgba(16, 185, 129, 0.5)'
                : '1px solid rgba(239, 68, 68, 0.5)',
            boxShadow: '0 12px 36px rgba(0, 0, 0, 0.55)',
            borderRadius: 'var(--radius-md)',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            maxWidth: '540px',
            animation: 'fadeInUp 0.2s ease-out',
          }}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor:
                actionToast.decision === 'APPLIED'
                  ? 'rgba(16, 185, 129, 0.18)'
                  : 'rgba(239, 68, 68, 0.18)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {actionToast.decision === 'APPLIED' ? (
              <ThumbsUp size={18} style={{ color: 'var(--success)' }} />
            ) : (
              <ThumbsDown size={18} style={{ color: 'var(--danger)' }} />
            )}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                lineHeight: 1.4,
              }}
            >
              {actionToast.message}
            </div>
            <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Cleared from Matches feed • Tracked in Applications
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <button
              type="button"
              onClick={() => handleUndoTrack(actionToast.match, actionToast.appId)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                backgroundColor: 'transparent',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                color: 'var(--text-secondary)',
                fontSize: '11.5px',
                fontWeight: 600,
                padding: '4px 8px',
                cursor: 'pointer',
              }}
              title="Undo decision and bring job back to Matches"
            >
              <Undo2 size={12} /> Undo
            </button>

            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setActionToast(null);
                navigate('/applications');
              }}
              style={{ fontSize: '11.5px', padding: '4px 8px' }}
            >
              Applications →
            </Button>

            <button
              type="button"
              onClick={() => setActionToast(null)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <X size={15} />
            </button>
          </div>
        </div>
      )}
    </AppLayout>
  );
};
