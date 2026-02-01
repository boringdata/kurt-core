import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Select } from '../Select';

const mockOptions = [
  { value: '1', label: 'Option 1' },
  { value: '2', label: 'Option 2' },
  { value: '3', label: 'Option 3', disabled: true },
];

describe('Select Component', () => {
  it('renders a select button', () => {
    render(<Select options={mockOptions} />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('renders with label', () => {
    render(<Select options={mockOptions} label="Choose one" id="test-select" />);
    const label = screen.getByText('Choose one');
    expect(label).toBeInTheDocument();
  });

  it('opens dropdown on button click', async () => {
    render(<Select options={mockOptions} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    const listbox = screen.getByRole('listbox');
    expect(listbox).toBeInTheDocument();
  });

  it('displays all options in dropdown', async () => {
    render(<Select options={mockOptions} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    mockOptions.forEach((opt) => {
      const option = screen.getByRole('option', { name: String(opt.label) });
      expect(option).toBeInTheDocument();
    });
  });

  it('selects an option', async () => {
    const handleChange = vi.fn();
    render(<Select options={mockOptions} onChange={handleChange} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    const option = screen.getByRole('option', { name: 'Option 1' });
    fireEvent.click(option);
    expect(handleChange).toHaveBeenCalledWith('1');
  });

  it('displays placeholder text', () => {
    render(<Select options={mockOptions} placeholder="Select..." />);
    expect(screen.getByText('Select...')).toBeInTheDocument();
  });

  it('displays selected value', () => {
    render(<Select options={mockOptions} value="1" />);
    expect(screen.getByText('Option 1')).toBeInTheDocument();
  });

  it('closes dropdown after selection', async () => {
    render(<Select options={mockOptions} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    const option = screen.getByRole('option', { name: 'Option 1' });
    fireEvent.click(option);
    await waitFor(() => {
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });
  });

  it('closes dropdown on escape key', async () => {
    render(<Select options={mockOptions} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    fireEvent.keyDown(button, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('navigates with arrow keys', async () => {
    render(<Select options={mockOptions} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    fireEvent.keyDown(button, { key: 'ArrowDown' });
    fireEvent.keyDown(button, { key: 'ArrowDown' });
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('supports disabled state', () => {
    render(<Select options={mockOptions} disabled />);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('disables individual options', async () => {
    render(<Select options={mockOptions} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    const disabledOption = screen.getByRole('option', { name: 'Option 3' });
    expect(disabledOption).toBeDisabled();
  });

  it('shows hint text', () => {
    render(<Select options={mockOptions} hint="This is a hint" />);
    expect(screen.getByText('This is a hint')).toBeInTheDocument();
  });

  it('shows error message', () => {
    render(<Select options={mockOptions} error="This is an error" hasError={true} />);
    const error = screen.getByRole('alert');
    expect(error).toBeInTheDocument();
    expect(error).toHaveTextContent('This is an error');
  });

  it('shows required indicator', () => {
    render(<Select options={mockOptions} label="Required" required />);
    const requiredIndicator = screen.getByLabelText('required');
    expect(requiredIndicator).toBeInTheDocument();
  });

  it('filters options with search', async () => {
    render(<Select options={mockOptions} searchable={true} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    const searchInput = screen.getByPlaceholderText('Search...');
    await userEvent.type(searchInput, '2');
    await waitFor(() => {
      expect(screen.getByText('Option 2')).toBeInTheDocument();
    });
  });

  it('shows no options message when search has no results', async () => {
    render(<Select options={mockOptions} searchable={true} noOptionsMessage="No match" />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    const searchInput = screen.getByPlaceholderText('Search...');
    await userEvent.type(searchInput, 'xyz');
    await waitFor(() => {
      expect(screen.getByText('No match')).toBeInTheDocument();
    });
  });

  it('supports multi-select', async () => {
    const handleChange = vi.fn();
    render(<Select options={mockOptions} multi onChange={handleChange} />);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    const option1 = screen.getByRole('option', { name: 'Option 1' });
    const option2 = screen.getByRole('option', { name: 'Option 2' });
    fireEvent.click(option1);
    fireEvent.click(button); // Reopen
    fireEvent.click(option2);
    expect(handleChange).toHaveBeenCalled();
  });

  it('applies error styling when hasError is true', () => {
    render(<Select options={mockOptions} error="Error" hasError={true} />);
    const container = screen.getByRole('combobox');
    expect(container).toHaveClass('select--error');
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(<Select options={mockOptions} ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });
});
