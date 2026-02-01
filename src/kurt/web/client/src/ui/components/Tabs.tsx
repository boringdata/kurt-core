import React from 'react';
import { cn } from '../shared/utils';

interface TabItem {
  id: string;
  label: string;
  disabled?: boolean;
  icon?: React.ReactNode;
  content?: React.ReactNode;
}

interface TabsProps {
  items: TabItem[];
  defaultValue?: string;
  value?: string;
  onChange?: (value: string) => void;
  orientation?: 'horizontal' | 'vertical';
  variant?: 'default' | 'underline' | 'pill';
  className?: string;
  tabListClassName?: string;
  tabButtonClassName?: string;
  tabPanelClassName?: string;
  animated?: boolean;
}

interface TabContext {
  value: string;
  onChange: (value: string) => void;
  disabled?: { [key: string]: boolean };
}

const TabContext = React.createContext<TabContext | undefined>(undefined);

/**
 * Tabs component with keyboard navigation and accessibility
 * Supports horizontal/vertical orientation, keyboard navigation (arrows, home, end)
 * WCAG 2.1 AA accessible with proper ARIA attributes
 */
const Tabs = React.forwardRef<HTMLDivElement, TabsProps>(
  ({
    items,
    defaultValue,
    value: controlledValue,
    onChange,
    orientation = 'horizontal',
    variant = 'default',
    className,
    tabListClassName,
    tabButtonClassName,
    tabPanelClassName,
    animated = true,
  }, ref) => {
    const [internalValue, setInternalValue] = React.useState(
      controlledValue || defaultValue || items[0]?.id || ''
    );

    const value = controlledValue !== undefined ? controlledValue : internalValue;

    const handleChange = (newValue: string) => {
      setInternalValue(newValue);
      onChange?.(newValue);
    };

    const contextValue: TabContext = {
      value,
      onChange: handleChange,
      disabled: items.reduce((acc, item) => {
        if (item.disabled) acc[item.id] = true;
        return acc;
      }, {} as { [key: string]: boolean }),
    };

    return (
      <TabContext.Provider value={contextValue}>
        <div
          ref={ref}
          className={cn(
            'flex',
            orientation === 'vertical' ? 'flex-row gap-4' : 'flex-col gap-0',
            className
          )}
        >
          <TabList
            items={items}
            orientation={orientation}
            variant={variant}
            className={tabListClassName}
            buttonClassName={tabButtonClassName}
          />
          <div className="flex-1">
            {items.map((item) => (
              <TabPanel
                key={item.id}
                id={item.id}
                animated={animated}
                className={tabPanelClassName}
              >
                {item.content}
              </TabPanel>
            ))}
          </div>
        </div>
      </TabContext.Provider>
    );
  }
);

Tabs.displayName = 'Tabs';

interface TabListProps {
  items: TabItem[];
  orientation: 'horizontal' | 'vertical';
  variant: 'default' | 'underline' | 'pill';
  className?: string;
  buttonClassName?: string;
}

