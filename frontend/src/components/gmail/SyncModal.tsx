import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Spinner } from '../common/Spinner';
import { api } from '../../api/client';
import { RefreshCw, CheckCircle2, AlertTriangle, Filter } from 'lucide-react';

interface SyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSyncComplete?: () => void;
}

interface SyncResponse {
  total_fetched: number;
  new_emails_stored: number;
  duplicates_skipped: number;
  status: string;
  message: string;
}

export const SyncModal: React.FC<SyncModalProps> = ({
  isOpen,
  onClose,
  onSyncComplete,
}) => {
  const [maxResults, setMaxResults] = useState<number>(50);
  const [queryOverride, setQueryOverride] = useState<string>('');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [result, setResult] = useState<SyncResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newAppPassword, setNewAppPassword] = useState<string>('');
  const [isReconnecting, setIsReconnecting] = useState<boolean>(false);
  const [reconnectSuccess, setReconnectSuccess] = useState<string | null>(null);

  const handleSync = async () => {
    setIsSyncing(true);
    setError(null);
    setResult(null);

    try {
      const payload: { max_results: number; query_override?: string } = {
        max_results: maxResults,
      };
      if (queryOverride.trim()) {
        payload.query_override = queryOverride.trim();
      }

      const res = await api.post<SyncResponse>('/emails/sync', payload);
      setResult(res);
      if (onSyncComplete) {
        onSyncComplete();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to sync with Gmail. Please ensure Gmail is connected.');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleUpdateAppPasswordAndSync = async () => {
    if (!newAppPassword.trim()) {
      alert('Please enter your 16-character Google App Password.');
      return;
    }
    setIsReconnecting(true);
    setError(null);
    try {
      await api.post('/gmail/connect-app-password', {
        app_password: newAppPassword.trim(),
      });
      setReconnectSuccess('App Password verified and updated successfully!');
      setNewAppPassword('');
      // Trigger sync immediately with the new password
      await handleSync();
    } catch (err: any) {
      setError(err.message || 'Failed to authenticate with new App Password.');
    } finally {
      setIsReconnecting(false);
    }
  };

  const handleResetAndClose = () => {
    setResult(null);
    setError(null);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={isSyncing ? () => {} : handleResetAndClose}
      title="Synchronize Gmail Job Emails"
      footer={
        result ? (
          <Button variant="primary" size="md" onClick={handleResetAndClose}>
            Done
          </Button>
        ) : (
          <>
            <Button
              variant="outline"
              size="md"
              disabled={isSyncing}
              onClick={handleResetAndClose}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="md"
              isLoading={isSyncing}
              leftIcon={<RefreshCw size={16} />}
              onClick={handleSync}
            >
              {isSyncing ? 'Syncing...' : 'Start Ingestion'}
            </Button>
          </>
        )
      }
    >
      {result ? (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            <CheckCircle2 size={32} color="var(--success)" />
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: 600, margin: '0 0 8px 0' }}>
            Ingestion Complete!
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
            {result.message}
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '12px',
              backgroundColor: 'var(--bg-card)',
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Fetched</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)' }}>
                {result.total_fetched}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Ingested</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--success)' }}>
                {result.new_emails_stored}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Duplicates</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--warning)' }}>
                {result.duplicates_skipped}
              </div>
            </div>
          </div>
        </div>
      ) : isSyncing ? (
        <div style={{ textAlign: 'center', padding: '36px 0' }}>
          <Spinner size={32} />
          <h4 style={{ marginTop: '18px', fontSize: '16px', fontWeight: 600 }}>
            Ingesting from Gmail...
          </h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: '340px', margin: '8px auto 0' }}>
            Retrieving messages via OAuth 2.0, stripping tracking noise, running duplicate hash matching, and caching records.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {reconnectSuccess && (
            <div
              style={{
                padding: '12px 14px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: 'var(--success)',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <CheckCircle2 size={16} />
              <span>{reconnectSuccess}</span>
            </div>
          )}

          {error && (
            <div
              style={{
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <AlertTriangle size={18} style={{ color: 'var(--danger)', flexShrink: 0, marginTop: '2px' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--danger)', marginBottom: '3px' }}>
                    Gmail Authentication Failed
                  </div>
                  <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Google rejected the login credentials. This happens if the 16-character App Password was revoked or changed, or if IMAP is disabled in your Gmail settings.
                  </div>
                </div>
              </div>

              {/* Inline Quick Fix Box */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  🔑 Paste your 16-character App Password to reconnect:
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <Input
                    placeholder="xxxx xxxx xxxx xxxx"
                    value={newAppPassword}
                    onChange={(e) => setNewAppPassword(e.target.value)}
                    disabled={isReconnecting}
                    style={{ flex: 1, fontFamily: 'monospace', letterSpacing: '1px' }}
                  />
                  <Button
                    variant="primary"
                    size="md"
                    isLoading={isReconnecting}
                    onClick={handleUpdateAppPasswordAndSync}
                  >
                    Update & Sync
                  </Button>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  <div style={{ marginBottom: '4px' }}>
                    <strong>1. Enable Gmail IMAP:</strong> In Gmail, open <strong>Settings ⚙️ ➔ See all settings ➔ Forwarding and POP/IMAP</strong>, select <strong>Enable IMAP</strong>, and click <em>Save Changes</em>.
                  </div>
                  <div>
                    <strong>2. Get new App Password:</strong> Generate a 16-character code at{' '}
                    <a
                      href="https://myaccount.google.com/apppasswords"
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}
                    >
                      myaccount.google.com/apppasswords ↗
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--text-secondary)',
                marginBottom: '8px',
              }}
            >
              Batch Size (Max Emails to Fetch)
            </label>
            <div style={{ display: 'flex', gap: '10px' }}>
              {[15, 25, 50, 100].map((count) => (
                <button
                  key={count}
                  type="button"
                  onClick={() => setMaxResults(count)}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border:
                      maxResults === count
                        ? '1px solid var(--accent-primary)'
                        : '1px solid var(--border-subtle)',
                    backgroundColor:
                      maxResults === count
                        ? 'rgba(99, 102, 241, 0.15)'
                        : 'var(--bg-input)',
                    color:
                      maxResults === count ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    fontWeight: maxResults === count ? 600 : 400,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {count} emails
                </button>
              ))}
            </div>
          </div>

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--text-secondary)',
                marginBottom: '8px',
              }}
            >
              Search Query Filter (Optional)
            </label>
            <Input
              placeholder='e.g., subject:(application OR interview OR offer)'
              value={queryOverride}
              onChange={(e) => setQueryOverride(e.target.value)}
              leftIcon={<Filter size={16} />}
            />
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
              Leave blank to use the smart job recruitment search query.
            </span>
          </div>

          <div
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}
          >
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
              Privacy & Ingestion Notice:
            </div>
            Only email headers and job-related email bodies matching recruitment heuristics are processed.
            Private personal correspondence is automatically ignored.
          </div>
        </div>
      )}
    </Modal>
  );
};
