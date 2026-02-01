/**
 * FocusTrap Component - Traps focus within a container
 * Essential for modals, dialogs, and dropdowns
 *
 * WCAG 2.1 AA Compliant:
 * - Focus management for keyboard navigation
 * - Prevents focus escaping the container
 * - Supports restore focus on unmount
 */

import React, { useEffect, useRef, ReactNode } from 'react';

interface FocusTrapProps {
  /** The content to wrap with focus trap */
  children: ReactNode;
  /** Whether the focus trap is active */
  active?: boolean;
  /** Callback when trap should close (e.g., on Escape) */
  onEscapeKey?: () => void;
  /** Restore focus to the element that had focus before trap was mounted */
  restoreFocus?: boolean;
  /** Optional class name */
  className?: string;
}

/**
 * Get all focusable elements within a container
 */
function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const focusableSelector = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input[type="text"]:not([disabled])',
    'input[type="radio"]:not([disabled])',
    'input[type="checkbox"]:not([disabled])',
    'input[type="number"]:not([disabled])',
    'input[type="email"]:not([disabled])',
    'input[type="url"]:not([disabled])',
    'input[type="tel"]:not([disabled])',
    'input[type="password"]:not([disabled])',
    'input[type="search"]:not([disabled])',
    'input[type="date"]:not([disabled])',
    'input[type="time"]:not([disabled])',
    'input[type="datetime-local"]:not([disabled])',
    'input[type="month"]:not([disabled])',
    'input[type="week"]:not([disabled])',
    'input[type="color"]:not([disabled])',
    'input[type="range"]:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  const elements = Array.from(container.querySelectorAll(focusableSelector));

  return elements.filter((element) => {
    const style = window.getComputedStyle(element);
    return style.display !== 'none' && style.visibility !== 'hidden';
  }) as HTMLElement[];
}

/**
 * FocusTrap Component
 * Traps keyboard focus within the component, preventing users from tabbing outside.
 *
 * Usage:
 * ```tsx
 * <FocusTrap active={isOpen} onEscapeKey={handleClose}>
 *   <Modal>...</Modal>
 * </FocusTrap>
 * ```
 */
export const FocusTrap: React.FC<FocusTrapProps> = ({
  children,
  active = true,
  onEscapeKey,
  restoreFocus = true,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!active || !containerRef.current) {
      return;
    }

    // Store the element that had focus before the trap was activated
    if (restoreFocus) {
      previousFocusRef.current = document.activeElement as HTMLElement;
    }

    const container = containerRef.current;
    const focusableElements = getFocusableElements(container);

    if (focusableElements.length === 0) {
      // If no focusable elements, focus the container itself
      container.setAttribute('tabindex', '-1');
      container.focus();
    } else {
      // Focus the first element
      focusableElements[0].focus();
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      // Handle Escape key
      if (event.key === 'Escape') {
        if (onEscapeKey) {
          event.preventDefault();
          onEscapeKey();
        }
        return;
      }

      // Handle Tab key for focus cycling
      if (event.key !== 'Tab') {
        return;
      }

      const activeElement = document.activeElement as HTMLElement;

      if (!container.contains(activeElement)) {
        return;
      }

      const focusableEls = getFocusableElements(container);
      if (focusableEls.length === 0) {
        event.preventDefault();
        return;
      }

      const firstElement = focusableEls[0];
      const lastElement = focusableEls[focusableEls.length - 1];

      // Tab key - move forward
      if (!event.shiftKey) {
        if (activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      } else {
        // Shift+Tab - move backward
        if (activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);

      // Restore focus to the element that had focus before
      if (restoreFocus && previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [active, onEscapeKey, restoreFocus]);

  return (
    <div ref={containerRef} className={className}>
      {children}
    </div>
  );
};

FocusTrap.displayName = 'FocusTrap';

export default FocusTrap;
