import React from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

interface AppLayoutProps {
  children: React.ReactNode;
  title?: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children, title, onRefresh, isRefreshing }) => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-app)' }}>
      {/* Fixed Left Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Header title={title} onRefresh={onRefresh} isRefreshing={isRefreshing} />
        <main
          style={{
            flexGrow: 1,
            padding: '32px 36px',
            maxWidth: '1440px',
            width: '100%',
            margin: '0 auto',
          }}
          className="animate-fade-in"
        >
          {children}
        </main>
      </div>
    </div>
  );
};
