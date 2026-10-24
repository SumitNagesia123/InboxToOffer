import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Spinner } from '../components/common/Spinner';
import { api } from '../api/client';
import { CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';

export const GmailCallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const errorParam = searchParams.get('error');

      if (errorParam) {
        setStatus('error');
        setErrorMessage(`Google OAuth was cancelled or denied: ${errorParam}`);
        return;
      }

      if (!code || !state) {
        setStatus('error');
        setErrorMessage('Missing authorization code or state parameter from Google.');
        return;
      }

      try {
        await api.post('/gmail/callback', { code, state });
        sessionStorage.removeItem('gmail_oauth_state');
        setStatus('success');

        // Automatically redirect to /emails after 2 seconds
        const timer = setTimeout(() => {
          navigate('/emails');
        }, 2200);

        return () => clearTimeout(timer);
      } catch (err: any) {
        setStatus('error');
        setErrorMessage(
          err.message || 'Failed to exchange authorization code. Please verify credentials and try again.'
        );
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        backgroundColor: 'var(--bg-base)',
      }}
    >
      <Card style={{ maxWidth: '460px', width: '100%', padding: '36px', textAlign: 'center' }}>
        {status === 'processing' && (
          <div>
            <Spinner size={36} />
            <h2 style={{ fontSize: '20px', fontWeight: 600, marginTop: '20px', marginBottom: '8px' }}>
              Finalizing Gmail Connection
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.5 }}>
              Exchanging authorization token with Google, establishing secure Fernet encrypted credentials, and preparing your ingestion pipeline...
            </p>
          </div>
        )}

        {status === 'success' && (
          <div>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
              }}
            >
              <CheckCircle2 size={36} color="var(--success)" />
            </div>
            <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>
              Gmail Connected Successfully!
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px', lineHeight: 1.5 }}>
              Your Google account is now authenticated. Redirecting you to your job email inbox...
            </p>
            <Button
              variant="primary"
              size="md"
              style={{ width: '100%' }}
              rightIcon={<ArrowRight size={16} />}
              onClick={() => navigate('/emails')}
            >
              Go to Job Emails
            </Button>
          </div>
        )}

        {status === 'error' && (
          <div>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
              }}
            >
              <AlertTriangle size={36} color="var(--danger)" />
            </div>
            <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>
              Connection Failed
            </h2>
            <p style={{ color: 'var(--danger)', fontSize: '13px', marginBottom: '24px', lineHeight: 1.5 }}>
              {errorMessage}
            </p>
            <div style={{ display: 'flex', gap: '12px' }}>
              <Button
                variant="outline"
                size="md"
                style={{ width: '100%' }}
                onClick={() => navigate('/emails')}
              >
                Back to Inbox
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
