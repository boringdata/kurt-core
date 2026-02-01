import React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../shared/utils';

interface AccordionItem {
  id: string;
  title: string;
  content: React.ReactNode;
  disabled?: boolean;
  icon?: React.ReactNode;
}

interface AccordionProps {
  items: AccordionItem[];
  defaultExpanded?: string[];
  expanded?: string[];
  onExpandChange?: (expanded: string[]) => void;
  mode?: 'single' | 'multiple';
  className?: string;
  itemClassName?: string;
  triggerClassName?: string;
  contentClassName?: string;
  animated?: boolean;
  ariaLabel?: string;
}

interface AccordionContextType {
  expanded: Set<string>;
  toggleItem: (id: string) => void;
  mode: 'single' | 'multiple';
  disabled?: { [key: string]: boolean };
}

const AccordionContext = React.createContext<AccordionContextType | undefined>(undefined);

/**
 * Accordion component with expand/collapse, keyboard navigation
 * Supports single or multiple open items, icon animations
 * WCAG 2.1 AA accessible with proper ARIA attributes
 */
const Accordion = React.forwardRef<HTMLDivElement, AccordionProps>(
  ({
    items,
    defaultExpanded = [],
    expanded: controlledExpanded,
    onExpandChange,
    mode = 'single',
    className,
    itemClassName,
    triggerClassName,
    contentClassName,
    animated = true,
    ariaLabel = 'Accordion',
  }, ref) => {
    const [internalExpanded, setInternalExpanded] = React.useState<Set<string>>(
      new Set(controlledExpanded || defaultExpanded)
    );

    const expanded = controlledExpanded
      ? new Set(controlledExpanded)
      : internalExpanded;

    const toggleItem = (id: string) => {
      const newExpanded = new Set(expanded);

      if (newExpanded.has(id)) {
        newExpanded.delete(id);
      } else {
        if (mode === 'single') {
          newExpanded.clear();
        }
        newExpanded.add(id);
      }

      setInternalExpanded(newExpanded);
      onExpandChange?.(Array.from(newExpanded));
    };

    const contextValue: AccordionContextType = {
      expanded,
      toggleItem,
      mode,
      disabled: items.reduce((acc, item) => {
        if (item.disabled) acc[item.id] = true;
        return acc;
      }, {} as { [key: string]: boolean }),
    };

    return (
      <AccordionContext.Provider value={contextValue}>
        <div
          ref={ref}
          role="region"
          aria-label={ariaLabel}
          className={cn('flex flex-col gap-2', className)}
        >
          {items.map((item, index) => (
            <AccordionItem
              key={item.id}
              item={item}
              index={index}
              isLast={index === items.length - 1}
              itemClassName={itemClassName}
              triggerClassName={triggerClassName}
              contentClassName={contentClassName}
              animated={animated}
            />
          ))}
        </div>
      </AccordionContext.Provider>
    );
  }
);

Accordion.displayName = 'Accordion';

interface AccordionItemProps {
  item: AccordionItem;
  index: number;
  isLast: boolean;
  itemClassName?: string;
  triggerClassName?: string;
  contentClassName?: string;
  animated: boolean;
}

const AccordionItemComponent = React.forwardRef<HTMLDivElement, AccordionItemProps>(
  ({
    item,
    index,
    isLast,
    itemClassName,
    triggerClassName,
    contentClassName,
    animated,
  }, ref) => {
    const context = React.useContext(AccordionContext);
    if (!context) throw new Error('AccordionItem must be used within Accordion');

    const isExpanded = context.expanded.has(item.id);
    const isDisabled = context.disabled?.[item.id] || false;
    const contentRef = React.useRef<HTMLDivElement>(null);
    const [contentHeight, setContentHeight] = React.useState<number | undefined>();

    React.useEffect(() => {
      if (contentRef.current && isExpanded && animated) {
        const resizeObserver = new ResizeObserver(() => {
          setContentHeight(contentRef.current?.scrollHeight);
        });
        resizeObserver.observe(contentRef.current);
        return () => resizeObserver.disconnect();
      } else {
        setContentHeight(undefined);
      }
    }, [isExpanded, animated]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
      const items = Array.from(document.querySelectorAll('[role="button"][data-accordion-trigger]'));
      const currentIndex = items.indexOf(e.currentTarget);

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const nextButton = items[(currentIndex + 1) % items.length] as HTMLButtonElement;
        nextButton?.focus();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prevButton = items[(currentIndex - 1 + items.length) % items.length] as HTMLButtonElement;
        prevButton?.focus();
      } else if (e.key === 'Home') {
        e.preventDefault();
        (items[0] as HTMLButtonElement)?.focus();
      } else if (e.key === 'End') {
        e.preventDefault();
        (items[items.length - 1] as HTMLButtonElement)?.focus();
      }
    };

    return (
      <div
        ref={ref}
        className={cn(
          'border rounded-lg overflow-hidden',
          'border-gray-200 dark:border-gray-700',
          !isLast && 'mb-0',
          itemClassName
        )}
      >
        <button
          role="button"
          data-accordion-trigger
          aria-expanded={isExpanded}
          aria-controls={`accordion-content-${item.id}`}
          disabled={isDisabled}
          onClick={() => {
            if (!isDisabled) {
              context.toggleItem(item.id);
            }
          }}
          onKeyDown={handleKeyDown}
          className={cn(
            'w-full flex items-center justify-between gap-4 px-4 py-3',
            'font-medium text-sm transition-colors',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 rounded',
            isDisabled
              ? 'opacity-50 cursor-not-allowed'
              : 'cursor-pointer bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700',
            triggerClassName
          )}
        >
          <div className="flex items-center gap-3 flex-1 text-left">
            {item.icon && (
              <span className="inline-flex h-5 w-5 flex-shrink-0">
                {item.icon}
              </span>
            )}
            <span className="text-gray-900 dark:text-white">
              {item.title}
            </span>
          </div>
          <ChevronDown
            className={cn(
              'h-5 w-5 flex-shrink-0 transition-transform duration-300',
              'text-gray-600 dark:text-gray-400',
              isExpanded && 'rotate-180'
            )}
            aria-hidden="true"
          />
        </button>

        <div
          id={`accordion-content-${item.id}`}
          role="region"
          aria-labelledby={`accordion-header-${item.id}`}
          className={cn(
            'overflow-hidden',
            animated && 'transition-all duration-300 ease-in-out'
          )}
          style={animated && isExpanded ? { maxHeight: contentHeight } : {}}
        >
          <div
            ref={contentRef}
            className={cn(
              'px-4 py-3',
              'border-t border-gray-200 dark:border-gray-700',
              'bg-gray-50 dark:bg-gray-900/50',
              'text-sm text-gray-700 dark:text-gray-300',
              contentClassName
            )}
          >
            {item.content}
          </div>
        </div>
      </div>
    );
  }
);

AccordionItemComponent.displayName = 'AccordionItem';

export { Accordion, AccordionItemComponent as AccordionItem, type AccordionItem, type AccordionProps };
export default Accordion;
