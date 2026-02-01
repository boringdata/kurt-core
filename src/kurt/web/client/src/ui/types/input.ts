import { InputHTMLAttributes, ReactNode } from 'react';

export type InputType = 'text' | 'password' | 'email' | 'number' | 'tel' | 'url';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /**
   * The type of input field
   * @default 'text'
   */
  type?: InputType;

  /**
   * The label for the input field
   */
  label?: ReactNode;

  /**
   * Hint text displayed below the input
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
   * CSS class for the input wrapper
   */
  wrapperClassName?: string;
}
