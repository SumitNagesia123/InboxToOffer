import React, { useEffect, useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Card } from '../common/Card';
import { api } from '../../api/client';
import {
  CheckCircle,
  AlertTriangle,
  Trash2,
  RotateCw,
} from 'lucide-react';

interface SweepPreviewItem {
  id: string;
  sender: string;
  subject: string;
  category: string;
  confidence: number;
  reason: string;
  received_at: string;
  has_applications: boolean;
  job_count: number;
}

interface SweepSkippedItem {
  id: string;
  sender: string;
  subject: string;
  reason: string;
}

interface SweepResponse {
  dry_run: boolean;
  total_scanned: number;
  total_discardable: number;
  total_skipped: number;
  total_unsure: number;
  total_keep: number;
  preview_discards: SweepPreviewItem[];
  skipped_items: SweepSkippedItem[];
  removed_count: number;
  backup_path?: string;
  message: string;
}

interface SweepModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSweepComplete?: () => void;
}

export const SweepModal: React.FC<SweepModalProps> = ({
  isOpen,
  onClose,
  onSweepComplete,
}) => {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<SweepResponse | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [summaryData, setSummaryData] = useState<SweepResponse | null>(null);

  // Fetch dry-run preview on open
  useEffect(() => {
    if (isOpen) {
      loadDryRun();
    } else {
      setPreviewData(null);
      setSummaryData(null);
      setSelectedIds(new Set());
    }
  }, [isOpen]);

  const loadDryRun = async () => {
    setIsLoading(true);
    try {
      const res = await api.post<SweepResponse>('/emails/sweep-non-job', {
        dry_run: true,
      });
      setPreviewData(res);
      // Pre-select all detected non-job discard candidates
      const allIds = new Set((res.preview_discards || []).map((p) => p.id));
      setSelectedIds(allIds);
    } catch (err: any) {
      console.error('Sweep dry run failed:', err);
      alert(`Could not analyze non-job emails: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleSelect = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const handleSelectAll = () => {
    if (!previewData) return;
    if (selectedIds.size === previewData.preview_discards.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(previewData.preview_discards.map((p) => p.id)));
    }
  };

  const handleExecuteSweep = async () => {
    if (selectedIds.size === 0) return;
    setIsDeleting(true);
    try {
      const res = await api.post<SweepResponse>('/emails/sweep-non-job', {
        dry_run: false,
        email_ids: Array.from(selectedIds),
      });
      setSummaryData(res);
      if (onSweepComplete) {
        onSweepComplete();
      }
    } catch (err: any) {
      console.error('Sweep execution failed:', err);
      alert(`Failed to delete selected emails: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const getCategoryVariant = (category: string) => {
    switch (category) {
      case 'COMMERCE_ORDER':
        return 'danger';
      case 'FINANCIAL_SPAM':
        return 'warning';
      case 'OTP_SECURITY':
        return 'info';
      case 'COURSE_PROMO':
        return 'neutral';
      default:
        return 'neutral';
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Clean & Sweep Non-Job Emails"
      maxWidth="780px"
      footer={
        summaryData ? (
          <div style={{ display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
            <Button variant="primary" size="md" onClick={onClose}>
              Done
            </Button>
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              width: '100%',
              alignItems: 'center',
            }}
          >
            <Button variant="ghost" size="md" onClick={onClose} disabled={isDeleting}>
              Cancel
            </Button>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <Button
                variant="danger"
                size="md"
                isLoading={isDeleting}
                disabled={isLoading || selectedIds.size === 0}
                leftIcon={<Trash2 size={15} />}
                onClick={handleExecuteSweep}
              >
                Purge Selected ({selectedIds.size} Emails)
              </Button>
            </div>
          </div>
        )
      }
    >
      {isLoading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RotateCw size={28} className="animate-spin" style={{ margin: '0 auto 12px', display: 'block' }} />
          <div>Auditing stored emails with AI triage classifier...</div>
        </div>
      ) : summaryData ? (
        /* Step 3: Summary View */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '8px 0' }}>
          <div
            style={{
              padding: '20px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              display: 'flex',
              gap: '14px',
              alignItems: 'flex-start',
            }}
          >
            <CheckCircle size={24} color="var(--success)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <h4 style={{ margin: '0 0 6px 0', fontSize: '16px', color: 'var(--text-primary)', fontWeight: 600 }}>
                Sweep Execution Successful
              </h4>
              <p style={{ margin: 0, fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {summaryData.message}
              </p>
            </div>
          </div>

          {/* Metrics Breakdown */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            <Card style={{ padding: '14px', textAlign: 'center' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Purged & Cleaned</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--danger)', marginTop: '4px' }}>
                {summaryData.removed_count}
              </div>
            </Card>
            <Card style={{ padding: '14px', textAlign: 'center' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Preserved Job Emails</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--success)', marginTop: '4px' }}>
                {summaryData.total_keep}
              </div>
            </Card>
            <Card style={{ padding: '14px', textAlign: 'center' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Pipeline Skipped</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--warning)', marginTop: '4px' }}>
                {summaryData.total_skipped}
              </div>
            </Card>
          </div>

          {summaryData.backup_path && (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', backgroundColor: 'var(--bg-surface)', padding: '10px 14px', borderRadius: '6px' }}>
              📦 Full JSON backup saved to: <code style={{ color: 'var(--accent-primary)' }}>{summaryData.backup_path}</code>
            </div>
          )}
        </div>
      ) : previewData ? (
        /* Step 1 & 2: Preview & Selection */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Header Overview Banner */}
          <div
            style={{
              padding: '16px',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {previewData.preview_discards.length} Non-Job Emails Detected
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Identified e-commerce packages, financial ads, and subscriptions that clutter your inbox.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Badge variant="success">{previewData.total_keep} Clean Job Emails</Badge>
              <Badge variant="neutral">{previewData.total_unsure} Flagged Unsure</Badge>
            </div>
          </div>

          {/* Application Safety Alert */}
          {previewData.skipped_items && previewData.skipped_items.length > 0 && (
            <div
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                display: 'flex',
                gap: '10px',
                alignItems: 'center',
                fontSize: '13px',
                color: 'var(--warning)',
              }}
            >
              <AlertTriangle size={18} style={{ flexShrink: 0 }} />
              <div>
                <strong>{previewData.skipped_items.length} email(s) automatically skipped</strong> because their extracted roles have active applications in your Kanban pipeline.
              </div>
            </div>
          )}

          {/* Select all toggle bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 4px' }}>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '13px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              <input
                type="checkbox"
                checked={selectedIds.size === previewData.preview_discards.length && previewData.preview_discards.length > 0}
                onChange={handleSelectAll}
                style={{ accentColor: 'var(--danger)', width: '15px', height: '15px' }}
              />
              Select All Discard Candidates ({previewData.preview_discards.length})
            </label>

            <span style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
              {selectedIds.size} of {previewData.preview_discards.length} selected for deletion
            </span>
          </div>

          {/* Scrollable list of discard preview items */}
          <div
            style={{
              maxHeight: '340px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              paddingRight: '4px',
            }}
          >
            {previewData.preview_discards.map((item) => (
              <div
                key={item.id}
                onClick={() => handleToggleSelect(item.id)}
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: selectedIds.has(item.id)
                    ? 'rgba(244, 63, 94, 0.08)'
                    : 'var(--bg-card)',
                  border: selectedIds.has(item.id)
                    ? '1px solid rgba(244, 63, 94, 0.3)'
                    : '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedIds.has(item.id)}
                  onChange={() => handleToggleSelect(item.id)}
                  onClick={(e) => e.stopPropagation()}
                  style={{ accentColor: 'var(--danger)', width: '15px', height: '15px', marginTop: '3px' }}
                />

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.sender}
                    </span>
                    <Badge variant={getCategoryVariant(item.category)}>
                      {item.category.replace(/_/g, ' ')} ({Math.round(item.confidence * 100)}%)
                    </Badge>
                  </div>

                  <div style={{ fontSize: '13.5px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                    {item.subject}
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Reason: {item.reason}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Modal>
  );
};
