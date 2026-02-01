import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Tabs } from '../Tabs';
import { Home } from 'lucide-react';

describe('Tabs', () => {
  const defaultItems = [
    {
      id: 'tab1',
      label: 'Tab 1',
      content: <div>Content 1</div>,
    },
    {
      id: 'tab2',
      label: 'Tab 2',
      content: <div>Content 2</div>,
    },
    {
      id: 'tab3',
      label: 'Tab 3',
      content: <div>Content 3</div>,
    },
  ];

  it('renders all tab buttons', () => {
    render(<Tabs items={defaultItems} />);

    expect(screen.getByText('Tab 1')).toBeInTheDocument();
    expect(screen.getByText('Tab 2')).toBeInTheDocument();
    expect(screen.getByText('Tab 3')).toBeInTheDocument();
  });

  it('shows content for first tab by default', () => {
    render(<Tabs items={defaultItems} />);

    expect(screen.getByText('Content 1')).toBeVisible();
    expect(screen.queryByText('Content 2')).not.toBeVisible();
    expect(screen.queryByText('Content 3')).not.toBeVisible();
  });

  it('switches tab on click', () => {
    render(<Tabs items={defaultItems} />);

    fireEvent.click(screen.getByText('Tab 2'));

    expect(screen.getByText('Content 2')).toBeVisible();
    expect(screen.queryByText('Content 1')).not.toBeVisible();
  });

  it('calls onChange callback when tab changes', () => {
    const handleChange = vi.fn();
    render(<Tabs items={defaultItems} onChange={handleChange} />);

    fireEvent.click(screen.getByText('Tab 2'));

    expect(handleChange).toHaveBeenCalledWith('tab2');
  });

  it('respects controlled value', () => {
    const { rerender } = render(
      <Tabs items={defaultItems} value="tab1" onChange={() => {}} />
    );

    expect(screen.getByText('Content 1')).toBeVisible();

    rerender(
      <Tabs items={defaultItems} value="tab2" onChange={() => {}} />
    );

    expect(screen.getByText('Content 2')).toBeVisible();
  });

  it('sets default value', () => {
    render(<Tabs items={defaultItems} defaultValue="tab3" />);

    expect(screen.getByText('Content 3')).toBeVisible();
  });

  it('disables disabled tabs', () => {
    const itemsWithDisabled = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
      { id: 'tab2', label: 'Tab 2', disabled: true, content: <div>Content 2</div> },
    ];

    render(<Tabs items={itemsWithDisabled} />);

    const disabledButton = screen.getByText('Tab 2').closest('button');
    expect(disabledButton).toBeDisabled();
  });

  it('prevents clicking disabled tabs', () => {
    const itemsWithDisabled = [
      { id: 'tab1', label: 'Tab 1', content: <div>Content 1</div> },
      { id: 'tab2', label: 'Tab 2', disabled: true, content: <div>Content 2</div> },
    ];

    render(<Tabs items={itemsWithDisabled} />);

    fireEvent.click(screen.getByText('Tab 2'));

    expect(screen.getByText('Content 1')).toBeVisible();
    expect(screen.queryByText('Content 2')).not.toBeVisible();
  });

  it('renders icons in tabs', () => {
    const itemsWithIcons = [
      {
        id: 'tab1',
        label: 'Home',
        icon: <Home data-testid="home-icon" />,
        content: <div>Home content</div>,
      },
    ];

    render(<Tabs items={itemsWithIcons} />);

    expect(screen.getByTestId('home-icon')).toBeInTheDocument();
  });

  it('sets aria-selected on active tab', () => {
    render(<Tabs items={defaultItems} />);

    const tab1Button = screen.getByText('Tab 1').closest('button');
    const tab2Button = screen.getByText('Tab 2').closest('button');

    expect(tab1Button).toHaveAttribute('aria-selected', 'true');
    expect(tab2Button).toHaveAttribute('aria-selected', 'false');
  });

  it('navigates with arrow keys', async () => {
    const user = userEvent.setup();
    render(<Tabs items={defaultItems} />);

    const tab1Button = screen.getByText('Tab 1').closest('button');
    tab1Button?.focus();

    await user.keyboard('{ArrowRight}');

    expect(screen.getByText('Content 2')).toBeVisible();
  });

  it('handles left arrow key navigation', async () => {
    const user = userEvent.setup();
    render(<Tabs items={defaultItems} defaultValue="tab2" />);

    const tab2Button = screen.getByText('Tab 2').closest('button');
    tab2Button?.focus();

    await user.keyboard('{ArrowLeft}');

    expect(screen.getByText('Content 1')).toBeVisible();
  });

  it('handles Home key to go to first tab', async () => {
    const user = userEvent.setup();
    render(<Tabs items={defaultItems} defaultValue="tab3" />);

    const tab3Button = screen.getByText('Tab 3').closest('button');
    tab3Button?.focus();

    await user.keyboard('{Home}');

    expect(screen.getByText('Content 1')).toBeVisible();
  });

  it('handles End key to go to last tab', async () => {
    const user = userEvent.setup();
    render(<Tabs items={defaultItems} />);

    const tab1Button = screen.getByText('Tab 1').closest('button');
    tab1Button?.focus();

    await user.keyboard('{End}');

    expect(screen.getByText('Content 3')).toBeVisible();
  });

  it('wraps around on arrow key navigation', async () => {
    const user = userEvent.setup();
    render(<Tabs items={defaultItems} />);

    const tab1Button = screen.getByText('Tab 1').closest('button');
    tab1Button?.focus();

    // Left arrow from first tab should go to last
    await user.keyboard('{ArrowLeft}');

    expect(screen.getByText('Content 3')).toBeVisible();
  });

  it('supports vertical orientation', () => {
    const { container } = render(
      <Tabs items={defaultItems} orientation="vertical" />
    );

    const tablist = container.querySelector('[role="tablist"]');
    expect(tablist).toHaveAttribute('aria-orientation', 'vertical');
  });

  it('supports different variants', () => {
    const { container: container1 } = render(
      <Tabs items={defaultItems} variant="default" />
    );

    const { container: container2 } = render(
      <Tabs items={defaultItems} variant="underline" />
    );

    const { container: container3 } = render(
      <Tabs items={defaultItems} variant="pill" />
    );

    expect(container1.querySelector('[role="tablist"]')).toBeInTheDocument();
    expect(container2.querySelector('[role="tablist"]')).toBeInTheDocument();
    expect(container3.querySelector('[role="tablist"]')).toBeInTheDocument();
  });

  it('has proper tab panel role', () => {
    const { container } = render(<Tabs items={defaultItems} />);

    const tabpanels = container.querySelectorAll('[role="tabpanel"]');
    expect(tabpanels.length).toBe(3);
  });

  it('hides inactive tab panels', () => {
    const { container } = render(<Tabs items={defaultItems} />);

    const panels = container.querySelectorAll('[role="tabpanel"]');
    panels.forEach((panel, index) => {
      if (index === 0) {
        expect(panel).toHaveAttribute('hidden', '');
        expect(panel).not.toBeVisible();
      }
    });
  });

  it('uses tabindex management for keyboard navigation', () => {
    render(<Tabs items={defaultItems} />);

    const tab1Button = screen.getByText('Tab 1').closest('button');
    const tab2Button = screen.getByText('Tab 2').closest('button');

    expect(tab1Button).toHaveAttribute('tabindex', '0');
    expect(tab2Button).toHaveAttribute('tabindex', '-1');
  });

  it('applies custom className to tab buttons', () => {
    const { container } = render(
      <Tabs items={defaultItems} tabButtonClassName="custom-button" />
    );

    const buttons = container.querySelectorAll('button[role="tab"]');
    buttons.forEach((button) => {
      expect(button).toHaveClass('custom-button');
    });
  });

  it('applies custom className to tab panels', () => {
    const { container } = render(
      <Tabs items={defaultItems} tabPanelClassName="custom-panel" />
    );

    const panels = container.querySelectorAll('[role="tabpanel"]');
    panels.forEach((panel) => {
      expect(panel).toHaveClass('custom-panel');
    });
  });
});
