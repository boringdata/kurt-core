import React, { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import { ListItem } from './ListItem';
import { List } from './List';

const meta: Meta<typeof ListItem> = {
  title: 'Data Display/ListItem',
  component: ListItem,
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <div style={{ maxWidth: '500px' }}>
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof ListItem>;

export const Basic: Story = {
  args: {
    children: 'Basic list item',
  },
};

export const WithSubtitle: Story = {
  args: {
    children: 'Primary content',
    subtitle: 'Subtitle information',
  },
};

export const WithDescription: Story = {
  args: {
    children: 'Item title',
    subtitle: 'Subtitle',
    description: 'This is a longer description that provides more context about the item',
  },
};

export const WithAvatar: Story = {
  args: {
    children: 'Alice Johnson',
    subtitle: 'Engineering',
    avatar: (
      <div
        style={{
          width: '100%',
          height: '100%',
          borderRadius: '50%',
          backgroundColor: '#3b82f6',
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          fontSize: '0.875rem',
        }}
      >
        AJ
      </div>
    ),
  },
};

export const WithIcon: Story = {
  args: {
    children: 'Notification',
    subtitle: 'You have a new message',
    icon: <span style={{ fontSize: '1.5rem' }}>🔔</span>,
  },
};

export const WithAction: Story = {
  args: {
    children: 'Item with action',
    subtitle: 'Click the button on the right',
    action: <button style={{ padding: '0.25rem 0.75rem' }}>Action</button>,
  },
};

export const Clickable: Story = {
  args: {
    children: 'Clickable item',
    subtitle: 'Click me for interaction',
    clickable: true,
    onClick: () => alert('Item clicked!'),
  },
};

export const Selected: Story = {
  args: {
    children: 'Selected item',
    subtitle: 'This item is currently selected',
    selected: true,
  },
};

export const Active: Story = {
  args: {
    children: 'Active/Current page',
    subtitle: 'Navigation indicator',
    active: true,
  },
};

export const Disabled: Story = {
  args: {
    children: 'Disabled item',
    subtitle: 'This item cannot be interacted with',
    disabled: true,
  },
};

export const WithDivider: Story = {
  args: {
    children: 'Item with divider',
    subtitle: 'There is a line below',
    divider: true,
  },
};

export const AsLink: Story = {
  args: {
    children: 'Link item',
    subtitle: 'This renders as an anchor tag',
    href: '#',
    icon: <span>🔗</span>,
  },
};

export const ComplexContent: Story = {
  args: {
    avatar: (
      <div
        style={{
          width: '100%',
          height: '100%',
          borderRadius: '50%',
          backgroundColor: '#ec4899',
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
        }}
      >
        DP
      </div>
    ),
    children: 'Diana Prince',
    subtitle: 'Product Manager',
    description: 'Working on new features for Q1 2024',
    action: (
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>Edit</button>
        <button style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>Remove</button>
      </div>
    ),
  },
};

export const InList: Story = {
  render: () => (
    <List type="ul" divided={true}>
      <ListItem
        avatar={
          <div
            style={{
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              backgroundColor: '#3b82f6',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
            }}
          >
            AJ
          </div>
        }
        clickable
      >
        <strong>Alice Johnson</strong>
        <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
          alice@example.com
        </div>
      </ListItem>
      <ListItem
        avatar={
          <div
            style={{
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              backgroundColor: '#ec4899',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
            }}
          >
            BS
          </div>
        }
        clickable
      >
        <strong>Bob Smith</strong>
        <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
          bob@example.com
        </div>
      </ListItem>
      <ListItem
        avatar={
          <div
            style={{
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              backgroundColor: '#8b5cf6',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
            }}
          >
            CB
          </div>
        }
        clickable
      >
        <strong>Charlie Brown</strong>
        <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
          charlie@example.com
        </div>
      </ListItem>
    </List>
  ),
};

export const SelectableList: Story = {
  render: () => {
    const [selected, setSelected] = useState<string | null>(null);

    const items = [
      { id: 'a', name: 'Alice Johnson', role: 'Engineering' },
      { id: 'b', name: 'Bob Smith', role: 'Design' },
      { id: 'c', name: 'Charlie Brown', role: 'Product' },
    ];

    return (
      <List type="ul">
        {items.map((item) => (
          <ListItem
            key={item.id}
            clickable
            selected={selected === item.id}
            onClick={() => setSelected(item.id)}
            icon={<span>👤</span>}
          >
            <strong>{item.name}</strong>
            <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
              {item.role}
            </div>
          </ListItem>
        ))}
      </List>
    );
  },
};

export const ResponsiveList: Story = {
  render: () => (
    <List type="ul" divided={true}>
      {['Item 1', 'Item 2', 'Item 3', 'Item 4'].map((item, idx) => (
        <ListItem
          key={idx}
          avatar={
            <div
              style={{
                width: '100%',
                height: '100%',
                borderRadius: '50%',
                backgroundColor: `hsl(${idx * 90}, 70%, 50%)`,
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
              }}
            >
              {idx + 1}
            </div>
          }
          clickable
        >
          <strong>{item}</strong>
          <div style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.25rem' }}>
            Description for {item}
          </div>
        </ListItem>
      ))}
    </List>
  ),
  parameters: {
    viewport: {
      defaultViewport: 'mobile1',
    },
  },
};
