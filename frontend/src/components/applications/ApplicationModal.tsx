import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Input } from '../common/Input';
import { api } from '../../api/client';
import {
  Building,
  Calendar,
  ExternalLink,
  Trash2,
  Save,
} from 'lucide-react';

export interface ApplicationDetail {
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

const STAGES = [
  { id: 'APPLIED', label: 'Applied (Liked)' },
  { id: 'NOT_APPLIED', label: 'Not Applied (Disliked)' },
  { id: 'INTERVIEWING', label: 'Interviewing' },
  { id: 'OFFER', label: 'Offer' },
  { id: 'REJECTED', label: 'Rejected' },
  { id: 'DISCOVERED', label: 'Discovered' },
  { id: 'WITHDRAWN', label: 'Withdrawn' },
];

interface ApplicationModalProps {
  application: ApplicationDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdated: () => void;
}

export const ApplicationModal: React.FC<ApplicationModalProps> = ({
  application,
  isOpen,
  onClose,
  onUpdated,
}) => {
  const [status, setStatus] = useState<string>(application?.status || 'APPLIED');
  const [notes, setNotes] = useState<string>(application?.notes || '');
  const [appliedDate, setAppliedDate] = useState<string>(
    application?.applied_date ? application.applied_date.substring(0, 10) : ''
  );
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  React.useEffect(() => {
    if (application) {
      setStatus(application.status);
      setNotes(application.notes || '');
      setAppliedDate(application.applied_date ? application.applied_date.substring(0, 10) : '');
    }
  }, [application]);

  if (!application) return null;

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.patch(`/applications/${application.id}`, {
        status,
        notes,
        applied_date: appliedDate ? new Date(appliedDate).toISOString() : undefined,
      });
      onUpdated();
      onClose();
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Remove this application from your tracking pipeline?')) return;
    setIsDeleting(true);
    try {
      await api.delete(`/applications/${application.id}`);
      onUpdated();
      onClose();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const getStageVariant = (st: string): 'primary' | 'danger' | 'success' | 'warning' | 'info' | 'neutral' => {
    switch (st) {
      case 'OFFER':
        return 'success';
      case 'INTERVIEWING':
        return 'primary';
      case 'APPLIED':
        return 'success';
      case 'NOT_APPLIED':
        return 'danger';
      case 'REJECTED':
        return 'danger';
      case 'WITHDRAWN':
      case 'DISCOVERED':
      default:
        return 'neutral';
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Application Details & Interview Tracker"
      maxWidth="680px"
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
          <Button
            variant="danger"
            size="sm"
            isLoading={isDeleting}
            leftIcon={<Trash2 size={14} />}
            onClick={handleDelete}
          >
            Remove
          </Button>

          <div style={{ display: 'flex', gap: '8px' }}>
            <Button variant="outline" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={isSaving}
              leftIcon={<Save size={14} />}
              onClick={handleSave}
            >
              Save Changes
            </Button>
          </div>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Header Summary */}
        <div
          style={{
            padding: '18px',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 6px 0', color: 'var(--text-primary)' }}>
                {application.job?.title || 'Tracked Role'}
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '14px' }}>
                <Building size={14} color="var(--text-muted)" />
                <span style={{ fontWeight: 600 }}>{application.job?.company_name || 'Company'}</span>
                {application.job?.location && (
                  <>
                    <span>•</span>
                    <span>{application.job.location}</span>
                  </>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
              <Badge variant={getStageVariant(status)}>{status}</Badge>
              {typeof application.match_score === 'number' && (
                <Badge score={application.match_score}>{Math.round(application.match_score)}% Match</Badge>
              )}
            </div>
          </div>

          {application.job?.job_url && (
            <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
              <a
                href={application.job.job_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontSize: '12.5px',
                  color: 'var(--accent-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  textDecoration: 'none',
                }}
              >
                <ExternalLink size={13} />
                View Original Job Posting
              </a>
            </div>
          )}
        </div>

        {/* Pipeline Stage Transition Buttons */}
        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
            Pipeline Stage
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
            {STAGES.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setStatus(s.id)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '12.5px',
                  fontWeight: status === s.id ? 600 : 400,
                  border:
                    status === s.id
                      ? '1px solid var(--accent-primary)'
                      : '1px solid var(--border-subtle)',
                  backgroundColor:
                    status === s.id
                      ? 'rgba(99, 102, 241, 0.15)'
                      : 'var(--bg-card)',
                  color:
                    status === s.id ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  textAlign: 'center',
                }}
              >
                {status === s.id ? `✓ ${s.label}` : s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Applied Date */}
        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
            Application Submission Date
          </label>
          <Input
            type="date"
            value={appliedDate}
            onChange={(e) => setAppliedDate(e.target.value)}
            leftIcon={<Calendar size={15} />}
          />
        </div>

        {/* Candidate Private Notes */}
        <div>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
            Private Notes & Interview Prep
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Record recruiter names, interview scheduled times, compensation notes, preparation links..."
            rows={5}
            style={{
              width: '100%',
              padding: '12px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-primary)',
              fontSize: '13px',
              lineHeight: 1.5,
              resize: 'vertical',
              outline: 'none',
              fontFamily: 'inherit',
            }}
          />
        </div>
      </div>
    </Modal>
  );
};
