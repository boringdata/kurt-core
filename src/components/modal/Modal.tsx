/**
 * Modal/Dialog Component
 * Features: focus trap, backdrop, animations, keyboard support (Escape)
 */

import React, { useEffect, useRef, useState } from 'react';
import { useFocusTrap, usePreviousFocus } from '../../hooks/useFocusTrap';
import { ModalProps, ModalSize } from '../../types/modal';
import './Modal.css';

const getSizeClass = (size: ModalSize): string => {
  switch (size) {
    case 'small':
      return 'modal--small';
    case 'large':
      return 'modal--large';
    case 'medium':
    default:
      return 'modal--medium';
  }
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'medium',
  showCloseButton = true,
  closeOnBackdropClick = true,
  closeOnEscapeKey = true,
  footer,
  className,
}) => {
  const [isExiting, setIsExiting] = useState(false);
  const modalRef = useFocusTrap({ active: isOpen && !isExiting });
  const { saveFocus, restoreFocus } = usePreviousFocus();

  // Handle opening/closing with animations
  useEffect(() => {
    if (isOpen) {
      saveFocus();
      // Add no-scroll class to body
      document.body.style.overflow = 'hidden';
      setIsExiting(false);
    } else if (!isExiting) {
      restoreFocus();
      // Remove no-scroll class from body
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen, saveFocus, restoreFocus, isExiting]);

  // Handle Escape key
  useEffect(() => {
    if (!isOpen || !closeOnEscapeKey) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, closeOnEscapeKey]);

  const handleClose = () => {
    setIsExiting(true);
    // Wait for animation to complete
    setTimeout(() => {
      onClose();
      setIsExiting(false);
    }, 200);
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (closeOnBackdropClick && e.target === e.currentTarget) {
      handleClose();
    }
  };

  if (!isOpen && !isExiting) {
    return null;
  }

  return (
    <div
      className={`modal-backdrop ${isExiting ? 'modal-backdrop--exiting' : ''}`}
      onClick={handleBackdropClick}
      role="presentation"
      aria-hidden={!isOpen}
    >
      <div
        ref={modalRef}
        className={`modal ${getSizeClass(size)} ${isExiting ? 'modal--exiting' : ''} ${className || ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
      >
        {/* Header */}
        <div className="modal__header">
          {title && (
            <h2 id="modal-title" className="modal__title">
              {title}
            </h2>
          )}
          {showCloseButton && (
            <button
              className="modal__close-button"
              onClick={handleClose}
              aria-label="Close modal"
            >
              ×
            </button>
          )}
        </div>

        {/* Body */}
        <div className="modal__body">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="modal__footer">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default Modal;
