/**
 * Icon and IconButton Components - Icon management and clickable icons
 *
 * WCAG 2.1 AA Compliant:
 * - Proper ARIA labels for icons
 * - Icon buttons with semantic HTML
 * - Loading states with proper indication
 * - Focus management
 */

import React, { ReactNode, CSSProperties } from 'react';
import Spinner from './Spinner';

interface IconProps {
  /** Icon element or SVG */
  icon: ReactNode;
  /** Size of icon */
  size?: 'small' | 'medium' | 'large' | 'xl';
  /** Color of icon */
  color?: string;
  /** Optional class name */
  className?: string;
  /** Optional style */
  style?: CSSProperties;
  /** Accessible label */
  label?: string;
  /** Rotate icon */
  rotate?: 0 | 90 | 180 | 270;
  /** Flip icon */
  flip?: 'horizontal' | 'vertical' | 'both' | 'none';
}

interface IconButtonProps {
  /** Icon element */
  icon: ReactNode;
  /** Alternative to icon - use aria-label */
  'aria-label'?: string;
  /** Size of button */
  size?: 'small' | 'medium' | 'large';
  /** Variant style */
  variant?: 'default' | 'primary' | 'danger' | 'ghost';
  /** Click handler */
  onClick?: () => void;
  /** Whether button is disabled */
  disabled?: boolean;
  /** Loading state */
  isLoading?: boolean;
  /** Tooltip text */
  tooltip?: string;
  /** Optional class name */
  className?: string;
  /** Icon color */
  color?: string;
}

const sizeMap = {
  small: {
    icon: 16,
    padding: '6px',
    text: 'text-xs',
  },
  medium: {
    icon: 20,
    padding: '8px',
    text: 'text-sm',
  },
  large: {
    icon: 24,
    padding: '10px',
    text: 'text-base',
  },
  xl: {
    icon: 32,
    padding: '12px',
    text: 'text-lg',
  },
};

const buttonSizeMap = {
  small: {
    padding: '4px',
    size: 16,
  },
  medium: {
    padding: '8px',
    size: 20,
  },
  large: {
    padding: '12px',
    size: 24,
  },
};

const variantMap = {
  default: 'border border-gray-300 bg-white hover:bg-gray-50',
  primary: 'border border-blue-500 bg-blue-500 hover:bg-blue-600 text-white',
  danger: 'border border-red-500 bg-red-500 hover:bg-red-600 text-white',
  ghost: 'text-gray-600 hover:bg-gray-100',
};

/**
 * Icon Component
 * Wrapper for icon SVGs with sizing and styling
 *
 * Usage:
 * ```tsx
 * <Icon icon={<StarIcon />} size="medium" color="#f59e0b" />
 * ```
 */
export const Icon: React.FC<IconProps> = ({
  icon,
  size = 'medium',
  color,
  className = '',
  style,
  label,
  rotate = 0,
  flip = 'none',
}) => {
  const sizeConfig = sizeMap[size];
  const dimension = sizeConfig.icon;

  let transforms = [];
  if (rotate !== 0) {
    transforms.push(`rotate(${rotate}deg)`);
  }
  if (flip !== 'none') {
    if (flip === 'horizontal' || flip === 'both') {
      transforms.push('scaleX(-1)');
    }
    if (flip === 'vertical' || flip === 'both') {
      transforms.push('scaleY(-1)');
    }
  }

  return (
    <span
      className={`inline-flex items-center justify-center flex-shrink-0 ${className}`}
      style={{
        width: dimension,
        height: dimension,
        color,
        transform: transforms.length > 0 ? transforms.join(' ') : undefined,
        ...style,
      }}
      role={label ? 'img' : undefined}
      aria-label={label}
    >
      {icon}
    </span>
  );
};

/**
 * IconButton Component
 * Clickable icon with button semantics
 *
 * Usage:
 * ```tsx
 * <IconButton icon={<TrashIcon />} onClick={handleDelete} />
 * <IconButton icon={<PlusIcon />} variant="primary" />
 * ```
 */
export const IconButton: React.FC<IconButtonProps> = ({
  icon,
  'aria-label': ariaLabel,
  size = 'medium',
  variant = 'default',
  onClick,
  disabled = false,
  isLoading = false,
  tooltip,
  className = '',
  color,
}) => {
  const sizeConfig = buttonSizeMap[size];
  const variantClass = variantMap[variant];

  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`relative inline-flex items-center justify-center rounded-lg transition-colors cursor-pointer ${variantClass} ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${className}`}
      style={{
        padding: sizeConfig.padding,
      }}
      aria-label={ariaLabel}
      title={tooltip}
    >
      {isLoading ? (
        <Spinner size="small" />
      ) : (
        <Icon
          icon={icon}
          size={size === 'small' ? 'small' : size === 'large' ? 'large' : 'medium'}
          color={color}
        />
      )}
    </button>
  );
};

/**
 * IconButtonGroup - Group of icon buttons
 */
export const IconButtonGroup: React.FC<{
  buttons: Array<{
    icon: ReactNode;
    onClick?: () => void;
    label?: string;
    disabled?: boolean;
  }>;
  size?: 'small' | 'medium' | 'large';
  className?: string;
}> = ({ buttons, size = 'medium', className = '' }) => {
  return (
    <div className={`flex gap-1 ${className}`} role="group">
      {buttons.map((btn, index) => (
        <IconButton
          key={index}
          icon={btn.icon}
          aria-label={btn.label}
          size={size}
          onClick={btn.onClick}
          disabled={btn.disabled}
        />
      ))}
    </div>
  );
};

/**
 * IconWithText - Icon next to text
 */
export const IconWithText: React.FC<{
  icon: ReactNode;
  text: string;
  iconPosition?: 'left' | 'right';
  gap?: string;
  className?: string;
}> = ({
  icon,
  text,
  iconPosition = 'left',
  gap = '8px',
  className = '',
}) => {
  const children = [
    <Icon key="icon" icon={icon} />,
    <span key="text">{text}</span>,
  ];

  if (iconPosition === 'right') {
    children.reverse();
  }

  return (
    <span className={`inline-flex items-center ${className}`} style={{ gap }}>
      {children}
    </span>
  );
};

/**
 * Badge - Badge with icon
 */
export const IconBadge: React.FC<{
  icon: ReactNode;
  count?: number;
  max?: number;
  className?: string;
}> = ({ icon, count, max = 99, className = '' }) => {
  return (
    <div className={`relative inline-flex ${className}`}>
      <Icon icon={icon} />
      {count !== undefined && count > 0 && (
        <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
          {count > max ? `${max}+` : count}
        </span>
      )}
    </div>
  );
};

Icon.displayName = 'Icon';
IconButton.displayName = 'IconButton';
IconButtonGroup.displayName = 'IconButtonGroup';
IconWithText.displayName = 'IconWithText';
IconBadge.displayName = 'IconBadge';

export {
  IconButton,
  IconButtonGroup,
  IconWithText,
  IconBadge,
};

export default Icon;
