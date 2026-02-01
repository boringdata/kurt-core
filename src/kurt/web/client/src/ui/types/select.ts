import { ReactNode, SelectHTMLAttributes } from 'react';

export interface SelectOption {
  /**
   * Unique identifier for the option
   */
  value: string | number;

  /**
   * Display text for the option
   */
  label: ReactNode;

  /**
   * Whether the option is disabled
   */
  disabled?: boolean;

  /**
   * Optional description for the option
   */
  description?: ReactNode;

  /**
   * Group ID for grouping options
   */
  groupId?: string;
}

export interface SelectGroup {
  /**
   * Unique identifier for the group
   */
  id: string;

  /**
   * Group label
   */
  label: string;

  /**
   * Options in this group
   */
  options: SelectOption[];

  /**
   * Whether the group is disabled
   */
  disabled?: boolean;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'value'> {
  /**
   * The options to display in the dropdown
   */
  options: SelectOption[];

  /**
   * Option groups for organization
   */
  groups?: SelectGroup[];

  /**
   * The currently selected value
   */
  value?: string | number | null;

  /**
   * The label for the select field
   */
  label?: ReactNode;

  /**
   * Hint text displayed below the select
   */
  hint?: ReactNode;

  /**
   * Error message displayed when the field has an error
   */
  error?: ReactNode;

  /**
   * Whether the field is required
   */
  required?: boolean;

  /**
   * Whether the field has an error
   */
  hasError?: boolean;

  /**
   * Placeholder text for the select
   */
  placeholder?: string;

  /**
   * Whether to enable search/filter functionality
   */
  searchable?: boolean;

  /**
   * Whether to allow multiple selections
   */
  multi?: boolean;

  /**
   * Whether the select is open (controlled)
   */
  open?: boolean;

  /**
   * Callback when open state changes
   */
  onOpenChange?: (open: boolean) => void;

  /**
   * Callback when value changes
   */
  onChange?: (value: string | number | (string | number)[] | null) => void;

  /**
   * Search placeholder
   */
  searchPlaceholder?: string;

  /**
   * No options message
   */
  noOptionsMessage?: ReactNode;

  /**
   * Additional CSS class names
   */
  className?: string;

  /**
   * CSS class for the label
   */
  labelClassName?: string;

  /**
   * CSS class for the hint text
   */
  hintClassName?: string;

  /**
   * CSS class for the error message
   */
  errorClassName?: string;

  /**
   * CSS class for the select wrapper
   */
  wrapperClassName?: string;
}

export interface ComboboxProps extends SelectProps {
  /**
   * Whether to filter options by search term
   */
  filterOptions?: boolean;

  /**
   * Custom filter function
   */
  filterFn?: (options: SelectOption[], searchTerm: string) => SelectOption[];

  /**
   * Whether to create new options on unknown input
   */
  creatable?: boolean;
}
