/**
 * Toast/Notification Types
 * Supports auto-dismiss, stacking, service/hook API with variants
 */

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface Toast {
  id: string;
  message: string;
  variant?: ToastVariant;
  duration?: number; // milliseconds, 0 = no auto-dismiss
  action?: ToastAction;
  onClose?: () => void;
}

export interface ToastOptions {
  message: string;
  variant?: ToastVariant;
  duration?: number;
  action?: ToastAction;
}
