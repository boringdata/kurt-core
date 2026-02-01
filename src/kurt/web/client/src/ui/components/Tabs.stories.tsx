import React from 'react';
import { Tabs } from './Tabs';
import { Home, Settings, Users, BarChart3 } from 'lucide-react';

export default {
  title: 'Components/Tabs',
  component: Tabs,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
};

export const Basic = {
  render: () => (
    <Tabs
      items={[
        {
          id: 'tab1',
          label: 'Overview',
          content: <div className="p-4">Overview content goes here</div>,
        },
        {
          id: 'tab2',
          label: 'Details',
          content: <div className="p-4">Details content goes here</div>,
        },
        {
          id: 'tab3',
          label: 'Settings',
          content: <div className="p-4">Settings content goes here</div>,
        },
      ]}
    />
  ),
};

export const WithIcons = {
  render: () => (
    <Tabs
      items={[
        {
          id: 'home',
          label: 'Home',
          icon: <Home className="h-4 w-4" />,
          content: <div className="p-4">Welcome to the home tab</div>,
        },
        {
          id: 'users',
          label: 'Users',
          icon: <Users className="h-4 w-4" />,
          content: <div className="p-4">User management interface</div>,
        },
        {
          id: 'settings',
          label: 'Settings',
          icon: <Settings className="h-4 w-4" />,
          content: <div className="p-4">Application settings</div>,
        },
      ]}
    />
  ),
};

export const Variants = {
  render: () => (
    <div className="flex flex-col gap-8">
      <div>
        <h3 className="font-semibold mb-2">Default Variant</h3>
        <Tabs
          variant="default"
          items={[
            {
              id: 'tab1',
              label: 'Tab One',
              content: <div className="p-4">Default variant content</div>,
            },
            {
              id: 'tab2',
              label: 'Tab Two',
              content: <div className="p-4">Tab two content</div>,
            },
          ]}
        />
      </div>

      <div>
        <h3 className="font-semibold mb-2">Underline Variant</h3>
        <Tabs
          variant="underline"
          items={[
            {
              id: 'tab1',
              label: 'Tab One',
              content: <div className="p-4">Underline variant content</div>,
            },
            {
              id: 'tab2',
              label: 'Tab Two',
              content: <div className="p-4">Tab two content</div>,
            },
          ]}
        />
      </div>

      <div>
        <h3 className="font-semibold mb-2">Pill Variant</h3>
        <Tabs
          variant="pill"
          items={[
            {
              id: 'tab1',
              label: 'Tab One',
              content: <div className="p-4">Pill variant content</div>,
            },
            {
              id: 'tab2',
              label: 'Tab Two',
              content: <div className="p-4">Tab two content</div>,
            },
          ]}
        />
      </div>
    </div>
  ),
};

export const DisabledTabs = {
  render: () => (
    <Tabs
      items={[
        {
          id: 'enabled1',
          label: 'Enabled Tab',
          content: <div className="p-4">This tab is enabled</div>,
        },
        {
          id: 'disabled',
          label: 'Disabled Tab',
          disabled: true,
          content: <div className="p-4">This tab is disabled</div>,
        },
        {
          id: 'enabled2',
          label: 'Another Enabled',
          content: <div className="p-4">This tab is also enabled</div>,
        },
      ]}
    />
  ),
};

export const VerticalOrientation = {
  render: () => (
    <Tabs
      orientation="vertical"
      items={[
        {
          id: 'overview',
          label: 'Overview',
          icon: <Home className="h-4 w-4" />,
          content: (
            <div className="p-6 bg-blue-50 dark:bg-blue-900/20 rounded">
              <h2 className="font-bold mb-2">Overview Content</h2>
              <p>This is the overview tab content displayed vertically</p>
            </div>
          ),
        },
        {
          id: 'analytics',
          label: 'Analytics',
          icon: <BarChart3 className="h-4 w-4" />,
          content: (
            <div className="p-6 bg-green-50 dark:bg-green-900/20 rounded">
              <h2 className="font-bold mb-2">Analytics Content</h2>
              <p>This is the analytics tab content displayed vertically</p>
            </div>
          ),
        },
        {
          id: 'settings',
          label: 'Settings',
          icon: <Settings className="h-4 w-4" />,
          content: (
            <div className="p-6 bg-purple-50 dark:bg-purple-900/20 rounded">
              <h2 className="font-bold mb-2">Settings Content</h2>
              <p>This is the settings tab content displayed vertically</p>
            </div>
          ),
        },
      ]}
    />
  ),
};

