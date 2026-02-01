import { InputHTMLAttributes, ReactNode } from 'react';

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /**
   * The label for the checkbox
   */
  label?: ReactNode;

  /**
   * Description text below the label
   */
  description?: ReactNode;

  /**
   * Whether the checkbox is indeterminate
   */
  indeterminate?: boolean;

  /**
   * Additional CSS class names
   */
  className?: string;

  /**
   * CSS class for the label
   */
  labelClassName?: string;

  /**
   * CSS class for the description
   */
  descriptionClassName?: string;

  /**
   * CSS class for the wrapper
   */
  wrapperClassName?: string;
}

export interface CheckboxGroupProps {
  /**
   * The label for the group
   */
  label?: ReactNode;

  /**
   * The checkboxes to display
   */
  items: Array<{
    value: string | number;
    label: ReactNode;
    description?: ReactNode;
    disabled?: boolean;
  }>;

  /**
   * The currently selected values
   */
  value?: (string | number)[];

  /**
   * Callback when value changes
   */
  onChange?: (value: (string | number)[]) => void;

  /**
   * Whether the group is disabled
   */
  disabled?: boolean;

  /**
   * Layout direction
   */
  direction?: 'vertical' | 'horizontal';

  /**
   * Additional CSS class names
   */
  className?: string;
}

export interface RadioProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /**
   * The label for the radio
   */
  label?: ReactNode;

  /**
   * Description text below the label
   */
  description?: ReactNode;

  /**
   * Additional CSS class names
   */
  className?: string;

  /**
   * CSS class for the label
   */
  labelClassName?: string;

  /**
   * CSS class for the description
   */
  descriptionClassName?: string;

  /**
   * CSS class for the wrapper
   */
  wrapperClassName?: string;
}

export interface RadioGroupProps {
  /**
   * The label for the group
   */
  label?: ReactNode;

  /**
   * The radio buttons to display
   */
  items: Array<{
    value: string | number;
    label: ReactNode;
    description?: ReactNode;
    disabled?: boolean;
  }>;

  /**
   * The currently selected value
   */
  value?: string | number | null;

  /**
   * Callback when value changes
   */
  onChange?: (value: string | number) => void;

  /**
   * Whether the group is disabled
   */
  disabled?: boolean;

  /**
   * Layout direction
   */
  direction?: 'vertical' | 'horizontal';

  /**
   * Additional CSS class names
   */
  className?: string;
}
