import React from 'react';
import { Accordion, AccordionItem } from './Accordion';
import { Settings, HelpCircle, Shield, BookOpen } from 'lucide-react';

export default {
  title: 'Components/Accordion',
  component: Accordion,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
};

export const Basic = {
  render: () => (
    <Accordion
      items={[
        {
          id: 'item1',
          title: 'Section One',
          content: <p>This is the content for the first accordion section.</p>,
        },
        {
          id: 'item2',
          title: 'Section Two',
          content: <p>This is the content for the second accordion section.</p>,
        },
        {
          id: 'item3',
          title: 'Section Three',
          content: <p>This is the content for the third accordion section.</p>,
        },
      ]}
    />
  ),
};

export const WithIcons = {
  render: () => (
    <Accordion
      items={[
        {
          id: 'settings',
          title: 'Settings',
          icon: <Settings className="h-5 w-5" />,
          content: (
            <div className="space-y-2">
              <p>Configure your application settings and preferences here.</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>User preferences</li>
                <li>Theme selection</li>
                <li>Notification settings</li>
              </ul>
            </div>
          ),
        },
        {
          id: 'help',
          title: 'Help & Support',
          icon: <HelpCircle className="h-5 w-5" />,
          content: (
            <div className="space-y-2">
              <p>Get help and support for common questions.</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>FAQ</li>
                <li>Documentation</li>
                <li>Contact support</li>
              </ul>
            </div>
          ),
        },
        {
          id: 'security',
          title: 'Security & Privacy',
          icon: <Shield className="h-5 w-5" />,
          content: (
            <div className="space-y-2">
              <p>Learn about our security practices and privacy policies.</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Privacy Policy</li>
                <li>Security Updates</li>
                <li>Data Protection</li>
              </ul>
            </div>
          ),
        },
      ]}
    />
  ),
};

export const MultipleOpen = {
  render: () => (
    <Accordion
      mode="multiple"
      defaultExpanded={['item1']}
      items={[
        {
          id: 'item1',
          title: 'First Section (Initially Open)',
          content: <p>This section is expanded by default. You can open multiple sections simultaneously.</p>,
        },
        {
          id: 'item2',
          title: 'Second Section',
          content: <p>Click here to expand this section. Multiple sections can be open at once.</p>,
        },
        {
          id: 'item3',
          title: 'Third Section',
          content: <p>You can toggle any section independently in multiple mode.</p>,
        },
      ]}
    />
  ),
};

export const SingleOpen = {
  render: () => (
    <Accordion
      mode="single"
      defaultExpanded={['intro']}
      items={[
        {
          id: 'intro',
          title: 'Introduction',
          content: (
            <p>
              In single mode (default), only one accordion section can be open at a time.
              Opening a new section automatically closes the previously open section.
            </p>
          ),
        },
        {
          id: 'features',
          title: 'Features',
          content: (
            <ul className="list-disc pl-5 space-y-1">
              <li>Single or multiple open items</li>
              <li>Smooth animations</li>
              <li>Keyboard navigation</li>
              <li>Icon animations</li>
            </ul>
          ),
        },
        {
          id: 'usage',
          title: 'Usage',
          content: (
            <p>
              Set the <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">mode</code> prop
              to &quot;single&quot; or &quot;multiple&quot; to control the behavior.
            </p>
          ),
        },
      ]}
    />
  ),
};

export const DisabledItems = {
  render: () => (
    <Accordion
      items={[
        {
          id: 'enabled1',
          title: 'Enabled Section',
          content: <p>This section is enabled and can be clicked.</p>,
        },
        {
          id: 'disabled',
          title: 'Disabled Section',
          disabled: true,
          content: <p>This section is disabled and cannot be clicked.</p>,
        },
        {
          id: 'enabled2',
          title: 'Another Enabled Section',
          content: <p>This section is also enabled.</p>,
        },
      ]}
    />
  ),
};

export const Controlled = {
  render: () => {
    const [expanded, setExpanded] = React.useState<string[]>(['faq1']);

    return (
      <div className="flex flex-col gap-4">
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded">
          <p className="font-semibold text-sm">Currently Open Sections:</p>
          <p className="text-sm">{expanded.length === 0 ? 'None' : expanded.join(', ')}</p>
        </div>

        <Accordion
          mode="multiple"
          expanded={expanded}
          onExpandChange={setExpanded}
          items={[
            {
              id: 'faq1',
              title: 'What is this?',
              content: (
                <p>This is a controlled accordion component. The state is managed from outside.</p>
              ),
            },
            {
              id: 'faq2',
              title: 'How does it work?',
              content: (
                <p>
                  The accordion is controlled by the <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">expanded</code> prop
                  and the <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">onExpandChange</code> callback.
                </p>
              ),
            },
            {
              id: 'faq3',
              title: 'Can I customize it?',
              content: <p>Yes! You can customize styling, animations, and behavior through props.</p>,
            },
          ]}
        />
      </div>
    );
  },
};

