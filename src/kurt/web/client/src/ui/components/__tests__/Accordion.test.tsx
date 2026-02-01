import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Accordion } from '../Accordion';
import { Settings } from 'lucide-react';

describe('Accordion', () => {
  const defaultItems = [
    {
      id: 'item1',
      title: 'Section 1',
      content: <div>Content 1</div>,
    },
    {
      id: 'item2',
      title: 'Section 2',
      content: <div>Content 2</div>,
    },
    {
      id: 'item3',
      title: 'Section 3',
      content: <div>Content 3</div>,
    },
  ];

  it('renders all accordion items', () => {
    render(<Accordion items={defaultItems} />);

    expect(screen.getByText('Section 1')).toBeInTheDocument();
    expect(screen.getByText('Section 2')).toBeInTheDocument();
    expect(screen.getByText('Section 3')).toBeInTheDocument();
  });

  it('expands item on click', () => {
    render(<Accordion items={defaultItems} />);

    const section2 = screen.getByText('Section 2');
    fireEvent.click(section2);

    expect(screen.getByText('Content 2')).toBeVisible();
  });

  it('collapses item on second click in single mode', () => {
    render(<Accordion items={defaultItems} mode="single" />);

    const section1 = screen.getByText('Section 1');

    fireEvent.click(section1);
    expect(screen.getByText('Content 1')).toBeVisible();

    fireEvent.click(section1);
    expect(screen.queryByText('Content 1')).not.toBeVisible();
  });

  it('supports single mode (only one item open)', () => {
    render(<Accordion items={defaultItems} mode="single" />);

    const section1 = screen.getByText('Section 1');
    const section2 = screen.getByText('Section 2');

    fireEvent.click(section1);
    expect(screen.getByText('Content 1')).toBeVisible();

    fireEvent.click(section2);
    expect(screen.queryByText('Content 1')).not.toBeVisible();
    expect(screen.getByText('Content 2')).toBeVisible();
  });

  it('supports multiple mode (multiple items open)', () => {
    render(<Accordion items={defaultItems} mode="multiple" />);

    const section1 = screen.getByText('Section 1');
    const section2 = screen.getByText('Section 2');

    fireEvent.click(section1);
    fireEvent.click(section2);

    expect(screen.getByText('Content 1')).toBeVisible();
    expect(screen.getByText('Content 2')).toBeVisible();
  });

  it('opens default expanded items', () => {
    render(
      <Accordion items={defaultItems} defaultExpanded={['item1', 'item2']} />
    );

    expect(screen.getByText('Content 1')).toBeVisible();
    expect(screen.getByText('Content 2')).toBeVisible();
    expect(screen.queryByText('Content 3')).not.toBeVisible();
  });

  it('disables disabled items', () => {
    const itemsWithDisabled = [
      { id: 'item1', title: 'Enabled', content: <div>Content</div> },
      { id: 'item2', title: 'Disabled', disabled: true, content: <div>Content</div> },
    ];

    render(<Accordion items={itemsWithDisabled} />);

    const disabledButton = screen.getByText('Disabled').closest('button');
    expect(disabledButton).toBeDisabled();
  });

  it('prevents clicking disabled items', () => {
    const itemsWithDisabled = [
      { id: 'item1', title: 'Enabled', content: <div>Enabled Content</div> },
      { id: 'item2', title: 'Disabled', disabled: true, content: <div>Disabled Content</div> },
    ];

    render(<Accordion items={itemsWithDisabled} />);

    fireEvent.click(screen.getByText('Disabled'));

    expect(screen.queryByText('Disabled Content')).not.toBeVisible();
  });

  it('renders icons', () => {
    const itemsWithIcons = [
      {
        id: 'item1',
        title: 'Settings',
        icon: <Settings data-testid="settings-icon" />,
        content: <div>Settings content</div>,
      },
    ];

    render(<Accordion items={itemsWithIcons} />);

    expect(screen.getByTestId('settings-icon')).toBeInTheDocument();
  });

  it('calls onExpandChange callback', () => {
    const handleExpand = vi.fn();
    render(
      <Accordion
        items={defaultItems}
        mode="multiple"
        onExpandChange={handleExpand}
      />
    );

    fireEvent.click(screen.getByText('Section 1'));

    expect(handleExpand).toHaveBeenCalledWith(['item1']);
  });

  it('respects controlled expanded state', () => {
    const { rerender } = render(
      <Accordion items={defaultItems} expanded={['item1']} onExpandChange={() => {}} />
    );

    expect(screen.getByText('Content 1')).toBeVisible();

    rerender(
      <Accordion items={defaultItems} expanded={['item2']} onExpandChange={() => {}} />
    );

    expect(screen.queryByText('Content 1')).not.toBeVisible();
    expect(screen.getByText('Content 2')).toBeVisible();
  });

  it('sets aria-expanded attribute', () => {
    render(<Accordion items={defaultItems} />);

    const section1Button = screen.getByText('Section 1').closest('button');
    const section2Button = screen.getByText('Section 2').closest('button');

    expect(section1Button).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(section1Button!);

    expect(section1Button).toHaveAttribute('aria-expanded', 'true');
  });

  it('has proper role attributes for accessibility', () => {
    const { container } = render(<Accordion items={defaultItems} />);

    const buttons = container.querySelectorAll('button[role="button"]');
    const regions = container.querySelectorAll('[role="region"]');

    expect(buttons.length).toBeGreaterThan(0);
    expect(regions.length).toBeGreaterThan(0);
  });

  it('navigates with arrow keys', async () => {
    const user = userEvent.setup();
    render(<Accordion items={defaultItems} />);

    const section1Button = screen.getByText('Section 1').closest('button');
    section1Button?.focus();

    await user.keyboard('{ArrowDown}');

    // Focus should move to next item
    const section2Button = screen.getByText('Section 2').closest('button');
    expect(document.activeElement).toBe(section2Button);
  });

  it('navigates with arrow up key', async () => {
    const user = userEvent.setup();
    render(<Accordion items={defaultItems} defaultExpanded={['item3']} />);

    const section3Button = screen.getByText('Section 3').closest('button');
    section3Button?.focus();

    await user.keyboard('{ArrowUp}');

    const section2Button = screen.getByText('Section 2').closest('button');
    expect(document.activeElement).toBe(section2Button);
  });

  it('handles Home key to go to first item', async () => {
    const user = userEvent.setup();
    render(<Accordion items={defaultItems} />);

    const section3Button = screen.getByText('Section 3').closest('button');
    section3Button?.focus();

    await user.keyboard('{Home}');

    const section1Button = screen.getByText('Section 1').closest('button');
    expect(document.activeElement).toBe(section1Button);
  });

  it('handles End key to go to last item', async () => {
    const user = userEvent.setup();
    render(<Accordion items={defaultItems} />);

    const section1Button = screen.getByText('Section 1').closest('button');
    section1Button?.focus();

    await user.keyboard('{End}');

    const section3Button = screen.getByText('Section 3').closest('button');
    expect(document.activeElement).toBe(section3Button);
  });

  it('rotates chevron icon when expanded', () => {
    render(<Accordion items={defaultItems} />);

    const section1Button = screen.getByText('Section 1').closest('button');
    const chevron = section1Button?.querySelector('svg');

    expect(chevron).toBeInTheDocument();

    fireEvent.click(section1Button!);

    // Chevron should be rotated (180 degrees)
    expect(chevron).toHaveClass('rotate-180');
  });

  it('applies animation when expanding', async () => {
    render(<Accordion items={defaultItems} animated={true} />);

    const section1Button = screen.getByText('Section 1');
    fireEvent.click(section1Button);

    await waitFor(() => {
      expect(screen.getByText('Content 1')).toBeVisible();
    });
  });

  it('disables animation when animated is false', () => {
    const { container } = render(
      <Accordion items={defaultItems} animated={false} />
    );

    const contentDiv = container.querySelector('[role="region"] > div');
    expect(contentDiv).not.toHaveClass('transition-all');
  });

  it('applies custom className', () => {
    const { container } = render(
      <Accordion items={defaultItems} className="custom-accordion" />
    );

    const rootDiv = container.querySelector('[role="region"]');
    expect(rootDiv).toHaveClass('custom-accordion');
  });

  it('applies custom item className', () => {
    const { container } = render(
      <Accordion items={defaultItems} itemClassName="custom-item" />
    );

    const items = container.querySelectorAll('.custom-item');
    expect(items.length).toBeGreaterThan(0);
  });

  it('has proper aria-label on container', () => {
    const { container } = render(
      <Accordion items={defaultItems} ariaLabel="FAQ" />
    );

    const rootDiv = container.querySelector('[role="region"]');
    expect(rootDiv).toHaveAttribute('aria-label', 'FAQ');
  });

  it('hides content when collapsed', () => {
    render(<Accordion items={defaultItems} />);

    expect(screen.queryByText('Content 1')).not.toBeVisible();
    expect(screen.queryByText('Content 2')).not.toBeVisible();
    expect(screen.queryByText('Content 3')).not.toBeVisible();
  });

  it('shows content when expanded', () => {
    render(<Accordion items={defaultItems} defaultExpanded={['item1', 'item2']} />);

    expect(screen.getByText('Content 1')).toBeVisible();
    expect(screen.getByText('Content 2')).toBeVisible();
  });
});
