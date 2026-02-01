/**
 * Skeleton Component - Placeholder for loading states
 *
 * WCAG 2.1 AA Compliant:
 * - Proper semantic structure
 * - aria-busy and aria-label for screen readers
 * - Distinct from actual content
 */

import React from 'react';

interface SkeletonProps {
  /** Width of the skeleton */
  width?: string | number;
  /** Height of the skeleton */
  height?: string | number;
  /** Border radius */
  radius?: 'none' | 'small' | 'medium' | 'large' | 'full';
  /** Variant style */
  variant?: 'text' | 'circle' | 'rect';
  /** Animation type */
  animation?: 'pulse' | 'wave' | 'none';
  /** Optional class name */
  className?: string;
}

interface SkeletonGroupProps {
  /** Number of skeleton items */
  count?: number;
  /** Spacing between items */
  spacing?: string;
  /** Stagger animation delay */
  staggerDelay?: number;
  /** Children or skeleton configuration */
  children?: React.ReactNode;
  /** Optional class name */
  className?: string;
}

const radiusMap = {
  none: '0',
  small: '4px',
  medium: '8px',
  large: '12px',
  full: '9999px',
};

/**
 * Skeleton Component - Individual skeleton placeholder
 *
 * Usage:
 * ```tsx
 * <Skeleton height={20} width="100%" />
 * <Skeleton variant="circle" width={40} height={40} />
 * ```
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = 16,
  radius = 'small',
  variant = 'rect',
  animation = 'pulse',
  className = '',
}) => {
  const widthValue = typeof width === 'number' ? `${width}px` : width;
  const heightValue = typeof height === 'number' ? `${height}px` : height;
  const borderRadius = radiusMap[radius];

  let animationClass = '';
  if (animation === 'pulse') {
    animationClass = 'animate-pulse';
  } else if (animation === 'wave') {
    animationClass = 'relative overflow-hidden bg-gray-200 before:absolute before:inset-0 before:bg-gradient-to-r before:from-transparent before:via-white before:to-transparent before:animate-shimmer';
  }

  return (
    <div
      className={`bg-gray-200 ${animationClass} ${className}`}
      style={{
        width: widthValue,
        height: heightValue,
        borderRadius: variant === 'circle' ? '50%' : borderRadius,
      }}
      role="status"
      aria-busy="true"
      aria-label="Loading content"
    />
  );
};

/**
 * SkeletonGroup Component - Multiple skeleton placeholders
 *
 * Usage:
 * ```tsx
 * <SkeletonGroup count={3} />
 * <SkeletonGroup count={5} staggerDelay={100}>
 *   <Skeleton height={20} />
 *   <Skeleton height={16} />
 * </SkeletonGroup>
 * ```
 */
export const SkeletonGroup: React.FC<SkeletonGroupProps> = ({
  count = 3,
  spacing = '12px',
  staggerDelay = 0,
  children,
  className = '',
}) => {
  return (
    <div
      className={`space-y-3 ${className}`}
      style={{
        gap: spacing,
      }}
      role="status"
      aria-busy="true"
      aria-label="Loading content"
    >
      {children ? (
        children
      ) : (
        <>
          {Array.from({ length: count }).map((_, index) => (
            <div
              key={index}
              style={{
                animation:
                  staggerDelay > 0
                    ? `pulse ${1.5 + (staggerDelay * index) / 1000}s cubic-bezier(0.4, 0, 0.6, 1) infinite`
                    : undefined,
              }}
            >
              <Skeleton />
            </div>
          ))}
        </>
      )}
    </div>
  );
};

/**
 * SkeletonCard - Common card skeleton variant
 */
export const SkeletonCard: React.FC<{ count?: number; className?: string }> = ({
  count = 1,
  className = '',
}) => {
  return (
    <div className={`space-y-4 ${className}`}>
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="rounded border border-gray-200 p-4 space-y-3">
          <Skeleton height={24} />
          <Skeleton height={16} width="80%" />
          <Skeleton height={16} width="60%" />
        </div>
      ))}
    </div>
  );
};

/**
 * SkeletonText - Multiple lines of text skeleton
 */
export const SkeletonText: React.FC<{
  lines?: number;
  lastLineWidth?: string;
  className?: string;
}> = ({ lines = 3, lastLineWidth = '80%', className = '' }) => {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          height={16}
          width={index === lines - 1 ? lastLineWidth : '100%'}
        />
      ))}
    </div>
  );
};

/**
 * SkeletonTable - Table skeleton variant
 */
export const SkeletonTable: React.FC<{
  rows?: number;
  columns?: number;
  className?: string;
}> = ({ rows = 5, columns = 4, className = '' }) => {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-2">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <div key={colIndex} className="flex-1">
              <Skeleton height={20} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

Skeleton.displayName = 'Skeleton';
SkeletonGroup.displayName = 'SkeletonGroup';
SkeletonCard.displayName = 'SkeletonCard';
SkeletonText.displayName = 'SkeletonText';
SkeletonTable.displayName = 'SkeletonTable';

export { SkeletonGroup, SkeletonCard, SkeletonText, SkeletonTable };

export default Skeleton;
