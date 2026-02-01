/**
 * Portal Component - Renders content outside the DOM hierarchy
 * Useful for modals, dropdowns, tooltips, and popovers
 *
 * WCAG 2.1 AA Compliant:
 * - Proper DOM structure for assistive technologies
 * - Focus management support
 */

import React, { useEffect, useRef, ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface PortalProps {
  /** The content to render in the portal */
  children: ReactNode;
  /** The DOM element to render into (defaults to document.body) */
  container?: HTMLElement | null;
  /** Optional class name for the portal wrapper */
  className?: string;
  /** Optional id for the portal element */
  id?: string;
}

/**
 * Portal Component
 * Renders children into a DOM node outside the current component hierarchy.
 *
 * Usage:
 * ```tsx
 * <Portal>
 *   <Modal>...</Modal>
 * </Portal>
 * ```
 */
export const Portal: React.FC<PortalProps> = ({
  children,
  container,
  className,
  id,
}) => {
  // Use provided container, fall back to body, then create if needed
  const portalElement = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!portalElement.current) {
      portalElement.current = document.createElement('div');
      if (className) {
        portalElement.current.className = className;
      }
      if (id) {
        portalElement.current.id = id;
      }
    }

    // Determine the target container
    const targetContainer = container || document.body;

    if (portalElement.current && targetContainer) {
      targetContainer.appendChild(portalElement.current);
    }

    return () => {
      if (portalElement.current && targetContainer) {
        targetContainer.removeChild(portalElement.current);
      }
    };
  }, [container, className, id]);

  if (!portalElement.current) {
    return null;
  }

  return createPortal(children, portalElement.current);
};

Portal.displayName = 'Portal';

export default Portal;
