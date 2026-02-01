import React, { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import { Table } from './Table';
import { TableColumn } from '../types/table';

interface SampleData {
  id: string;
  name: string;
  email: string;
  department: string;
  status: 'Active' | 'Inactive' | 'On Leave';
  joinDate: string;
}

const sampleData: SampleData[] = [
  {
    id: '1',
    name: 'Alice Johnson',
    email: 'alice@example.com',
    department: 'Engineering',
    status: 'Active',
    joinDate: '2022-01-15',
  },
  {
    id: '2',
    name: 'Bob Smith',
    email: 'bob@example.com',
    department: 'Design',
    status: 'Active',
    joinDate: '2021-08-20',
  },
  {
    id: '3',
    name: 'Charlie Brown',
    email: 'charlie@example.com',
    department: 'Engineering',
    status: 'On Leave',
    joinDate: '2023-03-10',
  },
  {
    id: '4',
    name: 'Diana Prince',
    email: 'diana@example.com',
    department: 'Product',
    status: 'Active',
    joinDate: '2020-06-01',
  },
  {
    id: '5',
    name: 'Eve Wilson',
    email: 'eve@example.com',
    department: 'Marketing',
    status: 'Inactive',
    joinDate: '2023-11-22',
  },
];

const columns: TableColumn<SampleData>[] = [
  { id: 'name', header: 'Name', accessor: 'name', sortable: true, width: '200px' },
  { id: 'email', header: 'Email', accessor: 'email', width: '220px' },
  { id: 'department', header: 'Department', accessor: 'department', sortable: true, width: '150px' },
  {
    id: 'status',
    header: 'Status',
    accessor: 'status',
    sortable: true,
    render: (value) => (
      <span
        style={{
          display: 'inline-block',
          padding: '0.25rem 0.75rem',
          borderRadius: '0.25rem',
          fontSize: '0.75rem',
          fontWeight: '500',
          backgroundColor:
            value === 'Active'
              ? '#dcfce7'
              : value === 'On Leave'
                ? '#fef3c7'
                : '#fee2e2',
          color:
            value === 'Active'
              ? '#15803d'
              : value === 'On Leave'
                ? '#b45309'
                : '#991b1b',
        }}
      >
        {value}
      </span>
    ),
    width: '120px',
  },
  {
    id: 'joinDate',
    header: 'Join Date',
    accessor: 'joinDate',
    sortable: true,
    width: '120px',
  },
];

const meta: Meta<typeof Table> = {
  title: 'Data Display/Table',
  component: Table,
  tags: ['autodocs'],
  argTypes: {
    striped: { control: 'boolean' },
    hoverable: { control: 'boolean' },
    compact: { control: 'boolean' },
    selectable: { control: 'boolean' },
    loading: { control: 'boolean' },
    isEmpty: { control: 'boolean' },
    showFooter: { control: 'boolean' },
  },
};

export default meta;
type Story = StoryObj<typeof Table>;

export const Default: Story = {
  args: {
    data: sampleData,
    columns,
    striped: true,
    hoverable: true,
  },
};

export const WithSelection: Story = {
  args: {
    data: sampleData,
    columns,
    selectable: true,
    striped: true,
    hoverable: true,
  },
  render: (args) => {
    const [selectedRows, setSelectedRows] = useState<string[]>([]);
    return (
      <div>
        <Table {...args} selectedRows={selectedRows} onSelectRows={setSelectedRows} />
        <p style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#666' }}>
          Selected: {selectedRows.length > 0 ? selectedRows.join(', ') : 'None'}
        </p>
      </div>
    );
  },
};

export const WithSorting: Story = {
  args: {
    data: sampleData,
    columns,
    striped: true,
    hoverable: true,
  },
  render: (args) => {
    const [sortState, setSortState] = useState<{ columnId: string | null; order: 'asc' | 'desc' | null }>({
      columnId: null,
      order: null,
    });

    return (
      <div>
        <Table
          {...args}
          onSort={(columnId, order) => {
            setSortState({ columnId, order });
          }}
        />
        <p style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#666' }}>
          Sorted by: {sortState.columnId ? `${sortState.columnId} (${sortState.order})` : 'None'}
        </p>
      </div>
    );
  },
};

export const Compact: Story = {
  args: {
    data: sampleData,
    columns,
    compact: true,
    striped: true,
    hoverable: true,
  },
};

export const NoHover: Story = {
  args: {
    data: sampleData,
    columns,
    hoverable: false,
    striped: true,
  },
};

export const Loading: Story = {
  args: {
    data: sampleData,
    columns,
    loading: true,
    striped: true,
    hoverable: true,
  },
};

export const Empty: Story = {
  args: {
    data: [],
    columns,
    emptyMessage: 'No employees found',
    striped: true,
  },
};

export const CustomEmpty: Story = {
  args: {
    data: [],
    columns,
    renderEmpty: () => (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📭</div>
        <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>No Data Available</div>
        <div style={{ fontSize: '0.875rem', color: '#666' }}>
          Start by adding your first employee
        </div>
      </div>
    ),
    striped: true,
  },
};

export const WithFooter: Story = {
  args: {
    data: sampleData,
    columns,
    showFooter: true,
    footerContent: (
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>Total: {sampleData.length} employees</span>
        <button style={{ padding: '0.5rem 1rem', cursor: 'pointer', borderRadius: '0.25rem' }}>
          Export
        </button>
      </div>
    ),
    striped: true,
    hoverable: true,
  },
};

export const SelectionAndSorting: Story = {
  args: {
    data: sampleData,
    columns,
    selectable: true,
    striped: true,
    hoverable: true,
  },
  render: (args) => {
    const [selectedRows, setSelectedRows] = useState<string[]>([]);
    const [sortState, setSortState] = useState<{ columnId: string | null; order: 'asc' | 'desc' | null }>({
      columnId: null,
      order: null,
    });

    return (
      <div>
        <Table
          {...args}
          selectedRows={selectedRows}
          onSelectRows={setSelectedRows}
          onSort={(columnId, order) => {
            setSortState({ columnId, order });
          }}
        />
        <div style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#666' }}>
          <p>Selected: {selectedRows.length > 0 ? selectedRows.join(', ') : 'None'}</p>
          <p>Sorted by: {sortState.columnId ? `${sortState.columnId} (${sortState.order})` : 'None'}</p>
        </div>
      </div>
    );
  },
};

export const Responsive: Story = {
  args: {
    data: sampleData.slice(0, 3),
    columns,
    selectable: true,
    striped: true,
    hoverable: true,
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile1',
    },
  },
};
