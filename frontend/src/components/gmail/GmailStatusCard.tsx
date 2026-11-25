import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Unlink,
  ExternalLink,
  Key,
  ShieldCheck,
  Copy,
  Check,
  Sparkles,
  Inbox,
  Briefcase,
  Award,
  Lock,
  Mail,
  Info,
} from 'lucide-react';
import { api } from '../../api/client';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Modal } from '../common/Modal';
import { Input } from '../common/Input';

export interface GmailStatus {
  connected: boolean;
  is_connected?: boolean;
  provider: string;
  client_id?: string;
  scopes: string[];
  expires_at?: string;
}

interface SyncRealResponse {
  success: boolean;
  connected: boolean;
  message: string;
  total_fetched: number;
  new_stored: number;
  jobs_extracted: number;
  matches_computed: number;
}

interface GmailStatusCardProps {
  onSyncClick?: () => void;
  onStatusChange?: (connected: boolean) => void;
}

export const GmailStatusCard: React.FC<GmailStatusCardProps> = ({
  onSyncClick,
  onStatusChange,
}) => {
  const [status, setStatus] = useState<GmailStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showDisconnectModal, setShowDisconnectModal] = useState<boolean>(false);
  const [showConnectModal, setShowConnectModal] = useState<boolean>(false);
  const [isDisconnecting, setIsDisconnecting] = useState<boolean>(false);

  // Active Connection Tab: 'app_password' | 'oauth'
  const [activeTab, setActiveTab] = useState<'app_password' | 'oauth'>('app_password');

  // App Password Form
  const [appPassword, setAppPassword] = useState<string>('');
  const [isSubmittingAppPass, setIsSubmittingAppPass] = useState<boolean>(false);
  const [syncResult, setSyncResult] = useState<SyncRealResponse | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  // OAuth Form
  const [clientId, setClientId] = useState<string>('');
  const [clientSecret, setClientSecret] = useState<string>('');
  const [isSavingOAuth, setIsSavingOAuth] = useState<boolean>(false);
  const [copiedUri, setCopiedUri] = useState<boolean>(false);

  const [candidateEmail, setCandidateEmail] = useState<string>('sumitnagesia826@gmail.com');
  const REDIRECT_URI = `${window.location.protocol}//${window.location.hostname}:8000/api/v1/gmail/callback`;

  const fetchStatus = async () => {
    try {
      const data = await api.get<GmailStatus>('/gmail/status');
      const isConn = Boolean(data.connected ?? data.is_connected);
      setStatus({ ...data, connected: isConn });
      if (onStatusChange) onStatusChange(isConn);
    } catch {
      setStatus({ connected: false, provider: 'google', scopes: [] });
      if (onStatusChange) onStatusChange(false);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    api.get<{ email?: string }>('/auth/me')
      .then((user) => {
        if (user?.email) setCandidateEmail(user.email);
      })
      .catch(() => {});
  }, []);

  const handleOpenConnect = () => {
    setAuthError(null);
    setSyncResult(null);
    setShowConnectModal(true);
  };

  const handleConnectAppPassword = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const clean = appPassword.replace(/\s+/g, '').trim();
    if (!clean || clean.length < 8) {
      setAuthError('Please enter your 16-character Google App Password.');
      return;
    }

    setIsSubmittingAppPass(true);
    setAuthError(null);
    setSyncResult(null);

    try {
      const res = await api.post<SyncRealResponse>('/gmail/connect-app-password', {
        app_password: clean,
      });
      setSyncResult(res);
      await fetchStatus();
      if (onStatusChange) onStatusChange(true);
    } catch (err: any) {
      setAuthError(
        err.message || 'Failed to authenticate with Gmail IMAP. Please verify your App Password.'
      );
    } finally {
      setIsSubmittingAppPass(false);
    }
  };

  const handleSaveOAuth = async () => {
    setIsSavingOAuth(true);
    try {
      if (clientId.trim() && clientSecret.trim()) {
        try {
          await api.post('/gmail/configure-oauth', {
            client_id: clientId.trim(),
            client_secret: clientSecret.trim(),
          });
        } catch (e) {
          // Ignore read-only file system write errors on cloud hosts
        }
      }

      const res = await api.get<{
        authorization_url: string;
        state: string;
        is_configured?: boolean;
      }>('/gmail/connect');

      if (res.authorization_url) {
        sessionStorage.setItem('gmail_oauth_state', res.state);
        window.location.href = res.authorization_url;
      } else {
        alert('OAuth not configured. Please ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in your Render environment variables.');
      }
    } catch (err: any) {
      alert(`Failed to connect Google OAuth: ${err.message}`);
    } finally {
      setIsSavingOAuth(false);
    }
  };

  const handleCopyUri = () => {
    navigator.clipboard.writeText(REDIRECT_URI);
    setCopiedUri(true);
    setTimeout(() => setCopiedUri(false), 2000);
  };

  const handleDisconnect = async () => {
    setIsDisconnecting(true);
    try {
      await api.delete('/gmail/disconnect');
      setShowDisconnectModal(false);
      await fetchStatus();
      if (onStatusChange) onStatusChange(false);
    } catch (err: any) {
      if (err.status === 401 || err.message?.includes('token') || err.message?.includes('log in')) {
        window.location.href = '/login?session_expired=true&redirect=/emails';
        return;
      }
      alert(`Disconnect failed: ${err.message}`);
    } finally {
      setIsDisconnecting(false);
    }
  };

  if (isLoading) {
    return (
      <Card style={{ padding: '20px' }}>
        <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Checking Gmail status...</div>
      </Card>
    );
  }

  const isConnected = !!status?.connected;
  const isImap = status?.provider === 'google_imap';

  return (
    <>
      <Card
        style={{
          border: isConnected ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(245, 158, 11, 0.3)',
          background: isConnected
            ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(15, 23, 42, 0.8) 100%)'
            : 'linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, rgba(15, 23, 42, 0.8) 100%)',
          padding: '24px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '12px',
                backgroundColor: isConnected ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {isConnected ? (
                <CheckCircle2 size={24} color="var(--success)" />
              ) : (
                <AlertCircle size={24} color="var(--warning)" />
              )}
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '17px', margin: 0 }}>Gmail Inbox Sync</h3>
                <Badge variant={isConnected ? 'success' : 'warning'}>
                  {isConnected ? (isImap ? 'Live IMAP Sync' : 'Connected & Active') : 'Action Required'}
                </Badge>
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
                {isConnected
                  ? `Real candidate inbox (${candidateEmail}) synchronized. Automated job extraction & match scoring active.`
                  : 'Connect your real Gmail inbox to automatically ingest genuine job alerts, interviews, and applications.'}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {isConnected ? (
              <>
                {onSyncClick && (
                  <Button
                    variant="primary"
                    size="sm"
                    leftIcon={<RefreshCw size={14} />}
                    onClick={onSyncClick}
                  >
                    Sync Inbox Now
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<Unlink size={14} />}
                  onClick={() => setShowDisconnectModal(true)}
                >
                  Disconnect
                </Button>
              </>
            ) : (
              <Button
                variant="primary"
                size="md"
                leftIcon={<Mail size={16} />}
                onClick={handleOpenConnect}
              >
                Connect Real Gmail Account
              </Button>
            )}
          </div>
        </div>

        {isConnected && (
          <div
            style={{
              marginTop: '16px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '12px',
              color: 'var(--text-muted)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={14} color="var(--success)" />
              <span>
                Account: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{candidateEmail}</span> ({isImap ? 'imap.gmail.com:993' : 'Google OAuth 2.0'})
              </span>
            </div>
            <div>
              Security: <span style={{ color: 'var(--success)' }}>AES-128 Fernet Encrypted</span>
            </div>
          </div>
        )}
      </Card>

      {/* Connect Gmail Modal */}
      <Modal
        isOpen={showConnectModal}
        onClose={() => {
          setShowConnectModal(false);
          setSyncResult(null);
          setAuthError(null);
        }}
        title="Connect Your Real Gmail Account"
        footer={
          syncResult ? (
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                setShowConnectModal(false);
                setSyncResult(null);
              }}
            >
              View Ingested Emails
            </Button>
          ) : (
            <Button
              variant="outline"
              size="md"
              onClick={() => {
                setShowConnectModal(false);
                setAuthError(null);
              }}
            >
              Cancel
            </Button>
          )
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {syncResult ? (
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
                Real Gmail Inbox Synchronized!
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '13.5px', marginBottom: '20px' }}>
                {syncResult.message}
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
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', fontSize: '12px', color: 'var(--text-muted)' }}>
                    <Inbox size={13} /> Emails Read
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                    {syncResult.total_fetched}
                  </div>
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', fontSize: '12px', color: 'var(--text-muted)' }}>
                    <Briefcase size={13} /> Jobs Parsed
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--accent-secondary)', marginTop: '4px' }}>
                    {syncResult.jobs_extracted}
                  </div>
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', fontSize: '12px', color: 'var(--text-muted)' }}>
                    <Award size={13} /> Matches Scored
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--success)', marginTop: '4px' }}>
                    {syncResult.matches_computed}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Tab Selector */}
              <div
                style={{
                  display: 'flex',
                  backgroundColor: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-md)',
                  padding: '4px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <button
                  type="button"
                  onClick={() => setActiveTab('app_password')}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    backgroundColor: activeTab === 'app_password' ? 'var(--accent-primary)' : 'transparent',
                    color: activeTab === 'app_password' ? '#ffffff' : 'var(--text-secondary)',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  ⚡ Direct Gmail Sync (App Password)
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('oauth')}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: 'none',
                    backgroundColor: activeTab === 'oauth' ? 'var(--accent-primary)' : 'transparent',
                    color: activeTab === 'oauth' ? '#ffffff' : 'var(--text-secondary)',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  🔑 Google Cloud OAuth
                </button>
              </div>

              {authError && (
                <div
                  style={{
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    color: 'var(--danger)',
                    fontSize: '13px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                  }}
                >
                  <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <span>{authError}</span>
                </div>
              )}

              {activeTab === 'app_password' ? (
                <form onSubmit={handleConnectAppPassword} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div
                    style={{
                      padding: '14px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'rgba(99, 102, 241, 0.08)',
                      border: '1px solid rgba(99, 102, 241, 0.25)',
                      fontSize: '13px',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.5,
                    }}
                  >
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Info size={16} color="var(--accent-primary)" />
                      How to connect your real Gmail in 30 seconds:
                    </div>
                    <ol style={{ margin: '0', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <li>
                        Go to Google's{' '}
                        <a
                          href="https://myaccount.google.com/apppasswords"
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--accent-primary)', textDecoration: 'underline' }}
                        >
                          App Passwords Page <ExternalLink size={12} style={{ display: 'inline', verticalAlign: 'middle' }} />
                        </a>
                      </li>
                      <li>Name your app (e.g. <code>Job Intel</code>) and click <strong>Create</strong>.</li>
                      <li>Copy the generated 16-character code (e.g. <code>abcd efgh ijkl mnop</code>).</li>
                      <li>Paste it into the field below and click <strong>Connect & Ingest Real Emails</strong>.</li>
                    </ol>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      Candidate Email
                    </label>
                    <Input
                      value={candidateEmail}
                      disabled
                      leftIcon={<Mail size={16} />}
                      style={{ opacity: 0.8 }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      16-Character Google App Password
                    </label>
                    <Input
                      type="password"
                      placeholder="e.g. abcd efgh ijkl mnop"
                      value={appPassword}
                      onChange={(e) => setAppPassword(e.target.value)}
                      leftIcon={<Lock size={16} />}
                      autoFocus
                    />
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                      Encrypted with AES-128 Fernet. Only used to read your inbox messages for job correspondence.
                    </span>
                  </div>

                  <Button
                    type="submit"
                    variant="primary"
                    size="md"
                    isLoading={isSubmittingAppPass}
                    leftIcon={<Sparkles size={16} />}
                    style={{ marginTop: '8px' }}
                  >
                    {isSubmittingAppPass ? 'Connecting to Gmail & Syncing Real Mails...' : 'Connect & Sync Real Emails'}
                  </Button>
                </form>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    If you have registered an OAuth 2.0 Web Application in Google Cloud Console, enter your client details below:
                  </p>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      Authorized Redirect URI (Copy to Google Cloud Console):
                    </label>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        backgroundColor: 'var(--bg-input)',
                        padding: '6px 10px',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '12px',
                        color: 'var(--accent-secondary)',
                        fontFamily: 'monospace',
                      }}
                    >
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {REDIRECT_URI}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        leftIcon={copiedUri ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                        onClick={handleCopyUri}
                      >
                        {copiedUri ? 'Copied' : 'Copy'}
                      </Button>
                    </div>
                  </div>

                  <Input
                    label="Google Client ID"
                    placeholder="xxxxxxxx.apps.googleusercontent.com"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                  />

                  <Input
                    label="Google Client Secret"
                    placeholder="Enter Client Secret"
                    type="password"
                    value={clientSecret}
                    onChange={(e) => setClientSecret(e.target.value)}
                  />

                  <Button
                    variant="primary"
                    size="md"
                    isLoading={isSavingOAuth}
                    leftIcon={<Key size={15} />}
                    onClick={handleSaveOAuth}
                    style={{ alignSelf: 'flex-start' }}
                  >
                    Save & Authenticate via Google
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </Modal>

      {/* Disconnect Confirmation Modal */}
      <Modal
        isOpen={showDisconnectModal}
        onClose={() => setShowDisconnectModal(false)}
        title="Disconnect Gmail Account"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowDisconnectModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={isDisconnecting}
              onClick={handleDisconnect}
            >
              Confirm Disconnect
            </Button>
          </>
        }
      >
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          Are you sure you want to disconnect your Gmail integration? Live inbox synchronization and automated
          job extraction will be paused until reconnected.
        </p>
      </Modal>
    </>
  );
};
