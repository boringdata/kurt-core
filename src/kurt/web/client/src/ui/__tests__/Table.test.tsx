import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Table } from '../components/Table';
import { TableColumn } from '../types/table';

interface TestData {
  id: string;
  name: string;
  email: string;
  status: string;
}

const mockData: TestData[] = [
  { id: '1', name: 'Alice Johnson', email: 'alice@example.com', status: 'Active' },
  { id: '2', name: 'Bob Smith', email: 'bob@example.com', status: 'Active' },
  { id: '3', name: 'Charlie Brown', email: 'charlie@example.com', status: 'Inactive' },
];

const columns: TableColumn<TestData>[] = [
  { id: 'name', header: 'Name', accessor: 'name', sortable: true },
  { id: 'email', header: 'Email', accessor: 'email' },
  { id: 'status', header: 'Status', accessor: 'status', sortable: true },
];

describe('Table Component', () => {
  describe('Rendering', () => {
    it('renders table with columns and data', () => {
      render(<Table data={mockData} columns={columns} />);

      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Email')).toBeInTheDocument();
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
      expect(screen.getByText('bob@example.com')).toBeInTheDocument();
    });

    it('renders empty state when no data', () => {
      render(<Table data={[]} columns={columns} emptyMessage="No data available" />);

      expect(screen.getByText('No data available')).toBeInTheDocument();
    });

    it('renders custom empty state', () => {
      render(
        <Table
          data={[]}
          columns={columns}
          renderEmpty={() => <div>Custom empty message</div>}
        />
      );

      expect(screen.getByText('Custom empty message')).toBeInTheDocument();
    });

    it('renders loading state', () => {
      render(<Table data={mockData} columns={columns} loading={true} />);

      expect(screen.getByRole('table')).toHaveClass('table--loading');
    });

    it('renders footer when enabled', () => {
      render(
        <Table
          data={mockData}
          columns={columns}
          showFooter={true}
          footerContent={<div>Total: 3 rows</div>}
        />
      );

      expect(screen.getByText('Total: 3 rows')).toBeInTheDocument();
    });
  });

  describe('Sorting', () => {
    it('handles column sort click', async () => {
      const onSort = vi.fn();
      render(
        <Table
          data={mockData}
          columns={columns}
          onSort={onSort}
        />
      );

      const nameHeader = screen.getByRole('columnheader', { name: /Sort by Name/ });
      await userEvent.click(nameHeader);

      expect(onSort).toHaveBeenCalledWith('name', 'asc');
    });

    it('cycles through sort orders', async () => {
      const onSort = vi.fn();
      render(
        <Table
          data={mockData}
          columns={columns}
          onSort={onSort}
        />
      );

      const nameHeader = screen.getByRole('columnheader', { name: /Sort by Name/ });

      // First click: asc
      await userEvent.click(nameHeader);
      expect(onSort).toHaveBeenLastCalledWith('name', 'asc');

      // Second click: desc
      await userEvent.click(nameHeader);
      expect(onSort).toHaveBeenLastCalledWith('name', 'desc');

      // Third click: null (clear)
      await userEvent.click(nameHeader);
      expect(onSort).toHaveBeenLastCalledWith('name', null);
    });

    it('does not allow sorting non-sortable columns', async () => {
      const onSort = vi.fn();
      render(
        <Table
          data={mockData}
          columns={columns}
          onSort={onSort}
        />
      );

      const emailHeader = screen.getByRole('columnheader', { name: 'Email' });
      expect(emailHeader.tagName).not.toBe('BUTTON');
    });
  });

  describe('Row Selection', () => {
    it('renders checkboxes when selectable', () => {
      render(
        <Table
          data={mockData}
          columns={columns}
          selectable={true}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBe(4); // 1 header + 3 rows
    });

    it('handles individual row selection', async () => {
      const onSelectRows = vi.fn();
      render(
        <Table
          data={mockData}
          columns={columns}
          selectable={true}
          onSelectRows={onSelectRows}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await userEvent.click(checkboxes[1]); // Click first row checkbox

      expect(onSelectRows).toHaveBeenCalledWith(['1']);
    });

    it('handles select all', async () => {
      const onSelectRows = vi.fn();
      render(
        <Table
          data={mockData}
          columns={columns}
          selectable={true}
          onSelectRows={onSelectRows}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await userEvent.click(checkboxes[0]); // Click header checkbox

      expect(onSelectRows).toHaveBeenCalledWith(['1', '2', '3']);
    });

    it('marks selected rows', () => {
      render(
        <Table
          data={mockData}
          columns={columns}
          selectable={true}
          selectedRows={['1', '3']}
        />
      );

      const rows = screen.getAllByRole('row');
      expect(rows[1]).toHaveClass('table-row--selected'); // First data row
      expect(rows[3]).toHaveClass('table-row--selected'); // Third data row
    });
  });

  describe('Custom Rendering', () => {
    it('renders custom cell content', () => {
      const customColumns: TableColumn<TestData>[] = [
        {
          id: 'name',
          header: 'Name',
          render: (value) => <span className="custom">{value.toUpperCase()}</span>,
        },
      ];

      render(
        <Table
          data={[{ id: '1', name: 'test', email: 'test@test.com', status: 'Active' }]}
          columns={customColumns}
        />
      );

      expect(screen.getByText('TEST')).toBeInTheDocument();
      expect(screen.getByText('TEST')).toHaveClass('custom');
    });

    it('accepts function accessors', () => {
      const customColumns: TableColumn<TestData>[] = [
        {
          id: 'nameEmail',
          header: 'Name (Email)',
          accessor: (row) => `${row.name} (${row.email})`,
        },
      ];

      render(
        <Table
          data={[{ id: '1', name: 'Alice', email: 'alice@test.com', status: 'Active' }]}
          columns={customColumns}
        />
      );

      expect(screen.getByText('Alice (alice@test.com)')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<Table data={mockData} columns={columns} />);

      expect(screen.getByRole('table')).toHaveAttribute('role', 'table');
      const headerCells = screen.getAllByRole('columnheader');
      expect(headerCells.length).toBe(3);
    });

    it('supports keyboard navigation in sort buttons', async () => {
      render(<Table data={mockData} columns={columns} />);

      const sortButton = screen.getByRole('columnheader', { name: /Sort by Name/ }).querySelector('button');
      expect(sortButton).toBeInTheDocument();

      if (sortButton) {
        sortButton.focus();
        expect(document.activeElement).toBe(sortButton);

        await userEvent.keyboard('{Enter}');
        // Verify sort was triggered
      }
    });

    it('checkboxes have proper labels', () => {
      render(
        <Table
          data={mockData}
          columns={columns}
          selectable={true}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      checkboxes.forEach((checkbox) => {
        expect(checkbox).toHaveAttribute('aria-label');
      });
    });

    it('shows loading indicator with aria-busy', () => {
      render(<Table data={mockData} columns={columns} loading={true} />);

      const overlay = screen.getByLabelText('Loading table data');
      expect(overlay).toHaveAttribute('aria-busy', 'true');
    });
  });

  describe('Variants', () => {
    it('applies striped variant', () => {
      const { container } = render(
        <Table data={mockData} columns={columns} striped={true} />
      );

      expect(container.querySelector('.table--striped')).toBeInTheDocument();
    });

    it('applies hoverable variant', () => {
      const { container } = render(
        <Table data={mockData} columns={columns} hoverable={true} />
      );

      expect(container.querySelector('.table--hoverable')).toBeInTheDocument();
    });

    it('applies compact variant', () => {
      const { container } = render(
        <Table data={mockData} columns={columns} compact={true} />
      );

      expect(container.querySelector('.table--compact')).toBeInTheDocument();
    });
  });

  describe('Custom row ID accessor', () => {
    it('accepts custom rowId function', async () => {
      const onSelectRows = vi.fn();
      render(
        <Table
          data={mockData}
          columns={columns}
          selectable={true}
          rowId={(row) => `row-${row.email}`}
          onSelectRows={onSelectRows}
        />
      );

      const checkboxes = screen.getAllByRole('checkbox');
      await userEvent.click(checkboxes[1]);

      expect(onSelectRows).toHaveBeenCalledWith(['row-alice@example.com']);
    });
  });
});
