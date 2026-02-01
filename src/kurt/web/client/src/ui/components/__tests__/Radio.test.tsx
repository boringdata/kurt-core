import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Radio, RadioGroup } from '../Radio';

describe('Radio Component', () => {
  it('renders a radio button', () => {
    render(<Radio />);
    const radio = screen.getByRole('radio');
    expect(radio).toBeInTheDocument();
  });

  it('renders with label', () => {
    render(<Radio label="Option 1" />);
    const label = screen.getByText('Option 1');
    expect(label).toBeInTheDocument();
  });

  it('renders with description', () => {
    render(
      <Radio label="Premium" description="Get all features" />
    );
    expect(screen.getByText('Get all features')).toBeInTheDocument();
  });

  it('handles selection', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<Radio label="Option" onChange={handleChange} />);

    const radio = screen.getByRole('radio');
    await user.click(radio);

    expect(handleChange).toHaveBeenCalled();
    expect(radio).toBeChecked();
  });

  it('supports disabled state', () => {
    render(<Radio label="Disabled" disabled />);
    const radio = screen.getByRole('radio');
    expect(radio).toBeDisabled();
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(<Radio ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });

  it('applies custom className', () => {
    render(<Radio className="custom-class" />);
    const radio = screen.getByRole('radio');
    expect(radio).toHaveClass('custom-class');
  });
});

describe('RadioGroup Component', () => {
  const items = [
    { value: 'option1', label: 'Option 1' },
    { value: 'option2', label: 'Option 2' },
    { value: 'option3', label: 'Option 3' },
  ];

  it('renders all radio buttons in group', () => {
    render(<RadioGroup items={items} />);
    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(3);
  });

  it('renders group label', () => {
    render(<RadioGroup label="Choose one" items={items} />);
    expect(screen.getByText('Choose one')).toBeInTheDocument();
  });

  it('enforces mutual exclusion', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <RadioGroup items={items} value="option1" onChange={handleChange} />
    );

    const radios = screen.getAllByRole('radio');
    expect(radios[0]).toBeChecked();
    expect(radios[1]).not.toBeChecked();

    await user.click(radios[1]);

    expect(handleChange).toHaveBeenCalledWith('option2');
  });

  it('supports disabled state on group', () => {
    render(<RadioGroup items={items} disabled />);
    const radios = screen.getAllByRole('radio');
    radios.forEach((radio) => {
      expect(radio).toBeDisabled();
    });
  });

  it('supports disabled items in group', () => {
    const disabledItems = [
      { value: 'option1', label: 'Option 1' },
      { value: 'option2', label: 'Option 2', disabled: true },
      { value: 'option3', label: 'Option 3' },
    ];

    render(<RadioGroup items={disabledItems} />);
    const radios = screen.getAllByRole('radio');
    expect(radios[1]).toBeDisabled();
    expect(radios[0]).not.toBeDisabled();
  });

  it('renders with descriptions', () => {
    const itemsWithDesc = [
      { value: 'a', label: 'Option A', description: 'Description A' },
      { value: 'b', label: 'Option B', description: 'Description B' },
    ];

    render(<RadioGroup items={itemsWithDesc} />);
    expect(screen.getByText('Description A')).toBeInTheDocument();
    expect(screen.getByText('Description B')).toBeInTheDocument();
  });

  it('supports vertical layout', () => {
    render(<RadioGroup items={items} direction="vertical" />);
    const group = screen.getByRole('radiogroup');
    expect(group).toHaveClass('radio-group--vertical');
  });

  it('supports horizontal layout', () => {
    render(<RadioGroup items={items} direction="horizontal" />);
    const group = screen.getByRole('radiogroup');
    expect(group).toHaveClass('radio-group--horizontal');
  });

  it('all radios have same name for group', () => {
    render(<RadioGroup items={items} />);
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    const names = radios.map((r) => r.name);

    // All should have the same name
    expect(new Set(names).size).toBe(1);

    // Names should start with 'radio-group-'
    expect(names[0]).toMatch(/^radio-group-/);
  });

  it('forwards ref', () => {
    const ref = vi.fn();
    render(<RadioGroup items={items} ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });
});
