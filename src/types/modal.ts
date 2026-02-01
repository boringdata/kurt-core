/**
 * Modal/Dialog Types
 * Supports focus trap, backdrop, animations, keyboard support (Escape)
 */

export type ModalSize = 'small' | 'medium' | 'large';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: ModalSize;
  showCloseButton?: boolean;
  closeOnBackdropClick?: boolean;
  closeOnEscapeKey?: boolean;
  footer?: React.ReactNode;
  className?: string;
}

export interface FocusTrapConfig {
  active: boolean;
  paused?: boolean;
}
