import { ReactNode, FormHTMLAttributes } from 'react';

export interface FormGroupProps {
  /**
   * The label for the form group
   */
  label?: ReactNode;

  /**
   * Hint text below the label
   */
  hint?: ReactNode;

  /**
   * Error message
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
   * The form field content
   */
  children?: ReactNode;

  /**
   * CSS class names
   */
  className?: string;

  /**
   * CSS class for the label
   */
  labelClassName?: string;

  /**
   * CSS class for the hint
   */
  hintClassName?: string;

  /**
   * CSS class for the error
   */
  errorClassName?: string;
}

export interface FormFieldProps extends FormGroupProps {
  /**
   * The field name
   */
  name?: string;

  /**
   * The field value
   */
  value?: string | number | readonly string[];

  /**
   * Change callback
   */
  onChange?: (value: string | number) => void;

  /**
   * Whether the field is disabled
   */
  disabled?: boolean;

  /**
   * Field type (for auto-detection of component)
   */
  type?: string;
}

export interface FormLayoutProps extends FormHTMLAttributes<HTMLFormElement> {
  /**
   * Layout direction
   */
  layout?: 'vertical' | 'horizontal' | 'inline';

  /**
   * Gap between fields
   */
  gap?: 'sm' | 'md' | 'lg';

  /**
   * The form fields
   */
  children?: ReactNode;

  /**
   * CSS class names
   */
  className?: string;
}

export interface ValidationMessageProps {
  /**
   * The error message
   */
  message?: ReactNode;

  /**
   * The warning message
   */
  warning?: ReactNode;

  /**
   * The success message
   */
  success?: ReactNode;

  /**
   * CSS class names
   */
  className?: string;
}
