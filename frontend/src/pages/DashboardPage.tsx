import React, { useEffect, useState, useMemo } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { Spinner } from '../components/common/Spinner';
import { MatchDetailModal, type JobMatch } from '../components/matches/MatchDetailModal';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import {
  Mail,
  Briefcase,
  Send,
  Calendar,
  CalendarCheck,
  RefreshCw,
  RotateCw,
  X,
  CheckCircle2,
  Bookmark,
  BookmarkCheck,
  Volume2,
  VolumeX,
  Star,
  Zap,
  Copy,
  Bell,
  Check,
  Brain,
  SlidersHorizontal,
  Upload,
  ExternalLink,
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Modal } from '../components/common/Modal';
import { Button } from '../components/common/Button';

interface DashboardKPIs {
  total_emails_ingested: number;
  total_jobs_discovered: number;
  unique_jobs_count: number;
  duplicate_jobs_count: number;
  duplicate_rate_percentage: number;
  high_match_jobs_count: number;
  average_match_score: number;
  total_applications: number;
  active_applications: number;
  interview_rate_percentage: number;
  offer_rate_percentage: number;
}

interface ActivityItem {
  id: string;
  activity_type: string;
  title: string;
  description: string;
  timestamp: string;
}

interface RealEmailItem {
  id: string;
  sender: string;
  subject: string;
  category: string;
  received_at: string;
  processed_status: string;
}

interface RealApplicationItem {
  id: string;
  job_id: string;
  status: string;
  applied_date?: string;
  job?: {
    company_name: string;
    title: string;
    location?: string;
    work_mode?: string;
  };
}

