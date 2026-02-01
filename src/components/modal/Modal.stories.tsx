import type { Meta, StoryObj } from '@storybook/react';
import React, { useState } from 'react';
import Modal from './Modal';

const meta = {
  title: 'Overlay/Modal',
  component: Modal,
} satisfies Meta<typeof Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

function ModalDemoWrapper({
  title,
  size,
  showCloseButton,
  closeOnBackdropClick,
  closeOnEscapeKey,
}: any) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ padding: '20px' }}>
      <button
        onClick={() => setIsOpen(true)}
        style={{
          padding: '8px 16px',
          backgroundColor: '#3b82f6',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
        }}
      >
        Open Modal
      </button>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title={title}
        size={size}
        showCloseButton={showCloseButton}
        closeOnBackdropClick={closeOnBackdropClick}
        closeOnEscapeKey={closeOnEscapeKey}
      >
        <p style={{ marginBottom: '16px' }}>
          This is the modal content. You can put any React elements here.
        </p>
        <p>
          {closeOnEscapeKey
            ? 'Press Escape to close this modal.'
            : 'You cannot close this modal with Escape.'}
        </p>
      </Modal>
    </div>
  );
}

function ModalWithFooter() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ padding: '20px' }}>
      <button
        onClick={() => setIsOpen(true)}
        style={{
          padding: '8px 16px',
          backgroundColor: '#3b82f6',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
        }}
      >
        Open Modal with Footer
      </button>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Confirm Action"
        footer={
          <div style={{ display: 'flex', gap: '12px', width: '100%' }}>
            <button
              onClick={() => setIsOpen(false)}
              style={{
                flex: 1,
                padding: '8px 16px',
                backgroundColor: '#e5e7eb',
                color: '#1f2937',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              Cancel
            </button>
            <button
              onClick={() => {
                alert('Confirmed!');
                setIsOpen(false);
              }}
              style={{
                flex: 1,
                padding: '8px 16px',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              Confirm
            </button>
          </div>
        }
      >
        <p>Are you sure you want to proceed with this action?</p>
      </Modal>
    </div>
  );
}

function ModalWithLongContent() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ padding: '20px' }}>
      <button
        onClick={() => setIsOpen(true)}
        style={{
          padding: '8px 16px',
          backgroundColor: '#3b82f6',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
        }}
      >
        Open Modal with Long Content
      </button>

      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="Terms & Conditions">
        <div>
          <p>
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
            incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud
            exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
          </p>
          <p>
            Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat
            nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui
            officia deserunt mollit anim id est laborum.
          </p>
          <p>
            Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque
            laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi
            architecto beatae vitae dicta sunt explicabo.
          </p>
          <p>
            Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia
            consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.
          </p>
        </div>
      </Modal>
    </div>
  );
}

export const Default: Story = {
  render: () => <ModalDemoWrapper title="Modal Title" />,
};

export const Small: Story = {
  render: () => <ModalDemoWrapper title="Small Modal" size="small" />,
};

export const Large: Story = {
  render: () => <ModalDemoWrapper title="Large Modal" size="large" />,
};

export const NoCloseButton: Story = {
  render: () => <ModalDemoWrapper title="No Close Button" showCloseButton={false} />,
};

export const NoBackdropClick: Story = {
  render: () => <ModalDemoWrapper title="Click-Trap Modal" closeOnBackdropClick={false} />,
};

export const NoEscapeKey: Story = {
  render: () => <ModalDemoWrapper title="Escape-Disabled Modal" closeOnEscapeKey={false} />,
};

export const WithFooter: Story = {
  render: () => <ModalWithFooter />,
};

export const LongContent: Story = {
  render: () => <ModalWithLongContent />,
};

export const FocusTrap: Story = {
  render: () => (
    <div style={{ padding: '20px' }}>
      <p style={{ marginBottom: '16px' }}>
        <strong>Note:</strong> Open the modal and use Tab to navigate. Focus is trapped within the
        modal.
      </p>
      <ModalDemoWrapper title="Focus Trap Demo" />
    </div>
  ),
};
