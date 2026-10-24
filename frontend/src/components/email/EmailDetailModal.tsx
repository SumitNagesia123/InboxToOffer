import React, { useEffect, useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Spinner } from '../common/Spinner';
import { api } from '../../api/client';
import {
  Mail,
  User,
  Calendar,
  Sparkles,
  FileText,
  Code,
} from 'lucide-react';

export interface EmailDetail {
  id: string;
  gmail_message_id: string;
  gmail_thread_id?: string;
  sender: string;
  recipient: string;
  subject: string;
  received_at: string;
  category: string;
  classification_confidence?: number;
  classification_reason?: string;
  processed_status: string;
  body_text?: string;
  body_html?: string;
  created_at: string;
}

interface EmailDetailModalProps {
  emailId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onEmailUpdated?: () => void;
}

export const EmailDetailModal: React.FC<EmailDetailModalProps> = ({
  emailId,
  isOpen,
  onClose,
  onEmailUpdated,
}) => {
  const [detail, setDetail] = useState<EmailDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isClassifying, setIsClassifying] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'text' | 'html'>('text');

  const fetchDetail = async (id: string) => {
    setIsLoading(true);
    try {
      const data = await api.get<EmailDetail>(`/emails/${id}`);
      setDetail(data);
    } catch (err) {
      console.error('Failed to load email details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && emailId) {
      fetchDetail(emailId);
      setActiveTab('text');
    } else {
      setDetail(null);
    }
  }, [isOpen, emailId]);

  const handleReclassify = async () => {
    if (!emailId) return;
    setIsClassifying(true);
    try {
      const updated = await api.post<EmailDetail>(`/emails/${emailId}/classify`);
      setDetail(updated);
      if (onEmailUpdated) onEmailUpdated();
    } catch (err: any) {
      alert(`Reclassification failed: ${err.message}`);
    } finally {
      setIsClassifying(false);
    }
  };

  const getBadgeVariant = (cat: string): 'primary' | 'danger' | 'success' | 'warning' | 'info' | 'neutral' => {
    const c = cat.toUpperCase();
    if (c.includes('OFFER')) return 'success';
    if (c.includes('INTERVIEW')) return 'primary';
    if (c.includes('JOB')) return 'info';
    if (c.includes('REJECT')) return 'danger';
    if (c.includes('APPLICATION') || c.includes('ACK')) return 'warning';
    return 'neutral';
  };

  const confidencePct = detail?.classification_confidence
    ? Math.round(detail.classification_confidence * 100)
    : null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Email Intelligence Viewer"
      maxWidth="720px"
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Gmail ID: <code style={{ color: 'var(--text-secondary)' }}>{detail?.gmail_message_id}</code>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              variant="outline"
              size="sm"
              isLoading={isClassifying}
              leftIcon={<Sparkles size={14} />}
              onClick={handleReclassify}
            >
              Re-classify (NLP)
            </Button>
            <Button variant="primary" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      }
    >
      {isLoading || !detail ? (
        <div style={{ textAlign: 'center', padding: '48px 0' }}>
          <Spinner size={32} />
          <p style={{ marginTop: '16px', fontSize: '14px', color: 'var(--text-muted)' }}>
            Retrieving email body and NLP classification data...
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Header Info */}
          <div
            style={{
              padding: '16px',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
              <h3 style={{ fontSize: '17px', fontWeight: 600, margin: '0 0 10px 0', lineHeight: 1.4 }}>
                {detail.subject}
              </h3>
              <Badge variant={getBadgeVariant(detail.category)}>
                {detail.category}
              </Badge>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '10px',
                fontSize: '13px',
                color: 'var(--text-secondary)',
                marginTop: '10px',
                paddingTop: '10px',
                borderTop: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <User size={14} color="var(--text-muted)" />
                <span style={{ color: 'var(--text-muted)' }}>From:</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{detail.sender}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Mail size={14} color="var(--text-muted)" />
                <span style={{ color: 'var(--text-muted)' }}>To:</span>
                <span>{detail.recipient}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Calendar size={14} color="var(--text-muted)" />
                <span style={{ color: 'var(--text-muted)' }}>Date:</span>
                <span>{new Date(detail.received_at).toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* NLP Classification Insight Banner */}
          <div
            style={{
              padding: '14px 16px',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.05) 100%)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={16} color="var(--accent-primary)" />
                <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
                  NLP Intelligence Assessment
                </span>
              </div>
              {confidencePct !== null && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Confidence:</span>
                  <div
                    style={{
                      width: '70px',
                      height: '6px',
                      backgroundColor: 'rgba(255,255,255,0.1)',
                      borderRadius: '3px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${confidencePct}%`,
                        height: '100%',
                        backgroundColor:
                          confidencePct > 80
                            ? 'var(--success)'
                            : confidencePct > 50
                            ? 'var(--warning)'
                            : 'var(--danger)',
                      }}
                    />
                  </div>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {confidencePct}%
                  </span>
                </div>
              )}
            </div>
            {detail.classification_reason ? (
              <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                {detail.classification_reason}
              </p>
            ) : (
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
                Rule-based & keyword pattern classifier assigned initial taxonomy.
              </p>
            )}
          </div>

          {/* Content View Tabs */}
          <div>
            <div
              style={{
                display: 'flex',
                gap: '8px',
                borderBottom: '1px solid var(--border-subtle)',
                paddingBottom: '8px',
                marginBottom: '12px',
              }}
            >
              <button
                type="button"
                onClick={() => setActiveTab('text')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  backgroundColor: activeTab === 'text' ? 'var(--accent-primary)' : 'transparent',
                  color: activeTab === 'text' ? '#fff' : 'var(--text-secondary)',
                  fontSize: '13px',
                  fontWeight: activeTab === 'text' ? 600 : 400,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <FileText size={14} />
                Cleaned Body Text
              </button>
              {detail.body_html && (
                <button
                  type="button"
                  onClick={() => setActiveTab('html')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 14px',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    backgroundColor: activeTab === 'html' ? 'var(--accent-primary)' : 'transparent',
                    color: activeTab === 'html' ? '#fff' : 'var(--text-secondary)',
                    fontSize: '13px',
                    fontWeight: activeTab === 'html' ? 600 : 400,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <Code size={14} />
                  Original Email HTML
                </button>
              )}
            </div>

            {activeTab === 'text' ? (
              <div
                style={{
                  maxHeight: '380px',
                  overflowY: 'auto',
                  padding: '16px',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '12.5px',
                  lineHeight: 1.6,
                  color: 'var(--text-secondary)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {detail.body_text || '(No cleaned plain text content available)'}
              </div>
            ) : (
              <div
                style={{
                  maxHeight: '380px',
                  overflowY: 'auto',
                  padding: '16px',
                  backgroundColor: '#ffffff',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  color: '#1f2937',
                }}
              >
                <iframe
                  title="Sanitized Email HTML"
                  srcDoc={detail.body_html}
                  sandbox="allow-same-origin"
                  style={{
                    width: '100%',
                    height: '340px',
                    border: 'none',
                    backgroundColor: '#ffffff',
                  }}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
};
