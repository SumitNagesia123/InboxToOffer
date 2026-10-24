import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  score?: number; // If provided, dynamically styles as a match badge
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  score,
  className = '',
  ...props
}) => {
  let badgeVariant = variant;

  if (typeof score === 'number') {
    if (score >= 80) badgeVariant = 'success';
    else if (score >= 65) badgeVariant = 'primary';
    else if (score >= 50) badgeVariant = 'warning';
    else badgeVariant = 'neutral';
  }

  return (
    <span className={`badge badge-${badgeVariant} ${className}`} {...props}>
      {children}
    </span>
  );
};
