/**
 * Tooltip and Popover Components - Information disclosure components
 *
 * WCAG 2.1 AA Compliant:
 * - Keyboard navigation (Escape to close)
 * - Focus management
 * - ARIA attributes for tooltips/popovers
 * - Proper positioning
 */

import React, { useRef, useEffect, useState, ReactNode } from 'react';
import Portal from './Portal';
import FocusTrap from './FocusTrap';
import { calculatePosition, Position } from './Positioning';

interface TooltipProps {
  /** Tooltip content */
  content: string | ReactNode;
  /** Element that triggers the tooltip */
  children: ReactNode;
  /** Trigger mode */
  trigger?: 'hover' | 'click' | 'focus';
  /** Placement relative to trigger */
  placement?: 'top' | 'bottom' | 'left' | 'right';
  /** Delay before showing (ms) */
  delay?: number;
  /** Background color */
  bgColor?: string;
  /** Text color */
  textColor?: string;
  /** Optional class name */
  className?: string;
}

interface PopoverProps {
  /** Popover title */
  title?: string;
  /** Popover content */
  children: ReactNode;
  /** Trigger element */
  trigger: ReactNode;
  /** Trigger mode */
  triggerMode?: 'click' | 'hover' | 'focus';
  /** Placement relative to trigger */
  placement?: 'top' | 'bottom' | 'left' | 'right';
  /** Show close button */
  showClose?: boolean;
  /** Callback when closed */
  onClose?: () => void;
  /** Optional class name */
  className?: string;
  /** Custom width */
  width?: string | number;
}

/**
 * Tooltip Component
 * Displays brief information on hover/click
 *
 * Usage:
 * ```tsx
 * <Tooltip content="Click to save" placement="top">
 *   <button>Save</button>
 * </Tooltip>
 * ```
 */
export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  trigger = 'hover',
  placement = 'top',
  delay = 200,
  bgColor = '#1f2937',
  textColor = '#ffffff',
  className = '',
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState<Position | null>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isVisible && triggerRef.current && tooltipRef.current) {
      const pos = calculatePosition(triggerRef.current, tooltipRef.current, {
        placement: placement as any,
        offset: [8, 0],
      });
      setPosition(pos);
    }
  }, [isVisible, placement]);

  const handleMouseEnter = () => {
    if (trigger === 'hover') {
      timeoutRef.current = setTimeout(() => setIsVisible(true), delay);
    }
  };

  const handleMouseLeave = () => {
    if (trigger === 'hover') {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      setIsVisible(false);
    }
  };

  const handleClick = () => {
    if (trigger === 'click') {
      setIsVisible(!isVisible);
    }
  };

  const handleFocus = () => {
    if (trigger === 'focus') {
      setIsVisible(true);
    }
  };

  const handleBlur = () => {
    if (trigger === 'focus') {
      setIsVisible(false);
    }
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        onFocus={handleFocus}
        onBlur={handleBlur}
      >
        {children}
      </div>

      {isVisible && position && (
        <Portal>
          <div
            ref={tooltipRef}
            style={{
              position: 'fixed',
              top: position.top,
              left: position.left,
              zIndex: 1000,
              backgroundColor: bgColor,
              color: textColor,
            }}
            className={`px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap shadow-lg ${className}`}
            role="tooltip"
          >
            {content}
            {/* Arrow */}
            <div
              style={{
                position: 'absolute',
                width: 0,
                height: 0,
                borderLeft: '6px solid transparent',
                borderRight: '6px solid transparent',
                borderTop: `6px solid ${bgColor}`,
                bottom: '-6px',
                left: '50%',
                transform: 'translateX(-50%)',
              }}
            />
          </div>
        </Portal>
      )}
    </>
  );
};

/**
 * Popover Component
 * Shows complex content on click/hover
 *
 * Usage:
 * ```tsx
 * <Popover
 *   trigger={<button>Help</button>}
 *   title="Help"
 * >
 *   <p>This is helpful information.</p>
 * </Popover>
 * ```
 */
export const Popover: React.FC<PopoverProps> = ({
  title,
  children,
  trigger,
  triggerMode = 'click',
  placement = 'bottom',
  showClose = true,
  onClose,
  className = '',
  width = 300,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<Position | null>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && triggerRef.current && contentRef.current) {
      const pos = calculatePosition(triggerRef.current, contentRef.current, {
        placement: placement as any,
        offset: [8, 0],
      });
      setPosition(pos);
    }
  }, [isOpen, placement]);

  const handleClose = () => {
    setIsOpen(false);
    onClose?.();
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        contentRef.current &&
        !contentRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        handleClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  const widthValue = typeof width === 'number' ? `${width}px` : width;

  return (
    <>
      <div
        ref={triggerRef}
        onClick={() => triggerMode === 'click' && setIsOpen(!isOpen)}
        onMouseEnter={() => triggerMode === 'hover' && setIsOpen(true)}
        onMouseLeave={() => triggerMode === 'hover' && setIsOpen(false)}
      >
        {trigger}
      </div>

      {isOpen && position && (
        <Portal>
          <FocusTrap
            active={isOpen}
            onEscapeKey={handleClose}
            restoreFocus
          >
            <div
              ref={contentRef}
              style={{
                position: 'fixed',
                top: position.top,
                left: position.left,
                width: widthValue,
                zIndex: 1000,
              }}
              className={`rounded-lg border border-gray-200 bg-white shadow-lg ${className}`}
              role="dialog"
              aria-modal="true"
            >
              {/* Header */}
              {(title || showClose) && (
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                  {title && <h3 className="font-semibold text-gray-900">{title}</h3>}
                  {showClose && (
                    <button
                      onClick={handleClose}
                      className="text-gray-500 hover:text-gray-700 p-1"
                      aria-label="Close"
                    >
                      ✕
                    </button>
                  )}
                </div>
              )}

              {/* Content */}
              <div className="p-4">{children}</div>
            </div>
          </FocusTrap>
        </Portal>
      )}
    </>
  );
};

/**
 * InfoIcon with Tooltip - Common pattern
 */
export const InfoIcon: React.FC<{
  content: string;
  className?: string;
}> = ({ content, className = '' }) => {
  return (
    <Tooltip content={content} trigger="hover" placement="top">
      <span
        className={`inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-600 text-xs font-bold cursor-help ${className}`}
      >
        ?
      </span>
    </Tooltip>
  );
};

/**
 * HoverCard - Hover-triggered card with content
 */
export const HoverCard: React.FC<{
  trigger: ReactNode;
  children: ReactNode;
  delay?: number;
  className?: string;
}> = ({ trigger, children, delay = 200, className = '' }) => {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => setIsVisible(true), delay);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setIsVisible(false);
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <div
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="relative"
    >
      {trigger}
      {isVisible && (
        <div
          className={`absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg p-4 z-50 ${className}`}
        >
          {children}
        </div>
      )}
    </div>
  );
};

Tooltip.displayName = 'Tooltip';
Popover.displayName = 'Popover';
InfoIcon.displayName = 'InfoIcon';
HoverCard.displayName = 'HoverCard';

export {
  Popover,
  InfoIcon,
  HoverCard,
};

export default Tooltip;
