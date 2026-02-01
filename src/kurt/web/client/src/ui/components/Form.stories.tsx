import type { Meta, StoryObj } from '@storybook/react';
import {
  FormLayout,
  FormGroup,
  ValidationMessage,
  FormSection,
} from './Form';
import { Input } from './Input';
import { Textarea } from './Textarea';
import { Checkbox, CheckboxGroup } from './Checkbox';
import { RadioGroup } from './Radio';
import { Select } from './Select';

const meta = {
  title: 'Form/Form Layout',
  component: FormLayout,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'Form layout components for building accessible forms with validation.',
      },
    },
  },
} satisfies Meta<typeof FormLayout>;

export default meta;
type Story = StoryObj<typeof meta>;

export const VerticalLayout: Story = {
  render: () => (
    <FormLayout layout="vertical" gap="md" style={{ maxWidth: '500px' }}>
      <FormGroup label="Name" required hint="Your full name">
        <Input placeholder="John Doe" />
      </FormGroup>
      <FormGroup label="Email" required hint="We'll never share your email">
        <Input type="email" placeholder="john@example.com" />
      </FormGroup>
      <FormGroup label="Message">
        <Textarea placeholder="Your message..." minRows={3} />
      </FormGroup>
      <button type="submit">Submit</button>
    </FormLayout>
  ),
};

export const HorizontalLayout: Story = {
  render: () => (
    <FormLayout layout="horizontal" gap="md" style={{ maxWidth: '600px' }}>
      <FormGroup label="First Name" required>
        <Input placeholder="John" />
      </FormGroup>
      <FormGroup label="Last Name" required>
        <Input placeholder="Doe" />
      </FormGroup>
      <FormGroup label="Email" required style={{ flex: '1 0 100%' }}>
        <Input type="email" placeholder="john@example.com" />
      </FormGroup>
      <button type="submit" style={{ flex: '0 0 auto' }}>
        Submit
      </button>
    </FormLayout>
  ),
};

export const InlineLayout: Story = {
  render: () => (
    <FormLayout layout="inline" gap="md">
      <FormGroup label="Search" style={{ flex: 1, minWidth: '200px' }}>
        <Input placeholder="Enter search term..." />
      </FormGroup>
      <button type="submit" style={{ marginTop: '1.5rem' }}>
        Search
      </button>
    </FormLayout>
  ),
};

export const WithValidation: Story = {
  render: () => (
    <FormLayout layout="vertical" gap="md" style={{ maxWidth: '500px' }}>
      <FormGroup label="Email" required hasError error="Please enter a valid email">
        <Input
          type="email"
          placeholder="you@example.com"
          hasError
          error="Please enter a valid email"
        />
      </FormGroup>
      <FormGroup label="Password" required>
        <Input
          type="password"
          placeholder="Enter a strong password"
          hint="At least 8 characters"
        />
      </FormGroup>
      <ValidationMessage
        message="Please correct the errors above before submitting"
        role="alert"
      />
      <button type="submit">Sign Up</button>
    </FormLayout>
  ),
};

export const WithValidationStates: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <ValidationMessage message="Email address is already registered" />
      <ValidationMessage warning="This field will be required in the next step" />
      <ValidationMessage success="Email confirmed successfully" />
    </div>
  ),
};

export const FormSection: Story = {
  render: () => (
    <FormLayout layout="vertical" gap="lg" style={{ maxWidth: '600px' }}>
      <FormSection
        title="Personal Information"
        description="Tell us about yourself"
      >
        <FormGroup label="First Name" required>
          <Input placeholder="John" />
        </FormGroup>
        <FormGroup label="Last Name" required>
          <Input placeholder="Doe" />
        </FormGroup>
        <FormGroup label="Email" required>
          <Input type="email" placeholder="john@example.com" />
        </FormGroup>
      </FormSection>

      <FormSection
        title="Preferences"
        description="Customize your experience"
      >
        <FormGroup label="Theme">
          <RadioGroup
            direction="horizontal"
            items={[
              { value: 'light', label: 'Light' },
              { value: 'dark', label: 'Dark' },
            ]}
            value="light"
          />
        </FormGroup>
        <FormGroup label="Notifications">
          <CheckboxGroup
            direction="vertical"
            items={[
              { value: 'email', label: 'Email notifications' },
              { value: 'sms', label: 'SMS alerts' },
            ]}
            value={['email']}
          />
        </FormGroup>
      </FormSection>

      <button type="submit">Save Settings</button>
    </FormLayout>
  ),
};

