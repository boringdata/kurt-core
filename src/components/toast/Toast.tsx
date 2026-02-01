/**
 * Toast Component
 * Individual toast notification with optional action button and auto-dismiss
 */

import React, { useEffect, useState } from 'react';
import { Toast as ToastType, ToastVariant } from '../../types/toast';
import './Toast.css';

interface ToastProps extends ToastType {
  onRemove?: () => void;
}

const getVariantIcon = (variant: ToastVariant) => {
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

export const Toast: React.FC<ToastProps> = ({
  id,
  message,
  variant = 'info',
  duration = 5000,
  action,
  onRemove,
}) => {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (duration === 0) return; // No auto-dismiss

    const timer = setTimeout(() => {
      setIsExiting(true);
      // Allow animation to complete before removing
      setTimeout(onRemove, 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onRemove]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(onRemove, 300);
  };

  const handleActionClick = () => {
    action?.onClick();
    handleClose();
  };

  return (
    <div
      className={`toast toast--${variant} ${isExiting ? 'toast--exiting' : ''}`}
      role="status"
      aria-live="polite"
      aria-label={`${variant} notification: ${message}`}
    >
      <div className="toast__content">
        <span className="toast__icon" aria-hidden="true">
          {getVariantIcon(variant)}
        </span>
        <span className="toast__message">{message}</span>
      </div>

      <div className="toast__actions">
        {action && (
          <button
            className="toast__action-button"
            onClick={handleActionClick}
            aria-label={action.label}
          >
            {action.label}
          </button>
        )}
        <button
          className="toast__close-button"
          onClick={handleClose}
          aria-label="Close notification"
        >
          ×
        </button>
      </div>
    </div>
  );
};

export default Toast;
