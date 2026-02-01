import { TextareaHTMLAttributes, ReactNode } from 'react';

export interface TextareaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'rows'> {
  /**
   * The label for the textarea
   */
  label?: ReactNode;

  /**
   * Hint text displayed below the textarea
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
   * Whether to auto-resize the textarea based on content
   */
  autoResize?: boolean;

  /**
   * Minimum number of rows
   */
  minRows?: number;

  /**
   * Maximum number of rows (only applies when autoResize is true)
   */
  maxRows?: number;

  /**
   * Whether to show character count
   */
  showCharCount?: boolean;

  /**
   * Maximum character count
   */
  maxCharacters?: number;

  /**
   * Whether the textarea is resizable (CSS resize property)
   */
  resizable?: boolean;

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
   * CSS class for the textarea wrapper
   */
  wrapperClassName?: string;

  /**
   * CSS class for the character count
   */
  charCountClassName?: string;
}
