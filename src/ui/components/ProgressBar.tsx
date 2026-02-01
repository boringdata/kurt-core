/**
 * ProgressBar Component - Visual progress indicator
 *
 * WCAG 2.1 AA Compliant:
 * - ARIA roles for progress indication
 * - Proper color contrast
 * - Accessible labels
 */

import React from 'react';

interface ProgressBarProps {
  /** Progress value (0-100) */
  value: number;
  /** Maximum value (default 100) */
  max?: number;
  /** Label text */
  label?: string;
  /** Show percentage text */
  showLabel?: boolean;
  /** Color variant */
  variant?: 'primary' | 'success' | 'warning' | 'danger';
  /** Height of the bar */
  height?: string | number;
  /** Striped animation */
  striped?: boolean;
  /** Animated striped */
  animated?: boolean;
  /** Size variant */
  size?: 'small' | 'medium' | 'large';
  /** Optional class name */
  className?: string;
}

interface ProgressGroupProps {
  /** Array of progress items */
  items: Array<{
    value: number;
    label?: string;
    variant?: 'primary' | 'success' | 'warning' | 'danger';
  }>;
  /** Optional class name */
  className?: string;
}

const variantColorMap = {
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
};

const sizeHeightMap = {
  small: '4px',
  medium: '8px',
  large: '12px',
};

/**
 * ProgressBar Component
 * Visual indicator for progress/completion
 *
 * Usage:
 * ```tsx
 * <ProgressBar value={65} label="Upload Progress" />
 * <ProgressBar value={100} variant="success" />
 * ```
 */
export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  label,
  showLabel = true,
  variant = 'primary',
  height,
  striped = false,
  animated = false,
  size = 'medium',
  className = '',
}) => {
  const percentage = Math.min(Math.max(value, 0), max);
  const progressPercent = (percentage / max) * 100;
  const color = variantColorMap[variant];
  const heightValue = height || sizeHeightMap[size];
  const heightPx = typeof heightValue === 'number' ? `${heightValue}px` : heightValue;

  const stripedClass =
    striped || animated
      ? 'bg-gradient-to-r from-transparent via-white/20 to-transparent bg-[length:20px_20px]'
      : '';

  const animatedClass = animated ? 'animate-pulse' : '';

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label className="text-sm font-medium text-gray-700 mb-2 block">
          {label}
        </label>
      )}

      {/* Progress bar container */}
      <div
        className="w-full rounded-full overflow-hidden bg-gray-200"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || 'Progress'}
        style={{
          height: heightPx,
        }}
      >
        {/* Progress fill */}
        <div
          className={`h-full transition-all ${stripedClass} ${animatedClass}`}
          style={{
            width: `${progressPercent}%`,
            backgroundColor: color,
          }}
        />
      </div>

      {/* Percentage text */}
      {showLabel && (
        <div className="mt-2 text-sm text-gray-600">
          {percentage}% complete
        </div>
      )}
    </div>
  );
};

/**
 * SteppedProgress Component
 * Progress bar with discrete steps
 */
export const SteppedProgress: React.FC<{
  current: number;
  total: number;
  labels?: string[];
  className?: string;
}> = ({ current, total, labels = [], className = '' }) => {
  return (
    <div className={`w-full ${className}`}>
      {/* Step indicators */}
      <div className="flex items-center justify-between mb-4">
        {Array.from({ length: total }).map((_, index) => {
          const isComplete = index < current;
          const isCurrent = index === current - 1;

          return (
            <div
              key={index}
              className={`flex flex-col items-center flex-1 ${
                index > 0 ? '-ml-4' : ''
              }`}
            >
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full font-semibold text-sm z-10 ${
                  isComplete
                    ? 'bg-green-500 text-white'
                    : isCurrent
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-600'
                }`}
                role="img"
                aria-label={`Step ${index + 1}`}
              >
                {index + 1}
              </div>
              {labels[index] && (
                <span className="text-xs text-gray-600 mt-2 text-center">
                  {labels[index]}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Progress line */}
      <div className="flex">
        {Array.from({ length: total - 1 }).map((_, index) => {
          const isComplete = index < current - 1;

          return (
            <div
              key={index}
              className={`flex-1 h-1 mx-1 ${
                isComplete ? 'bg-green-500' : 'bg-gray-200'
              }`}
            />
          );
        })}
      </div>
    </div>
  );
};

/**
 * CircularProgress Component
 * Circular progress indicator
 */
export const CircularProgress: React.FC<{
  value: number;
  max?: number;
  size?: number;
  thickness?: number;
  color?: string;
  label?: string;
  className?: string;
}> = ({
  value,
  max = 100,
  size = 100,
  thickness = 4,
  color = '#3b82f6',
  label,
  className = '',
}) => {
  const percentage = (value / max) * 100;
  const circumference = 2 * Math.PI * ((size - thickness) / 2);
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={(size - thickness) / 2}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={thickness}
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={(size - thickness) / 2}
            fill="none"
            stroke={color}
            strokeWidth={thickness}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.3s' }}
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-semibold text-gray-700">
            {Math.round(percentage)}%
          </span>
        </div>
      </div>

      {label && <p className="mt-2 text-sm text-gray-600">{label}</p>}
    </div>
  );
};

/**
 * ProgressGroup Component
 * Multiple progress bars grouped together
 */
export const ProgressGroup: React.FC<ProgressGroupProps> = ({
  items,
  className = '',
}) => {
  const total = items.reduce((sum, item) => sum + item.value, 0);

  return (
    <div
      className={`flex w-full rounded-full overflow-hidden bg-gray-200 h-4 ${className}`}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round((items.reduce((sum, item) => sum + item.value, 0) / (items.length * 100)) * 100)}
    >
      {items.map((item, index) => (
        <div
          key={index}
          style={{
            width: `${item.value}%`,
            backgroundColor:
              variantColorMap[item.variant || 'primary'],
          }}
          title={item.label}
        />
      ))}
    </div>
  );
};

ProgressBar.displayName = 'ProgressBar';
SteppedProgress.displayName = 'SteppedProgress';
CircularProgress.displayName = 'CircularProgress';
ProgressGroup.displayName = 'ProgressGroup';

export {
  SteppedProgress,
  CircularProgress,
  ProgressGroup,
};

export default ProgressBar;
