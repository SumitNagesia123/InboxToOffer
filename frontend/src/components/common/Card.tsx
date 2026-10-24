import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  glass?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  hoverable = false,
  glass = false,
  className = '',
  ...props
}) => {
  const classes = [
    'card',
    glass ? 'glass-panel' : '',
    hoverable ? 'card-hoverable' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
};
