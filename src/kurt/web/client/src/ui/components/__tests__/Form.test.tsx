import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  FormGroup,
  FormLayout,
  ValidationMessage,
  FormSection,
} from '../Form';

describe('FormGroup Component', () => {
  it('renders form group', () => {
    render(<FormGroup><input /></FormGroup>);
    const wrapper = screen.getByRole('textbox').parentElement;
    expect(wrapper).toHaveClass('form-group-content');
  });

  it('renders label', () => {
    render(
      <FormGroup label="Name">
        <input />
      </FormGroup>
    );
    expect(screen.getByText('Name')).toBeInTheDocument();
  });

  it('renders hint', () => {
    render(
      <FormGroup hint="This is a hint">
        <input />
      </FormGroup>
    );
    expect(screen.getByText('This is a hint')).toBeInTheDocument();
  });

  it('renders error message', () => {
    render(
      <FormGroup error="This field is required" hasError={true}>
        <input />
      </FormGroup>
    );
    const error = screen.getByRole('alert');
    expect(error).toBeInTheDocument();
    expect(error).toHaveTextContent('This field is required');
  });

  it('renders required indicator', () => {
    render(
      <FormGroup label="Required Field" required>
        <input />
      </FormGroup>
    );
    const requiredIndicator = screen.getByLabelText('required');
    expect(requiredIndicator).toBeInTheDocument();
  });

  it('applies error class when hasError is true', () => {
    const { container } = render(
      <FormGroup error="Error" hasError={true}>
        <input />
      </FormGroup>
    );
    const group = container.querySelector('.form-group');
    expect(group).toHaveClass('form-group--error');
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(
      <FormGroup ref={ref}>
        <input />
      </FormGroup>
    );
    expect(ref).toHaveBeenCalled();
  });

  it('does not render error when hasError is false', () => {
    render(
      <FormGroup error="Error" hasError={false}>
        <input />
      </FormGroup>
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('FormLayout Component', () => {
  it('renders form', () => {
    const { container } = render(
      <FormLayout>
        <input />
      </FormLayout>
    );
    const form = container.querySelector('form');
    expect(form).toBeInTheDocument();
  });

  it('supports vertical layout', () => {
    const { container } = render(
      <FormLayout layout="vertical">
        <input />
      </FormLayout>
    );
    const form = container.querySelector('form');
    expect(form).toHaveClass('form-layout--vertical');
  });

  it('supports horizontal layout', () => {
    const { container } = render(
      <FormLayout layout="horizontal">
        <input />
      </FormLayout>
    );
    const form = container.querySelector('form');
    expect(form).toHaveClass('form-layout--horizontal');
  });

  it('supports inline layout', () => {
    const { container } = render(
      <FormLayout layout="inline">
        <input />
      </FormLayout>
    );
    const form = container.querySelector('form');
    expect(form).toHaveClass('form-layout--inline');
  });

  it('applies gap classes', () => {
    const { container: container1 } = render(
      <FormLayout gap="sm">
        <input />
      </FormLayout>
    );
    expect(container1.querySelector('form')).toHaveClass('form-layout--gap-sm');

    const { container: container2 } = render(
      <FormLayout gap="md">
        <input />
      </FormLayout>
    );
    expect(container2.querySelector('form')).toHaveClass('form-layout--gap-md');

    const { container: container3 } = render(
      <FormLayout gap="lg">
        <input />
      </FormLayout>
    );
    expect(container3.querySelector('form')).toHaveClass('form-layout--gap-lg');
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(
      <FormLayout ref={ref}>
        <input />
      </FormLayout>
    );
    expect(ref).toHaveBeenCalled();
  });

  it('handles form submit', () => {
    const handleSubmit = vi.fn((e) => e.preventDefault());
    render(
      <FormLayout onSubmit={handleSubmit}>
        <button type="submit">Submit</button>
      </FormLayout>
    );
    const button = screen.getByText('Submit');
    button.click();
    expect(handleSubmit).toHaveBeenCalled();
  });
});

describe('ValidationMessage Component', () => {
  it('renders error message', () => {
    render(<ValidationMessage message="Error occurred" />);
    const message = screen.getByText('Error occurred');
    expect(message).toBeInTheDocument();
    expect(message.parentElement).toHaveClass('validation-message--error');
  });

  it('renders warning message', () => {
    render(<ValidationMessage warning="Warning text" />);
    const message = screen.getByText('Warning text');
    expect(message).toBeInTheDocument();
    expect(message.parentElement).toHaveClass('validation-message--warning');
  });

  it('renders success message', () => {
    render(<ValidationMessage success="Success message" />);
    const message = screen.getByText('Success message');
    expect(message).toBeInTheDocument();
    expect(message.parentElement).toHaveClass('validation-message--success');
  });

  it('does not render when no message provided', () => {
    const { container } = render(<ValidationMessage />);
    expect(container.firstChild).toBeNull();
  });

  it('renders with role alert for error', () => {
    render(<ValidationMessage message="Error" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders with role status for warning', () => {
    render(<ValidationMessage warning="Warning" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders with role status for success', () => {
    render(<ValidationMessage success="Success" />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(<ValidationMessage message="Test" ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });
});

describe('FormSection Component', () => {
  it('renders form section', () => {
    const { container } = render(
      <FormSection>
        <input />
      </FormSection>
    );
    const section = container.querySelector('.form-section');
    expect(section).toBeInTheDocument();
  });

  it('renders title', () => {
    render(
      <FormSection title="Personal Information">
        <input />
      </FormSection>
    );
    expect(screen.getByText('Personal Information')).toBeInTheDocument();
  });

  it('renders description', () => {
    render(
      <FormSection description="Enter your details">
        <input />
      </FormSection>
    );
    expect(screen.getByText('Enter your details')).toBeInTheDocument();
  });

  it('renders title with h3 tag', () => {
    render(
      <FormSection title="Section Title">
        <input />
      </FormSection>
    );
    const h3 = screen.getByText('Section Title').tagName;
    expect(h3).toBe('H3');
  });

  it('renders content', () => {
    render(
      <FormSection>
        <input data-testid="test-input" />
      </FormSection>
    );
    expect(screen.getByTestId('test-input')).toBeInTheDocument();
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(<FormSection ref={ref}><input /></FormSection>);
    expect(ref).toHaveBeenCalled();
  });
});
