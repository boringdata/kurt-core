import React, { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import { List, ListItem } from './index';

const meta: Meta<typeof List> = {
  title: 'Data Display/List',
  component: List,
  tags: ['autodocs'],
  argTypes: {
    type: { control: 'radio', options: ['ul', 'ol'] },
    divided: { control: 'boolean' },
    compact: { control: 'boolean' },
  },
};

export default meta;
type Story = StoryObj<typeof List>;

export const UnorderedList: Story = {
  args: {
    type: 'ul',
    items: ['First item', 'Second item', 'Third item', 'Fourth item'],
  },
};

export const OrderedList: Story = {
  args: {
    type: 'ol',
    items: ['First step', 'Second step', 'Third step', 'Fourth step'],
  },
};

export const DividedList: Story = {
  args: {
    type: 'ul',
    divided: true,
    items: ['Item with divider', 'Another item', 'One more item'],
  },
};

export const CompactList: Story = {
  args: {
    type: 'ul',
    compact: true,
    items: ['Compact item 1', 'Compact item 2', 'Compact item 3'],
  },
};

export const WithChildren: Story = {
  render: () => (
    <List type="ul">
      <li>Item with <strong>bold</strong> text</li>
      <li>Item with <em>italic</em> text</li>
      <li>Item with <code>code</code></li>
    </List>
  ),
};

export const NestedLists: Story = {
  render: () => (
    <List type="ol">
      <li>
        First item
        <List type="ul" style={{ marginTop: '0.5rem' }}>
          <li>Nested item 1</li>
          <li>Nested item 2</li>
        </List>
      </li>
      <li>Second item</li>
      <li>
        Third item
        <List type="ul" style={{ marginTop: '0.5rem' }}>
          <li>Another nested item</li>
        </List>
      </li>
    </List>
  ),
};
