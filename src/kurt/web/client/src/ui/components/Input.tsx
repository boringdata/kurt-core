import React, { forwardRef } from 'react';
import { InputProps } from '../types/input';
import './Input.css';

/**
 * Input component with support for multiple input types
 * Provides built-in label, hint, and error message support
 * WCAG 2.1 AA compliant with proper accessibility attributes
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      type = 'text',
      label,
      hint,
      error,
      required = false,
      hasError = !!error,
      className = '',
      labelClassName = '',
      hintClassName = '',
      errorClassName = '',
      wrapperClassName = '',
      id,
      disabled = false,
      readOnly = false,
      placeholder,
      ...props
    },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
    const hintId = hint ? `${inputId}-hint` : undefined;
    const errorId = error ? `${inputId}-error` : undefined;

    // Combine aria-describedby for both hint and error
    const ariaDescribedBy = [hintId, hasError ? errorId : undefined]
      .filter(Boolean)
      .join(' ') || undefined;

    const inputClassName = [
      'input',
      `input--${type}`,
      disabled && 'input--disabled',
      readOnly && 'input--readonly',
      hasError && 'input--error',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div className={`input-wrapper ${wrapperClassName}`.trim()}>
        {label && (
          <label htmlFor={inputId} className={`input-label ${labelClassName}`.trim()}>
            {label}
            {required && <span className="input-required" aria-label="required">*</span>}
          </label>
        )}

        <input
          ref={ref}
          id={inputId}
          type={type}
          className={inputClassName}
          disabled={disabled}
          readOnly={readOnly}
          required={required}
          placeholder={placeholder}
          aria-label={typeof label === 'string' ? label : undefined}
          aria-describedby={ariaDescribedBy}
          aria-invalid={hasError}
          aria-required={required}
          {...props}
        />

        {hint && (
          <div id={hintId} className={`input-hint ${hintClassName}`.trim()}>
            {hint}
          </div>
        )}

        {error && hasError && (
          <div id={errorId} className={`input-error ${errorClassName}`.trim()} role="alert">
            {error}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
