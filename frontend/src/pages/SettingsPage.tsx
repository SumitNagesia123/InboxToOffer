import React, { useEffect, useState } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Modal } from '../components/common/Modal';
import { api } from '../api/client';
import {
  Send,
  CheckCircle2,
  Eye,
  Mail,
  Clock,
  DollarSign,
  Shield,
  FileText,
  Code,
} from 'lucide-react';

interface Preferences {
  digest_enabled: boolean;
  digest_time: string;
  preferred_work_modes: string[];
  min_desired_salary?: number;
}

interface DigestPreview {
  recipient_email: string;
  subject: string;
  date_formatted: string;
  total_jobs_evaluated: number;
  top_matches_count: number;
  top_matches: Array<{
    job_id: string;
    company_name: string;
    title: string;
    location?: string;
    work_mode: string;
    salary_formatted?: string;
    match_score: number;
    matched_skills: string[];
    job_url?: string;
  }>;
  interview_alerts_count: number;
  html_content: string;
  text_content: string;
}

const WORK_MODES = ['REMOTE', 'HYBRID', 'ON_SITE'];

export const SettingsPage: React.FC = () => {
  const [pref, setPref] = useState<Preferences>({
    digest_enabled: true,
    digest_time: '22:00',
    preferred_work_modes: ['REMOTE', 'HYBRID'],
    min_desired_salary: 100000,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Digest Preview Modal State
  const [preview, setPreview] = useState<DigestPreview | null>(null);
  const [previewTab, setPreviewTab] = useState<'html' | 'text'>('html');

  useEffect(() => {
    api.get<Preferences>('/settings').then(setPref).catch(console.error);
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(false);

    try {
      const updated = await api.patch<Preferences>('/settings', pref);
      setPref(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTriggerDigest = async () => {
    setIsTriggering(true);
    try {
      const res = await api.post<{ top_matches_count: number; message: string }>('/digest/trigger?force=true');
      alert(`Daily digest dispatched! ${res.top_matches_count} top matching opportunities delivered.`);
    } catch (err: any) {
      alert(`Dispatch failed: ${err.message}`);
    } finally {
      setIsTriggering(false);
    }
  };

  const handlePreviewDigest = async () => {
    setIsPreviewing(true);
    try {
      const data = await api.get<DigestPreview>('/digest/preview');
      setPreview(data);
      setPreviewTab('html');
    } catch (err: any) {
      alert(`Failed to generate digest preview: ${err.message}`);
    } finally {
      setIsPreviewing(false);
    }
  };

  const toggleWorkMode = (mode: string) => {
    setPref((prev) => {
      const current = prev.preferred_work_modes || [];
      const updated = current.includes(mode)
        ? current.filter((m) => m !== mode)
        : [...current, mode];
      return { ...prev, preferred_work_modes: updated };
    });
  };

  return (
    <AppLayout title="System Settings & Daily Digest Intelligence">
      <div style={{ maxWidth: '800px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Daily Intelligence Digest Card */}
        <Card style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <Mail size={20} color="var(--accent-primary)" />
            <h3 style={{ fontSize: '18px', margin: 0, fontWeight: 700 }}>
              Daily Career Intelligence Digest
            </h3>
          </div>
          <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.5 }}>
            Automated scheduled job digest compiled and delivered directly to your inbox every evening at your target hour.
          </p>

          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Toggle */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>
                  Enable Scheduled Email Digest
                </div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Aggregates top matching roles, salary intel, and interview scheduling alerts
                </div>
              </div>
              <input
                type="checkbox"
                checked={pref.digest_enabled}
                onChange={(e) => setPref({ ...pref, digest_enabled: e.target.checked })}
                style={{ width: '20px', height: '20px', accentColor: 'var(--accent-primary)', cursor: 'pointer' }}
              />
            </div>

            {/* Target Time */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                Delivery Schedule Time (Local 24-Hour Format)
              </label>
              <Input
                type="text"
                value={pref.digest_time}
                onChange={(e) => setPref({ ...pref, digest_time: e.target.value })}
                leftIcon={<Clock size={15} />}
                helperText="Standard default: 22:00 (10:00 PM local time)"
              />
            </div>

            {/* Modality Preferences */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                Preferred Work Modes for Digest
              </label>
              <div style={{ display: 'flex', gap: '10px' }}>
                {WORK_MODES.map((mode) => {
                  const isSelected = (pref.preferred_work_modes || []).includes(mode);
                  return (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => toggleWorkMode(mode)}
                      style={{
                        flex: 1,
                        padding: '10px 14px',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '13px',
                        fontWeight: isSelected ? 600 : 400,
                        border: isSelected
                          ? '1px solid var(--accent-primary)'
                          : '1px solid var(--border-subtle)',
                        backgroundColor: isSelected
                          ? 'rgba(99, 102, 241, 0.15)'
                          : 'var(--bg-card)',
                        color: isSelected ? 'var(--accent-primary)' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {isSelected ? `✓ ${mode}` : mode}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Minimum Salary Threshold */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                Minimum Compensation Floor ($/yr)
              </label>
              <Input
                type="number"
                value={pref.min_desired_salary || ''}
                onChange={(e) =>
                  setPref({ ...pref, min_desired_salary: e.target.value ? Number(e.target.value) : undefined })
                }
                leftIcon={<DollarSign size={15} />}
                helperText="Omit roles below this compensation figure from high-priority digest alerts"
              />
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '10px' }}>
              <Button type="submit" variant="primary" size="md" isLoading={isSaving}>
                Save Preferences
              </Button>
              {saveSuccess && (
                <span style={{ fontSize: '13px', color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CheckCircle2 size={16} /> Preferences successfully updated!
                </span>
              )}
            </div>
          </form>

          {/* Digest Testing & Preview Tools */}
          <div
            style={{
              marginTop: '32px',
              paddingTop: '24px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <h4 style={{ fontSize: '15px', fontWeight: 600, margin: 0 }}>
              On-Demand Digest Testing & Inspection
            </h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
              Preview today's compiled email digest directly in the browser or trigger an immediate test dispatch to your verified email.
            </p>

            <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
              <Button
                variant="outline"
                size="md"
                isLoading={isPreviewing}
                leftIcon={<Eye size={15} />}
                onClick={handlePreviewDigest}
              >
                Preview Today's Digest
              </Button>

              <Button
                variant="secondary"
                size="md"
                isLoading={isTriggering}
                leftIcon={<Send size={15} />}
                onClick={handleTriggerDigest}
              >
                Send Digest Now
              </Button>
            </div>
          </div>
        </Card>

        {/* Security & Multi-Tenant Isolation Info Card */}
        <Card style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <Shield size={18} color="var(--success)" />
            <h4 style={{ fontSize: '15px', fontWeight: 600, margin: 0 }}>
              Tenant Isolation & Data Privacy
            </h4>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
            All OAuth access tokens, candidate resumes, and extracted intelligence records are partitioned strictly by <code>user_id</code> and encrypted using AES-128 Fernet cryptography. Disconnecting your Google integration purges tokens and halts synchronization.
          </p>
        </Card>
      </div>

      {/* Digest Preview Modal */}
      <Modal
        isOpen={!!preview}
        onClose={() => setPreview(null)}
        title="Today's Job Intelligence Digest Preview"
        maxWidth="780px"
        footer={
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
            <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>
              Recipient: <code style={{ color: 'var(--text-primary)' }}>{preview?.recipient_email}</code>
            </div>
            <Button variant="primary" size="sm" onClick={() => setPreview(null)}>
              Close Preview
            </Button>
          </div>
        }
      >
        {preview && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {/* Digest Meta Header */}
            <div
              style={{
                padding: '16px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                Subject: {preview.subject}
              </div>
              <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                <span>Date: {preview.date_formatted}</span>
                <span>•</span>
                <span>Top Matches: <strong style={{ color: 'var(--success)' }}>{preview.top_matches_count}</strong></span>
                <span>•</span>
                <span>Evaluated: {preview.total_jobs_evaluated} roles</span>
              </div>
            </div>

            {/* Tab switch */}
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
              <button
                type="button"
                onClick={() => setPreviewTab('html')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  backgroundColor: previewTab === 'html' ? 'var(--accent-primary)' : 'transparent',
                  color: previewTab === 'html' ? '#fff' : 'var(--text-secondary)',
                  fontSize: '13px',
                  fontWeight: previewTab === 'html' ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                <Code size={14} /> Rendered Email HTML
              </button>
              <button
                type="button"
                onClick={() => setPreviewTab('text')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  backgroundColor: previewTab === 'text' ? 'var(--accent-primary)' : 'transparent',
                  color: previewTab === 'text' ? '#fff' : 'var(--text-secondary)',
                  fontSize: '13px',
                  fontWeight: previewTab === 'text' ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                <FileText size={14} /> Plain Text Fallback
              </button>
            </div>

            {previewTab === 'html' ? (
              <div
                style={{
                  maxHeight: '440px',
                  overflowY: 'auto',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: '#ffffff',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <iframe
                  title="Digest HTML View"
                  srcDoc={preview.html_content}
                  sandbox="allow-same-origin"
                  style={{
                    width: '100%',
                    height: '420px',
                    border: 'none',
                    backgroundColor: '#ffffff',
                  }}
                />
              </div>
            ) : (
              <div
                style={{
                  maxHeight: '440px',
                  overflowY: 'auto',
                  padding: '16px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  fontFamily: 'monospace',
                  fontSize: '12.5px',
                  lineHeight: 1.6,
                  color: 'var(--text-secondary)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {preview.text_content}
              </div>
            )}
          </div>
        )}
      </Modal>
    </AppLayout>
  );
};
