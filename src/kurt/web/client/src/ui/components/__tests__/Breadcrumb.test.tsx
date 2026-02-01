import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import Breadcrumb from '../Breadcrumb';
import { Home } from 'lucide-react';

describe('Breadcrumb', () => {
  it('renders breadcrumb items in order', () => {
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
          { label: 'Shoes', isActive: true },
        ]}
      />
    );

    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Products')).toBeInTheDocument();
    expect(screen.getByText('Shoes')).toBeInTheDocument();
  });

  it('renders separator between items', () => {
    const { container } = render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
        ]}
      />
    );

    const separators = container.querySelectorAll('[aria-hidden="true"]');
    expect(separators.length).toBeGreaterThan(0);
  });

  it('renders custom separator', () => {
    const { container } = render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
        ]}
        separator={<span className="custom-sep">→</span>}
      />
    );

    expect(screen.getByText('→')).toBeInTheDocument();
  });

  it('calls onClick handler when clickable item is clicked', () => {
    const handleClick = vi.fn();
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/', onClick: handleClick },
          { label: 'Products', isActive: true },
        ]}
      />
    );

    fireEvent.click(screen.getByText('Home'));
    expect(handleClick).toHaveBeenCalled();
  });

  it('calls onItemClick callback', () => {
    const handleItemClick = vi.fn();
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
        ]}
        onItemClick={handleItemClick}
      />
    );

    fireEvent.click(screen.getByText('Home'));
    expect(handleItemClick).toHaveBeenCalled();
  });

  it('marks active item with aria-current="page"', () => {
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', isActive: true },
        ]}
      />
    );

    const activeLink = screen.getByText('Products');
    expect(activeLink).toHaveAttribute('aria-current', 'page');
  });

  it('renders icons when provided', () => {
    const { container } = render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/', icon: <Home data-testid="home-icon" /> },
          { label: 'Products', isActive: true },
        ]}
      />
    );

    expect(screen.getByTestId('home-icon')).toBeInTheDocument();
  });

  it('supports keyboard navigation on clickable items', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/', onClick: handleClick },
          { label: 'Products', isActive: true },
        ]}
      />
    );

    const homeLink = screen.getByText('Home');
    await user.keyboard('{Enter}');

    homeLink.focus();
    fireEvent.keyDown(homeLink, { key: 'Enter' });
    expect(handleClick).toHaveBeenCalled();
  });

  it('renders with custom className', () => {
    const { container } = render(
      <Breadcrumb
        items={[{ label: 'Home', href: '/' }]}
        className="custom-class"
      />
    );

    const nav = container.querySelector('nav');
    expect(nav).toHaveClass('custom-class');
  });

  it('has proper aria-label for accessibility', () => {
    const { container } = render(
      <Breadcrumb
        items={[{ label: 'Home', href: '/' }]}
        ariaLabel="Main navigation"
      />
    );

    const nav = container.querySelector('nav');
    expect(nav).toHaveAttribute('aria-label', 'Main navigation');
  });

  it('renders links with href attribute', () => {
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/home' },
          { label: 'Products', href: '/products' },
        ]}
      />
    );

    expect(screen.getByText('Home')).toHaveAttribute('href', '/home');
    expect(screen.getByText('Products')).toHaveAttribute('href', '/products');
  });

  it('prevents default link behavior on click', () => {
    const handleClick = vi.fn();
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/', onClick: handleClick },
        ]}
      />
    );

    const link = screen.getByText('Home');
    const clickEvent = new MouseEvent('click', { bubbles: true });
    const preventDefaultSpy = vi.spyOn(clickEvent, 'preventDefault');

    fireEvent.click(link);
    expect(preventDefaultSpy).toHaveBeenCalled();
  });

  it('collapses items on small screens', () => {
    // Mock window.innerWidth
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 500,
    });

    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
          { label: 'Shoes', href: '/shoes' },
          { label: 'Running', isActive: true },
        ]}
        collapseAt="sm"
      />
    );

    expect(screen.getByText('...')).toBeInTheDocument();
  });

  it('does not render ellipsis on large screens', () => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1200,
    });

    const { queryByText } = render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
          { label: 'Shoes', href: '/shoes' },
          { label: 'Running', isActive: true },
        ]}
        collapseAt="sm"
      />
    );

    expect(queryByText('...')).not.toBeInTheDocument();
  });
});
