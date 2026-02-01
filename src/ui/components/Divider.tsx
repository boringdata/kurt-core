/**
 * Divider/Separator Component - Visual separator between content
 *
 * WCAG 2.1 AA Compliant:
 * - Proper semantic role
 * - Clear visual separation
 */

import React, { ReactNode } from 'react';

interface DividerProps {
  /** Direction of divider */
  direction?: 'horizontal' | 'vertical';
  /** Line style */
  variant?: 'solid' | 'dashed' | 'dotted';
  /** Color of divider */
  color?: string;
  /** Thickness of line */
  thickness?: string | number;
  /** Margin/spacing */
  margin?: string | number;
  /** Full width (horizontal only) */
  fullWidth?: boolean;
  /** Optional label/text in center */
  label?: ReactNode;
  /** Optional class name */
  className?: string;
}

const variantStyleMap = {
  solid: 'solid',
  dashed: 'dashed',
  dotted: 'dotted',
};

/**
 * Divider Component
 * Visual separator between sections of content
 *
 * Usage:
 * ```tsx
 * <Divider />
 * <Divider direction="vertical" />
 * <Divider label="Or" />
 * ```
 */
export const Divider: React.FC<DividerProps> = ({
  direction = 'horizontal',
  variant = 'solid',
  color = '#e5e7eb',
  thickness = '1px',
  margin = '16px',
  fullWidth = true,
  label,
  className = '',
}) => {
  const thicknessValue =
    typeof thickness === 'number' ? `${thickness}px` : thickness;
  const marginValue = typeof margin === 'number' ? `${margin}px` : margin;
  const borderStyle = variantStyleMap[variant];

  if (direction === 'horizontal') {
    // Horizontal divider
    if (label) {
      // Divider with label in center
      return (
        <div
          className={`flex items-center gap-4 my-4 ${className}`}
          role="separator"
          aria-orientation="horizontal"
        >
          <div
            className="flex-1"
            style={{
              borderTop: `${thicknessValue} ${borderStyle} ${color}`,
            }}
          />
          <span className="px-2 text-sm text-gray-600">{label}</span>
          <div
            className="flex-1"
            style={{
              borderTop: `${thicknessValue} ${borderStyle} ${color}`,
            }}
          />
        </div>
      );
    }

    // Simple horizontal divider
    return (
      <div
        className={`w-full ${className}`}
        style={{
          borderTop: `${thicknessValue} ${borderStyle} ${color}`,
          margin: `${marginValue} 0`,
        }}
        role="separator"
        aria-orientation="horizontal"
      />
    );
  } else {
    // Vertical divider
    return (
      <div
        className={`h-full ${className}`}
        style={{
          borderLeft: `${thicknessValue} ${borderStyle} ${color}`,
          margin: `0 ${marginValue}`,
        }}
        role="separator"
        aria-orientation="vertical"
      />
    );
  }
};

/**
 * SectionDivider Component
 * Larger divider for major section breaks
 */
export const SectionDivider: React.FC<{
  title?: ReactNode;
  className?: string;
}> = ({ title, className = '' }) => {
  return (
    <div className={`my-8 ${className}`}>
      {title ? (
        <div className="flex items-center gap-4">
          <div className="flex-1 border-t border-gray-300" />
          <h2 className="text-lg font-semibold text-gray-700 px-4">{title}</h2>
          <div className="flex-1 border-t border-gray-300" />
        </div>
      ) : (
        <div className="border-t-2 border-gray-300" />
      )}
    </div>
  );
};

/**
 * InlineText Divider - Divider for inline text
 */
export const TextDivider: React.FC<{
  text: string;
  className?: string;
}> = ({ text, className = '' }) => {
  return (
    <div className={`flex items-center gap-3 my-4 ${className}`}>
      <div className="flex-1 border-t border-gray-300" />
      <span className="text-xs font-medium text-gray-500 uppercase px-2">
        {text}
      </span>
      <div className="flex-1 border-t border-gray-300" />
    </div>
  );
};

/**
 * BorderBox Component
 * Box with decorative borders/dividers
 */
export const BorderBox: React.FC<{
  children: ReactNode;
  variant?: 'all' | 'top' | 'bottom' | 'left' | 'right';
  color?: string;
  thickness?: string | number;
  className?: string;
}> = ({
  children,
  variant = 'all',
  color = '#e5e7eb',
  thickness = '1px',
  className = '',
}) => {
  const thicknessValue =
    typeof thickness === 'number' ? `${thickness}px` : thickness;

  let borderStyle = '';
  switch (variant) {
    case 'all':
      borderStyle = `${thicknessValue} solid ${color}`;
      break;
    case 'top':
      borderStyle = `${thicknessValue} solid ${color}`;
      break;
    case 'bottom':
      borderStyle = `${thicknessValue} solid ${color}`;
      break;
    case 'left':
      borderStyle = `${thicknessValue} solid ${color}`;
      break;
    case 'right':
      borderStyle = `${thicknessValue} solid ${color}`;
      break;
  }

  const style =
    variant === 'all'
      ? { border: borderStyle }
      : variant === 'top'
        ? { borderTop: borderStyle }
        : variant === 'bottom'
          ? { borderBottom: borderStyle }
          : variant === 'left'
            ? { borderLeft: borderStyle }
            : { borderRight: borderStyle };

  return (
    <div className={`rounded-lg ${className}`} style={style}>
      {children}
    </div>
  );
};

Divider.displayName = 'Divider';
SectionDivider.displayName = 'SectionDivider';
TextDivider.displayName = 'TextDivider';
BorderBox.displayName = 'BorderBox';

export { SectionDivider, TextDivider, BorderBox };

export default Divider;