export const Controlled = {
  render: () => {
    const [activeTab, setActiveTab] = React.useState('tab1');

    return (
      <div className="flex flex-col gap-4">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('tab1')}
            className={`px-4 py-2 rounded ${
              activeTab === 'tab1'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            Go to Tab 1
          </button>
          <button
            onClick={() => setActiveTab('tab2')}
            className={`px-4 py-2 rounded ${
              activeTab === 'tab2'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            Go to Tab 2
          </button>
        </div>

        <Tabs
          value={activeTab}
          onChange={setActiveTab}
          items={[
            {
              id: 'tab1',
              label: 'Controlled Tab 1',
              content: <div className="p-4">Content controlled from outside</div>,
            },
            {
              id: 'tab2',
              label: 'Controlled Tab 2',
              content: <div className="p-4">Switch using the buttons above</div>,
            },
          ]}
        />
      </div>
    );
  },
};

export const KeyboardNavigation = {
  render: () => (
    <div>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Keyboard Navigation Test: Use Arrow Keys (←→), Home, and End to navigate tabs
      </p>
      <Tabs
        items={[
          {
            id: 'tab1',
            label: 'First Tab',
            content: <div className="p-4">Use arrow keys to navigate between tabs</div>,
          },
          {
            id: 'tab2',
            label: 'Second Tab',
            content: <div className="p-4">Press Home to go to first tab, End for last tab</div>,
          },
          {
            id: 'tab3',
            label: 'Third Tab',
            content: <div className="p-4">Tab key moves focus to buttons, arrow keys switch tabs</div>,
          },
          {
            id: 'tab4',
            label: 'Fourth Tab',
            content: <div className="p-4">Last tab in the list</div>,
          },
        ]}
      />
    </div>
  ),
};

export const DarkMode = {
  render: () => (
    <div className="dark bg-gray-900 p-6 rounded">
      <Tabs
        items={[
          {
            id: 'dark1',
            label: 'Dark Tab 1',
            icon: <Home className="h-4 w-4" />,
            content: <div className="p-4 bg-gray-800 rounded">Dark mode content</div>,
          },
          {
            id: 'dark2',
            label: 'Dark Tab 2',
            icon: <Settings className="h-4 w-4" />,
            content: <div className="p-4 bg-gray-800 rounded">Dark mode tab 2</div>,
          },
        ]}
      />
    </div>
  ),
};

export const Accessibility = {
  render: () => (
    <div className="flex flex-col gap-4">
      <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded">
        <p className="font-semibold text-sm">Accessibility Features</p>
        <ul className="text-sm mt-2 space-y-1">
          <li>✓ Full keyboard navigation (arrow keys, Home, End)</li>
          <li>✓ ARIA labels and roles for screen readers</li>
          <li>✓ Focus management and visible focus indicators</li>
          <li>✓ Semantic HTML structure</li>
          <li>✓ High contrast support</li>
        </ul>
      </div>

      <Tabs
        items={[
          {
            id: 'a11y1',
            label: 'Accessible Tab 1',
            content: <div className="p-4">Tab content with full WCAG 2.1 AA compliance</div>,
          },
          {
            id: 'a11y2',
            label: 'Accessible Tab 2',
            content: <div className="p-4">All interactive elements are keyboard accessible</div>,
          },
        ]}
      />
    </div>
  ),
};
