/**
 * Alert/Banner Types
 * Supports dismissible alerts, icons, action buttons, color variants
 */

export type AlertVariant = 'success' | 'error' | 'warning' | 'info';

export interface AlertAction {
  label: string;
  onClick: () => void;
}

export interface AlertProps {
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
