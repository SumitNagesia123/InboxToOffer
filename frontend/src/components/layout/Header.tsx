import React, { useEffect, useState } from 'react';
import { Bell, RefreshCw, RotateCw, Check } from 'lucide-react';
import { api } from '../../api/client';
import { Button } from '../common/Button';

interface HeaderProps {
  title?: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  category: string;
  is_read: boolean;
  created_at: string;
}

export const Header: React.FC<HeaderProps> = ({ title = 'Dashboard', onRefresh, isRefreshing: propIsRefreshing }) => {
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [localRefreshing, setLocalRefreshing] = useState<boolean>(false);
  const [showNotifications, setShowNotifications] = useState<boolean>(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  const isRefreshing = propIsRefreshing || localRefreshing;

  const fetchUnreadCount = async () => {
    try {
      const res = await api.get<{ unread_count: number }>('/notifications/unread-count');
      setUnreadCount(res.unread_count);
    } catch {
      // ignore
    }
  };

  const fetchNotifications = async () => {
    try {
      const res = await api.get<{ items: NotificationItem[] }>('/notifications?limit=6');
      setNotifications(res.items);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleGlobalRefresh = async () => {
    setLocalRefreshing(true);
    try {
      if (onRefresh) {
        onRefresh();
      }
      window.dispatchEvent(new CustomEvent('app:refresh-data'));
      await fetchUnreadCount();
    } finally {
      setTimeout(() => setLocalRefreshing(false), 700);
    }
  };

  const handleSyncGmail = async () => {
    setIsSyncing(true);
    try {
      await api.post('/gmail/sync', { max_results: 25 });
      await fetchUnreadCount();
      window.dispatchEvent(new CustomEvent('app:refresh-data'));
      alert('Gmail sync completed successfully!');
    } catch (err: any) {
      alert(`Sync error: ${err.message || 'Failed to trigger sync'}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleToggleNotifications = () => {
    if (!showNotifications) {
      fetchNotifications();
    }
    setShowNotifications(!showNotifications);
  };

  const handleMarkAllRead = async () => {
    try {
      await api.post('/notifications/mark-all-read');
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // ignore
    }
  };

  return (
    <header
      style={{
        height: '68px',
        backgroundColor: 'rgba(8, 12, 20, 0.75)',
        backdropFilter: 'var(--glass-blur)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '0 28px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Page Title */}
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700, margin: 0 }}>{title}</h1>
      </div>

      {/* Action Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', position: 'relative' }}>
        {/* Quick Refresh Button */}
        <Button
          variant="outline"
          size="sm"
          isLoading={isRefreshing}
          leftIcon={<RotateCw size={14} className={isRefreshing ? 'animate-spin' : ''} />}
          onClick={handleGlobalRefresh}
          title="Refresh current page intelligence and metrics"
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </Button>

        {/* Manual Gmail Sync Button */}
        <Button
          variant="primary"
          size="sm"
          isLoading={isSyncing}
          leftIcon={<RefreshCw size={14} className={isSyncing ? 'animate-spin' : ''} />}
          onClick={handleSyncGmail}
        >
          {isSyncing ? 'Syncing...' : 'Sync Gmail'}
        </Button>

        {/* Notifications Icon with Badge */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={handleToggleNotifications}
            style={{
              position: 'relative',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              width: '38px',
              height: '38px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'all var(--transition-fast)',
            }}
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span
                style={{
                  position: 'absolute',
                  top: '-4px',
                  right: '-4px',
                  backgroundColor: 'var(--primary)',
                  color: '#ffffff',
                  fontSize: '10px',
                  fontWeight: 700,
                  borderRadius: 'var(--radius-full)',
                  minWidth: '18px',
                  height: '18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '0 4px',
                  boxShadow: '0 0 10px var(--primary-glow)',
                }}
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div
              style={{
                position: 'absolute',
                top: '48px',
                right: 0,
                width: '340px',
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--shadow-lg)',
                overflow: 'hidden',
                zIndex: 100,
                animation: 'fadeIn 150ms ease-out',
              }}
            >
              <div
                style={{
                  padding: '14px 16px',
                  borderBottom: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span style={{ fontWeight: 600, fontSize: '14px' }}>Notifications</span>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--primary)',
                      fontSize: '12px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <Check size={12} /> Mark all read
                  </button>
                )}
              </div>

              <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                {notifications.length === 0 ? (
                  <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                    No notifications yet
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      style={{
                        padding: '12px 16px',
                        borderBottom: '1px solid var(--border-subtle)',
                        backgroundColor: n.is_read ? 'transparent' : 'rgba(99, 102, 241, 0.05)',
                        transition: 'background var(--transition-fast)',
                      }}
                    >
                      <div style={{ fontSize: '13px', fontWeight: n.is_read ? 500 : 600, color: 'var(--text-primary)' }}>
                        {n.title}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                        {n.message}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
