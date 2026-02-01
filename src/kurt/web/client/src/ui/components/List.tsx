import React from 'react';
import { ListProps } from '../types/list';
import './List.css';

/**
 * List component for displaying ordered or unordered lists
 * Supports flexible content with avatars, icons, and actions
 * WCAG 2.1 AA compliant with proper accessibility attributes
 */
export const List = React.forwardRef<HTMLUListElement | HTMLOListElement, ListProps>(
  (
    { items, children, type = 'ul', divided = false, className = '', compact = false, role },
    ref
  ) => {
    const Component = type === 'ol' ? 'ol' : 'ul';

    const listClassName = [
      'list',
      `list--${type}`,
      divided && 'list--divided',
      compact && 'list--compact',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <Component ref={ref as any} className={listClassName} role={role || 'list'}>
        {items ? items.map((item, index) => <li key={index}>{item}</li>) : children}
      </Component>
    );
  }
);

List.displayName = 'List';
