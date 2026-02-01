/**
 * Alert Component
 * Dismissible banner with icon support, action buttons, and color variants
 */

import React, { useState } from 'react';
import { AlertVariant, AlertAction } from '../../types/alert';
import './Alert.css';

interface AlertProps {
  title?: string;
  description?: string;
  variant?: AlertVariant;
  icon?: React.ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
  actions?: AlertAction[];
  children?: React.ReactNode;
  className?: string;
}

const getVariantIcon = (variant: AlertVariant) => {
  switch (variant) {
    case 'success':
      return '✓';
    case 'error':
      return '✕';
    case 'warning':
      return '⚠';
    case 'info':
      return 'ℹ';
    default:
      return '';
  }
};

export const Alert: React.FC<AlertProps> = ({
  title,
  description,
  variant = 'info',
  icon: customIcon,
  dismissible = false,
  onDismiss,
  actions = [],
  children,
  className,
}) => {
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) {
    return null;
  }

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss?.();
  };

  const icon = customIcon || getVariantIcon(variant);

  return (
    <div
      className={`alert alert--${variant} ${className || ''}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="alert__container">
        <div className="alert__header">
          {icon && <span className="alert__icon" aria-hidden="true">{icon}</span>}
          {title && <h3 className="alert__title">{title}</h3>}
        </div>

        <div className="alert__content">
          {description && <p className="alert__description">{description}</p>}
          {children}
        </div>
      </div>

      <div className="alert__actions">
        {actions.map((action, index) => (
          <button
            key={index}
            className="alert__action-button"
            onClick={action.onClick}
          >
            {action.label}
          </button>
        ))}

        {dismissible && (
          <button
            className="alert__close-button"
            onClick={handleDismiss}
            aria-label="Dismiss alert"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
};

export default Alert;
