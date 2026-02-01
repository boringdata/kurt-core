import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Checkbox, CheckboxGroup } from '../Checkbox';

describe('Checkbox Component', () => {
  it('renders a checkbox', () => {
    render(<Checkbox />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeInTheDocument();
  });

  it('renders with label', () => {
    render(<Checkbox label="Accept terms" />);
    const label = screen.getByText('Accept terms');
    expect(label).toBeInTheDocument();
  });

  it('renders with description', () => {
    render(
      <Checkbox label="Newsletter" description="Get weekly updates" />
    );
    expect(screen.getByText('Get weekly updates')).toBeInTheDocument();
  });

  it('toggles checked state', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Checkbox label="Option" onChange={handleChange} />);

    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);

    expect(handleChange).toHaveBeenCalled();
    expect(checkbox).toBeChecked();
  });

  it('supports disabled state', () => {
    render(<Checkbox label="Disabled" disabled />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeDisabled();
  });

  it('supports indeterminate state', () => {
    const { rerender } = render(<Checkbox indeterminate={false} />);
    let checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.indeterminate).toBe(false);

    rerender(<Checkbox indeterminate={true} />);
    checkbox = screen.getByRole('checkbox') as HTMLInputElement;
    expect(checkbox.indeterminate).toBe(true);
  });

  it('applies indeterminate class', () => {
    render(<Checkbox indeterminate={true} />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toHaveClass('checkbox--indeterminate');
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(<Checkbox ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });
});

describe('CheckboxGroup Component', () => {
  const items = [
    { value: '1', label: 'Option 1' },
    { value: '2', label: 'Option 2' },
    { value: '3', label: 'Option 3' },
  ];

  it('renders all checkboxes in group', () => {
    render(<CheckboxGroup items={items} />);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes).toHaveLength(3);
  });

  it('renders group label', () => {
    render(<CheckboxGroup label="Options" items={items} />);
    expect(screen.getByText('Options')).toBeInTheDocument();
  });

  it('handles multiple selections', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <CheckboxGroup items={items} value={['1']} onChange={handleChange} />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[1]); // Click second checkbox

    expect(handleChange).toHaveBeenCalledWith(['1', '2']);
  });

  it('handles deselection', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <CheckboxGroup
        items={items}
        value={['1', '2']}
        onChange={handleChange}
      />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    await user.click(checkboxes[0]); // Click first checkbox

    expect(handleChange).toHaveBeenCalledWith(['2']);
  });

  it('supports disabled state on group', () => {
    render(<CheckboxGroup items={items} disabled />);
    const checkboxes = screen.getAllByRole('checkbox');
    checkboxes.forEach((checkbox) => {
      expect(checkbox).toBeDisabled();
    });
  });

  it('supports disabled items in group', () => {
    const disabledItems = [
      { value: '1', label: 'Option 1' },
      { value: '2', label: 'Option 2', disabled: true },
      { value: '3', label: 'Option 3' },
    ];

    render(<CheckboxGroup items={disabledItems} />);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[1]).toBeDisabled();
    expect(checkboxes[0]).not.toBeDisabled();
  });

  it('renders with descriptions', () => {
    const itemsWithDesc = [
      { value: '1', label: 'Option 1', description: 'Description 1' },
      { value: '2', label: 'Option 2', description: 'Description 2' },
    ];

    render(<CheckboxGroup items={itemsWithDesc} />);
    expect(screen.getByText('Description 1')).toBeInTheDocument();
    expect(screen.getByText('Description 2')).toBeInTheDocument();
  });

  it('supports vertical layout', () => {
    render(<CheckboxGroup items={items} direction="vertical" />);
    const group = screen.getByRole('group');
    expect(group).toHaveClass('checkbox-group--vertical');
  });

  it('supports horizontal layout', () => {
    render(<CheckboxGroup items={items} direction="horizontal" />);
    const group = screen.getByRole('group');
    expect(group).toHaveClass('checkbox-group--horizontal');
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(<CheckboxGroup items={items} ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });
});
