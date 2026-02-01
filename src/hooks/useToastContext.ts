/**
 * Toast Context and Service
 * Provides toast service API for displaying notifications with auto-dismiss
 */

import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { Toast, ToastOptions } from '../types/toast';

interface ToastContextType {
  toasts: Toast[];
  addToast: (options: ToastOptions) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

export const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToastContext() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToastContext must be used within ToastProvider');
  }
  return context;
}

/**
 * Custom hook for using toast notifications
 * Generates unique IDs and manages toast lifecycle
 */
export function useToast() {
  const { addToast, removeToast, clearAll } = useToastContext();
  const toastIdRef = useRef(0);

  const generateId = useCallback(() => {
    toastIdRef.current += 1;
    return `toast-${toastIdRef.current}-${Date.now()}`;
  }, []);

  return {
    success: (message: string, duration?: number) =>
      addToast({ message, variant: 'success', duration }),
    error: (message: string, duration?: number) =>
      addToast({ message, variant: 'error', duration }),
    warning: (message: string, duration?: number) =>
      addToast({ message, variant: 'warning', duration }),
    info: (message: string, duration?: number) =>
      addToast({ message, variant: 'info', duration }),
    toast: addToast,
    remove: removeToast,
    clearAll,
  };
}
