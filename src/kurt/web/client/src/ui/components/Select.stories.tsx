import type { Meta, StoryObj } from '@storybook/react';
import { Select } from './Select';

const meta = {
  title: 'Form/Select',
  component: Select,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component:
          'A dropdown select component with search, multi-select, and keyboard navigation support.',
      },
    },
  },
  argTypes: {
    label: {
      control: 'text',
      description: 'The label for the select',
    },
    placeholder: {
      control: 'text',
      description: 'Placeholder text when nothing is selected',
    },
    searchable: {
      control: 'boolean',
      description: 'Enable search functionality',
    },
    multi: {
      control: 'boolean',
      description: 'Allow multiple selections',
    },
    disabled: {
      control: 'boolean',
      description: 'Disable the select',
    },
  },
} satisfies Meta<typeof Select>;

export default meta;
type Story = StoryObj<typeof meta>;

const basicOptions = [
  { value: '1', label: 'Option 1' },
  { value: '2', label: 'Option 2' },
  { value: '3', label: 'Option 3' },
  { value: '4', label: 'Option 4' },
];

const countriesOptions = [
  { value: 'us', label: 'United States' },
  { value: 'ca', label: 'Canada' },
  { value: 'mx', label: 'Mexico' },
  { value: 'uk', label: 'United Kingdom' },
  { value: 'fr', label: 'France' },
  { value: 'de', label: 'Germany' },
  { value: 'jp', label: 'Japan' },
  { value: 'au', label: 'Australia' },
];

const optionsWithDesc = [
  {
    value: 'basic',
    label: 'Basic Plan',
    description: '$9/month - Perfect for individuals',
  },
  {
    value: 'pro',
    label: 'Pro Plan',
    description: '$29/month - For growing teams',
  },
  {
    value: 'enterprise',
    label: 'Enterprise',
    description: 'Custom pricing - For large organizations',
  },
];

export const BasicSelect: Story = {
  args: {
    options: basicOptions,
    placeholder: 'Choose an option...',
  },
};

export const WithLabel: Story = {
  args: {
    label: 'Select an option',
    options: basicOptions,
    placeholder: 'Choose...',
  },
};

export const WithHint: Story = {
  args: {
    label: 'Country',
    hint: 'Select your country of residence',
    options: countriesOptions,
    placeholder: 'Select a country...',
  },
};

export const WithError: Story = {
  args: {
    label: 'Country',
    options: countriesOptions,
    error: 'Please select a country',
    hasError: true,
    required: true,
  },
};

export const Searchable: Story = {
  args: {
    label: 'Country',
    options: countriesOptions,
    searchable: true,
    placeholder: 'Search or select...',
  },
};

export const MultiSelect: Story = {
  args: {
    label: 'Select interests',
    options: basicOptions,
    multi: true,
    placeholder: 'Select one or more...',
  },
};

export const Disabled: Story = {
  args: {
    label: 'Disabled select',
    options: basicOptions,
    disabled: true,
  },
};

export const WithDescriptions: Story = {
  args: {
    label: 'Choose a plan',
    options: optionsWithDesc,
    placeholder: 'Select a plan...',
  },
};

export const SearchableWithDescriptions: Story = {
  args: {
    label: 'Choose a plan',
    options: optionsWithDesc,
    searchable: true,
    placeholder: 'Search plans...',
  },
};

export const MultiSelectSearchable: Story = {
  args: {
    label: 'Select countries',
    options: countriesOptions,
    searchable: true,
    multi: true,
    placeholder: 'Search and select countries...',
  },
};

export const NoOptions: Story = {
  args: {
    label: 'Empty select',
    options: [],
    noOptionsMessage: 'No options available',
  },
};

export const Required: Story = {
  args: {
    label: 'Select one',
    options: basicOptions,
    required: true,
  },
};

export const FormUsage: Story = {
  render: () => (
    <form style={{ maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <label style={{ fontSize: '0.875rem', fontWeight: '500', display: 'block', marginBottom: '0.5rem' }}>
          Country <span style={{ color: '#ef4444' }}>*</span>
        </label>
        <Select
          options={countriesOptions}
          placeholder="Select your country..."
          required
        />
      </div>

      <div>
        <label style={{ fontSize: '0.875rem', fontWeight: '500', display: 'block', marginBottom: '0.5rem' }}>
          Subscription Plan
        </label>
        <Select
          options={optionsWithDesc}
          placeholder="Choose a plan..."
          searchable
        />
      </div>

      <div>
        <label style={{ fontSize: '0.875rem', fontWeight: '500', display: 'block', marginBottom: '0.5rem' }}>
          Interests
        </label>
        <Select
          options={basicOptions}
          placeholder="Select your interests..."
          multi
        />
      </div>

      <button type="submit" style={{ padding: '0.625rem 1rem' }}>
        Submit
      </button>
    </form>
  ),
};

export const SearchableForm: Story = {
  render: () => (
    <div style={{ maxWidth: '400px' }}>
      <Select
        label="Country"
        options={countriesOptions}
        searchable
        placeholder="Search and select a country..."
        hint="Start typing to search"
        required
      />
    </div>
  ),
};
