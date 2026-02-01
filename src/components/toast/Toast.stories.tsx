import type { Meta, StoryObj } from '@storybook/react';
import ToastContainer from './ToastContainer';
import { useToast } from '../../hooks/useToastContext';

const meta = {
  title: 'Feedback/Toast',
  component: ToastContainer,
  parameters: {
    layout: 'fullscreen',
  },
} satisfies Meta<typeof ToastContainer>;

export default meta;
type Story = StoryObj<typeof meta>;

function ToastShowcase() {
  const toast = useToast();

  return (
    <div style={{ padding: '40px' }}>
      <h1>Toast Notifications</h1>

      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '20px' }}>
        <button
          onClick={() => toast.success('Success message!')}
          style={{
            padding: '8px 16px',
            backgroundColor: '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Show Success
        </button>

        <button
          onClick={() => toast.error('Error message!')}
          style={{
            padding: '8px 16px',
            backgroundColor: '#ef4444',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Show Error
        </button>

        <button
          onClick={() => toast.warning('Warning message!')}
          style={{
            padding: '8px 16px',
            backgroundColor: '#f59e0b',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Show Warning
        </button>

        <button
          onClick={() => toast.info('Info message!')}
          style={{
            padding: '8px 16px',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Show Info
        </button>

        <button
          onClick={() =>
            toast.success('Undo action?', 0, {
              label: 'Undo',
              onClick: () => alert('Undo clicked!'),
            })
          }
          style={{
            padding: '8px 16px',
            backgroundColor: '#8b5cf6',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Show with Action
        </button>
      </div>

      <p style={{ marginTop: '40px', color: '#666' }}>
        Click buttons above to see toast notifications. They auto-dismiss after 5 seconds (except
        with actions).
      </p>
    </div>
  );
}

export const Default: Story = {
  render: () => (
    <ToastContainer>
      <ToastShowcase />
    </ToastContainer>
  ),
};

export const TopLeft: Story = {
  render: () => (
    <ToastContainer position="top-left">
      <button
        onClick={() => {
          const toast = useToast();
          toast.info('Top left notification');
        }}
        style={{
          padding: '8px 16px',
          backgroundColor: '#3b82f6',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          position: 'absolute',
          top: '20px',
          left: '20px',
        }}
      >
        Show Top Left
      </button>
    </ToastContainer>
  ),
};

export const TopRight: Story = {
  render: () => (
    <ToastContainer position="top-right">
      <button
        onClick={() => {
          const toast = useToast();
          toast.info('Top right notification');
        }}
        style={{
          padding: '8px 16px',
          backgroundColor: '#3b82f6',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          position: 'absolute',
          top: '20px',
          right: '20px',
        }}
      >
        Show Top Right
      </button>
    </ToastContainer>
  ),
};

export const Variants: Story = {
  render: () => (
    <ToastContainer>
      <ToastShowcase />
    </ToastContainer>
  ),
};
