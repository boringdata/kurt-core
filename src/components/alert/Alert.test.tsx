/**
 * Alert Component Tests
 * Verifies dismissible alerts, icons, action buttons, variants, and accessibility
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Alert from './Alert';

describe('Alert Component', () => {
  it('should render alert with title and description', () => {
    render(
      <Alert
        title="Alert Title"
        description="Alert description text"
      />
    );

    expect(screen.getByText('Alert Title')).toBeInTheDocument();
    expect(screen.getByText('Alert description text')).toBeInTheDocument();
  });

  it('should render children instead of description', () => {
    render(
      <Alert title="Alert Title">
        <p>Custom children content</p>
      </Alert>
    );

    expect(screen.getByText('Custom children content')).toBeInTheDocument();
  });

  it('should apply variant CSS class', () => {
    const { container } = render(
      <Alert title="Error Alert" variant="error" />
    );

    expect(container.querySelector('.alert--error')).toBeInTheDocument();
  });

  it('should display variant icon', () => {
    const { container } = render(
      <Alert title="Success" variant="success" />
    );

    const icon = container.querySelector('.alert__icon');
    expect(icon).toHaveTextContent('✓');
  });

  it('should use custom icon when provided', () => {
    const { container } = render(
      <Alert title="Custom Icon" icon="🎉" />
    );

    const icon = container.querySelector('.alert__icon');
    expect(icon).toHaveTextContent('🎉');
  });

  it('should show close button when dismissible', () => {
    render(
      <Alert title="Dismissible" dismissible={true} />
    );

    expect(screen.getByLabelText('Dismiss alert')).toBeInTheDocument();
  });

  it('should not show close button when not dismissible', () => {
    render(
      <Alert title="Not Dismissible" dismissible={false} />
    );

    expect(screen.queryByLabelText('Dismiss alert')).not.toBeInTheDocument();
  });

  it('should dismiss alert on close button click', () => {
    const mockOnDismiss = vi.fn();
    const { container } = render(
      <Alert
        title="Dismissible Alert"
        dismissible={true}
        onDismiss={mockOnDismiss}
      />
    );

    const closeButton = screen.getByLabelText('Dismiss alert');
    fireEvent.click(closeButton);

    expect(mockOnDismiss).toHaveBeenCalled();
    expect(container.querySelector('.alert')).not.toBeInTheDocument();
  });

  it('should render action buttons', () => {
    const actions = [
      { label: 'Accept', onClick: vi.fn() },
      { label: 'Reject', onClick: vi.fn() },
    ];

    render(
      <Alert
        title="Actions"
        actions={actions}
      />
    );

    expect(screen.getByRole('button', { name: 'Accept' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
  });

  it('should call action onClick when clicked', () => {
    const mockAction = vi.fn();
    const actions = [
      { label: 'Click Me', onClick: mockAction },
    ];

    render(
      <Alert
        title="Action Test"
        actions={actions}
      />
    );

    const actionButton = screen.getByRole('button', { name: 'Click Me' });
    fireEvent.click(actionButton);

    expect(mockAction).toHaveBeenCalled();
  });

  it('should have proper ARIA attributes for accessibility', () => {
    const { container } = render(
      <Alert title="Accessible Alert" />
    );

    const alert = container.querySelector('[role="alert"]');
    expect(alert).toHaveAttribute('aria-live', 'assertive');
  });

  it('should handle all variants', () => {
    const variants: Array<'success' | 'error' | 'warning' | 'info'> = [
      'success',
      'error',
      'warning',
      'info',
    ];

    variants.forEach((variant) => {
      const { container } = render(
        <Alert
          title={`${variant} alert`}
          variant={variant}
        />
      );

      expect(container.querySelector(`.alert--${variant}`)).toBeInTheDocument();
    });
  });

  it('should apply custom className', () => {
    const { container } = render(
      <Alert
        title="Custom Class"
        className="custom-class"
      />
    );

    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });
});
