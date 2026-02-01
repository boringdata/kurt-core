/**
 * Toast Container Component
 * Manages stacking and display of multiple toasts
 */

import React, { useState, useCallback } from 'react';
import Toast from './Toast';
import { ToastContext } from '../../hooks/useToastContext';
import { Toast as ToastType, ToastOptions } from '../../types/toast';
import './ToastContainer.css';

interface ToastContainerProps {
  maxToasts?: number;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  children?: React.ReactNode;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({
  maxToasts = 5,
  position = 'bottom-right',
  children,
}) => {
  const [toasts, setToasts] = useState<ToastType[]>([]);

  const addToast = useCallback(
    (options: ToastOptions): string => {
      const id = `toast-${Date.now()}-${Math.random()}`;

      const newToast: ToastType = {
        id,
        message: options.message,
        variant: options.variant || 'info',
        duration: options.duration ?? 5000,
        action: options.action,
      };

      setToasts((prev) => {
        const updated = [newToast, ...prev];
        // Keep only maxToasts, remove oldest ones
        return updated.slice(0, maxToasts);
      });

      return id;
    },
    [maxToasts]
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, clearAll }}>
      {children}
      <div
        className={`toast-container toast-container--${position}`}
        role="region"
        aria-label="Notifications"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            {...toast}
            onRemove={() => removeToast(toast.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export default ToastContainer;
