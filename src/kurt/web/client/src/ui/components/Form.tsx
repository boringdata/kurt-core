import React, { forwardRef } from 'react';
import {
  FormGroupProps,
  FormLayoutProps,
  ValidationMessageProps,
} from '../types/form';
import './Form.css';

/**
 * FormGroup component for wrapping form fields with label, hint, and error
 */
export const FormGroup = forwardRef<HTMLDivElement, FormGroupProps>(
  (
    {
      label,
      hint,
      error,
      required = false,
      hasError = !!error,
      children,
      className = '',
      labelClassName = '',
      hintClassName = '',
      errorClassName = '',
    },
    ref
  ) => {
    const groupId = `form-group-${Math.random().toString(36).substr(2, 9)}`;
    const hintId = hint ? `${groupId}-hint` : undefined;
    const errorId = error ? `${groupId}-error` : undefined;

    return (
      <div
        ref={ref}
        className={`form-group ${hasError ? 'form-group--error' : ''} ${className}`.trim()}
      >
        {label && (
          <label className={`form-group-label ${labelClassName}`.trim()}>
            {label}
            {required && <span className="form-required" aria-label="required">*</span>}
          </label>
        )}

        {hint && (
          <div id={hintId} className={`form-group-hint ${hintClassName}`.trim()}>
            {hint}
          </div>
        )}

        <div className="form-group-content">{children}</div>

        {error && hasError && (
          <div id={errorId} className={`form-group-error ${errorClassName}`.trim()} role="alert">
            {error}
          </div>
        )}
      </div>
    );
  }
);

FormGroup.displayName = 'FormGroup';

/**
 * FormLayout component for wrapping a form with layout utilities
 */
export const FormLayout = forwardRef<HTMLFormElement, FormLayoutProps>(
  (
    {
      layout = 'vertical',
      gap = 'md',
      children,
      className = '',
      ...props
    },
    ref
  ) => {
    const formClassName = [
      'form-layout',
      `form-layout--${layout}`,
      `form-layout--gap-${gap}`,
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <form ref={ref} className={formClassName} {...props}>
        {children}
      </form>
    );
  }
);

FormLayout.displayName = 'FormLayout';

/**
 * ValidationMessage component for displaying validation feedback
 */
export const ValidationMessage = forwardRef<HTMLDivElement, ValidationMessageProps>(
  (
    {
      message,
      warning,
      success,
      className = '',
    },
    ref
  ) => {
    let type = 'error';
    let content = message;

    if (success) {
      type = 'success';
      content = success;
    } else if (warning) {
      type = 'warning';
      content = warning;
    }

    if (!content) {
      return null;
    }

    const validationClassName = [
      'validation-message',
      `validation-message--${type}`,
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div
        ref={ref}
        className={validationClassName}
        role={type === 'error' ? 'alert' : 'status'}
      >
        {type === 'error' && (
          <svg
            className="validation-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        )}
        {type === 'warning' && (
          <svg
            className="validation-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3.05h16.94a2 2 0 0 0 1.71-3.05L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
        )}
        {type === 'success' && (
          <svg
            className="validation-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        )}
        <span className="validation-text">{content}</span>
      </div>
    );
  }
);

ValidationMessage.displayName = 'ValidationMessage';

/**
 * FormSection component for grouping related fields
 */
export const FormSection = forwardRef<HTMLDivElement, { title?: string; description?: string; children?: React.ReactNode; className?: string }>(
  ({ title, description, children, className = '' }, ref) => {
    return (
      <div ref={ref} className={`form-section ${className}`.trim()}>
        {title && <h3 className="form-section-title">{title}</h3>}
        {description && <p className="form-section-description">{description}</p>}
        <div className="form-section-content">{children}</div>
      </div>
    );
  }
);

FormSection.displayName = 'FormSection';