export const ComplexForm: Story = {
  render: () => (
    <FormLayout
      layout="vertical"
      gap="lg"
      style={{ maxWidth: '700px' }}
      onSubmit={(e) => {
        e.preventDefault();
        console.log('Form submitted');
      }}
    >
      <h2>Application Form</h2>

      <FormSection title="Contact Information">
        <FormGroup label="Full Name" required>
          <Input placeholder="Jane Smith" />
        </FormGroup>
        <FormGroup label="Email" required hint="We'll use this for notifications">
          <Input type="email" placeholder="jane@example.com" />
        </FormGroup>
        <FormGroup label="Phone">
          <Input type="tel" placeholder="+1 (555) 123-4567" />
        </FormGroup>
      </FormSection>

      <FormSection title="Background">
        <FormGroup label="Experience Level" required>
          <RadioGroup
            direction="vertical"
            items={[
              { value: 'beginner', label: 'Beginner' },
              { value: 'intermediate', label: 'Intermediate' },
              { value: 'advanced', label: 'Advanced' },
            ]}
            value="intermediate"
          />
        </FormGroup>
        <FormGroup label="Skills">
          <CheckboxGroup
            direction="vertical"
            items={[
              { value: 'js', label: 'JavaScript' },
              { value: 'react', label: 'React' },
              { value: 'ts', label: 'TypeScript' },
              { value: 'python', label: 'Python' },
            ]}
            value={['js', 'react', 'ts']}
          />
        </FormGroup>
      </FormSection>

      <FormSection title="Additional Information">
        <FormGroup label="Portfolio URL">
          <Input type="url" placeholder="https://example.com" />
        </FormGroup>
        <FormGroup label="Cover Letter">
          <Textarea
            placeholder="Tell us why you're interested..."
            showCharCount
            maxCharacters={500}
            minRows={4}
          />
        </FormGroup>
        <FormGroup>
          <Checkbox
            label="I agree to the terms and conditions"
            description="Please read our terms before submitting"
          />
        </FormGroup>
      </FormSection>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <button type="submit">Submit Application</button>
        <button type="reset" style={{ background: '#e5e7eb', color: '#1f2937' }}>
          Clear Form
        </button>
      </div>
    </FormLayout>
  ),
};

export const CheckoutForm: Story = {
  render: () => (
    <FormLayout
      layout="vertical"
      gap="lg"
      style={{ maxWidth: '600px' }}
      onSubmit={(e) => {
        e.preventDefault();
        console.log('Checkout submitted');
      }}
    >
      <h2>Checkout</h2>

      <FormSection title="Billing Address">
        <FormGroup label="Full Name" required>
          <Input placeholder="Jane Smith" />
        </FormGroup>
        <FormGroup label="Email" required>
          <Input type="email" placeholder="jane@example.com" />
        </FormGroup>
        <FormGroup label="Address" required>
          <Input placeholder="123 Main St" />
        </FormGroup>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <FormGroup label="City" required style={{ flex: 1 }}>
            <Input placeholder="New York" />
          </FormGroup>
          <FormGroup label="State" required style={{ flex: '0 0 120px' }}>
            <Input placeholder="NY" maxLength={2} />
          </FormGroup>
          <FormGroup label="ZIP" required style={{ flex: '0 0 120px' }}>
            <Input placeholder="10001" />
          </FormGroup>
        </div>
      </FormSection>

      <FormSection title="Shipping">
        <FormGroup>
          <Checkbox
            label="Same as billing address"
            checked
            description="Ship to the address above"
          />
        </FormGroup>
      </FormSection>

      <FormSection title="Payment Method">
        <RadioGroup
          direction="vertical"
          items={[
            {
              value: 'card',
              label: 'Credit/Debit Card',
              description: 'Visa, Mastercard, Amex',
            },
            {
              value: 'paypal',
              label: 'PayPal',
              description: 'Fast and secure',
            },
            {
              value: 'bank',
              label: 'Bank Transfer',
              description: '1-2 business days',
            },
          ]}
          value="card"
        />
      </FormSection>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <button type="submit">Complete Purchase</button>
        <button type="button" style={{ background: '#e5e7eb', color: '#1f2937' }}>
          Continue Shopping
        </button>
      </div>
    </FormLayout>
  ),
};
