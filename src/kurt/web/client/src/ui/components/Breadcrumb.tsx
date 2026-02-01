import React from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '../shared/utils';

interface BreadcrumbItem {
  label: string;
  href?: string;
  icon?: React.ReactNode;
  isActive?: boolean;
  onClick?: () => void;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: React.ReactNode;
  className?: string;
  collapseAt?: 'sm' | 'md' | 'lg';
  onItemClick?: (item: BreadcrumbItem) => void;
  ariaLabel?: string;
}

/**
 * Breadcrumb component for hierarchical navigation
 * Supports custom separators, icons, mobile collapse, and clickable links
 * WCAG 2.1 AA accessible with proper ARIA attributes
 */
const Breadcrumb = React.forwardRef<HTMLNavElement, BreadcrumbProps>(
  ({
    items,
    separator = <ChevronRight className="h-4 w-4" />,
    className,
    collapseAt = 'sm',
    onItemClick,
    ariaLabel = 'Breadcrumb navigation',
  }, ref) => {
    const [collapsed, setCollapsed] = React.useState(false);

    const getCollapseBreakpoint = () => {
      switch (collapseAt) {
        case 'md':
          return 768;
        case 'lg':
          return 1024;
        case 'sm':
        default:
          return 640;
      }
    };

    React.useEffect(() => {
      const handleResize = () => {
        setCollapsed(window.innerWidth < getCollapseBreakpoint());
      };

      handleResize();
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }, [collapseAt]);

    const visibleItems = collapsed && items.length > 3
      ? [items[0], { label: '...', isActive: false }, ...items.slice(-2)]
      : items;

    const handleItemClick = (item: BreadcrumbItem) => {
      if (item.onClick) {
        item.onClick();
      }
      if (onItemClick) {
        onItemClick(item);
      }
    };

    return (
      <nav
        ref={ref}
        aria-label={ariaLabel}
        className={cn('flex items-center', className)}
      >
        <ol className="flex items-center gap-2">
          {visibleItems.map((item, index) => (
            <li key={`${item.label}-${index}`} className="flex items-center gap-2">
              {item.label === '...' ? (
                <span
                  className="text-sm font-medium text-gray-500 dark:text-gray-400 px-2"
                  aria-hidden="true"
                >
                  ...
                </span>
              ) : (
                <>
                  <div className="flex items-center gap-1">
                    {item.icon && (
                      <span className="inline-flex h-4 w-4 flex-shrink-0">
                        {item.icon}
                      </span>
                    )}
                    {item.href && !item.isActive ? (
                      <a
                        href={item.href}
                        onClick={(e) => {
                          e.preventDefault();
                          handleItemClick(item);
                        }}
                        className={cn(
                          'text-sm font-medium transition-colors',
                          'text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300',
                          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 rounded px-1'
                        )}
                        aria-current={item.isActive ? 'page' : undefined}
                      >
                        {item.label}
                      </a>
                    ) : (
                      <span
                        className={cn(
                          'text-sm font-medium',
                          item.isActive
                            ? 'text-gray-900 dark:text-white'
                            : 'text-gray-600 dark:text-gray-300 cursor-pointer hover:text-gray-900 dark:hover:text-white'
                        )}
                        aria-current={item.isActive ? 'page' : undefined}
                        onClick={() => {
                          if (!item.isActive && item.onClick) {
                            handleItemClick(item);
                          }
                        }}
                        role={!item.href && !item.isActive ? 'button' : undefined}
                        tabIndex={!item.href && !item.isActive ? 0 : undefined}
                        onKeyDown={(e) => {
                          if (!item.href && !item.isActive && (e.key === 'Enter' || e.key === ' ')) {
                            e.preventDefault();
                            handleItemClick(item);
                          }
                        }}
                      >
                        {item.label}
                      </span>
                    )}
                  </div>
                </>
              )}

              {index < visibleItems.length - 1 && (
                <span
                  className="flex-shrink-0 text-gray-400 dark:text-gray-600"
                  aria-hidden="true"
                >
                  {separator}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>
    );
  }
);

Breadcrumb.displayName = 'Breadcrumb';

export default Breadcrumb;
