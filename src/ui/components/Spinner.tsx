/**
 * Spinner Component - Loading indicator
 *
 * WCAG 2.1 AA Compliant:
 * - Proper ARIA labels
 * - aria-busy for screen readers
 * - Accessible loading states
 */

import React from 'react';

interface SpinnerProps {
  /** Size of the spinner */
  size?: 'small' | 'medium' | 'large';
  /** Color of the spinner */
  color?: string;
  /** Type of spinner animation */
  variant?: 'ring' | 'dots' | 'bar';
  /** Label/message for screen readers */
  label?: string;
  /** Optional class name */
  className?: string;
}

interface LoadingOverlayProps {
  /** Whether to show the overlay */
  isVisible: boolean;
  /** Spinner size */
  size?: 'small' | 'medium' | 'large';
  /** Loading message */
  message?: string;
  /** Optional class name */
  className?: string;
}

const sizeMap = {
  small: 24,
  medium: 40,
  large: 60,
};

/**
 * Spinner Component - Animated loading indicator
 *
 * Usage:
 * ```tsx
 * <Spinner size="medium" />
 * <Spinner variant="dots" color="#3b82f6" />
 * ```
 */
export const Spinner: React.FC<SpinnerProps> = ({
  size = 'medium',
  color = '#3b82f6',
  variant = 'ring',
  label = 'Loading',
  className = '',
}) => {
  const dimension = sizeMap[size];

  return (
    <div
      className={`inline-flex items-center justify-center ${className}`}
      role="status"
      aria-busy="true"
      aria-label={label}
    >
      {variant === 'ring' && (
        <svg
          width={dimension}
          height={dimension}
          viewBox={`0 0 ${dimension} ${dimension}`}
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="animate-spin"
        >
          <circle
            cx={dimension / 2}
            cy={dimension / 2}
            r={dimension / 2 - 4}
            stroke="#e5e7eb"
            strokeWidth="4"
          />
          <circle
            cx={dimension / 2}
            cy={dimension / 2}
            r={dimension / 2 - 4}
            stroke={color}
            strokeWidth="4"
            strokeDasharray={`${(Math.PI * (dimension - 8)) / 2} ${Math.PI * (dimension - 8)}`}
            strokeLinecap="round"
            className="animate-spin"
          />
        </svg>
      )}

      {variant === 'dots' && (
        <div className="flex gap-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                width: dimension / 3,
                height: dimension / 3,
                backgroundColor: color,
                borderRadius: '50%',
                animation: `bounce 1.4s infinite ${i * 0.2}s`,
              }}
            />
          ))}
        </div>
      )}

      {variant === 'bar' && (
        <div
          style={{
            width: dimension,
            height: dimension / 3,
            backgroundColor: '#e5e7eb',
            borderRadius: '4px',
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              height: '100%',
              width: '40%',
              backgroundColor: color,
              borderRadius: '4px',
              animation: 'slideBar 1.5s infinite',
            }}
          />
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes bounce {
          0%, 80%, 100% { opacity: 0.3; }
          40% { opacity: 1; }
        }
        @keyframes slideBar {
          0% { left: -100%; }
          50% { left: 100%; }
          100% { left: 100%; }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
};

/**
 * LoadingOverlay Component - Full-page loading overlay
 *
 * Usage:
 * ```tsx
 * <LoadingOverlay isVisible={isLoading} message="Processing..." />
 * ```
 */
export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  isVisible,
  size = 'large',
  message,
  className = '',
}) => {
  if (!isVisible) {
    return null;
  }

  return (
    <div
      className={`fixed inset-0 flex items-center justify-center bg-black/30 z-50 ${className}`}
      role="status"
      aria-busy="true"
      aria-label={message || 'Loading'}
    >
      <div className="bg-white rounded-lg p-8 shadow-xl flex flex-col items-center gap-4">
        <Spinner size={size} />
        {message && <p className="text-sm text-gray-600">{message}</p>}
      </div>
    </div>
  );
};

/**
 * InlineSpinner - Spinner for inline use with text
 */
export const InlineSpinner: React.FC<{
  label?: string;
  className?: string;
}> = ({ label = 'Loading', className = '' }) => {
  return (
    <span className={`flex items-center gap-2 ${className}`}>
      <Spinner size="small" />
      <span className="text-sm text-gray-600">{label}</span>
    </span>
  );
};

Spinner.displayName = 'Spinner';
LoadingOverlay.displayName = 'LoadingOverlay';
InlineSpinner.displayName = 'InlineSpinner';

export { LoadingOverlay, InlineSpinner };

export default Spinner;
