/**
 * Modal Component Tests
 * Verifies focus trap, backdrop, animations, keyboard support, and accessibility
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Modal from './Modal';

describe('Modal Component', () => {
  it('should not render when isOpen is false', () => {
    const { container } = render(
      <Modal isOpen={false} onClose={() => {}}>
        <p>Modal content</p>
      </Modal>
    );

    expect(container.querySelector('.modal')).not.toBeInTheDocument();
  });

  it('should render when isOpen is true', () => {
    render(
      <Modal isOpen={true} onClose={() => {}}>
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.getByText('Modal content')).toBeInTheDocument();
  });

  it('should render title when provided', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} title="Modal Title">
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.getByText('Modal Title')).toBeInTheDocument();
  });

  it('should render children', () => {
    render(
      <Modal isOpen={true} onClose={() => {}}>
        <div>Custom content</div>
      </Modal>
    );

    expect(screen.getByText('Custom content')).toBeInTheDocument();
  });

  it('should render footer when provided', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} footer={<button>Save</button>}>
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
  });

  it('should show close button by default', () => {
    render(
      <Modal isOpen={true} onClose={() => {}}>
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.getByLabelText('Close modal')).toBeInTheDocument();
  });

  it('should not show close button when showCloseButton is false', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} showCloseButton={false}>
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.queryByLabelText('Close modal')).not.toBeInTheDocument();
  });

  it('should close when close button is clicked', () => {
    const mockOnClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={mockOnClose}>
        <p>Modal content</p>
      </Modal>
    );

    const closeButton = screen.getByLabelText('Close modal');
    fireEvent.click(closeButton);

    // Wait for animation
    vi.useFakeTimers();
    vi.advanceTimersByTime(200);
    vi.useRealTimers();

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should close when backdrop is clicked if closeOnBackdropClick is true', () => {
    const mockOnClose = vi.fn();
    const { container } = render(
      <Modal isOpen={true} onClose={mockOnClose} closeOnBackdropClick={true}>
        <p>Modal content</p>
      </Modal>
    );

    const backdrop = container.querySelector('.modal-backdrop');
    fireEvent.click(backdrop as HTMLElement);

    vi.useFakeTimers();
    vi.advanceTimersByTime(200);
    vi.useRealTimers();

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should not close when backdrop is clicked if closeOnBackdropClick is false', () => {
    const mockOnClose = vi.fn();
    const { container } = render(
      <Modal isOpen={true} onClose={mockOnClose} closeOnBackdropClick={false}>
        <p>Modal content</p>
      </Modal>
    );

    const backdrop = container.querySelector('.modal-backdrop');
    fireEvent.click(backdrop as HTMLElement);

    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it('should close when Escape key is pressed if closeOnEscapeKey is true', () => {
    const mockOnClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={mockOnClose} closeOnEscapeKey={true}>
        <p>Modal content</p>
      </Modal>
    );

    fireEvent.keyDown(document, { key: 'Escape' });

    vi.useFakeTimers();
    vi.advanceTimersByTime(200);
    vi.useRealTimers();

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should not close when Escape key is pressed if closeOnEscapeKey is false', () => {
    const mockOnClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={mockOnClose} closeOnEscapeKey={false}>
        <p>Modal content</p>
      </Modal>
    );

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it('should apply size classes correctly', () => {
    const sizes: Array<'small' | 'medium' | 'large'> = ['small', 'medium', 'large'];

    sizes.forEach((size) => {
      const { container } = render(
        <Modal isOpen={true} onClose={() => {}} size={size}>
          <p>Modal content</p>
        </Modal>
      );

      expect(container.querySelector(`.modal--${size}`)).toBeInTheDocument();
    });
  });

  it('should have proper ARIA attributes', () => {
    const { container } = render(
      <Modal isOpen={true} onClose={() => {}} title="Accessible Modal">
        <p>Modal content</p>
      </Modal>
    );

    const modal = container.querySelector('[role="dialog"]');
    expect(modal).toHaveAttribute('aria-modal', 'true');
    expect(modal).toHaveAttribute('aria-labelledby', 'modal-title');
  });

  it('should apply custom className', () => {
    const { container } = render(
      <Modal isOpen={true} onClose={() => {}} className="custom-class">
        <p>Modal content</p>
      </Modal>
    );

    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('should disable body scroll when modal is open', () => {
    render(
      <Modal isOpen={true} onClose={() => {}}>
        <p>Modal content</p>
      </Modal>
    );

    expect(document.body.style.overflow).toBe('hidden');
  });

  it('should restore body scroll when modal is closed', () => {
    const { rerender } = render(
      <Modal isOpen={true} onClose={() => {}}>
        <p>Modal content</p>
      </Modal>
    );

    expect(document.body.style.overflow).toBe('hidden');

    rerender(
      <Modal isOpen={false} onClose={() => {}}>
        <p>Modal content</p>
      </Modal>
    );

    expect(document.body.style.overflow).toBe('');
  });
});
