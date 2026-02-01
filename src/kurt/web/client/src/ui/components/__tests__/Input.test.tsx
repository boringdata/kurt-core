import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from '../Input';

describe('Input Component', () => {
  it('renders a basic text input', () => {
    render(<Input />);
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'text');
  });

  it('renders with label', () => {
    render(<Input label="Email" id="email-input" />);
    const label = screen.getByText('Email');
    expect(label).toBeInTheDocument();
    expect(label).toHaveAttribute('for', 'email-input');
  });

  it('renders required indicator', () => {
    render(<Input label="Required Field" required />);
    const requiredIndicator = screen.getByLabelText('required');
    expect(requiredIndicator).toBeInTheDocument();
    expect(requiredIndicator).toHaveTextContent('*');
  });

  it('renders hint text', () => {
    render(<Input hint="Enter a valid email address" />);
    const hint = screen.getByText('Enter a valid email address');
    expect(hint).toBeInTheDocument();
  });

  it('renders error message', () => {
    render(<Input error="This field is required" hasError={true} />);
    const error = screen.getByRole('alert');
    expect(error).toBeInTheDocument();
    expect(error).toHaveTextContent('This field is required');
  });

  it('renders different input types', () => {
    const types = ['text', 'password', 'email', 'number', 'tel', 'url'];

    types.forEach((type) => {
      const { unmount } = render(<Input type={type as any} />);
      const input = screen.getByRole('textbox');
      expect(input).toHaveAttribute('type', type);
      unmount();
    });
  });

  it('supports placeholder text', () => {
    render(<Input placeholder="Enter your name" />);
    const input = screen.getByPlaceholderText('Enter your name');
    expect(input).toBeInTheDocument();
  });

  it('supports disabled state', () => {
    render(<Input disabled label="Disabled Input" />);
    const input = screen.getByRole('textbox');
    expect(input).toBeDisabled();
  });

  it('supports readonly state', () => {
    render(<Input readOnly defaultValue="Read only value" />);
    const input = screen.getByDisplayValue('Read only value');
    expect(input).toHaveAttribute('readOnly');
  });

  it('supports required attribute', () => {
    render(<Input required />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('required');
  });

  it('handles input change events', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Input onChange={handleChange} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'test value');

    expect(handleChange).toHaveBeenCalled();
    expect(input).toHaveValue('test value');
  });

  it('handles focus and blur events', async () => {
    const handleFocus = vi.fn();
    const handleBlur = vi.fn();
    render(<Input onFocus={handleFocus} onBlur={handleBlur} />);

    const input = screen.getByRole('textbox');
    await userEvent.setup().click(input);
    expect(handleFocus).toHaveBeenCalled();

    await userEvent.setup().click(document.body);
    expect(handleBlur).toHaveBeenCalled();
  });

  it('applies correct accessibility attributes', () => {
    render(
      <Input
        label="Email Address"
        hint="example@domain.com"
        error="Invalid email"
        hasError={true}
        required={true}
        id="email"
      />
    );

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-required', 'true');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', expect.stringContaining('email-hint'));
  });

  it('generates unique IDs when not provided', () => {
    const { rerender } = render(<Input hint="hint 1" />);
    const hint1 = screen.getByText('hint 1');
    const input1 = screen.getByRole('textbox');
    const firstDescribedBy = input1.getAttribute('aria-describedby');

    rerender(<Input hint="hint 2" />);
    const hint2 = screen.getByText('hint 2');
    const input2 = screen.getByRole('textbox');
    const secondDescribedBy = input2.getAttribute('aria-describedby');

    // IDs should be different
    expect(firstDescribedBy).not.toBe(secondDescribedBy);
  });

  it('applies custom className', () => {
    render(<Input className="custom-class" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveClass('custom-class');
  });

  it('applies custom label className', () => {
    render(<Input label="Test" labelClassName="custom-label" />);
    const label = screen.getByText('Test');
    expect(label).toHaveClass('custom-label');
  });

  it('applies custom hint className', () => {
    render(<Input hint="Test hint" hintClassName="custom-hint" />);
    const hint = screen.getByText('Test hint');
    expect(hint).toHaveClass('custom-hint');
  });

  it('applies custom error className', () => {
    render(<Input error="Test error" hasError={true} errorClassName="custom-error" />);
    const error = screen.getByRole('alert');
    expect(error).toHaveClass('custom-error');
  });

  it('applies error class only when hasError is true', () => {
    const { rerender } = render(<Input error="Error message" hasError={false} />);
    let input = screen.getByRole('textbox');
    expect(input).not.toHaveClass('input--error');

    rerender(<Input error="Error message" hasError={true} />);
    input = screen.getByRole('textbox');
    expect(input).toHaveClass('input--error');
  });

  it('forwards ref correctly', () => {
    const ref = vi.fn();
    render(<Input ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });

  it('supports all standard HTML input attributes', () => {
    render(
      <Input
        maxLength={50}
        minLength={5}
        pattern="[A-Z]+"
        autoComplete="email"
      />
    );
    const input = screen.getByRole('textbox') as HTMLInputElement;
    expect(input).toHaveAttribute('maxLength', '50');
    expect(input).toHaveAttribute('minLength', '5');
    expect(input).toHaveAttribute('pattern', '[A-Z]+');
    expect(input).toHaveAttribute('autoComplete', 'email');
  });
});
