import React from 'react';
import Breadcrumb from './Breadcrumb';
import { Home, FileText, Settings } from 'lucide-react';

export default {
  title: 'Components/Breadcrumb',
  component: Breadcrumb,
  parameters: {
    layout: 'padded',
  },
  tags: ['autodocs'],
};

export const Basic = {
  render: () => (
    <Breadcrumb
      items={[
        { label: 'Home', href: '/' },
        { label: 'Documents', href: '/documents' },
        { label: 'My Document', isActive: true },
      ]}
    />
  ),
};

export const WithIcons = {
  render: () => (
    <Breadcrumb
      items={[
        { label: 'Home', href: '/', icon: <Home className="h-4 w-4" /> },
        { label: 'Documents', href: '/documents', icon: <FileText className="h-4 w-4" /> },
        { label: 'Settings', isActive: true, icon: <Settings className="h-4 w-4" /> },
      ]}
    />
  ),
};

export const CustomSeparator = {
  render: () => (
    <Breadcrumb
      items={[
        { label: 'Home', href: '/' },
        { label: 'Projects', href: '/projects' },
        { label: 'Active Project', isActive: true },
      ]}
      separator={<span className="mx-2 text-gray-400">→</span>}
    />
  ),
};

export const MobileCollapse = {
  render: () => (
    <div className="flex flex-col gap-8">
      <div>
        <p className="text-sm font-semibold mb-2">Desktop (collapse at sm breakpoint)</p>
        <Breadcrumb
          items={[
            { label: 'Home', href: '/' },
            { label: 'Projects', href: '/projects' },
            { label: 'Phase 1', href: '/projects/p1' },
            { label: 'Component Library', href: '/projects/p1/components' },
            { label: 'Breadcrumb', isActive: true },
          ]}
          collapseAt="sm"
        />
      </div>
      <div>
        <p className="text-sm font-semibold mb-2">Desktop (collapse at md breakpoint)</p>
        <Breadcrumb
          items={[
            { label: 'Home', href: '/' },
            { label: 'Projects', href: '/projects' },
            { label: 'Phase 1', href: '/projects/p1' },
            { label: 'Component Library', href: '/projects/p1/components' },
            { label: 'Breadcrumb', isActive: true },
          ]}
          collapseAt="md"
        />
      </div>
    </div>
  ),
};

export const Clickable = {
  render: () => (
    <Breadcrumb
      items={[
        { label: 'Home', href: '/', onClick: () => alert('Navigated to Home') },
        { label: 'Documents', href: '/documents', onClick: () => alert('Navigated to Documents') },
        { label: 'Current', isActive: true },
      ]}
      onItemClick={(item) => console.log('Item clicked:', item)}
    />
  ),
};

export const DarkMode = {
  render: () => (
    <div className="dark bg-gray-900 p-4 rounded">
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
          { label: 'Electronics', isActive: true },
        ]}
      />
    </div>
  ),
};

export const Accessibility = {
  render: () => (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm font-semibold mb-2">Keyboard Navigation Test</p>
        <p className="text-xs text-gray-600 mb-3">Press Tab to focus breadcrumb items, then use arrow keys or Enter</p>
        <Breadcrumb
          items={[
            { label: 'Home', href: '/' },
            { label: 'Services', href: '/services' },
            { label: 'Consulting', isActive: true },
          ]}
          ariaLabel="Main navigation breadcrumb"
        />
      </div>
    </div>
  ),
};
