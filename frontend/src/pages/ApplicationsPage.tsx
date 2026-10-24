import React, { useEffect, useState, useCallback } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { ApplicationModal, type ApplicationDetail } from '../components/applications/ApplicationModal';
import { api } from '../api/client';
import {
  KanbanSquare,
  Search,
  Calendar,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Award,
  Clock,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
  Layers,
  Sparkles,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface ApplicationItem {
  id: string;
  job_id: string;
  status: string;
  applied_date?: string;
  notes?: string;
  job?: {
    company_name: string;
    title: string;
    location?: string;
    work_mode?: string;
    salary_min?: number;
    salary_max?: number;
    salary_currency?: string;
    job_url?: string;
    platform_source?: string;
  };
  match_score?: number;
  created_at: string;
  updated_at: string;
}

interface ApplicationListResponse {
  items: ApplicationItem[];
  total: number;
  skip: number;
  limit: number;
}

interface PipelineSummary {
  stage_counts: Record<string, number>;
  active_applications: number;
  total_applications: number;
  interview_rate_percentage: number;
  offer_rate_percentage: number;
}

const STAGES = [
  { id: 'APPLIED', label: 'Applied (Liked)', color: 'var(--success)', icon: ThumbsUp },
  { id: 'NOT_APPLIED', label: 'Not Applied (Disliked)', color: 'var(--danger)', icon: ThumbsDown },
  { id: 'INTERVIEWING', label: 'Interviewing', color: 'var(--warning)', icon: TrendingUp },
  { id: 'OFFER', label: 'Offer Received', color: 'var(--accent-primary)', icon: Award },
  { id: 'REJECTED', label: 'Archived / Rejected', color: 'var(--text-muted)', icon: Clock },
  { id: 'DISCOVERED', label: 'Discovered', color: 'var(--text-muted)', icon: Layers },
];

export const ApplicationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [summary, setSummary] = useState<PipelineSummary | null>(null);
  const [search, setSearch] = useState<string>('');
  const [activeFilterTab, setActiveFilterTab] = useState<'ALL' | 'APPLIED' | 'NOT_APPLIED' | 'ACTIVE'>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Modal inspection
  const [selectedApp, setSelectedApp] = useState<ApplicationDetail | null>(null);

  const fetchApplications = useCallback(async () => {
    setIsLoading(true);
    try {
      const [appListRes, pipelineSummaryRes] = await Promise.allSettled([
        api.get<ApplicationListResponse>('/applications?limit=100'),
        api.get<PipelineSummary>('/applications/pipeline/summary'),
      ]);

      if (appListRes.status === 'fulfilled') {
        setApplications(appListRes.value.items || []);
      } else {
        console.error('Failed to load applications list:', appListRes.reason);
      }

      if (pipelineSummaryRes.status === 'fulfilled') {
        setSummary(pipelineSummaryRes.value);
      } else {
        console.error('Failed to load pipeline summary:', pipelineSummaryRes.reason);
      }
    } catch (err) {
      console.error('Failed to load application pipeline:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApplications();
    const handleGlobalRefresh = () => {
      fetchApplications();
    };
    window.addEventListener('app:refresh-data', handleGlobalRefresh);
    return () => {
      window.removeEventListener('app:refresh-data', handleGlobalRefresh);
    };
  }, [fetchApplications]);

  const handleStageTransition = async (appId: string, targetStage: string) => {
    // Optimistic update
    setApplications((prev) =>
      prev.map((app) => (app.id === appId ? { ...app, status: targetStage } : app))
    );

    try {
      await api.patch(`/applications/${appId}`, { status: targetStage });
      window.dispatchEvent(new CustomEvent('app:refresh-data'));
      fetchApplications();
    } catch (err: any) {
      alert(`Could not advance stage: ${err.message}`);
      fetchApplications();
    }
  };

  const getStageVariant = (st: string): 'primary' | 'danger' | 'success' | 'warning' | 'info' | 'neutral' => {
    switch (st) {
      case 'OFFER':
        return 'primary';
      case 'INTERVIEWING':
        return 'warning';
      case 'APPLIED':
        return 'success';
      case 'NOT_APPLIED':
        return 'danger';
      case 'REJECTED':
        return 'neutral';
      case 'WITHDRAWN':
      case 'DISCOVERED':
      default:
        return 'neutral';
    }
  };

  // Status counts
  const appliedCount = applications.filter((a) => a.status === 'APPLIED').length;
  const notAppliedCount = applications.filter((a) => a.status === 'NOT_APPLIED').length;
  const interviewingAndOfferCount = applications.filter(
    (a) => a.status === 'INTERVIEWING' || a.status === 'OFFER'
  ).length;

  // Filter applications by search and active category tab
  const filtered = applications.filter((app) => {
    const titleMatch = app.job?.title?.toLowerCase().includes(search.toLowerCase());
    const companyMatch = app.job?.company_name?.toLowerCase().includes(search.toLowerCase());
    const notesMatch = app.notes?.toLowerCase().includes(search.toLowerCase());
    const locationMatch = app.job?.location?.toLowerCase().includes(search.toLowerCase());
    const matchesSearch = !search || titleMatch || companyMatch || notesMatch || locationMatch;

    if (!matchesSearch) return false;

    if (activeFilterTab === 'APPLIED') {
      return app.status === 'APPLIED';
    }
    if (activeFilterTab === 'NOT_APPLIED') {
      return app.status === 'NOT_APPLIED';
    }
    if (activeFilterTab === 'ACTIVE') {
      return app.status === 'INTERVIEWING' || app.status === 'OFFER';
    }
    return true;
  });

  // Stages to show based on filter tab
  const displayedStages =
    activeFilterTab === 'APPLIED'
      ? STAGES.filter((s) => s.id === 'APPLIED')
      : activeFilterTab === 'NOT_APPLIED'
      ? STAGES.filter((s) => s.id === 'NOT_APPLIED')
      : activeFilterTab === 'ACTIVE'
      ? STAGES.filter((s) => s.id === 'INTERVIEWING' || s.id === 'OFFER')
      : STAGES;

  return (
    <AppLayout title="Career Application Tracking Pipeline">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* KPI Metrics Summary */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '16px',
          }}
        >
          {/* Card 1: Total Tracked */}
          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Total Tracked</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                  {applications.length}
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
                <KanbanSquare size={22} color="var(--accent-primary)" />
              </div>
            </div>
          </Card>

          {/* Card 2: Applied (Liked) */}
          <Card
            style={{
              padding: '18px 20px',
              cursor: 'pointer',
              border: activeFilterTab === 'APPLIED' ? '1.5px solid var(--success)' : undefined,
            }}
            onClick={() => setActiveFilterTab(activeFilterTab === 'APPLIED' ? 'ALL' : 'APPLIED')}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Applied (Liked 👍)</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--success)', marginTop: '4px' }}>
                  {appliedCount}
                </div>
              </div>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(16, 185, 129, 0.14)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <ThumbsUp size={22} color="var(--success)" fill="rgba(16, 185, 129, 0.2)" />
              </div>
            </div>
          </Card>

          {/* Card 3: Not Applied (Disliked) */}
          <Card
            style={{
              padding: '18px 20px',
              cursor: 'pointer',
              border: activeFilterTab === 'NOT_APPLIED' ? '1.5px solid var(--danger)' : undefined,
            }}
            onClick={() => setActiveFilterTab(activeFilterTab === 'NOT_APPLIED' ? 'ALL' : 'NOT_APPLIED')}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Not Applied (Disliked 👎)</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--danger)', marginTop: '4px' }}>
                  {notAppliedCount}
                </div>
              </div>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(239, 68, 68, 0.14)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <ThumbsDown size={22} color="var(--danger)" fill="rgba(239, 68, 68, 0.2)" />
              </div>
            </div>
          </Card>

          {/* Card 4: Interviews & Offers */}
          <Card
            style={{
              padding: '18px 20px',
              cursor: 'pointer',
              border: activeFilterTab === 'ACTIVE' ? '1.5px solid var(--warning)' : undefined,
            }}
            onClick={() => setActiveFilterTab(activeFilterTab === 'ACTIVE' ? 'ALL' : 'ACTIVE')}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Interviews & Offers</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--warning)', marginTop: '4px' }}>
                  {interviewingAndOfferCount}
                </div>
                {summary && (
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {Math.round(summary.interview_rate_percentage)}% conversion rate
                  </div>
                )}
              </div>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(245, 158, 11, 0.14)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Award size={22} color="var(--warning)" />
              </div>
            </div>
          </Card>
        </div>

        {/* Filter Tabs & Search Controls */}
        <Card style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ flex: 1, minWidth: '260px' }}>
                <Input
                  placeholder="Search tracked applications by role, company, location, or notes..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  leftIcon={<Search size={16} />}
                />
              </div>

              <Button
                variant="outline"
                size="md"
                onClick={() => navigate('/matches')}
                leftIcon={<Sparkles size={15} color="var(--accent-primary)" />}
              >
                Find More Matches
              </Button>
            </div>

            {/* Quick Indication Filter Pills */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                flexWrap: 'wrap',
                paddingTop: '6px',
                borderTop: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '12.5px', color: 'var(--text-muted)', fontWeight: 600 }}>Filter:</span>
              <button
                type="button"
                onClick={() => setActiveFilterTab('ALL')}
                style={{
                  padding: '5px 12px',
                  borderRadius: '20px',
                  fontSize: '12.5px',
                  fontWeight: activeFilterTab === 'ALL' ? 700 : 500,
                  cursor: 'pointer',
                  border:
                    activeFilterTab === 'ALL'
                      ? '1px solid var(--accent-primary)'
                      : '1px solid var(--border-subtle)',
                  backgroundColor:
                    activeFilterTab === 'ALL' ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-card)',
                  color: activeFilterTab === 'ALL' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                }}
              >
                All Tracked ({applications.length})
              </button>

              <button
                type="button"
                onClick={() => setActiveFilterTab('APPLIED')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '5px 12px',
                  borderRadius: '20px',
                  fontSize: '12.5px',
                  fontWeight: activeFilterTab === 'APPLIED' ? 700 : 500,
                  cursor: 'pointer',
                  border:
                    activeFilterTab === 'APPLIED'
                      ? '1.5px solid var(--success)'
                      : '1px solid var(--border-subtle)',
                  backgroundColor:
                    activeFilterTab === 'APPLIED' ? 'rgba(16, 185, 129, 0.18)' : 'var(--bg-card)',
                  color: activeFilterTab === 'APPLIED' ? 'var(--success)' : 'var(--text-secondary)',
                }}
              >
                <ThumbsUp size={12} fill={activeFilterTab === 'APPLIED' ? 'currentColor' : 'none'} />
                <span>Applied ({appliedCount})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveFilterTab('NOT_APPLIED')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '5px 12px',
                  borderRadius: '20px',
                  fontSize: '12.5px',
                  fontWeight: activeFilterTab === 'NOT_APPLIED' ? 700 : 500,
                  cursor: 'pointer',
                  border:
                    activeFilterTab === 'NOT_APPLIED'
                      ? '1.5px solid var(--danger)'
                      : '1px solid var(--border-subtle)',
                  backgroundColor:
                    activeFilterTab === 'NOT_APPLIED' ? 'rgba(239, 68, 68, 0.18)' : 'var(--bg-card)',
                  color: activeFilterTab === 'NOT_APPLIED' ? 'var(--danger)' : 'var(--text-secondary)',
                }}
              >
                <ThumbsDown size={12} fill={activeFilterTab === 'NOT_APPLIED' ? 'currentColor' : 'none'} />
                <span>Not Applied ({notAppliedCount})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveFilterTab('ACTIVE')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '5px 12px',
                  borderRadius: '20px',
                  fontSize: '12.5px',
                  fontWeight: activeFilterTab === 'ACTIVE' ? 700 : 500,
                  cursor: 'pointer',
                  border:
                    activeFilterTab === 'ACTIVE'
                      ? '1.5px solid var(--warning)'
                      : '1px solid var(--border-subtle)',
                  backgroundColor:
                    activeFilterTab === 'ACTIVE' ? 'rgba(245, 158, 11, 0.18)' : 'var(--bg-card)',
                  color: activeFilterTab === 'ACTIVE' ? 'var(--warning)' : 'var(--text-secondary)',
                }}
              >
                <Award size={12} />
                <span>Interviews & Offers ({interviewingAndOfferCount})</span>
              </button>
            </div>
          </div>
        </Card>

        {/* Kanban Board */}
        {isLoading ? (
          <Card style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading pipeline board...
          </Card>
        ) : applications.length === 0 ? (
          <Card style={{ padding: '48px', textAlign: 'center' }}>
            <div style={{ maxWidth: '420px', margin: '0 auto' }}>
              <KanbanSquare size={40} color="var(--accent-primary)" style={{ margin: '0 auto 16px', display: 'block' }} />
              <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
                No Applications Tracked Yet
              </h3>
              <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginBottom: '20px', lineHeight: 1.5 }}>
                Visit the <strong>Matches</strong> page to find jobs matching your resume, click <strong>Quick Apply</strong>, and use the <strong>Like (👍 Applied)</strong> or <strong>Dislike (👎 Not Applied)</strong> buttons to start tracking them!
              </p>
              <Button
                variant="primary"
                size="md"
                leftIcon={<Sparkles size={16} />}
                onClick={() => navigate('/matches')}
              >
                Explore Job Matches →
              </Button>
            </div>
          </Card>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${displayedStages.length}, minmax(300px, 1fr))`,
              gap: '16px',
              overflowX: 'auto',
              paddingBottom: '16px',
              alignItems: 'start',
            }}
          >
            {displayedStages.map((stage, stageIdx) => {
              const stageApps = filtered.filter((a) => a.status === stage.id);
              const prevStage = stageIdx > 0 ? displayedStages[stageIdx - 1] : null;
              const nextStage = stageIdx < displayedStages.length - 1 ? displayedStages[stageIdx + 1] : null;

              return (
                <div
                  key={stage.id}
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--border-subtle)',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    minHeight: '520px',
                  }}
                >
                  {/* Column Header */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      paddingBottom: '12px',
                      borderBottom: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div
                        style={{
                          width: '10px',
                          height: '10px',
                          borderRadius: '50%',
                          backgroundColor: stage.color,
                        }}
                      />
                      <span style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {stage.label}
                      </span>
                    </div>
                    <Badge variant={getStageVariant(stage.id)}>{stageApps.length}</Badge>
                  </div>

                  {/* Cards in Column */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {stageApps.length === 0 ? (
                      <div
                        style={{
                          padding: '36px 12px',
                          textAlign: 'center',
                          color: 'var(--text-muted)',
                          fontSize: '12.5px',
                          border: '1px dashed var(--border-subtle)',
                          borderRadius: 'var(--radius-md)',
                        }}
                      >
                        No jobs currently in this stage
                      </div>
                    ) : (
                      stageApps.map((app) => {
                        const initial = app.job?.company_name
                          ? app.job.company_name.charAt(0).toUpperCase()
                          : '?';

                        const isApplied = app.status === 'APPLIED';
                        const isNotApplied = app.status === 'NOT_APPLIED';

                        return (
                          <Card
                            key={app.id}
                            style={{
                              padding: '14px',
                              cursor: 'pointer',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '10px',
                              borderLeft: isApplied
                                ? '3.5px solid var(--success)'
                                : isNotApplied
                                ? '3.5px solid var(--danger)'
                                : undefined,
                            }}
                            onClick={() => setSelectedApp(app)}
                          >
                            {/* Prominent Indication Badge: Applied vs Not Applied */}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              {isApplied && (
                                <span
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    padding: '3px 8px',
                                    borderRadius: '10px',
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    backgroundColor: 'rgba(16, 185, 129, 0.14)',
                                    border: '1px solid rgba(16, 185, 129, 0.3)',
                                    color: 'var(--success)',
                                  }}
                                >
                                  <ThumbsUp size={11} fill="currentColor" /> Applied (Liked)
                                </span>
                              )}
                              {isNotApplied && (
                                <span
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    padding: '3px 8px',
                                    borderRadius: '10px',
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    backgroundColor: 'rgba(239, 68, 68, 0.14)',
                                    border: '1px solid rgba(239, 68, 68, 0.3)',
                                    color: 'var(--danger)',
                                  }}
                                >
                                  <ThumbsDown size={11} fill="currentColor" /> Not Applied (Disliked)
                                </span>
                              )}
                              {!isApplied && !isNotApplied && (
                                <Badge variant={getStageVariant(app.status)}>{app.status}</Badge>
                              )}

                              {typeof app.match_score === 'number' && (
                                <Badge score={app.match_score}>{Math.round(app.match_score)}% Fit</Badge>
                              )}
                            </div>

                            {/* Card Header: Avatar & Title */}
                            <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                              <div
                                style={{
                                  width: '32px',
                                  height: '32px',
                                  borderRadius: '6px',
                                  backgroundColor: 'rgba(99, 102, 241, 0.12)',
                                  color: 'var(--accent-primary)',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontWeight: 700,
                                  fontSize: '13px',
                                  flexShrink: 0,
                                }}
                              >
                                {initial}
                              </div>
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div
                                  style={{
                                    fontWeight: 600,
                                    fontSize: '13.5px',
                                    color: 'var(--text-primary)',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                  }}
                                  title={app.job?.title}
                                >
                                  {app.job?.title || 'Job Title'}
                                </div>
                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                                  {app.job?.company_name || 'Company'}
                                  {app.job?.location ? ` • ${app.job.location}` : ''}
                                </div>
                              </div>
                            </div>

                            {/* Applied Date & Portal link */}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                              {app.applied_date ? (
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <Calendar size={11} />
                                  Applied {new Date(app.applied_date).toLocaleDateString()}
                                </span>
                              ) : (
                                <span>Tracked {new Date(app.created_at).toLocaleDateString()}</span>
                              )}

                              {app.job?.job_url && (
                                <a
                                  href={app.job.job_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    color: 'var(--accent-primary)',
                                    textDecoration: 'none',
                                    fontWeight: 600,
                                  }}
                                >
                                  Portal <ExternalLink size={10} />
                                </a>
                              )}
                            </div>

                            {/* Private Notes snippet */}
                            {app.notes && (
                              <div
                                style={{
                                  fontSize: '11.5px',
                                  color: 'var(--text-muted)',
                                  fontStyle: 'italic',
                                  backgroundColor: 'rgba(255, 255, 255, 0.02)',
                                  padding: '6px 8px',
                                  borderRadius: '4px',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                "{app.notes}"
                              </div>
                            )}

                            {/* Quick Action Decision / Toggle Bar */}
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                paddingTop: '8px',
                                borderTop: '1px solid var(--border-subtle)',
                              }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              {/* 1-Click Toggle between Applied and Not Applied */}
                              <div style={{ display: 'flex', gap: '4px' }}>
                                <button
                                  type="button"
                                  onClick={() => handleStageTransition(app.id, 'APPLIED')}
                                  title="Mark as Applied (Liked)"
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    padding: '3px 7px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    backgroundColor: isApplied ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
                                    border: isApplied ? '1px solid var(--success)' : '1px solid var(--border-subtle)',
                                    color: isApplied ? 'var(--success)' : 'var(--text-muted)',
                                  }}
                                >
                                  <ThumbsUp size={11} fill={isApplied ? 'currentColor' : 'none'} />
                                  <span>Applied</span>
                                </button>

                                <button
                                  type="button"
                                  onClick={() => handleStageTransition(app.id, 'NOT_APPLIED')}
                                  title="Mark as Not Applied (Disliked)"
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    padding: '3px 7px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    backgroundColor: isNotApplied ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                                    border: isNotApplied ? '1px solid var(--danger)' : '1px solid var(--border-subtle)',
                                    color: isNotApplied ? 'var(--danger)' : 'var(--text-muted)',
                                  }}
                                >
                                  <ThumbsDown size={11} fill={isNotApplied ? 'currentColor' : 'none'} />
                                  <span>Not Applied</span>
                                </button>
                              </div>

                              {/* Stage navigation buttons */}
                              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                {prevStage && (
                                  <button
                                    type="button"
                                    onClick={() => handleStageTransition(app.id, prevStage.id)}
                                    title={`Move back to ${prevStage.label}`}
                                    style={{
                                      background: 'transparent',
                                      border: '1px solid var(--border-subtle)',
                                      borderRadius: '4px',
                                      padding: '3px 5px',
                                      color: 'var(--text-muted)',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                    }}
                                  >
                                    <ChevronLeft size={13} />
                                  </button>
                                )}
                                {nextStage && (
                                  <button
                                    type="button"
                                    onClick={() => handleStageTransition(app.id, nextStage.id)}
                                    title={`Advance to ${nextStage.label}`}
                                    style={{
                                      background: 'transparent',
                                      border: '1px solid var(--border-subtle)',
                                      borderRadius: '4px',
                                      padding: '3px 5px',
                                      color: 'var(--text-muted)',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                    }}
                                  >
                                    <ChevronRight size={13} />
                                  </button>
                                )}
                              </div>
                            </div>
                          </Card>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal for Application Details & Interview Tracker */}
      <ApplicationModal
        application={selectedApp}
        isOpen={!!selectedApp}
        onClose={() => setSelectedApp(null)}
        onUpdated={() => {
          fetchApplications();
          window.dispatchEvent(new CustomEvent('app:refresh-data'));
        }}
      />
    </AppLayout>
  );
};
