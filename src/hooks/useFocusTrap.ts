/**
 * Focus Trap Hook
 * Traps keyboard focus within a modal element
 * WCAG 2.1 AA compliant keyboard navigation
 */

import { useEffect, useRef } from 'react';

interface UseFocusTrapOptions {
  active?: boolean;
}

/**
 * Hook that traps focus within a DOM element
 * Useful for modals, dialogs, and other modal components
 */
export function useFocusTrap(options: UseFocusTrapOptions = {}) {
  const { active = true } = options;
  const elementRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active || !elementRef.current) return;

    const element = elementRef.current;

    // Get all focusable elements
    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    // Focus first element on mount
    firstElement.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      const activeElement = document.activeElement;

      if (e.shiftKey) {
        // Shift + Tab - go backward
        if (activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab - go forward
        if (activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    element.addEventListener('keydown', handleKeyDown);

    return () => {
      element.removeEventListener('keydown', handleKeyDown);
    };
  }, [active]);

  return elementRef;
}

/**
 * Store previously focused element before opening modal
 * and restore focus when modal closes
 */
export function usePreviousFocus() {
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const saveFocus = () => {
    previousFocusRef.current = document.activeElement as HTMLElement;
  };

  const restoreFocus = () => {
    previousFocusRef.current?.focus();
  };

  return { saveFocus, restoreFocus };
}
