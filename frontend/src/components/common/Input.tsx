import React, { forwardRef } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, leftIcon, rightIcon, className = '', id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="input-group">
        {label && (
          <label htmlFor={inputId} className="input-label">
            {label}
          </label>
        )}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          {leftIcon && (
            <div
              style={{
                position: 'absolute',
                left: '12px',
                display: 'flex',
                alignItems: 'center',
                color: 'var(--text-muted)',
                pointerEvents: 'none',
              }}
            >
              {leftIcon}
            </div>
          )}
          <input
            id={inputId}
            ref={ref}
            className={`input-field ${className}`}
            style={{
              paddingLeft: leftIcon ? '38px' : '14px',
              paddingRight: rightIcon ? '38px' : '14px',
              borderColor: error ? 'var(--danger)' : undefined,
            }}
            {...props}
          />
          {rightIcon && (
            <div
              style={{
                position: 'absolute',
                right: '12px',
                display: 'flex',
                alignItems: 'center',
                color: 'var(--text-muted)',
              }}
            >
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <span style={{ fontSize: '12px', color: 'var(--danger)', marginTop: '2px' }}>
            {error}
          </span>
        )}
        {!error && helperText && (
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {helperText}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
