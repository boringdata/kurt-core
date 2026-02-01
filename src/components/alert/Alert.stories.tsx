import type { Meta, StoryObj } from '@storybook/react';
import Alert from './Alert';

const meta = {
  title: 'Feedback/Alert',
  component: Alert,
} satisfies Meta<typeof Alert>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Success: Story = {
  args: {
    title: 'Success!',
    description: 'Your operation completed successfully.',
    variant: 'success',
  },
};

export const Error: Story = {
  args: {
    title: 'Error',
    description: 'Something went wrong. Please try again.',
    variant: 'error',
  },
};

export const Warning: Story = {
  args: {
    title: 'Warning',
    description: 'Please review this before proceeding.',
    variant: 'warning',
  },
};

export const Info: Story = {
  args: {
    title: 'Information',
    description: 'Here is some useful information for you.',
    variant: 'info',
  },
};

export const Dismissible: Story = {
  args: {
    title: 'Dismissible Alert',
    description: 'You can close this alert by clicking the X button.',
    variant: 'info',
    dismissible: true,
  },
};

export const WithActions: Story = {
  args: {
    title: 'Action Required',
    description: 'Please confirm your action.',
    variant: 'warning',
    actions: [
      { label: 'Accept', onClick: () => alert('Accepted!') },
      { label: 'Reject', onClick: () => alert('Rejected!') },
    ],
  },
};

export const CustomIcon: Story = {
  args: {
    title: 'Custom Icon',
    description: 'This alert uses a custom icon.',
    variant: 'success',
    icon: '🎉',
  },
};

export const DescriptionOnly: Story = {
  args: {
    description: 'This alert has only a description, no title.',
    variant: 'info',
  },
};

export const WithChildren: Story = {
  args: {
    title: 'Complex Content',
    variant: 'info',
    children: (
      <div>
        <p>You can add any React elements as children.</p>
        <ul style={{ marginTop: '8px' }}>
          <li>Item 1</li>
          <li>Item 2</li>
          <li>Item 3</li>
        </ul>
      </div>
    ),
  },
};

export const AllVariants: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '20px' }}>
      <Alert title="Success" description="Everything is working fine." variant="success" />
      <Alert title="Error" description="An error has occurred." variant="error" />
      <Alert title="Warning" description="Please be careful." variant="warning" />
      <Alert title="Info" description="Here is some information." variant="info" />
    </div>
  ),
};

export const DismissibleVariants: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '20px' }}>
      <Alert
        title="Success"
        description="Everything is working fine."
        variant="success"
        dismissible={true}
      />
      <Alert
        title="Error"
        description="An error has occurred."
        variant="error"
        dismissible={true}
      />
      <Alert
        title="Warning"
        description="Please be careful."
        variant="warning"
        dismissible={true}
      />
      <Alert
        title="Info"
        description="Here is some information."
        variant="info"
        dismissible={true}
      />
    </div>
  ),
};
