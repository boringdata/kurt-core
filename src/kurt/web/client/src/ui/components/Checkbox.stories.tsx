import type { Meta, StoryObj } from '@storybook/react';
import { Checkbox, CheckboxGroup } from './Checkbox';

const meta = {
  title: 'Form/Checkbox',
  component: Checkbox,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component:
          'A checkbox component with support for indeterminate state and group management.',
      },
    },
  },
  argTypes: {
    label: {
      control: 'text',
      description: 'The label for the checkbox',
    },
    description: {
      control: 'text',
      description: 'Description text below the label',
    },
    checked: {
      control: 'boolean',
      description: 'Whether the checkbox is checked',
    },
    indeterminate: {
      control: 'boolean',
      description: 'Whether the checkbox is indeterminate',
    },
    disabled: {
      control: 'boolean',
      description: 'Whether the checkbox is disabled',
    },
  },
} satisfies Meta<typeof Checkbox>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unchecked: Story = {
  args: {
    label: 'I agree to the terms',
  },
};

export const Checked: Story = {
  args: {
    label: 'I agree to the terms',
    checked: true,
  },
};

export const Indeterminate: Story = {
  args: {
    label: 'Select all options',
    indeterminate: true,
  },
};

export const WithDescription: Story = {
  args: {
    label: 'Subscribe to newsletter',
    description: 'Receive updates about new features and improvements',
    checked: true,
  },
};

export const Disabled: Story = {
  args: {
    label: 'This option is not available',
    disabled: true,
  },
};

export const DisabledChecked: Story = {
  args: {
    label: 'Required - this option is always enabled',
    checked: true,
    disabled: true,
  },
};

export const LongLabel: Story = {
  args: {
    label: 'I acknowledge that I have read and understood the privacy policy and consent to the collection and processing of my personal data as described therein',
    description:
      'Your privacy is important to us. We will never share your information with third parties.',
  },
};

export const CheckboxGroupVertical: Story = {
  render: () => (
    <CheckboxGroup
      label="Interests"
      direction="vertical"
      items={[
        { value: '1', label: 'Technology' },
        { value: '2', label: 'Design' },
        { value: '3', label: 'Business' },
        { value: '4', label: 'Science' },
      ]}
      value={['1', '3']}
      onChange={(value) => console.log('Selected:', value)}
    />
  ),
};

export const CheckboxGroupHorizontal: Story = {
  render: () => (
    <CheckboxGroup
      label="Difficulty Level"
      direction="horizontal"
      items={[
        { value: 'easy', label: 'Easy' },
        { value: 'medium', label: 'Medium' },
        { value: 'hard', label: 'Hard' },
      ]}
      value={['medium']}
      onChange={(value) => console.log('Selected:', value)}
    />
  ),
};

export const CheckboxGroupWithDescriptions: Story = {
  render: () => (
    <CheckboxGroup
      label="Communication Preferences"
      direction="vertical"
      items={[
        {
          value: 'email',
          label: 'Email Notifications',
          description: 'Receive important updates via email',
        },
        {
          value: 'sms',
          label: 'SMS Alerts',
          description: 'Get urgent notifications via SMS',
        },
        {
          value: 'push',
          label: 'Push Notifications',
          description: 'Receive notifications on your device',
        },
      ]}
      value={['email', 'push']}
      onChange={(value) => console.log('Selected:', value)}
    />
  ),
};

export const CheckboxGroupDisabled: Story = {
  render: () => (
    <CheckboxGroup
      label="Access Level (Disabled)"
      direction="vertical"
      items={[
        { value: 'read', label: 'Read' },
        { value: 'write', label: 'Write' },
        { value: 'admin', label: 'Admin' },
      ]}
      disabled
      value={['read']}
    />
  ),
};

export const CheckboxGroupMixed: Story = {
  render: () => (
    <CheckboxGroup
      label="Permissions"
      direction="vertical"
      items={[
        { value: 'read', label: 'Read Files', description: 'View file contents' },
        { value: 'write', label: 'Write Files', description: 'Create and edit files' },
        {
          value: 'delete',
          label: 'Delete Files',
          description: 'Permanently remove files',
          disabled: true,
        },
        { value: 'share', label: 'Share Files', description: 'Share with others' },
      ]}
      value={['read', 'write']}
      onChange={(value) => console.log('Selected:', value)}
    />
  ),
};

export const TermsAndConditions: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '500px' }}>
      <Checkbox
        label="I agree to the Terms of Service"
        description="Please read the full terms before accepting"
      />
      <Checkbox
        label="I agree to the Privacy Policy"
        description="Your data will be handled according to these terms"
      />
      <Checkbox
        label="I want to receive marketing emails"
        description="Optional: Get updates about new features and promotions"
        checked
      />
      <button style={{ padding: '0.625rem 1rem', alignSelf: 'flex-start' }}>
        Continue
      </button>
    </div>
  ),
};
