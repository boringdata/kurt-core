import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { List, ListItem } from '../components';

describe('List Component', () => {
  describe('Rendering', () => {
    it('renders unordered list by default', () => {
      render(
        <List items={['Item 1', 'Item 2', 'Item 3']} />
      );

      const list = screen.getByRole('list');
      expect(list.tagName).toBe('UL');
    });

    it('renders ordered list when type="ol"', () => {
      render(
        <List items={['Item 1', 'Item 2']} type="ol" />
      );

      const list = screen.getByRole('list');
      expect(list.tagName).toBe('OL');
    });

    it('renders items with children prop', () => {
      render(
        <List>
          <li>Item 1</li>
          <li>Item 2</li>
        </List>
      );

      expect(screen.getByText('Item 1')).toBeInTheDocument();
      expect(screen.getByText('Item 2')).toBeInTheDocument();
    });

    it('applies divided variant', () => {
      const { container } = render(
        <List items={['Item 1', 'Item 2']} divided={true} />
      );

      expect(container.querySelector('.list--divided')).toBeInTheDocument();
    });

    it('applies compact variant', () => {
      const { container } = render(
        <List items={['Item 1']} compact={true} />
      );

      expect(container.querySelector('.list--compact')).toBeInTheDocument();
    });

    it('applies custom className', () => {
      const { container } = render(
        <List items={['Item 1']} className="custom-list" />
      );

      expect(container.querySelector('.custom-list')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has list role', () => {
      render(<List items={['Item 1']} />);

      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('accepts custom role', () => {
      render(<List items={['Item 1']} role="navigation" />);

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });
  });
});

describe('ListItem Component', () => {
  describe('Rendering', () => {
    it('renders basic list item', () => {
      render(<ListItem>Item content</ListItem>);

      expect(screen.getByText('Item content')).toBeInTheDocument();
    });

    it('renders with all content slots', () => {
      render(
        <ListItem
          avatar={<div>Avatar</div>}
          subtitle="Subtitle"
          description="Description"
          action={<button>Action</button>}
        >
          Primary
        </ListItem>
      );

      expect(screen.getByText('Avatar')).toBeInTheDocument();
      expect(screen.getByText('Primary')).toBeInTheDocument();
      expect(screen.getByText('Subtitle')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
    });

    it('renders with icon instead of avatar', () => {
      render(
        <ListItem
          icon={<span data-testid="icon">🔔</span>}
        >
          Notification
        </ListItem>
      );

      expect(screen.getByTestId('icon')).toBeInTheDocument();
    });

    it('renders custom content slot', () => {
      render(
        <ListItem
          content={<div>Custom content</div>}
        >
          Title
        </ListItem>
      );

      expect(screen.getByText('Custom content')).toBeInTheDocument();
    });

    it('renders as link when href is provided', () => {
      render(
        <ListItem href="/page" target="_blank">
          Link item
        </ListItem>
      );

      const link = screen.getByRole('link', { name: 'Link item' });
      expect(link).toHaveAttribute('href', '/page');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('applies divider', () => {
      const { container } = render(
        <ListItem divider={true}>Item</ListItem>
      );

      expect(container.querySelector('.list-item--divider')).toBeInTheDocument();
    });
  });

  describe('Interaction', () => {
    it('handles click on clickable item', async () => {
      const onClick = vi.fn();
      render(
        <ListItem clickable={true} onClick={onClick}>
          Clickable item
        </ListItem>
      );

      const item = screen.getByRole('button');
      await userEvent.click(item);

      expect(onClick).toHaveBeenCalledOnce();
    });

    it('handles Enter key on clickable item', async () => {
      const onClick = vi.fn();
      render(
        <ListItem clickable={true} onClick={onClick}>
          Clickable item
        </ListItem>
      );

      const item = screen.getByRole('button');
      item.focus();
      await userEvent.keyboard('{Enter}');

      expect(onClick).toHaveBeenCalledOnce();
    });

    it('handles Space key on clickable item', async () => {
      const onClick = vi.fn();
      render(
        <ListItem clickable={true} onClick={onClick}>
          Clickable item
        </ListItem>
      );

      const item = screen.getByRole('button');
      item.focus();
      await userEvent.keyboard(' ');

      expect(onClick).toHaveBeenCalledOnce();
    });

    it('does not trigger click when disabled', async () => {
      const onClick = vi.fn();
      render(
        <ListItem clickable={true} onClick={onClick} disabled={true}>
          Disabled item
        </ListItem>
      );

      const item = screen.getByRole('button');
      await userEvent.click(item);

      expect(onClick).not.toHaveBeenCalled();
    });
  });

  describe('States', () => {
    it('applies selected state', () => {
      const { container } = render(
        <ListItem selected={true}>Selected item</ListItem>
      );

      expect(container.querySelector('.list-item--selected')).toBeInTheDocument();
    });

    it('applies active state', () => {
      const { container } = render(
        <ListItem active={true}>Active item</ListItem>
      );

      expect(container.querySelector('.list-item--active')).toBeInTheDocument();
    });

    it('applies disabled state', () => {
      const { container } = render(
        <ListItem disabled={true}>Disabled item</ListItem>
      );

      expect(container.querySelector('.list-item--disabled')).toBeInTheDocument();
    });

    it('applies clickable state', () => {
      const { container } = render(
        <ListItem clickable={true}>Clickable item</ListItem>
      );

      expect(container.querySelector('.list-item--clickable')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper role when not clickable', () => {
      render(<ListItem>Item</ListItem>);

      const item = screen.getByRole('listitem');
      expect(item).toBeInTheDocument();
    });

    it('has button role when clickable', () => {
      render(<ListItem clickable={true}>Item</ListItem>);

      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('has aria-selected when selected', () => {
      render(<ListItem selected={true}>Item</ListItem>);

      expect(screen.getByRole('listitem')).toHaveAttribute('aria-selected', 'true');
    });

    it('has aria-disabled when disabled', () => {
      render(<ListItem clickable={true} disabled={true}>Item</ListItem>);

      expect(screen.getByRole('button')).toHaveAttribute('aria-disabled', 'true');
    });

    it('has aria-current when active', () => {
      render(<ListItem href="/page" active={true}>Item</ListItem>);

      expect(screen.getByRole('link')).toHaveAttribute('aria-current', 'page');
    });

    it('is keyboard focusable when clickable', () => {
      const { container } = render(
        <ListItem clickable={true}>Item</ListItem>
      );

      const item = container.querySelector('.list-item');
      expect(item).toHaveAttribute('tabindex', '0');
    });

    it('is not keyboard focusable when disabled', () => {
      const { container } = render(
        <ListItem clickable={true} disabled={true}>Item</ListItem>
      );

      const item = container.querySelector('.list-item');
      expect(item).toHaveAttribute('tabindex', '-1');
    });
  });

  describe('Custom className', () => {
    it('applies custom className to item', () => {
      const { container } = render(
        <ListItem className="custom-item">Item</ListItem>
      );

      expect(container.querySelector('.custom-item')).toBeInTheDocument();
    });

    it('applies custom contentClassName', () => {
      const { container } = render(
        <ListItem contentClassName="custom-content">Item</ListItem>
      );

      expect(container.querySelector('.custom-content')).toBeInTheDocument();
    });
  });
});
