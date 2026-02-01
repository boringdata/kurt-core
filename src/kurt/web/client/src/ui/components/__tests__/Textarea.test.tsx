import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Textarea } from '../Textarea';

describe('Textarea Component', () => {
  it('renders a textarea', () => {
    render(<Textarea />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeInTheDocument();
  });

  it('renders with label', () => {
    render(<Textarea label="Comments" id="comments" />);
    const label = screen.getByText('Comments');
    expect(label).toBeInTheDocument();
    expect(label).toHaveAttribute('for', 'comments');
  });

  it('renders placeholder', () => {
    render(<Textarea placeholder="Enter your message..." />);
    const textarea = screen.getByPlaceholderText('Enter your message...');
    expect(textarea).toBeInTheDocument();
  });

  it('renders hint text', () => {
    render(<Textarea hint="Help text" />);
    expect(screen.getByText('Help text')).toBeInTheDocument();
  });

  it('renders error message', () => {
    render(<Textarea error="This is required" hasError={true} />);
    const error = screen.getByRole('alert');
    expect(error).toBeInTheDocument();
    expect(error).toHaveTextContent('This is required');
  });

  it('renders character count', () => {
    render(<Textarea showCharCount maxCharacters={100} value="test" />);
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('handles input change', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Textarea onChange={handleChange} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'test value');

    expect(handleChange).toHaveBeenCalled();
    expect(textarea).toHaveValue('test value');
  });

  it('supports disabled state', () => {
    render(<Textarea disabled label="Disabled" />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeDisabled();
  });

  it('supports readonly state', () => {
    render(<Textarea readOnly value="Read only" />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute('readOnly');
  });

  it('supports required attribute', () => {
    render(<Textarea required />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveAttribute('required');
  });

  it('shows required indicator', () => {
    render(<Textarea label="Required" required />);
    const requiredIndicator = screen.getByLabelText('required');
    expect(requiredIndicator).toBeInTheDocument();
  });

  it('applies error class when hasError is true', () => {
    render(<Textarea error="Error" hasError={true} />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveClass('textarea--error');
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(<Textarea ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });

  it('applies custom className', () => {
    render(<Textarea className="custom-class" />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveClass('custom-class');
  });

  it('respects maxLength attribute', () => {
    render(<Textarea maxCharacters={50} />);
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea).toHaveAttribute('maxLength', '50');
  });

  it('displays character count with warning at 90%', () => {
    const { rerender } = render(
      <Textarea showCharCount maxCharacters={100} value="a" />
    );
    expect(screen.getByText('1')).toBeInTheDocument();

    rerender(<Textarea showCharCount maxCharacters={100} value={'a'.repeat(91)} />);
    const charCount = screen.getByText('91');
    expect(charCount.parentElement).toHaveClass('textarea-charcount--warning');
  });
});
