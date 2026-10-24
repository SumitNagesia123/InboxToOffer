import React, { useEffect, useState, useCallback } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Table, type Column } from '../components/common/Table';
import { Input } from '../components/common/Input';
import { GmailStatusCard } from '../components/gmail/GmailStatusCard';
import { SyncModal } from '../components/gmail/SyncModal';
import { EmailDetailModal } from '../components/email/EmailDetailModal';
import { SweepModal } from '../components/email/SweepModal';
import { api } from '../api/client';
import {
  Search,
  RefreshCw,
  RotateCw,
  Sparkles,
  Inbox,
  Briefcase,
  CalendarCheck,
  Award,
  Filter,
  Eye,
  ShieldAlert,
} from 'lucide-react';

interface EmailItem {
  id: string;
  user_id: string;
  gmail_message_id: string;
  sender: string;
  recipient: string;
  subject: string;
  received_at: string;
  category: string;
  processed_status: string;
  body_preview?: string;
  created_at: string;
}

interface EmailListResponse {
  items: EmailItem[];
  total: number;
  skip: number;
  limit: number;
}

const CATEGORIES = [
  { id: 'ALL', label: 'All Emails' },
  { id: 'JOB', label: 'Job Alerts' },
  { id: 'INTERVIEW', label: 'Interviews' },
  { id: 'OFFER', label: 'Offers' },
  { id: 'APPLICATION_ACK', label: 'Applied' },
  { id: 'REJECTION', label: 'Rejections' },
];

