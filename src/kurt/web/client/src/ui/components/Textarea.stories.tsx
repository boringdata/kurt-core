import type { Meta, StoryObj } from '@storybook/react';
import { Textarea } from './Textarea';

const meta = {
  title: 'Form/Textarea',
  component: Textarea,
  tags: ['autodocs'],
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component:
          'A textarea component with auto-resize capability, character count, and full accessibility support.',
      },
    },
  },
  argTypes: {
    label: {
      control: 'text',
      description: 'The label for the textarea',
    },
    hint: {
      control: 'text',
      description: 'Hint text displayed below the textarea',
    },
    error: {
      control: 'text',
      description: 'Error message displayed when the field has an error',
    },
    autoResize: {
      control: 'boolean',
      description: 'Whether to auto-resize based on content',
    },
    minRows: {
      control: 'number',
      description: 'Minimum number of rows',
    },
    maxRows: {
      control: 'number',
      description: 'Maximum number of rows',
    },
    showCharCount: {
      control: 'boolean',
      description: 'Whether to show character count',
    },
    maxCharacters: {
      control: 'number',
      description: 'Maximum character limit',
    },
    resizable: {
      control: 'boolean',
      description: 'Whether the textarea is resizable',
    },
    required: {
      control: 'boolean',
      description: 'Whether the field is required',
    },
    disabled: {
      control: 'boolean',
      description: 'Whether the field is disabled',
    },
  },
} satisfies Meta<typeof Textarea>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    label: 'Comments',
    placeholder: 'Enter your comments...',
    minRows: 3,
    autoResize: true,
  },
};

export const WithCharCount: Story = {
  args: {
    label: 'Bio',
    placeholder: 'Tell us about yourself',
    showCharCount: true,
    maxCharacters: 250,
    minRows: 4,
  },
};

export const WithHint: Story = {
  args: {
    label: 'Description',
    placeholder: 'Enter a detailed description',
    hint: 'Provide as much detail as possible to help us understand your needs',
    minRows: 4,
  },
};

export const WithError: Story = {
  args: {
    label: 'Feedback',
    placeholder: 'Your feedback...',
    error: 'This field is required',
    hasError: true,
    required: true,
    minRows: 3,
  },
};

export const Disabled: Story = {
  args: {
    label: 'Read-Only Content',
    value: 'This textarea is disabled and cannot be edited.',
    disabled: true,
    minRows: 3,
  },
};

export const ReadOnly: Story = {
  args: {
    label: 'Policy Content',
    value: 'This is our privacy policy that you can read but not modify.',
    readOnly: true,
    minRows: 5,
  },
};

export const Required: Story = {
  args: {
    label: 'Message',
    placeholder: 'Enter your message',
    required: true,
    minRows: 3,
  },
};

export const FixedSize: Story = {
  args: {
    label: 'Notes',
    placeholder: 'Fixed size textarea',
    autoResize: false,
    resizable: true,
    minRows: 4,
  },
};

export const AutoResizeWithMax: Story = {
  args: {
    label: 'Auto-resizing Text',
    placeholder: 'Type more to see auto-resize in action',
    autoResize: true,
    minRows: 2,
    maxRows: 8,
  },
};

export const WithCharCountAndError: Story = {
  args: {
    label: 'Review',
    placeholder: 'Write a review (max 500 characters)',
    showCharCount: true,
    maxCharacters: 500,
    error: 'Your review is too short',
    hasError: true,
    minRows: 4,
  },
};

export const CompleteForm: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '500px' }}>
      <Textarea
        label="Subject"
        placeholder="What is this about?"
        required
        hint="Keep it brief and descriptive"
        minRows={2}
      />
      <Textarea
        label="Message"
        placeholder="Your message here..."
        required
        hint="Please provide detailed information"
        showCharCount
        maxCharacters={1000}
        minRows={4}
      />
      <Textarea
        label="Additional Notes"
        placeholder="Any additional information?"
        hint="Optional field"
        minRows={3}
      />
      <button style={{ padding: '0.625rem 1rem', alignSelf: 'flex-start' }}>
        Submit
      </button>
    </div>
  ),
};
