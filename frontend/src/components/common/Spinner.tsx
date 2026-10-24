import React from 'react';
import { Loader2 } from 'lucide-react';

export interface SpinnerProps {
  size?: number;
  className?: string;
  color?: string;
  text?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 24,
  className = '',
  color = 'var(--primary)',
  text,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '10px',
        padding: '20px',
      }}
    >
      <Loader2
        size={size}
        style={{ color, animation: 'spin 1s linear infinite' }}
        className={className}
      />
      {text && (
        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          {text}
        </span>
      )}
    </div>
  );
};