interface RealJobItem {
  id: string;
  title: string;
  company_name: string;
  work_mode: string;
  location?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  min_experience_years?: number;
  max_experience_years?: number;
  platform_source: string;
  required_skills: string[];
  preferred_skills: string[];
  job_url?: string;
  source_email_id?: string;
  created_at: string;
}

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [jobs, setJobs] = useState<RealJobItem[]>([]);
  const [emails, setEmails] = useState<RealEmailItem[]>([]);
  const [applications, setApplications] = useState<RealApplicationItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showSyncBanner, setShowSyncBanner] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);
  const [applyFeedbackModal, setApplyFeedbackModal] = useState<{
    isOpen: boolean;
    jobTitle: string;
    companyName: string;
    jobUrl?: string;
    isOpened: boolean;
  } | null>(null);

  // Filters
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [activeIntelFilter, setActiveIntelFilter] = useState<string>('all');

  // Interactive Bookmarks & Applied states
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [appliedJobIds, setAppliedJobIds] = useState<Set<string>>(new Set());

  // Modals & Audio
  const [selectedMatch, setSelectedMatch] = useState<JobMatch | null>(null);
  const [isDigestOpen, setIsDigestOpen] = useState<boolean>(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState<boolean>(false);

  // Time-aware greeting
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }, []);

  const userName = user?.full_name ? user.full_name.split(' ')[0] : (user?.email ? user.email.split('@')[0] : 'Candidate');

  const loadRealData = async () => {
    try {
      const [analyticsRes, matchesRes, jobsRes, emailsRes, appsRes] = await Promise.allSettled([
        api.get<{ kpis: DashboardKPIs; recent_activities: ActivityItem[] }>('/analytics'),
        api.get<{ items: JobMatch[]; total: number }>('/matches?limit=100'),
        api.get<{ items: RealJobItem[]; total: number }>('/jobs?limit=100'),
        api.get<{ items: RealEmailItem[]; total: number }>('/emails?limit=5'),
        api.get<{ items: RealApplicationItem[]; total: number }>('/applications?limit=100'),
      ]);

      if (analyticsRes.status === 'fulfilled') {
        setKpis(analyticsRes.value.kpis);
      }
      if (matchesRes.status === 'fulfilled') {
        setMatches(matchesRes.value.items || []);
      }
      if (jobsRes.status === 'fulfilled') {
        setJobs(jobsRes.value.items || []);
      }
      if (emailsRes.status === 'fulfilled') {
        setEmails(emailsRes.value.items || []);
      }
      if (appsRes.status === 'fulfilled') {
        const appList = appsRes.value.items || [];
        setApplications(appList);
        // Only count jobs as "applied" if they have an active application status
        // DISCOVERED means the job was found in email but not yet applied for
        const APPLIED_STATUSES = new Set(['APPLIED', 'INTERVIEWING', 'OFFER']);
        const appliedSet = new Set<string>();
        appList.forEach((a) => {
          if (a.job_id && APPLIED_STATUSES.has(a.status)) appliedSet.add(a.job_id);
        });
        setAppliedJobIds(appliedSet);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const [isReloading, setIsReloading] = useState<boolean>(false);

  const handleReloadData = async () => {
    setIsReloading(true);
    try {
      await loadRealData();
    } finally {
      setTimeout(() => setIsReloading(false), 500);
    }
  };

  useEffect(() => {
    loadRealData();
    const handleGlobalRefresh = () => {
      loadRealData();
    };
    window.addEventListener('app:refresh-data', handleGlobalRefresh);
    return () => window.removeEventListener('app:refresh-data', handleGlobalRefresh);
  }, []);

  const handleManualSync = async () => {
    setIsSyncing(true);
    setSyncFeedback('Initiating live Gmail sync & autonomous processing...');
    setShowSyncBanner(true);

    try {
      await api.post('/gmail/sync', { max_results: 25 });
      setSyncFeedback('Gmail sync completed successfully.');
      await loadRealData();
    } catch (err: any) {
      setSyncFeedback(err.message || 'Gmail sync completed.');
      await loadRealData();
    } finally {
      setTimeout(() => {
        setIsSyncing(false);
      }, 1500);
      setTimeout(() => {
        setSyncFeedback(null);
      }, 6000);
    }
  };

  const toggleBookmark = (id: string) => {
    setBookmarkedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleQuickApply = async (jobId: string, title: string) => {
    const matchObj = matches.find((m) => m.job_id === jobId);
    const jobObj = jobs.find((j) => j.id === jobId);
    const company = matchObj?.company_name || jobObj?.company_name || 'Hiring Organization';
    const jobUrl = matchObj?.job_url || jobObj?.job_url;

    let opened = false;
    if (jobUrl) {
      try {
        window.open(jobUrl, '_blank', 'noopener,noreferrer');
        opened = true;
      } catch (e) {
        console.warn('Could not auto-open application tab:', e);
      }
    }

    try {
      await api.post('/applications', {
        job_id: jobId,
        status: 'APPLIED',
        applied_date: new Date().toISOString(),
        notes: `Applied from Job Intelligence Dashboard for role: ${title} at ${company}`,
      });
      // Optimistically mark as applied
      setAppliedJobIds((prev) => new Set(prev).add(jobId));
      // Refresh data to sync with server — do not await to prevent blocking UI
      loadRealData().catch(console.error);

      setApplyFeedbackModal({
        isOpen: true,
        jobTitle: title,
        companyName: company,
        jobUrl: jobUrl || undefined,
        isOpened: opened,
      });
    } catch (err: any) {
      console.error('Quick apply failed:', err);
      // Do NOT optimistically mark as applied if the request failed
      alert(`Could not track application: ${err.message || 'Please try again.'}`);
    }
  };

  // Filter matches or jobs
  const displayItems = useMemo(() => {
    if (matches.length > 0) {
      let filtered = matches;
      if (sourceFilter !== 'all') {
        // filter if metadata contains source
      }
      if (activeIntelFilter === 'strong_matches') {
        filtered = filtered.filter((m) => m.overall_match_score >= 80);
      }
      return filtered;
    }
    return [];
  }, [matches, sourceFilter, activeIntelFilter]);

  const formatSalary = (min?: number, max?: number, currency: string = 'INR') => {
    if (!min && !max) return 'Salary undisclosed';
    const sym = currency === 'INR' ? '₹' : '$';
    if (min && max) return `${sym}${min / 100000}L–${max / 100000}L PA`;
    if (min) return `From ${sym}${min / 100000}L PA`;
    return `Up to ${sym}${(max || 0) / 100000}L PA`;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Recently';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return 'Recently';
    }
  };

  return (
    <AppLayout
      title="Job Intelligence Dashboard"
      onRefresh={handleReloadData}
      isRefreshing={isReloading}
    >
      {isLoading ? (
        <Spinner size={36} text="Fetching live intelligence data..." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* 1. Dynamic Ingestion Progress Strip */}
          {showSyncBanner && (
            <div className="stitch-sync-banner">
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={handleReloadData}
                  className="stitch-sync-icon-circle"
                  style={{ cursor: 'pointer', border: 'none' }}
                  title="Click to refresh dashboard data"
                >
                  <RefreshCw
                    size={16}
                    style={{
                      animation: (isSyncing || isReloading) ? 'spin 1s linear infinite' : 'none',
                    }}
                  />
                </button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {isSyncing ? 'Synchronizing Gmail and AI matching pipeline' : 'Autonomous AI Intelligence Engine'}
                    </span>
                    <span
                      style={{
                        padding: '2px 8px',
                        background: 'rgba(99, 102, 241, 0.15)',
                        color: 'var(--primary)',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 700,
                      }}
                    >
                      {isSyncing ? 'Active' : 'Live'}
                    </span>
                  </div>

                  <div className="stitch-sync-steps">
                    <span className="stitch-sync-step-done">
                      <CheckCircle2 size={13} /> {kpis?.total_emails_ingested || 0} Emails Ingested
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>›</span>
                    <span className="stitch-sync-step-done">
                      <CheckCircle2 size={13} /> {kpis?.unique_jobs_count || 0} Jobs Extracted
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>›</span>
                    <span className="stitch-sync-step-done">
                      <CheckCircle2 size={13} /> {kpis?.high_match_jobs_count || 0} Strong Matches
                    </span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {syncFeedback && (
                  <span
                    style={{
                      fontSize: '12px',
                      color:
                        syncFeedback.toLowerCase().includes('error') ||
                        syncFeedback.toLowerCase().includes('failed') ||
                        syncFeedback.toLowerCase().includes('unexpected')
                          ? '#f87171'
                          : '#34d399',
                      fontWeight: 500,
                    }}
                  >
                    {syncFeedback}
                  </span>
                )}
                <button
                  onClick={() => setShowSyncBanner(false)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    borderRadius: '4px',
                  }}
                  title="Dismiss"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
          )}

          {/* 2. Executive Greeting Header */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'flex-end',
              justifyContent: 'space-between',
              gap: '16px',
              flexWrap: 'wrap',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                <h1 style={{ fontSize: '28px', fontWeight: 700, margin: 0, letterSpacing: '-0.02em' }}>
                  {greeting}, {userName}
                </h1>
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '3px 9px',
                    borderRadius: '9999px',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: '#34d399',
                    fontSize: '11px',
                    fontWeight: 700,
                    letterSpacing: '0.04em',
                  }}
                >
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: '#10b981',
                      boxShadow: '0 0 8px #10b981',
                    }}
                  />
                  LIVE
                </span>
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
                {kpis && kpis.total_emails_ingested > 0 ? (
                  <>
                    Processed{' '}
                    <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                      {kpis.total_emails_ingested} job emails
                    </span>{' '}
                    • Discovered {kpis.unique_jobs_count} unique opportunities ({kpis.duplicate_jobs_count} duplicates filtered)
                  </>
                ) : (
                  'Connect Gmail and upload your resume to discover matched opportunities.'
                )}
              </p>
            </div>

            {/* Action Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <div style={{ position: 'relative' }}>
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  style={{
                    appearance: 'none',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                    fontWeight: 500,
                    padding: '8px 32px 8px 14px',
                    borderRadius: '10px',
                    border: '1px solid var(--border-medium)',
                    cursor: 'pointer',
                    outline: 'none',
                  }}
                >
                  <option value="all">All Sources ({jobs.length})</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="naukri">Naukri</option>
                  <option value="indeed">Indeed</option>
                </select>
                <SlidersHorizontal
                  size={14}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                    pointerEvents: 'none',
                  }}
                />
              </div>

              <button
                className="btn btn-secondary"
                onClick={() => setIsDigestOpen(true)}
                style={{ padding: '8px 16px', fontSize: '13px' }}
              >
                <Calendar size={15} style={{ color: 'var(--primary)' }} />
                <span>Executive Digest</span>
              </button>

              <button
                className="btn btn-secondary"
                onClick={handleReloadData}
                disabled={isReloading}
                style={{ padding: '8px 16px', fontSize: '13px' }}
                title="Reload dashboard intelligence and stats"
              >
                <RotateCw size={15} className={isReloading ? 'animate-spin' : ''} />
                <span>{isReloading ? 'Refreshing...' : 'Refresh'}</span>
              </button>

              <button
                className="btn btn-primary"
                onClick={handleManualSync}
                disabled={isSyncing}
                style={{ padding: '8px 18px', fontSize: '13px' }}
              >
                <RefreshCw size={15} className={isSyncing ? 'animate-spin' : ''} />
                <span>{isSyncing ? 'Syncing...' : 'Sync Gmail'}</span>
              </button>
            </div>
          </div>

          {/* 3. Five High-Impact Summary KPI Cards with Real Data */}
          <div className="stitch-kpi-grid">
            {/* Card 1: Unique Discovered Jobs */}
            <div className="stitch-kpi-card">
              <div className="stitch-kpi-label">
                <span>Unique Jobs</span>
                <Briefcase size={16} style={{ color: 'var(--info)' }} />
              </div>
              <div className="stitch-kpi-number">
                <span>{kpis?.unique_jobs_count || 0}</span>
                {kpis && kpis.total_jobs_discovered > kpis.unique_jobs_count && (
                  <span
                    style={{
                      fontSize: '12px',
                      fontWeight: 700,
                      color: '#34d399',
                    }}
                  >
                    +{kpis.total_jobs_discovered - kpis.unique_jobs_count} dups
                  </span>
                )}
              </div>
              <div className="stitch-kpi-subtext">
                {kpis?.total_jobs_discovered || 0} total roles discovered
              </div>
            </div>

            {/* Card 2: Strong Matches */}
            <div className="stitch-kpi-card stitch-kpi-emerald">
              <div className="stitch-kpi-label" style={{ color: '#34d399' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Star size={14} fill="#10b981" /> Strong Matches
                </span>
                <span
                  style={{
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(16, 185, 129, 0.25)',
                    color: '#6ee7b7',
                    fontSize: '10px',
                    fontWeight: 800,
                  }}
                >
                  ≥80%
                </span>
              </div>
              <div className="stitch-kpi-number" style={{ color: '#6ee7b7' }}>
                <span>{kpis?.high_match_jobs_count || 0}</span>
                <span style={{ fontSize: '12px', color: '#a7f3d0', fontWeight: 600 }}>
                  Ready
                </span>
              </div>
              <div className="stitch-kpi-subtext" style={{ color: '#d1fae5' }}>
                Avg Compatibility: {kpis?.average_match_score || 0}%
              </div>
            </div>

            {/* Card 3: Ingested Emails */}
            <div className="stitch-kpi-card">
              <div className="stitch-kpi-label">
                <span>Emails Ingested</span>
                <Mail size={16} style={{ color: 'var(--text-muted)' }} />
              </div>
              <div className="stitch-kpi-number">
                <span>{kpis?.total_emails_ingested || 0}</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--primary)' }}>
                  100%
                </span>
              </div>
              <div className="stitch-kpi-subtext">
                {kpis?.duplicate_jobs_count || 0} duplicates filtered out
              </div>
            </div>

            {/* Card 4: Active Applications */}
            <div className="stitch-kpi-card">
              <div className="stitch-kpi-label">
                <span>Active Pipeline</span>
                <Send size={16} style={{ color: 'var(--warning)' }} />
              </div>
              <div className="stitch-kpi-number">
                <span>{kpis?.active_applications || 0}</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
                  Active
                </span>
              </div>
              <div className="stitch-kpi-subtext">
                {kpis?.total_applications || 0} total applications submitted
              </div>
            </div>

            {/* Card 5: Interviews & Rate */}
            <div className="stitch-kpi-card">
              <div className="stitch-kpi-label">
                <span>Interviews</span>
                <CalendarCheck size={16} style={{ color: '#10b981' }} />
              </div>
              <div className="stitch-kpi-number">
                <span>
                  {kpis && kpis.total_applications > 0
                    ? Math.round(((kpis.interview_rate_percentage || 0) / 100) * kpis.total_applications)
                    : 0}
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 800,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                    color: '#a5b4fc',
                  }}
                >
                  {kpis?.interview_rate_percentage || 0}%
                </span>
              </div>
              <div className="stitch-kpi-subtext">
                Interview conversion rate
              </div>
            </div>
          </div>

          {/* 4. Today's Job Intelligence Filter Bar with Real Values */}
          <div className="stitch-pill-bar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Brain size={18} style={{ color: 'var(--primary)' }} />
              <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
                Job Intelligence Distribution
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <button
                className={`stitch-pill ${activeIntelFilter === 'all' ? 'stitch-pill-active' : ''}`}
                onClick={() => setActiveIntelFilter('all')}
              >
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--primary)',
                  }}
                />
                <span>
                  <strong>{kpis?.unique_jobs_count || 0}</strong> Discovered Jobs
                </span>
              </button>

              <button
                className={`stitch-pill stitch-pill-emerald-glow ${
                  activeIntelFilter === 'strong_matches' ? 'stitch-pill-active' : ''
                }`}
                onClick={() =>
                  setActiveIntelFilter(activeIntelFilter === 'strong_matches' ? 'all' : 'strong_matches')
                }
              >
                <CheckCircle2 size={14} style={{ color: '#10b981' }} />
                <span>{kpis?.high_match_jobs_count || 0} Strong Matches</span>
              </button>

              <div
                className="stitch-pill"
                style={{ cursor: 'default' }}
              >
                <Copy size={13} style={{ color: 'var(--text-muted)' }} />
                <span>{kpis?.duplicate_jobs_count || 0} Duplicates Filtered</span>
              </div>

              <div
                className="stitch-pill"
                style={{ cursor: 'default' }}
              >
                <Bell size={13} style={{ color: 'var(--warning)' }} />
                <span>{kpis?.active_applications || 0} Active Applications</span>
              </div>
            </div>
          </div>

          {/* 5. Main Content Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 8fr) minmax(320px, 4fr)',
              gap: '24px',
              alignItems: 'start',
            }}
          >
            {/* Left Column: Top Matches / Discovered Jobs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingBottom: '2px',
                }}
              >
                <div>
                  <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>
                    {matches.length > 0 ? 'Top Job Matches' : 'Discovered Job Opportunities'}
                  </h2>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                    {matches.length > 0
                      ? 'AI-matched roles based on your uploaded resume skills and experience'
                      : 'Jobs extracted from your ingested email communications'}
                  </p>
                </div>
                <Link
                  to={matches.length > 0 ? '/matches' : '/jobs'}
                  style={{
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--primary)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  View all ({matches.length > 0 ? matches.length : jobs.length}) →
                </Link>
              </div>

              {/* Render Real Match Cards if matches computed */}
              {matches.length > 0 ? (
                displayItems.map((m) => {
                  const initials = m.company_name
                    ? m.company_name.split(' ').map((w) => w[0]).join('').slice(0, 3).toUpperCase()
                    : 'JOB';
                  const score = Math.round(m.overall_match_score || 0);
                  const isBookmarked = bookmarkedIds.has(m.id);
                  const isApplied = appliedJobIds.has(m.job_id);

                  return (
                    <div key={m.id} className="stitch-job-card">
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          justifyContent: 'space-between',
                          gap: '12px',
                          flexWrap: 'wrap',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', minWidth: 0 }}>
                          <div className={`stitch-avatar-badge ${score >= 80 ? 'emerald' : ''}`}>
                            {initials}
                          </div>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <h3
                                onClick={() => setSelectedMatch(m)}
                                style={{
                                  fontSize: '16px',
                                  fontWeight: 700,
                                  margin: 0,
                                  cursor: 'pointer',
                                  color: 'var(--text-primary)',
                                }}
                              >
                                {m.job_title}
                              </h3>
                            </div>
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '13px',
                                color: 'var(--text-secondary)',
                                marginTop: '4px',
                                flexWrap: 'wrap',
                              }}
                            >
                              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                {m.company_name}
                              </span>
                              <span>•</span>
                              <span>{formatDate(m.created_at)}</span>
                            </div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                          <span className="stitch-score-pill">
                            <Zap size={13} fill="#10b981" />
                            {score}% Match
                          </span>
                          <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 600, marginTop: '3px' }}>
                            {score >= 80 ? 'Strong Match' : score >= 60 ? 'Moderate Fit' : 'Fair'}
                          </span>
                        </div>
                      </div>

                      {/* Skills */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        {m.matched_skills?.slice(0, 5).map((skill) => (
                          <span key={skill} className="stitch-skill-chip">
                            {skill}
                          </span>
                        ))}
                      </div>

                      {/* AI Breakdown */}
                      <div className="stitch-ai-breakdown">
                        <div className="stitch-ai-breakdown-title">
                          <Brain size={14} />
                          <span>AI Breakdown</span>
                        </div>
                        <div className="stitch-ai-criteria-list">
                          {m.matched_skills?.slice(0, 4).map((c) => (
                            <span key={c} className="stitch-ai-check-item">
                              <CheckCircle2 size={13} /> {c}
                            </span>
                          ))}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', paddingTop: '2px' }}>
                          {m.missing_required_skills && m.missing_required_skills.length > 0 ? (
                            <span>
                              <span style={{ color: 'var(--danger)', fontWeight: 600 }}>Missing:</span>{' '}
                              {m.missing_required_skills.join(', ')}
                            </span>
                          ) : (
                            <span style={{ color: '#34d399', fontWeight: 500 }}>
                              Profile satisfies all identified core requisites
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Footer */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '12px',
                          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                          paddingTop: '12px',
                          fontSize: '12px',
                          color: 'var(--text-secondary)',
                          flexWrap: 'wrap',
                        }}
                      >
                        <div>
                          <span>Computed: {formatDate(m.created_at)}</span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <button
                            onClick={() => toggleBookmark(m.id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: isBookmarked ? '#f59e0b' : 'var(--text-muted)',
                              cursor: 'pointer',
                              padding: '6px',
                              borderRadius: '8px',
                              display: 'flex',
                              alignItems: 'center',
                            }}
                            title={isBookmarked ? 'Bookmarked' : 'Save'}
                          >
                            {isBookmarked ? <BookmarkCheck size={17} /> : <Bookmark size={17} />}
                          </button>

                          <button
                            onClick={() => setSelectedMatch(m)}
                            className="btn btn-ghost btn-sm"
                            style={{ color: 'var(--primary)' }}
                          >
                            View Job Details →
                          </button>

                          {m.job_url && (
                            <a
                              href={m.job_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ textDecoration: 'none' }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <button
                                className="btn btn-secondary btn-sm"
                                style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                                title="Open official job portal"
                              >
                                <span>Portal</span>
                                <ExternalLink size={12} />
                              </button>
                            </a>
                          )}

                          {isApplied ? (
                            <span
                              style={{
                                padding: '6px 14px',
                                borderRadius: '8px',
                                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                                color: 'var(--text-primary)',
                                fontSize: '13px',
                                fontWeight: 600,
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '5px',
                              }}
                            >
                              <Check size={14} style={{ color: '#10b981' }} /> Applied
                            </span>
                          ) : (
                            <button
                              onClick={() => handleQuickApply(m.job_id, m.job_title)}
                              className="btn btn-primary btn-sm"
                              title="Open job application link in new tab and record in your pipeline"
                            >
                              Quick Apply
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : jobs.length > 0 ? (
                /* Discovered Jobs List when matches have not been computed */
                jobs.map((job) => {
                  const initials = job.company_name
                    ? job.company_name.split(' ').map((w) => w[0]).join('').slice(0, 3).toUpperCase()
                    : 'JOB';
                  const isBookmarked = bookmarkedIds.has(job.id);
                  const isApplied = appliedJobIds.has(job.id);

                  return (
                    <div key={job.id} className="stitch-job-card">
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          justifyContent: 'space-between',
                          gap: '12px',
                          flexWrap: 'wrap',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', minWidth: 0 }}>
                          <div className="stitch-avatar-badge">{initials}</div>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                                {job.title}
                              </h3>
                              <span
                                style={{
                                  fontSize: '11px',
                                  padding: '2px 8px',
                                  borderRadius: '9999px',
                                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                                  color: 'var(--text-secondary)',
                                }}
                              >
                                {job.work_mode}
                              </span>
                            </div>
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '13px',
                                color: 'var(--text-secondary)',
                                marginTop: '4px',
                                flexWrap: 'wrap',
                              }}
                            >
                              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                {job.company_name}
                              </span>
                              {job.location && (
                                <>
                                  <span>•</span>
                                  <span>{job.location}</span>
                                </>
                              )}
                              <span>•</span>
                              <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                                {formatSalary(job.salary_min, job.salary_max, job.salary_currency)}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div>
                          <span
                            style={{
                              fontSize: '11px',
                              fontWeight: 700,
                              padding: '4px 10px',
                              borderRadius: '9999px',
                              backgroundColor: 'rgba(99, 102, 241, 0.15)',
                              color: '#a5b4fc',
                            }}
                          >
                            Extracted
                          </span>
                        </div>
                      </div>

                      {/* Required skills */}
                      {job.required_skills && job.required_skills.length > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                          {job.required_skills.slice(0, 5).map((s) => (
                            <span key={s} className="stitch-skill-chip">
                              {s}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Card Footer */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '12px',
                          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                          paddingTop: '12px',
                          fontSize: '12px',
                          color: 'var(--text-secondary)',
                          flexWrap: 'wrap',
                        }}
                      >
                        <div>
                          <span>Source: {job.platform_source}</span>
                          <span> • </span>
                          <span>{formatDate(job.created_at)}</span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <button
                            onClick={() => toggleBookmark(job.id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: isBookmarked ? '#f59e0b' : 'var(--text-muted)',
                              cursor: 'pointer',
                              padding: '6px',
                              borderRadius: '8px',
                              display: 'flex',
                              alignItems: 'center',
                            }}
                          >
                            {isBookmarked ? <BookmarkCheck size={17} /> : <Bookmark size={17} />}
                          </button>

                          {job.job_url && (
                            <a
                              href={job.job_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ textDecoration: 'none' }}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <button
                                className="btn btn-secondary btn-sm"
                                style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                                title="Open official job portal"
                              >
                                <span>Portal</span>
                                <ExternalLink size={12} />
                              </button>
                            </a>
                          )}

                          {isApplied ? (
                            <span
                              style={{
                                padding: '6px 14px',
                                borderRadius: '8px',
                                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                                color: 'var(--text-primary)',
                                fontSize: '13px',
                                fontWeight: 600,
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '5px',
                              }}
                            >
                              <Check size={14} style={{ color: '#10b981' }} /> Applied
                            </span>
                          ) : (
                            <button
                              onClick={() => handleQuickApply(job.id, job.title)}
                              className="btn btn-primary btn-sm"
                              title="Open job application link in new tab and record in your pipeline"
                            >
                              Quick Apply
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                /* Empty State */
                <div
                  style={{
                    padding: '48px 24px',
                    textAlign: 'center',
                    background: 'var(--bg-card)',
                    borderRadius: '16px',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '16px',
                  }}
                >
                  <Briefcase size={36} style={{ color: 'var(--text-muted)' }} />
                  <div>
                    <h3 style={{ fontSize: '17px', margin: '0 0 6px 0' }}>No Jobs Discovered Yet</h3>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '420px', margin: 0 }}>
                      Connect your Gmail account or sync incoming messages to automatically parse job opportunities and calculate compatibility scores.
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <Link to="/resume">
                      <button className="btn btn-primary">
                        <Upload size={16} /> Upload Resume
                      </button>
                    </Link>
                    <button className="btn btn-secondary" onClick={handleManualSync}>
                      <RefreshCw size={16} /> Sync Gmail Now
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Digest, Real Emails Feed, and Real Applications */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* 1. Daily Job Digest Summary Card */}
              <div className="stitch-digest-card">
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                    paddingBottom: '12px',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        color: 'var(--text-muted)',
                      }}
                    >
                      Real Intelligence Summary
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Executive Digest
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: '11px',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      backgroundColor: 'rgba(255, 255, 255, 0.06)',
                      color: 'var(--text-secondary)',
                      fontWeight: 500,
                    }}
                  >
                    {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <div className="stitch-digest-row">
                    <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Mail size={15} style={{ color: 'var(--text-muted)' }} /> Emails processed
                    </span>
                    <span style={{ fontWeight: 600 }}>{kpis?.total_emails_ingested || 0}</span>
                  </div>

                  <div className="stitch-digest-row">
                    <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Briefcase size={15} style={{ color: 'var(--info)' }} /> Unique jobs extracted
                    </span>
                    <span style={{ fontWeight: 700, color: 'var(--primary)' }}>
                      {kpis?.unique_jobs_count || 0}
                    </span>
                  </div>

                  <div className="stitch-digest-row">
                    <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Copy size={15} style={{ color: 'var(--text-muted)' }} /> Duplicates filtered out
                    </span>
                    <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>
                      {kpis?.duplicate_jobs_count || 0}
                    </span>
                  </div>

                  <div className="stitch-digest-row">
                    <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Star size={15} style={{ color: '#10b981' }} /> Strong matches (&gt;80%)
                    </span>
                    <span style={{ fontWeight: 700, color: '#34d399' }}>
                      {kpis?.high_match_jobs_count || 0}
                    </span>
                  </div>

                  <div className="stitch-digest-row">
                    <span style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Send size={15} style={{ color: 'var(--warning)' }} /> Active applications
                    </span>
                    <span style={{ fontWeight: 600, color: 'var(--warning)' }}>
                      {kpis?.active_applications || 0}
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    paddingTop: '8px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <button
                    className="btn btn-secondary"
                    onClick={() => setIsDigestOpen(true)}
                    style={{ flex: 1, fontSize: '13px' }}
                  >
                    View Executive Report
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setIsAudioPlaying(!isAudioPlaying)}
                    style={{
                      padding: '8px 12px',
                      fontSize: '13px',
                      color: isAudioPlaying ? '#10b981' : 'var(--primary)',
                    }}
                    title="Audio briefing"
                  >
                    {isAudioPlaying ? <Volume2 size={16} /> : <VolumeX size={16} />}
                    <span>{isAudioPlaying ? 'Playing' : 'Audio'}</span>
                  </button>
                </div>
              </div>

              {/* 2. Real Ingested Emails (Live Feed) */}
              <div className="stitch-digest-card">
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                    paddingBottom: '10px',
                  }}
                >
                  <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Recent Job Emails
                  </span>
                  <Link to="/emails" style={{ fontSize: '11px', color: 'var(--primary)', fontWeight: 600 }}>
                    View all ({emails.length}) →
                  </Link>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {emails.length === 0 ? (
                    <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                      No emails ingested yet.
                    </div>
                  ) : (
                    emails.map((em) => (
                      <Link to="/emails" key={em.id} style={{ textDecoration: 'none' }}>
                        <div className="stitch-feed-item">
                          <span
                            style={{
                              width: '7px',
                              height: '7px',
                              borderRadius: '50%',
                              backgroundColor: 'var(--primary)',
                              marginTop: '6px',
                              flexShrink: 0,
                            }}
                          />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: '6px',
                              }}
                            >
                              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                                {em.sender}
                              </span>
                              <span style={{ fontSize: '11px', color: 'var(--text-muted)', flexShrink: 0 }}>
                                {formatDate(em.received_at)}
                              </span>
                            </div>
                            <p
                              style={{
                                fontSize: '12px',
                                color: 'var(--text-secondary)',
                                margin: '2px 0 6px 0',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                              }}
                            >
                              {em.subject}
                            </p>
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: '2px 6px',
                                borderRadius: '4px',
                                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                                color: 'var(--text-secondary)',
                              }}
                            >
                              {em.category}
                            </span>
                          </div>
                        </div>
                      </Link>
                    ))
                  )}
                </div>
              </div>

              {/* 3. Real Application Activity Widget */}
              <div className="stitch-digest-card">
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                    paddingBottom: '10px',
                  }}
                >
                  <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Application Pipeline
                  </span>
                  <Link
                    to="/applications"
                    style={{ fontSize: '12px', color: 'var(--primary)', fontWeight: 500 }}
                  >
                    Track ({applications.length}) →
                  </Link>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {applications.length === 0 ? (
                    <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                      No tracked applications yet.
                    </div>
                  ) : (
                    applications.map((app) => (
                      <div
                        key={app.id}
                        style={{
                          padding: '10px 12px',
                          borderRadius: '10px',
                          backgroundColor: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid rgba(255, 255, 255, 0.05)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '10px',
                        }}
                      >
                        <div style={{ minWidth: 0 }}>
                          <div
                            style={{
                              fontSize: '13px',
                              fontWeight: 600,
                              color: 'var(--text-primary)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}
                          >
                            {app.job?.title || 'Job Application'}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {app.job?.company_name || 'Company'} • {formatDate(app.applied_date)}
                          </div>
                        </div>

                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: '9999px',
                            flexShrink: 0,
                            backgroundColor:
                              app.status === 'OFFER' || app.status === 'INTERVIEWING'
                                ? 'rgba(16, 185, 129, 0.18)'
                                : 'rgba(99, 102, 241, 0.18)',
                            color:
                              app.status === 'OFFER' || app.status === 'INTERVIEWING'
                                ? '#34d399'
                                : '#a5b4fc',
                          }}
                        >
                          {app.status}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Real Match Detail Modal */}
      {selectedMatch && (
        <MatchDetailModal
          match={selectedMatch}
          isOpen={Boolean(selectedMatch)}
          trackingStatus={
            appliedJobIds.has(selectedMatch.job_id)
              ? 'APPLIED'
              : applications.find((a) => a.job_id === selectedMatch.job_id)?.status
          }
          onClose={() => setSelectedMatch(null)}
          onApplicationCreated={() => {
            setAppliedJobIds((prev) => new Set(prev).add(selectedMatch.job_id));
            loadRealData().catch(console.error);
          }}
          onLikeApply={(match) => {
            setAppliedJobIds((prev) => new Set(prev).add(match.job_id));
            loadRealData().catch(console.error);
          }}
        />
      )}

      {/* Executive Digest Modal */}
      {isDigestOpen && (
        <div className="modal-overlay" onClick={() => setIsDigestOpen(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '640px', padding: '28px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '18px',
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: 'var(--primary)',
                    letterSpacing: '0.04em',
                  }}
                >
                  Autonomous Executive Briefing
                </div>
                <h2 style={{ fontSize: '20px', fontWeight: 800, margin: '2px 0 0 0' }}>
                  Live Intelligence Report
                </h2>
              </div>
              <button
                onClick={() => setIsDigestOpen(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Content from real database */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', fontSize: '14px', lineHeight: 1.6 }}>
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  📊 Pipeline Summary
                </h4>
                <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
                  The intelligence engine has ingested <strong>{kpis?.total_emails_ingested || 0} emails</strong>,
                  extracting <strong>{kpis?.unique_jobs_count || 0} unique job opportunities</strong> while eliminating{' '}
                  <strong>{kpis?.duplicate_jobs_count || 0} duplicate listings</strong>.
                </p>
              </div>

              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  🎯 Candidate Compatibility
                </h4>
                <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
                  Identified <strong>{kpis?.high_match_jobs_count || 0} strong matches</strong> with an average compatibility
                  rating of <strong>{kpis?.average_match_score || 0}%</strong>.
                </p>
              </div>

              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  📁 Active Pipeline
                </h4>
                <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
                  You currently have <strong>{kpis?.active_applications || 0} active applications</strong> in progress
                  out of <strong>{kpis?.total_applications || 0} total tracked</strong>, with an interview conversion rate of{' '}
                  <strong>{kpis?.interview_rate_percentage || 0}%</strong>.
                </p>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '10px',
                marginTop: '24px',
                paddingTop: '16px',
                borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <button className="btn btn-secondary" onClick={() => setIsDigestOpen(false)}>
                Close
              </button>
              <Link to="/matches">
                <button className="btn btn-primary" onClick={() => setIsDigestOpen(false)}>
                  Explore Matches
                </button>
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Quick Apply Confirmation & Tracking Modal */}
      {applyFeedbackModal && (
        <Modal
          isOpen={applyFeedbackModal.isOpen}
          onClose={() => setApplyFeedbackModal(null)}
          title={applyFeedbackModal.isOpened ? "Application Portal Opened & Tracked" : "Application Saved to Pipeline"}
          maxWidth="540px"
          footer={
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', width: '100%', flexWrap: 'wrap' }}>
              <Button variant="ghost" size="md" onClick={() => setApplyFeedbackModal(null)}>
                Dismiss
              </Button>
              {applyFeedbackModal.jobUrl && (
                <Button
                  variant="outline"
                  size="md"
                  rightIcon={<ExternalLink size={14} />}
                  onClick={() => window.open(applyFeedbackModal.jobUrl, '_blank')}
                >
                  Re-open Application Site
                </Button>
              )}
              <Button
                variant="primary"
                size="md"
                onClick={() => {
                  setApplyFeedbackModal(null);
                  navigate('/applications');
                }}
              >
                View in Applications Tracker →
              </Button>
            </div>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '8px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '12px',
                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <CheckCircle2 size={24} style={{ color: 'var(--success)' }} />
              </div>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '0 0 4px 0', color: 'var(--text-primary)' }}>
                  {applyFeedbackModal.jobTitle}
                </h3>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                  {applyFeedbackModal.companyName}
                </div>
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '14px 16px',
                fontSize: '13.5px',
                color: 'var(--text-secondary)',
                lineHeight: 1.6,
              }}
            >
              {applyFeedbackModal.isOpened ? (
                <>
                  <p style={{ margin: '0 0 8px 0', color: 'var(--text-primary)', fontWeight: 600 }}>
                    🚀 Official job application page opened in a new tab!
                  </p>
                  <p style={{ margin: 0 }}>
                    We launched the hiring portal for <strong>{applyFeedbackModal.companyName}</strong> so you can review their requirements and apply directly.
                  </p>
                </>
              ) : (
                <p style={{ margin: 0 }}>
                  This position has been saved to your pipeline. You can review the email details or add custom notes anytime.
                </p>
              )}
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                backgroundColor: 'rgba(99, 102, 241, 0.08)',
                borderRadius: '8px',
                border: '1px solid rgba(99, 102, 241, 0.2)',
                fontSize: '12.5px',
                color: 'var(--accent-primary)',
              }}
            >
              <span>📋</span>
              <span>
                Status updated to <strong>APPLIED</strong> in your <strong>Applications</strong> tab.
              </span>
            </div>
          </div>
        </Modal>
      )}
    </AppLayout>
  );
};
export default DashboardPage;
