/**
 * Table component types and interfaces
 */

export interface TableColumn<T = any> {
  /** Unique identifier for the column */
  id: string;
  /** Column header label */
  header: string | React.ReactNode;
  /** Property key or custom accessor function */
  accessor?: keyof T | ((row: T) => React.ReactNode);
  /** Whether this column is sortable */
  sortable?: boolean;
  /** Custom cell renderer */
  render?: (value: any, row: T, index: number) => React.ReactNode;
  /** Column width (CSS value) */
  width?: string;
  /** Custom header className */
  headerClassName?: string;
  /** Custom cell className */
  cellClassName?: string;
  /** Custom footer cell className */
  footerCellClassName?: string;
}

export type SortOrder = 'asc' | 'desc' | null;

export interface SortState {
  columnId: string | null;
  order: SortOrder;
}

export interface TableProps<T = any> {
  /** Array of data rows */
  data: T[];
  /** Column definitions */
  columns: TableColumn<T>[];
  /** Currently selected row IDs */
  selectedRows?: string[];
  /** Callback when row selection changes */
  onSelectRows?: (rowIds: string[]) => void;
  /** Callback when sort changes */
  onSort?: (columnId: string, order: SortOrder) => void;
  /** Row ID accessor (defaults to 'id') */
  rowId?: keyof T | ((row: T, index: number) => string);
  /** Enable row selection with checkboxes */
  selectable?: boolean;
  /** Show loading state */
  loading?: boolean;
  /** Show empty state */
  isEmpty?: boolean;
  /** Empty state message */
  emptyMessage?: string;
  /** Custom empty state renderer */
  renderEmpty?: () => React.ReactNode;
  /** Show footer row */
  showFooter?: boolean;
  /** Custom footer content */
  footerContent?: React.ReactNode;
  /** Enable striped rows */
  striped?: boolean;
  /** Enable row hover effect */
  hoverable?: boolean;
  /** Compact table variant */
  compact?: boolean;
  /** Custom row className */
  rowClassName?: string | ((row: T, index: number) => string);
  /** Custom body className */
  bodyClassName?: string;
  /** Custom className */
  className?: string;
  /** Allow multiple sort (shift+click) */
  multiSort?: boolean;
}

export interface TableState<T> {
  sortState: SortState;
  selectedRows: Set<string>;
  data: T[];
}