export const WithLongContent = {
  render: () => (
    <Accordion
      items={[
        {
          id: 'doc1',
          title: 'Complete Documentation',
          icon: <BookOpen className="h-5 w-5" />,
          content: (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              <h4 className="font-semibold">Getting Started</h4>
              <p>
                The accordion component is a flexible and accessible component for displaying
                collapsible content sections. It's fully WCAG 2.1 AA compliant with support for
                keyboard navigation, screen readers, and focus management.
              </p>

              <h4 className="font-semibold">Features</h4>
              <ul className="list-disc pl-5 space-y-1">
                <li>Single or multiple open items</li>
                <li>Smooth height animations</li>
                <li>Icon rotation animations</li>
                <li>Full keyboard navigation (arrow keys, Home, End)</li>
                <li>ARIA labels and roles for accessibility</li>
                <li>Disabled item support</li>
                <li>Customizable styling and animations</li>
                <li>TypeScript support</li>
              </ul>

              <h4 className="font-semibold">Keyboard Navigation</h4>
              <ul className="list-disc pl-5 space-y-1">
                <li><kbd className="bg-gray-100 dark:bg-gray-800 px-1 rounded">Arrow Down</kbd> - Move to next item</li>
                <li><kbd className="bg-gray-100 dark:bg-gray-800 px-1 rounded">Arrow Up</kbd> - Move to previous item</li>
                <li><kbd className="bg-gray-100 dark:bg-gray-800 px-1 rounded">Home</kbd> - Move to first item</li>
                <li><kbd className="bg-gray-100 dark:bg-gray-800 px-1 rounded">End</kbd> - Move to last item</li>
                <li><kbd className="bg-gray-100 dark:bg-gray-800 px-1 rounded">Enter</kbd> - Toggle current item</li>
              </ul>
            </div>
          ),
        },
      ]}
    />
  ),
};

export const DarkMode = {
  render: () => (
    <div className="dark bg-gray-900 p-6 rounded">
      <Accordion
        items={[
          {
            id: 'dark1',
            title: 'Dark Mode Section 1',
            icon: <Settings className="h-5 w-5" />,
            content: <p>This accordion is displayed in dark mode</p>,
          },
          {
            id: 'dark2',
            title: 'Dark Mode Section 2',
            icon: <HelpCircle className="h-5 w-5" />,
            content: <p>Colors are automatically adjusted for dark mode</p>,
          },
        ]}
      />
    </div>
  ),
};

export const Accessibility = {
  render: () => (
    <div className="flex flex-col gap-4">
      <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded">
        <p className="font-semibold text-sm">Accessibility Features</p>
        <ul className="text-sm mt-2 space-y-1">
          <li>✓ Full keyboard navigation (arrow keys, Home, End)</li>
          <li>✓ ARIA roles, labels, and expanded states</li>
          <li>✓ Focus management with focus trapping</li>
          <li>✓ Screen reader support</li>
          <li>✓ High contrast for dark mode</li>
          <li>✓ Semantic HTML structure</li>
          <li>✓ Smooth animations respect prefers-reduced-motion</li>
        </ul>
      </div>

      <Accordion
        ariaLabel="Accessibility settings"
        items={[
          {
            id: 'keyboard',
            title: 'Keyboard Navigation',
            content: (
              <div className="space-y-2">
                <p>Use arrow keys to move between sections and Enter to expand/collapse.</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Try pressing Tab to focus, then use arrow keys to navigate.
                </p>
              </div>
            ),
          },
          {
            id: 'screen-reader',
            title: 'Screen Reader Support',
            content: (
              <p>All sections have proper ARIA labels. Screen readers announce expanded/collapsed state.</p>
            ),
          },
          {
            id: 'motion',
            title: 'Motion Preferences',
            content: (
              <p>Animations are disabled for users who prefer reduced motion via system settings.</p>
            ),
          },
        ]}
      />
    </div>
  ),
};
