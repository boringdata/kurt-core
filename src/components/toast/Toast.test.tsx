/**
 * Toast Component Tests
 * Verifies auto-dismiss, stacking, variants, and accessibility
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Toast from './Toast';

describe('Toast Component', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('should render toast with message', () => {
    render(
      <Toast
        id="test-toast"
        message="Test message"
        onRemove={() => {}}
      />
    );

    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('should display variant icon', () => {
    const { container } = render(
      <Toast
        id="test-toast"
        message="Success"
        variant="success"
        onRemove={() => {}}
      />
    );

    const icon = container.querySelector('.toast__icon');
    expect(icon).toHaveTextContent('✓');
  });

  it('should apply variant CSS class', () => {
    const { container } = render(
      <Toast
        id="test-toast"
        message="Error"
        variant="error"
        onRemove={() => {}}
      />
    );

    expect(container.querySelector('.toast--error')).toBeInTheDocument();
  });

  it('should auto-dismiss after duration', async () => {
    const mockOnRemove = vi.fn();
    render(
      <Toast
        id="test-toast"
        message="Auto-dismiss"
        duration={3000}
        onRemove={mockOnRemove}
      />
    );

    vi.advanceTimersByTime(3000);
    vi.advanceTimersByTime(300); // Animation time

    await waitFor(() => {
      expect(mockOnRemove).toHaveBeenCalled();
    });
  });

  it('should not auto-dismiss when duration is 0', () => {
    const mockOnRemove = vi.fn();
    render(
      <Toast
        id="test-toast"
        message="No auto-dismiss"
        duration={0}
        onRemove={mockOnRemove}
      />
    );

    vi.advanceTimersByTime(10000);

    expect(mockOnRemove).not.toHaveBeenCalled();
  });

  it('should close on close button click', async () => {
    const mockOnRemove = vi.fn();
    render(
      <Toast
        id="test-toast"
        message="Test"
        onRemove={mockOnRemove}
      />
    );

    const closeButton = screen.getByLabelText('Close notification');
    fireEvent.click(closeButton);

    vi.advanceTimersByTime(300); // Animation time

    await waitFor(() => {
      expect(mockOnRemove).toHaveBeenCalled();
    });
  });

  it('should render action button when provided', () => {
    const mockAction = vi.fn();
    render(
      <Toast
        id="test-toast"
        message="Test"
        action={{ label: 'Undo', onClick: mockAction }}
        onRemove={() => {}}
      />
    );

    const actionButton = screen.getByRole('button', { name: 'Undo' });
    expect(actionButton).toBeInTheDocument();
  });

  it('should call action onClick and close on action button click', async () => {
    const mockAction = vi.fn();
    const mockOnRemove = vi.fn();
    render(
      <Toast
        id="test-toast"
        message="Test"
        action={{ label: 'Undo', onClick: mockAction }}
        onRemove={mockOnRemove}
      />
    );

    const actionButton = screen.getByRole('button', { name: 'Undo' });
    fireEvent.click(actionButton);

    expect(mockAction).toHaveBeenCalled();

    vi.advanceTimersByTime(300); // Animation time

    await waitFor(() => {
      expect(mockOnRemove).toHaveBeenCalled();
    });
  });

  it('should have proper ARIA attributes for accessibility', () => {
    const { container } = render(
      <Toast
        id="test-toast"
        message="Accessible toast"
        variant="success"
        onRemove={() => {}}
      />
    );

    const toast = container.querySelector('[role="status"]');
    expect(toast).toHaveAttribute('aria-live', 'polite');
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
        <Toast
          id={`test-${variant}`}
          message={`${variant} message`}
          variant={variant}
          onRemove={() => {}}
        />
      );

      expect(container.querySelector(`.toast--${variant}`)).toBeInTheDocument();
    });
  });
});
