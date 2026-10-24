import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Table, type Column } from '../components/common/Table';
import { JobFilterBar } from '../components/jobs/JobFilterBar';
import { JobCard } from '../components/jobs/JobCard';
import { JobDetailModal, type Job } from '../components/jobs/JobDetailModal';
import { getApplicationStatusConfig } from '../components/jobs/statusUtils';
import { api } from '../api/client';
import {
  Briefcase,
  Globe,
  Building2,
  GitMerge,
  ExternalLink,
  Eye,
  Layers,
  Sparkles,
} from 'lucide-react';

interface JobListResponse {
  items: Job[];
  total: number;
  skip: number;
  limit: number;
}

interface ApplicationSummaryItem {
  id: string;
  job_id?: string;
  status: string;
  job?: { company_name?: string; title?: string };
}

interface MatchSummaryItem {
  id: string;
  job_id: string;
  overall_match_score: number;
  company_name?: string;
  job_title?: string;
}

export const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [search, setSearch] = useState<string>('');
  const [workMode, setWorkMode] = useState<string>('ALL');
  const [includeDuplicates, setIncludeDuplicates] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [isDeduplicating, setIsDeduplicating] = useState<boolean>(false);

  // Pipeline Awareness & Resume Match states
  const [applicationsData, setApplicationsData] = useState<ApplicationSummaryItem[]>([]);
  const [matchesData, setMatchesData] = useState<MatchSummaryItem[]>([]);
  const [hideApplied, setHideApplied] = useState<boolean>(false);
  const [sortByMatch, setSortByMatch] = useState<boolean>(false);

  // Selected job for detail modal
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  const fetchAuxiliaryData = useCallback(async () => {
    try {
      const [appsRes, matchesRes] = await Promise.allSettled([
        api.get<{ items: ApplicationSummaryItem[] }>('/applications?limit=200'),
        api.get<{ items: MatchSummaryItem[] }>('/matches?limit=200'),
      ]);

      if (appsRes.status === 'fulfilled') {
        setApplicationsData(appsRes.value.items || []);
      } else {
        console.warn('Could not load applications for pipeline awareness:', appsRes.reason);
      }

      if (matchesRes.status === 'fulfilled') {
        setMatchesData(matchesRes.value.items || []);
      } else {
        console.warn('Could not load match scores for pipeline awareness:', matchesRes.reason);
      }
    } catch (err) {
      console.warn('Failed to fetch auxiliary pipeline data:', err);
    }
  }, []);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('limit', '100');
      params.append('include_duplicates', includeDuplicates ? 'true' : 'false');

      if (workMode !== 'ALL') {
        params.append('work_mode', workMode);
      }
      if (search.trim()) {
        params.append('search', search.trim());
      }

      const res = await api.get<JobListResponse>(`/jobs?${params.toString()}`);
      setJobs(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load jobs:', err);
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  }, [search, workMode, includeDuplicates]);

  useEffect(() => {
    fetchJobs();
    fetchAuxiliaryData();
  }, [fetchJobs, fetchAuxiliaryData]);

  useEffect(() => {
    const handleGlobalRefresh = () => {
      fetchJobs();
      fetchAuxiliaryData();
    };
    window.addEventListener('app:refresh-data', handleGlobalRefresh);
    return () => {
      window.removeEventListener('app:refresh-data', handleGlobalRefresh);
    };
  }, [fetchJobs, fetchAuxiliaryData]);

  // Memoized O(1) lookup map for application statuses by job_id (with fallback by normalized company + title)
  const applicationsLookup = useMemo(() => {
    const byJobId = new Map<string, string>();
    const byCompTitle = new Map<string, string>();

    // Stage priority for the rare case a job has multiple application records
    const statusPriority: Record<string, number> = {
      OFFER: 6,
      INTERVIEWING: 5,
      APPLIED: 4,
      NOT_APPLIED: 3,
      DISCOVERED: 2,
      REJECTED: 1,
      WITHDRAWN: 1,
    };

    for (const app of applicationsData) {
      const status = app.status;
      if (app.job_id) {
        const existing = byJobId.get(app.job_id);
        if (!existing || (statusPriority[status] || 0) >= (statusPriority[existing] || 0)) {
          byJobId.set(app.job_id, status);
        }
      }
      // Fallback matching: normalized company + title if job_id differs or is unlinked
      if (app.job?.company_name && app.job?.title) {
        const key = `${app.job.company_name.toLowerCase().trim()}::${app.job.title.toLowerCase().trim()}`;
        const existing = byCompTitle.get(key);
        if (!existing || (statusPriority[status] || 0) >= (statusPriority[existing] || 0)) {
          byCompTitle.set(key, status);
        }
      }
    }

    return { byJobId, byCompTitle };
  }, [applicationsData]);

  // Memoized O(1) lookup map for match scores by job_id (with fallback by normalized company + title)
  const matchesLookup = useMemo(() => {
    const byJobId = new Map<string, number>();
    const byCompTitle = new Map<string, number>();

    for (const match of matchesData) {
      if (match.job_id && typeof match.overall_match_score === 'number') {
        byJobId.set(match.job_id, match.overall_match_score);
      }
      // Fallback matching: normalized company + title
      if (match.company_name && match.job_title && typeof match.overall_match_score === 'number') {
        const key = `${match.company_name.toLowerCase().trim()}::${match.job_title.toLowerCase().trim()}`;
        byCompTitle.set(key, match.overall_match_score);
      }
    }

    return { byJobId, byCompTitle };
  }, [matchesData]);

  // Retrieve pipeline status for a specific job
  const getJobStatus = useCallback(
    (job: Job): string | undefined => {
      if (applicationsLookup.byJobId.has(job.id)) {
        return applicationsLookup.byJobId.get(job.id);
      }
      // Fallback to normalized company + title
      const key = `${job.company_name?.toLowerCase().trim()}::${job.title?.toLowerCase().trim()}`;
      return applicationsLookup.byCompTitle.get(key);
    },
    [applicationsLookup]
  );

  // Retrieve resume fit match score for a specific job
  const getJobScore = useCallback(
    (job: Job): number | undefined => {
      if (matchesLookup.byJobId.has(job.id)) {
        return matchesLookup.byJobId.get(job.id);
      }
      // Fallback to normalized company + title
      const key = `${job.company_name?.toLowerCase().trim()}::${job.title?.toLowerCase().trim()}`;
      return matchesLookup.byCompTitle.get(key);
    },
    [matchesLookup]
  );

  // Memoized filtered and sorted jobs (supporting "Hide already applied" & "Sort by match %")
  const displayedJobs = useMemo(() => {
    let list = [...jobs];

    if (hideApplied) {
      list = list.filter((j) => {
        const status = getJobStatus(j);
        return !(status === 'APPLIED' || status === 'INTERVIEWING' || status === 'OFFER');
      });
    }

    if (sortByMatch) {
      list.sort((a, b) => {
        const scoreA = getJobScore(a) ?? -1;
        const scoreB = getJobScore(b) ?? -1;
        return scoreB - scoreA;
      });
    }

    return list;
  }, [jobs, hideApplied, sortByMatch, getJobStatus, getJobScore]);

  const handleExtractAll = async () => {
    setIsExtracting(true);
    try {
      const res = await api.post<{ total_processed: number; jobs_extracted: number; message: string }>(
        '/jobs/extract-all?limit=50'
      );
      alert(`Job Extraction Complete: ${res.jobs_extracted} new structured roles extracted from ${res.total_processed} emails.`);
      fetchJobs();
    } catch (err: any) {
      alert(`Job extraction failed: ${err.message}`);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleDeduplicate = async () => {
    setIsDeduplicating(true);
    try {
      const res = await api.post<{ total_jobs: number; duplicates_identified: number; unique_canonical_jobs: number; message: string }>(
        '/jobs/deduplicate'
      );
      alert(
        `Duplicate Sweep Finished:\n• Total Jobs: ${res.total_jobs}\n• Duplicates Found: ${res.duplicates_identified}\n• Canonical Unique Roles: ${res.unique_canonical_jobs}`
      );
      fetchJobs();
    } catch (err: any) {
      alert(`Deduplication sweep failed: ${err.message}`);
    } finally {
      setIsDeduplicating(false);
    }
  };

  // KPI Calculations
  const remoteCount = jobs.filter((j) => j.work_mode?.toUpperCase() === 'REMOTE').length;
  const uniqueCompanies = new Set(jobs.map((j) => j.company_name?.toLowerCase())).size;
  const duplicateCount = jobs.filter((j) => j.is_duplicate).length;

  const getWorkModeVariant = (mode: string): 'primary' | 'danger' | 'success' | 'warning' | 'info' | 'neutral' => {
    const m = mode.toUpperCase();
    if (m === 'REMOTE') return 'success';
    if (m === 'HYBRID') return 'primary';
    if (m === 'ON_SITE') return 'warning';
    return 'neutral';
  };

  const columns: Column<Job>[] = [
    {
      key: 'title',
      header: 'Role & Company',
      render: (j) => {
        const initial = j.company_name ? j.company_name.charAt(0).toUpperCase() : '?';
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: 'rgba(99, 102, 241, 0.12)',
                color: 'var(--accent-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '14px',
                flexShrink: 0,
              }}
            >
              {initial}
            </div>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '13.5px' }}>
                {j.title}
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                {j.company_name}
              </div>
            </div>
          </div>
        );
      },
    },
    {
      key: 'location',
      header: 'Location & Mode',
      render: (j) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            {j.location || 'Undisclosed'}
          </span>
          <Badge variant={getWorkModeVariant(j.work_mode)}>{j.work_mode}</Badge>
        </div>
      ),
    },
    {
      key: 'salary',
      header: 'Salary Range',
      render: (j) => {
        if (!j.salary_min && !j.salary_max) {
          return <span style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Undisclosed</span>;
        }
        const curr = j.salary_currency || '$';
        return (
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--success)' }}>
            {j.salary_min && j.salary_max
              ? `${curr}${Math.round(j.salary_min / 1000)}k - ${curr}${Math.round(j.salary_max / 1000)}k`
              : `${curr}${Math.round((j.salary_min || j.salary_max || 0) / 1000)}k`}
          </span>
        );
      },
    },
    {
      key: 'platform_source',
      header: 'Source',
      render: (j) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Badge variant="info">{j.platform_source}</Badge>
          {j.is_duplicate && <Badge variant="warning">Dup</Badge>}
        </div>
      ),
    },
    {
      key: 'match_score',
      header: 'Resume Fit',
      render: (j) => {
        const score = getJobScore(j);
        if (typeof score === 'number' && score > 0) {
          return (
            <Badge score={score} style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
              <Sparkles size={11} /> {Math.round(score)}% match
            </Badge>
          );
        }
        return <Badge variant="neutral">Not scored</Badge>;
      },
    },
    {
      key: 'pipeline_status',
      header: 'Status',
      render: (j) => {
        const status = getJobStatus(j);
        const config = getApplicationStatusConfig(status);
        if (!config) return <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>—</span>;
        return <Badge variant={config.variant}>{config.label}</Badge>;
      },
    },
    {
      key: 'created_at',
      header: 'Extracted',
      render: (j) => (
        <span style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
          {new Date(j.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Action',
      render: (j) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }} onClick={(e) => e.stopPropagation()}>
          <Button
            size="sm"
            variant="outline"
            leftIcon={<Eye size={13} />}
            onClick={() => setSelectedJob(j)}
          >
            Inspect
          </Button>
          {j.job_url && (
            <a href={j.job_url} target="_blank" rel="noopener noreferrer">
              <Button size="sm" variant="ghost" rightIcon={<ExternalLink size={13} />} title="Direct job URL">
                Link
              </Button>
            </a>
          )}
        </div>
      ),
    },
  ];

  return (
    <AppLayout
      title="Job Discovery & Opportunity Hub"
      onRefresh={() => {
        fetchJobs();
        fetchAuxiliaryData();
      }}
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
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Discovered Roles</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                  {total}
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
                <Briefcase size={22} color="var(--accent-primary)" />
              </div>
            </div>
          </Card>

          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Remote Opportunities</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--success)', marginTop: '4px' }}>
                  {remoteCount}
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
                <Globe size={22} color="var(--success)" />
              </div>
            </div>
          </Card>

          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Hiring Companies</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent-secondary)', marginTop: '4px' }}>
                  {uniqueCompanies}
                </div>
              </div>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(139, 92, 246, 0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Building2 size={22} color="var(--accent-secondary)" />
              </div>
            </div>
          </Card>

          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Cross-Platform Duplicates</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--warning)', marginTop: '4px' }}>
                  {duplicateCount}
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
                <GitMerge size={22} color="var(--warning)" />
              </div>
            </div>
          </Card>
        </div>

        {/* Filter and Control Bar */}
        <JobFilterBar
          search={search}
          onSearchChange={setSearch}
          workMode={workMode}
          onWorkModeChange={setWorkMode}
          includeDuplicates={includeDuplicates}
          onIncludeDuplicatesChange={setIncludeDuplicates}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          onExtractAll={handleExtractAll}
          isExtracting={isExtracting}
          onDeduplicate={handleDeduplicate}
          isDeduplicating={isDeduplicating}
          hideApplied={hideApplied}
          onHideAppliedChange={setHideApplied}
          sortByMatch={sortByMatch}
          onSortByMatchChange={setSortByMatch}
        />

        {/* Jobs Presentation Area */}
        {viewMode === 'grid' ? (
          isLoading ? (
            <Card style={{ padding: '48px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Loading structured job opportunities...
            </Card>
          ) : displayedJobs.length === 0 ? (
            <Card style={{ padding: '48px', textAlign: 'center' }}>
              <div style={{ maxWidth: '420px', margin: '0 auto' }}>
                <Layers size={40} color="var(--text-muted)" style={{ margin: '0 auto 16px', display: 'block' }} />
                <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
                  {jobs.length > 0 ? 'No Matching Jobs Found' : 'No Jobs Discovered Yet'}
                </h3>
                <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginBottom: '20px', lineHeight: 1.5 }}>
                  {jobs.length > 0
                    ? 'All current jobs are either already applied to or filtered out by your current search and filters.'
                    : 'Synchronize your connected Gmail inbox, then click "Extract All Jobs" to automatically extract structured job postings, skills, and salaries.'}
                </p>
                {jobs.length === 0 && (
                  <Button
                    variant="primary"
                    size="md"
                    isLoading={isExtracting}
                    onClick={handleExtractAll}
                  >
                    Extract Jobs from Emails
                  </Button>
                )}
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
              {displayedJobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onInspect={(j) => setSelectedJob(j)}
                  applicationStatus={getJobStatus(job)}
                  matchScore={getJobScore(job)}
                />
              ))}
            </div>
          )
        ) : (
          <Card style={{ padding: '0px', overflow: 'hidden' }}>
            <Table<Job>
              columns={columns}
              data={displayedJobs}
              keyExtractor={(j) => j.id}
              isLoading={isLoading}
              onRowClick={(j) => setSelectedJob(j)}
              emptyMessage="No structured jobs match your filter criteria."
            />
          </Card>
        )}
      </div>

      {/* Structured Job Detail Modal */}
      <JobDetailModal
        job={selectedJob}
        isOpen={!!selectedJob}
        onClose={() => setSelectedJob(null)}
        onApplicationCreated={() => {
          fetchJobs();
          fetchAuxiliaryData();
        }}
        applicationStatus={selectedJob ? getJobStatus(selectedJob) : undefined}
        matchScore={selectedJob ? getJobScore(selectedJob) : undefined}
      />
    </AppLayout>
  );
};