const TabList = React.forwardRef<HTMLDivElement, TabListProps>(
  ({ items, orientation, variant, className, buttonClassName }, ref) => {
    const context = React.useContext(TabContext);
    if (!context) throw new Error('TabList must be used within Tabs');

    const tabListRef = React.useRef<HTMLDivElement>(null);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
      const enabledItems = items.filter(item => !item.disabled);
      const currentIndex = enabledItems.findIndex(item => item.id === context.value);

      let newIndex = currentIndex;

      if (orientation === 'horizontal') {
        if (e.key === 'ArrowRight') {
          e.preventDefault();
          newIndex = (currentIndex + 1) % enabledItems.length;
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault();
          newIndex = (currentIndex - 1 + enabledItems.length) % enabledItems.length;
        } else if (e.key === 'Home') {
          e.preventDefault();
          newIndex = 0;
        } else if (e.key === 'End') {
          e.preventDefault();
          newIndex = enabledItems.length - 1;
        }
      } else {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          newIndex = (currentIndex + 1) % enabledItems.length;
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          newIndex = (currentIndex - 1 + enabledItems.length) % enabledItems.length;
        } else if (e.key === 'Home') {
          e.preventDefault();
          newIndex = 0;
        } else if (e.key === 'End') {
          e.preventDefault();
          newIndex = enabledItems.length - 1;
        }
      }

      if (newIndex !== currentIndex) {
        context.onChange(enabledItems[newIndex].id);
        setTimeout(() => {
          const button = tabListRef.current?.querySelector<HTMLButtonElement>(
            `[data-tab-id="${enabledItems[newIndex].id}"]`
          );
          button?.focus();
        }, 0);
      }
    };

    const variantStyles = {
      default: 'border-b border-gray-200 dark:border-gray-700',
      underline: 'border-b-2 border-transparent',
      pill: 'bg-gray-100 dark:bg-gray-800 rounded-lg p-1 inline-flex gap-1',
    };

    return (
      <div
        ref={tabListRef}
        role="tablist"
        aria-orientation={orientation}
        className={cn(
          'flex gap-0',
          orientation === 'vertical' ? 'flex-col' : 'flex-row',
          variantStyles[variant],
          className
        )}
        onKeyDown={handleKeyDown}
      >
        {items.map((item, index) => (
          <TabButton
            key={item.id}
            item={item}
            index={index}
            variant={variant}
            className={buttonClassName}
          />
        ))}
      </div>
    );
  }
);

TabList.displayName = 'TabList';

interface TabButtonProps {
  item: TabItem;
  index: number;
  variant: 'default' | 'underline' | 'pill';
  className?: string;
}

const TabButton = React.forwardRef<HTMLButtonElement, TabButtonProps>(
  ({ item, index, variant, className }, ref) => {
    const context = React.useContext(TabContext);
    if (!context) throw new Error('TabButton must be used within Tabs');

    const isActive = context.value === item.id;

    const variantClasses = {
      default: cn(
        'px-4 py-3 border-b-2 font-medium text-sm transition-all',
        isActive
          ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
          : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
      ),
      underline: cn(
        'px-4 py-3 font-medium text-sm transition-all border-b-2',
        isActive
          ? 'border-blue-600 text-gray-900 dark:text-white dark:border-blue-400'
          : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
      ),
      pill: cn(
        'px-4 py-2 rounded-md font-medium text-sm transition-all',
        isActive
          ? 'bg-white dark:bg-gray-900 text-gray-900 dark:text-white shadow'
          : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
      ),
    };

    return (
      <button
        ref={ref}
        role="tab"
        data-tab-id={item.id}
        aria-selected={isActive}
        aria-controls={`tabpanel-${item.id}`}
        tabIndex={isActive ? 0 : -1}
        disabled={item.disabled}
        onClick={() => {
          if (!item.disabled) {
            context.onChange(item.id);
          }
        }}
        className={cn(
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 rounded transition-all',
          item.disabled && 'opacity-50 cursor-not-allowed',
          !item.disabled && 'cursor-pointer',
          variantClasses[variant],
          className
        )}
      >
        <div className="flex items-center gap-2">
          {item.icon && <span className="inline-flex h-4 w-4">{item.icon}</span>}
          <span>{item.label}</span>
        </div>
      </button>
    );
  }
);

TabButton.displayName = 'TabButton';

interface TabPanelProps {
  id: string;
  children?: React.ReactNode;
  animated?: boolean;
  className?: string;
}

const TabPanel = React.forwardRef<HTMLDivElement, TabPanelProps>(
  ({ id, children, animated = true, className }, ref) => {
    const context = React.useContext(TabContext);
    if (!context) throw new Error('TabPanel must be used within Tabs');

    const isActive = context.value === id;

    return (
      <div
        ref={ref}
        role="tabpanel"
        id={`tabpanel-${id}`}
        aria-labelledby={id}
        hidden={!isActive}
        className={cn(
          animated && 'transition-opacity duration-200',
          isActive ? 'opacity-100' : 'opacity-0 pointer-events-none',
          className
        )}
      >
        {isActive && children}
      </div>
    );
  }
);

TabPanel.displayName = 'TabPanel';

export { Tabs, TabList, TabButton, TabPanel, type TabItem, type TabsProps };
export default Tabs;
