import type { Meta, StoryObj } from '@storybook/react';
import { Input } from './Input';

const meta = {
  title: 'Form/Input',
  component: Input,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component:
          'A versatile input component supporting multiple input types with built-in label, hint, and error message support. Fully accessible with WCAG 2.1 AA compliance.',
      },
    },
  },
  argTypes: {
    type: {
      control: 'select',
      options: ['text', 'password', 'email', 'number', 'tel', 'url'],
      description: 'The type of input field',
    },
    label: {
      control: 'text',
      description: 'The label for the input field',
    },
    hint: {
      control: 'text',
      description: 'Hint text displayed below the input',
    },
    error: {
      control: 'text',
      description: 'Error message displayed when the field has an error',
    },
    placeholder: {
      control: 'text',
      description: 'Placeholder text for the input',
    },
    required: {
      control: 'boolean',
      description: 'Whether the field is required',
    },
    hasError: {
      control: 'boolean',
      description: 'Whether the field has an error',
    },
    disabled: {
      control: 'boolean',
      description: 'Whether the field is disabled',
    },
    readOnly: {
      control: 'boolean',
      description: 'Whether the field is read-only',
    },
  },
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TextInput: Story = {
  args: {
    type: 'text',
    label: 'Name',
    placeholder: 'Enter your name',
    hint: 'Your full legal name',
  },
};

export const EmailInput: Story = {
  args: {
    type: 'email',
    label: 'Email Address',
    placeholder: 'you@example.com',
    required: true,
    hint: 'We will never share your email',
  },
};

export const PasswordInput: Story = {
  args: {
    type: 'password',
    label: 'Password',
    placeholder: 'Enter your password',
    required: true,
    hint: 'Minimum 8 characters',
  },
};

export const NumberInput: Story = {
  args: {
    type: 'number',
    label: 'Age',
    placeholder: 'Enter your age',
    min: 0,
    max: 120,
  },
};

export const TelInput: Story = {
  args: {
    type: 'tel',
    label: 'Phone Number',
    placeholder: '+1 (555) 123-4567',
    required: true,
  },
};

export const URLInput: Story = {
  args: {
    type: 'url',
    label: 'Website',
    placeholder: 'https://example.com',
    hint: 'Include the full URL with protocol',
  },
};

export const WithError: Story = {
  args: {
    type: 'email',
    label: 'Email Address',
    placeholder: 'you@example.com',
    error: 'Please enter a valid email address',
    hasError: true,
    required: true,
  },
};

export const WithoutError: Story = {
  args: {
    type: 'email',
    label: 'Email Address',
    placeholder: 'you@example.com',
    error: 'Please enter a valid email address',
    hasError: false,
    required: true,
  },
};

export const Disabled: Story = {
  args: {
    label: 'Disabled Input',
    placeholder: 'This input is disabled',
    disabled: true,
    value: 'Disabled value',
  },
};

export const ReadOnly: Story = {
  args: {
    label: 'Read-Only Input',
    value: 'This is read-only',
    readOnly: true,
  },
};

export const Required: Story = {
  args: {
    label: 'Required Field',
    placeholder: 'This field is required',
    required: true,
  },
};

export const WithHintOnly: Story = {
  args: {
    label: 'Hint Example',
    placeholder: 'Enter some text',
    hint: 'This is helpful hint text to guide the user',
  },
};

export const LongHintText: Story = {
  args: {
    label: 'Password',
    type: 'password',
    placeholder: 'Enter your password',
    hint: 'Your password should be at least 8 characters long and contain a mix of uppercase, lowercase, numbers, and special characters for maximum security.',
  },
};

export const AllFeatures: Story = {
  args: {
    type: 'email',
    label: 'Email Address',
    placeholder: 'you@example.com',
    hint: 'We will use this to send you important updates',
    required: true,
    autoComplete: 'email',
    maxLength: 100,
  },
};

export const AllFeaturesWithError: Story = {
  args: {
    type: 'email',
    label: 'Email Address',
    placeholder: 'you@example.com',
    hint: 'We will use this to send you important updates',
    error: 'This email address is already registered',
    hasError: true,
    required: true,
    autoComplete: 'email',
    maxLength: 100,
  },
};

export const ValidationStates: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '400px' }}>
      <Input
        label="Valid Input"
        type="email"
        placeholder="valid@example.com"
        value="valid@example.com"
        readOnly
        hint="This input is valid"
      />
      <Input
        label="Invalid Input"
        type="email"
        placeholder="invalid@example"
        error="Please enter a valid email address"
        hasError={true}
        value="invalid@example"
      />
      <Input
        label="Empty Required"
        placeholder="This is required"
        error="This field is required"
        hasError={true}
        required={true}
      />
    </div>
  ),
};

export const FormField: Story = {
  render: () => (
    <form
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        maxWidth: '400px',
      }}
      onSubmit={(e) => e.preventDefault()}
    >
      <Input
        type="text"
        label="Full Name"
        placeholder="John Doe"
        required
        hint="Your legal name as it appears on official documents"
      />
      <Input
        type="email"
        label="Email Address"
        placeholder="john@example.com"
        required
        hint="We'll send you a confirmation email"
      />
      <Input
        type="password"
        label="Password"
        placeholder="Enter a strong password"
        required
        hint="At least 8 characters with mixed case and numbers"
      />
      <Input
        type="tel"
        label="Phone Number"
        placeholder="+1 (555) 123-4567"
        hint="Optional: Include country code for international numbers"
      />
      <button type="submit" style={{ padding: '0.625rem 1rem', borderRadius: '0.375rem' }}>
        Sign Up
      </button>
    </form>
  ),
};
