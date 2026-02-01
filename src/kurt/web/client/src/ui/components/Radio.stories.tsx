import type { Meta, StoryObj } from '@storybook/react';
import { Radio, RadioGroup } from './Radio';

const meta = {
  title: 'Form/Radio',
  component: Radio,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component:
          'A radio button component with support for group management and mutual exclusion.',
      },
    },
  },
  argTypes: {
    label: {
      control: 'text',
      description: 'The label for the radio button',
    },
    description: {
      control: 'text',
      description: 'Description text below the label',
    },
    checked: {
      control: 'boolean',
      description: 'Whether the radio button is checked',
    },
    disabled: {
      control: 'boolean',
      description: 'Whether the radio button is disabled',
    },
  },
} satisfies Meta<typeof Radio>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unchecked: Story = {
  args: {
    label: 'Option 1',
  },
};

export const Checked: Story = {
  args: {
    label: 'Option 1',
    checked: true,
  },
};

export const WithDescription: Story = {
  args: {
    label: 'Premium Plan',
    description: 'Get access to all features and priority support',
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
    label: 'Default option',
    checked: true,
    disabled: true,
  },
};

export const RadioGroupVertical: Story = {
  render: () => (
    <RadioGroup
      label="Select an option"
      direction="vertical"
      items={[
        { value: '1', label: 'Option 1' },
        { value: '2', label: 'Option 2' },
        { value: '3', label: 'Option 3' },
      ]}
      value="2"
      onChange={(value) => console.log('Selected:', value)}
    />
  ),
};

export const RadioGroupHorizontal: Story = {
  render: () => (
    <RadioGroup
      label="Choose a frequency"
      direction="horizontal"
      items={[
        { value: 'daily', label: 'Daily' },
        { value: 'weekly', label: 'Weekly' },
        { value: 'monthly', label: 'Monthly' },
      ]}
      value="weekly"
      onChange={(value) => console.log('Selected:', value)}
    />
  ),
};

export const RadioGroupWithDescriptions: Story = {
  render: () => (
    <RadioGroup
      label="Select a subscription plan"
      direction="vertical"
      items={[
        {
          value: 'basic',
          label: 'Basic Plan',
          description: '$9/month - Essential features for individuals',
        },
        {
          value: 'pro',
          label: 'Pro Plan',
          description: '$29/month - Advanced features and priority support',
        },
        {
          value: 'enterprise',
          label: 'Enterprise',
          description: 'Custom pricing - White-label solutions and dedicated support',
        },
      ]}
      value="pro"
      onChange={(value) => console.log('Selected:', value)}
    />
  ),
};

export const RadioGroupDisabled: Story = {
  render: () => (
    <RadioGroup
      label="Selection (Disabled)"
      direction="vertical"
      items={[
        { value: 'a', label: 'Option A' },
        { value: 'b', label: 'Option B' },
        { value: 'c', label: 'Option C' },
      ]}
      disabled
      value="b"
    />
  ),
};

export const RadioGroupMixed: Story = {
  render: () => (
    <RadioGroup
      label="Permission Level"
      direction="vertical"
      items={[
        { value: 'view', label: 'View Only', description: 'Can only view content' },
        {
          value: 'edit',
          label: 'Edit',
          description: 'Can view and edit content',
        },
        {
          value: 'admin',
          label: 'Admin',
          description: 'Full access and control',
        },
        {
          value: 'restricted',
          label: 'Restricted',
          description: 'Limited access',
          disabled: true,
        },
      ]}
      value="edit"
      onChange={(value) => console.log('Selected:', value)}
    />
  ),
};

export const SurveyForm: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '500px' }}>
      <div>
        <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>How satisfied are you?</h3>
        <RadioGroup
          direction="vertical"
          items={[
            { value: 'very-satisfied', label: 'Very Satisfied' },
            { value: 'satisfied', label: 'Satisfied' },
            { value: 'neutral', label: 'Neutral' },
            { value: 'dissatisfied', label: 'Dissatisfied' },
          ]}
          onChange={(value) => console.log('Selected:', value)}
        />
      </div>

      <div>
        <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>What would you improve?</h3>
        <RadioGroup
          direction="vertical"
          items={[
            { value: 'features', label: 'More features' },
            { value: 'performance', label: 'Better performance' },
            { value: 'support', label: 'Better support' },
            { value: 'pricing', label: 'Better pricing' },
          ]}
          onChange={(value) => console.log('Selected:', value)}
        />
      </div>

      <button style={{ padding: '0.625rem 1rem', alignSelf: 'flex-start' }}>
        Submit Feedback
      </button>
    </div>
  ),
};

export const PaymentMethod: Story = {
  render: () => (
    <RadioGroup
      label="Select a payment method"
      direction="vertical"
      items={[
        {
          value: 'card',
          label: 'Credit/Debit Card',
          description: 'Visa, Mastercard, or American Express',
        },
        {
          value: 'paypal',
          label: 'PayPal',
          description: 'Fast and secure payment with PayPal',
        },
        {
          value: 'bank',
          label: 'Bank Transfer',
          description: 'Direct bank transfer (may take 1-2 business days)',
        },
        {
          value: 'crypto',
          label: 'Cryptocurrency',
          description: 'Bitcoin, Ethereum, or other cryptocurrencies',
        },
      ]}
      value="card"
      onChange={(value) => console.log('Payment method:', value)}
    />
  ),
};
