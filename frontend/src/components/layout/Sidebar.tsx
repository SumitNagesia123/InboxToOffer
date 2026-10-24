import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Mail,
  Briefcase,
  Sparkles,
  KanbanSquare,
  FileText,
  BarChart3,
  Settings as SettingsIcon,
  LogOut,
  Zap,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface NavBadgeInfo {
  jobsCount: number;
  matchesCount: number;
  emailsCount: number;
  appsCount: number;
  hasResume: boolean;
  duplicateCount: number;
}

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const [isGmailConnected, setIsGmailConnected] = useState<boolean>(false);
  const [counts, setCounts] = useState<NavBadgeInfo>({
    jobsCount: 0,
    matchesCount: 0,
    emailsCount: 0,
    appsCount: 0,
    hasResume: false,
    duplicateCount: 0,
  });

  const loadRealCounts = async () => {
    try {
      const [gmailRes, jobsRes, matchesRes, emailsRes, appsRes, resumeRes, analyticsRes] =
        await Promise.allSettled([
          api.get<{ is_connected: boolean }>('/gmail/status'),
          api.get<{ total: number }>('/jobs?limit=1'),
          api.get<{ total: number }>('/matches?limit=1'),
          api.get<{ total: number }>('/emails?limit=1'),
          api.get<{ total: number }>('/applications?limit=1'),
          api.get<{ id: string }>('/resumes/me'),
          api.get<{ kpis: { duplicate_jobs_count: number } }>('/analytics'),
        ]);

      if (gmailRes.status === 'fulfilled') {
        const val: any = gmailRes.value;
        setIsGmailConnected(Boolean(val?.connected ?? val?.is_connected));
      }
      const totalMatches = matchesRes.status === 'fulfilled' ? matchesRes.value.total : 0;
      const totalApps = appsRes.status === 'fulfilled' ? appsRes.value.total : 0;
      setCounts({
        jobsCount: jobsRes.status === 'fulfilled' ? jobsRes.value.total : 0,
        matchesCount: Math.max(0, totalMatches - totalApps),
        emailsCount: emailsRes.status === 'fulfilled' ? emailsRes.value.total : 0,
        appsCount: totalApps,
        hasResume: resumeRes.status === 'fulfilled' && Boolean(resumeRes.value?.id),
        duplicateCount:
          analyticsRes.status === 'fulfilled' ? analyticsRes.value.kpis.duplicate_jobs_count : 0,
      });
    } catch {
      // Keep initial
    }
  };

  useEffect(() => {
    loadRealCounts();
    const handleGlobalRefresh = () => {
      loadRealCounts();
    };
    window.addEventListener('app:refresh-data', handleGlobalRefresh);
    const interval = setInterval(loadRealCounts, 20000);
    return () => {
      window.removeEventListener('app:refresh-data', handleGlobalRefresh);
      clearInterval(interval);
    };
  }, []);

  const navSections = [
    {
      title: 'MAIN',
      items: [
        { label: 'Dashboard', path: '/', icon: LayoutDashboard },
        {
          label: 'Jobs',
          path: '/jobs',
          icon: Briefcase,
          badge: counts.jobsCount > 0 ? String(counts.jobsCount) : undefined,
          badgeType: 'default' as const,
        },
        {
          label: 'Matches',
          path: '/matches',
          icon: Sparkles,
          badge: counts.matchesCount > 0 ? String(counts.matchesCount) : undefined,
          badgeType: 'emerald' as const,
        },
        {
          label: 'Emails',
          path: '/emails',
          icon: Mail,
          badge: counts.emailsCount > 0 ? String(counts.emailsCount) : undefined,
          badgeType: 'default' as const,
        },
      ],
    },
    {
      title: 'PROFILE',
      items: [
        {
          label: 'Resume',
          path: '/resume',
          icon: FileText,
          badge: counts.hasResume ? 'Active' : undefined,
          badgeType: 'primary' as const,
        },
        {
          label: 'Applications',
          path: '/applications',
          icon: KanbanSquare,
          badge: counts.appsCount > 0 ? String(counts.appsCount) : undefined,
          badgeType: 'default' as const,
        },
        { label: 'Analytics', path: '/analytics', icon: BarChart3 },
      ],
    },
    {
      title: 'SYSTEM',
      items: [
        { label: 'Settings', path: '/settings', icon: SettingsIcon },
        {
          label: 'Gmail Sync',
          path: '/emails',
          icon: Mail,
          badge: isGmailConnected ? 'Connected' : 'Offline',
          badgeType: 'status' as const,
        },
      ],
    },
  ];

  return (
    <aside
      style={{
        width: '256px',
        backgroundColor: 'var(--bg-primary)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          height: '64px',
          padding: '0 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div
          style={{
            width: '34px',
            height: '34px',
            borderRadius: '9px',
            background: 'var(--primary-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 12px var(--primary-glow)',
            flexShrink: 0,
          }}
        >
          <Zap size={18} color="#ffffff" fill="#ffffff" />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '17px',
              fontWeight: 800,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
            }}
          >
            Job Intel
          </span>
          <span
            style={{
              padding: '2px 6px',
              borderRadius: '9999px',
              backgroundColor: 'rgba(99, 102, 241, 0.2)',
              color: 'var(--primary)',
              fontSize: '10px',
              fontWeight: 800,
              letterSpacing: '0.04em',
            }}
          >
            AI
          </span>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav
        style={{
          padding: '16px 12px',
          flexGrow: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        {navSections.map((section) => (
          <div key={section.title} style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <div
              style={{
                fontSize: '11px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                color: 'var(--text-muted)',
                padding: '4px 12px 6px 12px',
              }}
            >
              {section.title}
            </div>

            {section.items.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path + item.label}
                  to={item.path}
                  end={item.path === '/'}
                  style={({ isActive }) => ({
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '13.5px',
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? '#ffffff' : 'var(--text-secondary)',
                    backgroundColor: isActive ? 'var(--primary)' : 'transparent',
                    boxShadow: isActive ? '0 2px 8px rgba(99, 102, 241, 0.35)' : 'none',
                    transition: 'all var(--transition-fast)',
                    textDecoration: 'none',
                  })}
                >
                  {({ isActive }) => (
                    <>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Icon size={18} color={isActive ? '#ffffff' : 'var(--text-muted)'} />
                        <span>{item.label}</span>
                      </div>

                      {item.badge && (
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '2px 7px',
                            borderRadius: '9999px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: isActive
                              ? 'rgba(255, 255, 255, 0.2)'
                              : item.badgeType === 'emerald'
                              ? 'rgba(16, 185, 129, 0.2)'
                              : item.badgeType === 'primary'
                              ? 'rgba(99, 102, 241, 0.15)'
                              : item.badgeType === 'status'
                              ? 'transparent'
                              : 'rgba(255, 255, 255, 0.08)',
                            color: isActive
                              ? '#ffffff'
                              : item.badgeType === 'emerald'
                              ? '#34d399'
                              : item.badgeType === 'primary'
                              ? '#a5b4fc'
                              : item.badgeType === 'status'
                              ? isGmailConnected
                                ? '#34d399'
                                : 'var(--text-muted)'
                              : 'var(--text-secondary)',
                          }}
                        >
                          {item.badgeType === 'status' && (
                            <span
                              style={{
                                width: '6px',
                                height: '6px',
                                borderRadius: '50%',
                                backgroundColor: isGmailConnected ? '#10b981' : 'var(--text-muted)',
                              }}
                            />
                          )}
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Real AI Pipeline Status Card */}
      <div style={{ padding: '12px' }}>
        <div
          style={{
            padding: '12px 14px',
            borderRadius: '12px',
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: 'var(--text-primary)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  backgroundColor: '#10b981',
                  boxShadow: '0 0 6px #10b981',
                }}
              />
              AI Parser Active
            </span>
            <Zap size={14} style={{ color: 'var(--primary)' }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <span>• {counts.emailsCount} emails in pipeline</span>
            <span>• {counts.jobsCount} unique jobs extracted</span>
          </div>

          <div
            style={{
              paddingTop: '6px',
              borderTop: '1px solid rgba(255, 255, 255, 0.06)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              color: 'var(--text-muted)',
              overflow: 'hidden',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: user?.email ? '#10b981' : 'var(--text-muted)',
                flexShrink: 0,
              }}
            />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email || 'Logged in user'}
            </span>
          </div>
        </div>
      </div>

      {/* User Footer Profile & Sign Out */}
      <div
        style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '12px',
              flexShrink: 0,
            }}
          >
            {user?.email ? user.email.charAt(0).toUpperCase() : 'U'}
          </div>
          <div style={{ overflow: 'hidden' }}>
            <div
              style={{
                fontSize: '12.5px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                whiteSpace: 'nowrap',
                textOverflow: 'ellipsis',
                overflow: 'hidden',
              }}
            >
              {user?.full_name || (user?.email ? user.email.split('@')[0] : 'User')}
            </div>
            <div
              style={{
                fontSize: '10.5px',
                color: 'var(--text-muted)',
                whiteSpace: 'nowrap',
                textOverflow: 'ellipsis',
                overflow: 'hidden',
              }}
            >
              Candidate Profile
            </div>
          </div>
        </div>

        <button
          onClick={logout}
          title="Sign Out"
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
};
