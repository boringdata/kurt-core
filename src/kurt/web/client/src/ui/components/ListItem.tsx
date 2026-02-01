import React from 'react';
import { ListItemProps } from '../types/list';
import './ListItem.css';

/**
 * ListItem component for flexible list item content
 * Supports avatars, icons, multiple content slots, and actions
 * WCAG 2.1 AA compliant with keyboard navigation support
 */
export const ListItem = React.forwardRef<HTMLDivElement, ListItemProps>(
  (
    {
      children,
      avatar,
      icon,
      subtitle,
      description,
      content,
      action,
      clickable = false,
      onClick,
      disabled = false,
      selected = false,
      divider = false,
      className = '',
      contentClassName = '',
      href,
      target,
      rel,
      active = false,
    },
    ref
  ) => {
    const isLink = !!href;
    const Component = isLink ? 'a' : 'div';

    const itemClassName = [
      'list-item',
      clickable && 'list-item--clickable',
      disabled && 'list-item--disabled',
      selected && 'list-item--selected',
      active && 'list-item--active',
      divider && 'list-item--divider',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    const contentWrapperClassName = [
      'list-item-content-wrapper',
      contentClassName,
    ]
      .filter(Boolean)
      .join(' ');

    const props: any = {
      ref,
      className: itemClassName,
      role: isLink ? 'link' : clickable ? 'button' : 'listitem',
    };

    if (isLink) {
      props.href = href;
      props.target = target;
      if (target === '_blank') {
        props.rel = rel || 'noopener noreferrer';
      } else if (rel) {
        props.rel = rel;
      }
      props.tabIndex = disabled ? -1 : 0;
    } else {
      props.onClick = onClick;
      if (clickable) {
        props.tabIndex = disabled ? -1 : 0;
        props.onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
          if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            onClick?.(e as any);
          }
        };
      }
    }

    if (selected) {
      props['aria-selected'] = true;
    }

    if (disabled) {
      props['aria-disabled'] = true;
    }

    if (active) {
      props['aria-current'] = 'page';
    }

    return (
      <Component {...props}>
        {/* Avatar or Icon */}
        {avatar && <div className="list-item-avatar">{avatar}</div>}
        {icon && !avatar && <div className="list-item-icon">{icon}</div>}

        {/* Main Content */}
        <div className={contentWrapperClassName}>
          {/* Primary Content */}
          {children && <div className="list-item-primary">{children}</div>}

          {/* Subtitle */}
          {subtitle && <div className="list-item-subtitle">{subtitle}</div>}

          {/* Description */}
          {description && <div className="list-item-description">{description}</div>}

          {/* Custom Content Slot */}
          {content && <div className="list-item-content">{content}</div>}
        </div>

        {/* Action Slot (right side) */}
        {action && <div className="list-item-action">{action}</div>}
      </Component>
    );
  }
);

ListItem.displayName = 'ListItem';
