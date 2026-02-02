/**
 * Dropdown/Menu Component - Accessible menu component
 *
 * WCAG 2.1 AA Compliant:
 * - Keyboard navigation (arrow keys, Enter, Escape)
 * - Focus management
 * - ARIA attributes for menus
 * - Click outside to close
 */

import React, { useRef, useEffect, useState, ReactNode } from 'react';
import FocusTrap from './FocusTrap';
import Portal from './Portal';

interface DropdownItem {
  id: string;
  label: string;
  icon?: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  divider?: boolean;
}

interface DropdownProps {
  /** Trigger element or text */
  trigger: ReactNode | string;
  /** Menu items */
  items: DropdownItem[];
  /** Placement relative to trigger */
  placement?: 'bottom' | 'top' | 'left' | 'right';
  /** Callback when item selected */
  onSelect?: (itemId: string) => void;
  /** Whether dropdown is initially open */
  defaultOpen?: boolean;
  /** Optional class name */
  className?: string;
  /** Close on item select */
  closeOnSelect?: boolean;
}

interface DropdownMenuProps {
  /** Menu items */
  items: DropdownItem[];
  /** Callback when item clicked */
  onItemClick?: (itemId: string) => void;
  /** Optional class name */
  className?: string;
  /** Label for accessibility */
  label?: string;
}

/**
 * DropdownMenu Component
 * The menu content for dropdowns
 */
export const DropdownMenu: React.FC<DropdownMenuProps> = ({
  items,
  onItemClick,
  className = '',
  label = 'Menu',
}) => {
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);

  const focusableItems = items.filter((item) => !item.disabled && !item.divider);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < focusableItems.length - 1 ? prev + 1 : prev
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : prev));
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const highlightedItem = focusableItems[highlightedIndex];
        if (highlightedItem) {
          onItemClick?.(highlightedItem.id);
          highlightedItem.onClick?.();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [highlightedIndex, focusableItems, onItemClick]);

  return (
    <div
      ref={menuRef}
      className={`rounded-lg border border-gray-200 bg-white shadow-lg py-1 ${className}`}
      role="menu"
      aria-label={label}
    >
      {items.map((item, index) => {
        if (item.divider) {
          return (
            <div
              key={item.id}
              className="border-t border-gray-200 my-1"
              role="separator"
            />
          );
        }

        const isHighlighted =
          focusableItems.findIndex((fi) => fi.id === item.id) === highlightedIndex;

        return (
          <button
            key={item.id}
            onClick={() => {
              onItemClick?.(item.id);
              item.onClick?.();
            }}
            disabled={item.disabled}
            className={`w-full px-4 py-2 text-left text-sm transition-colors flex items-center gap-2 ${
              isHighlighted && !item.disabled
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-700 hover:bg-gray-50'
            } ${
              item.disabled
                ? 'text-gray-400 cursor-not-allowed'
                : 'cursor-pointer'
            }`}
            role="menuitem"
            aria-disabled={item.disabled}
          >
            {item.icon && <span className="flex-shrink-0">{item.icon}</span>}
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
};

/**
 * Dropdown Component
 * Accessible dropdown menu with keyboard navigation
 *
 * Usage:
 * ```tsx
 * <Dropdown
 *   trigger="Menu"
 *   items={[
 *     { id: 'edit', label: 'Edit' },
 *     { id: 'delete', label: 'Delete', icon: <TrashIcon /> },
 *   ]}
 *   onSelect={(id) => console.log(id)}
 * />
 * ```
 */
export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  placement = 'bottom',
  onSelect,
  defaultOpen = false,
  className = '',
  closeOnSelect = true,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  const handleItemSelect = (itemId: string) => {
    onSelect?.(itemId);
    if (closeOnSelect) {
      setIsOpen(false);
    }
  };

  const placementClass = {
    bottom: 'mt-2',
    top: 'mb-2',
    left: 'mr-2',
    right: 'ml-2',
  }[placement];

  return (
    <div
      ref={containerRef}
      className={`relative inline-block ${className}`}
    >
      <button
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 transition-colors"
        aria-haspopup="menu"
        aria-expanded={isOpen}
      >
        {trigger}
      </button>

      {isOpen && (
        <Portal>
          <FocusTrap
            active={isOpen}
            onEscapeKey={() => setIsOpen(false)}
            restoreFocus
          >
            <div
              style={{
                position: 'fixed',
                top:
                  (triggerRef.current?.getBoundingClientRect().bottom ?? 0) +
                  window.scrollY,
                left:
                  (triggerRef.current?.getBoundingClientRect().left ?? 0) +
                  window.scrollX,
                zIndex: 1000,
              }}
              className={placementClass}
            >
              <DropdownMenu
                items={items}
                onItemClick={handleItemSelect}
                label="Dropdown menu"
              />
            </div>
          </FocusTrap>
        </Portal>
      )}
    </div>
  );
};

/**
 * DropdownTrigger Component - Trigger button for dropdown
 */
export const DropdownTrigger: React.FC<{
  children: ReactNode;
  onClick: () => void;
  isOpen: boolean;
  className?: string;
}> = ({ children, onClick, isOpen, className = '' }) => {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
        isOpen
          ? 'border-blue-500 bg-blue-50 text-blue-600'
          : 'border-gray-300 bg-white hover:bg-gray-50'
      } ${className}`}
      aria-haspopup="menu"
      aria-expanded={isOpen}
    >
      {children}
    </button>
  );
};

DropdownMenu.displayName = 'DropdownMenu';
Dropdown.displayName = 'Dropdown';
DropdownTrigger.displayName = 'DropdownTrigger';

export { DropdownTrigger };

export default Dropdown;