export const EmailsPage: React.FC = () => {
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [search, setSearch] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isClassifyingAll, setIsClassifyingAll] = useState<boolean>(false);

  // Modals state
  const [isSyncModalOpen, setIsSyncModalOpen] = useState<boolean>(false);
  const [isSweepModalOpen, setIsSweepModalOpen] = useState<boolean>(false);
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);

  const fetchEmails = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('limit', '100');
      if (selectedCategory !== 'ALL') {
        params.append('category', selectedCategory);
      }
      if (selectedStatus !== 'ALL') {
        params.append('status', selectedStatus);
      }
      if (search.trim()) {
        params.append('search', search.trim());
      }

      const res = await api.get<EmailListResponse>(`/emails?${params.toString()}`);
      setEmails(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load emails:', err);
      setEmails([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, selectedStatus, search]);

  useEffect(() => {
    fetchEmails();
  }, [fetchEmails]);

  useEffect(() => {
    const handleGlobalRefresh = () => {
      fetchEmails();
    };
    window.addEventListener('app:refresh-data', handleGlobalRefresh);
    return () => {
      window.removeEventListener('app:refresh-data', handleGlobalRefresh);
    };
  }, [fetchEmails]);

  const handleBatchClassify = async () => {
    setIsClassifyingAll(true);
    try {
      const res = await api.post<{ classified_count: number }>('/emails/classify-all?limit=50');
      alert(`Batch NLP Classification complete: ${res.classified_count} pending emails categorized.`);
      fetchEmails();
    } catch (err: any) {
      alert(`Batch classification error: ${err.message}`);
    } finally {
      setIsClassifyingAll(false);
    }
  };

  const getCategoryBadgeVariant = (category: string): 'primary' | 'danger' | 'success' | 'warning' | 'info' | 'neutral' => {
    const c = category.toUpperCase();
    if (c.includes('OFFER')) return 'success';
    if (c.includes('INTERVIEW')) return 'primary';
    if (c.includes('JOB')) return 'info';
    if (c.includes('REJECT')) return 'danger';
    if (c.includes('APPLICATION') || c.includes('ACK')) return 'warning';
    return 'neutral';
  };

  // KPI Calculations
  const jobCount = emails.filter((e) => e.category?.toUpperCase().includes('JOB')).length;
  const interviewCount = emails.filter(
    (e) => e.category?.toUpperCase().includes('INTERVIEW') || e.category?.toUpperCase().includes('OFFER')
  ).length;
  const pendingCount = emails.filter((e) => e.processed_status === 'PENDING').length;

  const columns: Column<EmailItem>[] = [
    {
      key: 'sender',
      header: 'Sender',
      render: (e) => {
        const initial = e.sender ? e.sender.charAt(0).toUpperCase() : '?';
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: 'rgba(99, 102, 241, 0.12)',
                color: 'var(--accent-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 600,
                fontSize: '13px',
                flexShrink: 0,
              }}
            >
              {initial}
            </div>
            <div style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
                {e.sender.replace(/<.*>/, '').trim() || e.sender}
              </div>
            </div>
          </div>
        );
      },
    },
    {
      key: 'subject',
      header: 'Subject & Intelligence Snippet',
      render: (e) => (
        <div style={{ maxWidth: '420px' }}>
          <div
            style={{
              fontWeight: 600,
              fontSize: '13.5px',
              color: 'var(--text-primary)',
              marginBottom: '3px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {e.subject || '(No Subject)'}
          </div>
          {e.body_preview && (
            <div
              style={{
                fontSize: '12px',
                color: 'var(--text-muted)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {e.body_preview}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (e) => (
        <Badge variant={getCategoryBadgeVariant(e.category)}>
          {e.category}
        </Badge>
      ),
    },
    {
      key: 'processed_status',
      header: 'Status',
      render: (e) => (
        <Badge
          variant={e.processed_status === 'PROCESSED' ? 'success' : 'warning'}
        >
          {e.processed_status}
        </Badge>
      ),
    },
    {
      key: 'received_at',
      header: 'Received',
      render: (e) => (
        <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
          {new Date(e.received_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      ),
    },
    {
      key: 'id',
      header: 'Action',
      render: (e) => (
        <Button
          variant="outline"
          size="sm"
          leftIcon={<Eye size={13} />}
          onClick={(ev) => {
            ev.stopPropagation();
            setSelectedEmailId(e.id);
          }}
        >
          Inspect
        </Button>
      ),
    },
  ];

  return (
    <AppLayout
      title="Job Email Intelligence Hub"
      onRefresh={fetchEmails}
      isRefreshing={isLoading}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Gmail OAuth Live Status Banner */}
        <GmailStatusCard
          onSyncClick={() => setIsSyncModalOpen(true)}
          onStatusChange={() => fetchEmails()}
        />

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
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Total Ingested</div>
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
                <Inbox size={22} color="var(--accent-primary)" />
              </div>
            </div>
          </Card>

          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Job Alerts</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--accent-secondary)', marginTop: '4px' }}>
                  {jobCount}
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
                <Briefcase size={22} color="var(--accent-secondary)" />
              </div>
            </div>
          </Card>

          <Card style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Interviews & Offers</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--success)', marginTop: '4px' }}>
                  {interviewCount}
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
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Pending Processing</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--warning)', marginTop: '4px' }}>
                  {pendingCount}
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
                <CalendarCheck size={22} color="var(--warning)" />
              </div>
            </div>
          </Card>
        </div>

        {/* Filter and Search Bar */}
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
                  placeholder="Search emails by sender, subject, or keywords..."
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
                  onClick={fetchEmails}
                  title="Reload emails list"
                >
                  Refresh
                </Button>
                <Button
                  variant="outline"
                  size="md"
                  isLoading={isClassifyingAll}
                  leftIcon={<Sparkles size={15} />}
                  onClick={handleBatchClassify}
                  title="Run NLP Classifier across pending ingested emails"
                >
                  NLP Classify Pending
                </Button>
                <Button
                  variant="outline"
                  size="md"
                  leftIcon={<ShieldAlert size={15} color="var(--danger)" />}
                  onClick={() => setIsSweepModalOpen(true)}
                  title="Audit and purge non-job emails (Amazon packages, financial spam, antivirus)"
                >
                  Sweep Non-Job
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  leftIcon={<RefreshCw size={15} />}
                  onClick={() => setIsSyncModalOpen(true)}
                >
                  Sync Gmail
                </Button>
              </div>
            </div>

            {/* Category and Status Filter Pills */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '12.5px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginRight: '4px' }}>
                  <Filter size={13} /> Category:
                </span>
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setSelectedCategory(cat.id)}
                    style={{
                      padding: '5px 12px',
                      borderRadius: '20px',
                      fontSize: '12.5px',
                      fontWeight: selectedCategory === cat.id ? 600 : 400,
                      border:
                        selectedCategory === cat.id
                          ? '1px solid var(--accent-primary)'
                          : '1px solid var(--border-subtle)',
                      backgroundColor:
                        selectedCategory === cat.id
                          ? 'rgba(99, 102, 241, 0.15)'
                          : 'var(--bg-card)',
                      color:
                        selectedCategory === cat.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              {/* Status Filter */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Status:</span>
                {(['ALL', 'PROCESSED', 'PENDING'] as const).map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setSelectedStatus(st)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '16px',
                      fontSize: '12px',
                      fontWeight: selectedStatus === st ? 600 : 400,
                      border:
                        selectedStatus === st
                          ? '1px solid var(--border-medium)'
                          : '1px solid transparent',
                      backgroundColor:
                        selectedStatus === st ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                      color: selectedStatus === st ? 'var(--text-primary)' : 'var(--text-muted)',
                      cursor: 'pointer',
                    }}
                  >
                    {st === 'ALL' ? 'All' : st === 'PROCESSED' ? 'Processed' : 'Pending'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Email Intelligence Table */}
        <Card style={{ padding: '0px', overflow: 'hidden' }}>
          <Table<EmailItem>
            columns={columns}
            data={emails}
            keyExtractor={(e) => e.id}
            isLoading={isLoading}
            onRowClick={(e: EmailItem) => setSelectedEmailId(e.id)}
            emptyMessage="No emails match your filter criteria. Click 'Sync Gmail' to ingest job correspondence."
          />
        </Card>
      </div>

      {/* Sync Gmail Ingestion Modal */}
      <SyncModal
        isOpen={isSyncModalOpen}
        onClose={() => setIsSyncModalOpen(false)}
        onSyncComplete={() => fetchEmails()}
      />

      {/* Sweep Non-Job Emails Modal */}
      <SweepModal
        isOpen={isSweepModalOpen}
        onClose={() => setIsSweepModalOpen(false)}
        onSweepComplete={() => fetchEmails()}
      />

      {/* Email Intelligence Inspector Modal */}
      <EmailDetailModal
        emailId={selectedEmailId}
        isOpen={!!selectedEmailId}
        onClose={() => setSelectedEmailId(null)}
        onEmailUpdated={() => fetchEmails()}
      />
    </AppLayout>
  );
};
