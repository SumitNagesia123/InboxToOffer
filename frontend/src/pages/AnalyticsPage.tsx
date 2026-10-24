import React, { useEffect, useState } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Spinner } from '../components/common/Spinner';
import { api } from '../api/client';
import { CheckCircle, XCircle } from 'lucide-react';

interface AnalyticsData {
  work_mode_distribution: Array<{ work_mode: string; count: number; percentage: number }>;
  platform_distribution: Array<{ platform_source: string; count: number; percentage: number }>;
  top_in_demand_skills: Array<{ name: string; demand_count: number; candidate_has_skill: boolean }>;
  match_score_distribution: Array<{ range_label: string; count: number; percentage: number }>;
}

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await api.get<AnalyticsData>('/analytics');
        setData(res);
      } catch (err) {
        console.error('Failed to load analytics:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <AppLayout title="Market Analytics & Skill Gaps">
      {isLoading ? (
        <Spinner size={36} text="Compiling Market Intelligence..." />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          {/* Top In-Demand Skills vs Candidate Possession */}
          <Card>
            <h3 style={{ fontSize: '17px', marginBottom: '16px' }}>Top Market Skills & Candidate Coverage</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {data?.top_in_demand_skills.map((s) => (
                <div
                  key={s.name}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {s.candidate_has_skill ? (
                      <CheckCircle size={16} color="var(--success)" />
                    ) : (
                      <XCircle size={16} color="var(--danger)" />
                    )}
                    <span style={{ fontWeight: 600, fontSize: '14px' }}>{s.name}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Badge variant={s.candidate_has_skill ? 'success' : 'neutral'}>
                      {s.candidate_has_skill ? 'On Resume' : 'Skill Gap'}
                    </Badge>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {s.demand_count} jobs
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Compatibility Match Histogram */}
          <Card>
            <h3 style={{ fontSize: '17px', marginBottom: '16px' }}>Compatibility Score Distribution</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {data?.match_score_distribution.map((b) => (
                <div key={b.range_label}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                    <span>{b.range_label}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {b.count} jobs ({b.percentage}%)
                    </span>
                  </div>
                  <div
                    style={{
                      height: '8px',
                      backgroundColor: 'var(--bg-primary)',
                      borderRadius: 'var(--radius-full)',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${b.percentage}%`,
                        backgroundColor: 'var(--primary)',
                        borderRadius: 'var(--radius-full)',
                        transition: 'width 0.5s ease-out',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Work Mode Breakdown */}
          <Card>
            <h3 style={{ fontSize: '17px', marginBottom: '16px' }}>Work Modality Breakdown</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {data?.work_mode_distribution.map((wm) => (
                <div key={wm.work_mode} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                  <span>{wm.work_mode}</span>
                  <span style={{ fontWeight: 600 }}>
                    {wm.count} jobs ({wm.percentage}%)
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Platform Discovery Breakdown */}
          <Card>
            <h3 style={{ fontSize: '17px', marginBottom: '16px' }}>Platform Distribution</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {data?.platform_distribution.map((src) => (
                <div key={src.platform_source} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                  <span>{src.platform_source}</span>
                  <span style={{ fontWeight: 600 }}>
                    {src.count} jobs ({src.percentage}%)
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </AppLayout>
  );
};
