import React, { forwardRef, useEffect, useRef } from 'react';
import { TextareaProps } from '../types/textarea';
import './Textarea.css';

/**
 * Textarea component with auto-resize and character count support
 * WCAG 2.1 AA compliant with proper accessibility attributes
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      label,
      hint,
      error,
      required = false,
      hasError = !!error,
      autoResize = true,
      minRows = 3,
      maxRows = 10,
      showCharCount = false,
      maxCharacters,
      resizable = !autoResize,
      className = '',
      labelClassName = '',
      hintClassName = '',
      errorClassName = '',
      wrapperClassName = '',
      charCountClassName = '',
      id,
      disabled = false,
      readOnly = false,
      value,
      onChange,
      ...props
    },
    ref
  ) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const internalRef = useRef<HTMLTextAreaElement>(null);

    // Use provided ref or internal ref
    const finalRef = (ref as React.Ref<HTMLTextAreaElement>) || internalRef;

    const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;
    const hintId = hint ? `${textareaId}-hint` : undefined;
    const errorId = error ? `${textareaId}-error` : undefined;
    const charCountId = showCharCount ? `${textareaId}-charcount` : undefined;

    const ariaDescribedBy = [hintId, hasError ? errorId : undefined, charCountId]
      .filter(Boolean)
      .join(' ') || undefined;

    // Auto-resize textarea
    const updateHeight = () => {
      if (!textareaRef.current || !autoResize) return;

      const textarea = textareaRef.current;
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      const lineHeight = parseInt(window.getComputedStyle(textarea).lineHeight, 10);
      const rowHeight = lineHeight || 20;

      const minHeight = minRows * rowHeight;
      const maxHeight = maxRows * rowHeight;

      const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
      textarea.style.height = `${newHeight}px`;
    };

    useEffect(() => {
      updateHeight();
    }, [value, autoResize, minRows, maxRows]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      updateHeight();
      onChange?.(e);
    };

    const currentLength = typeof value === 'string' ? value.length : 0;
    const charCountPercentage = maxCharacters ? (currentLength / maxCharacters) * 100 : 0;
    const charCountStatus =
      maxCharacters && currentLength >= maxCharacters * 0.9 ? 'warning' : 'normal';

    const textareaClassName = [
      'textarea',
      disabled && 'textarea--disabled',
      readOnly && 'textarea--readonly',
      hasError && 'textarea--error',
      !resizable && 'textarea--no-resize',
      autoResize && 'textarea--auto-resize',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div className={`textarea-wrapper ${wrapperClassName}`.trim()}>
        {label && (
          <label htmlFor={textareaId} className={`textarea-label ${labelClassName}`.trim()}>
            {label}
            {required && <span className="textarea-required" aria-label="required">*</span>}
          </label>
        )}

        <textarea
          ref={textareaRef}
          id={textareaId}
          className={textareaClassName}
          disabled={disabled}
          readOnly={readOnly}
          required={required}
          value={value}
          onChange={handleChange}
          maxLength={maxCharacters}
          aria-label={typeof label === 'string' ? label : undefined}
          aria-describedby={ariaDescribedBy}
          aria-invalid={hasError}
          aria-required={required}
          rows={minRows}
          {...props}
        />

        <div className="textarea-footer">
          {hint && (
            <div id={hintId} className={`textarea-hint ${hintClassName}`.trim()}>
              {hint}
            </div>
          )}

          {showCharCount && maxCharacters && (
            <div
              id={charCountId}
              className={`textarea-charcount textarea-charcount--${charCountStatus} ${charCountClassName}`.trim()}
              aria-live="polite"
              aria-atomic="true"
            >
              <span className="textarea-charcount-current">{currentLength}</span>
              <span className="textarea-charcount-separator">/</span>
              <span className="textarea-charcount-max">{maxCharacters}</span>
            </div>
          )}
        </div>

        {error && hasError && (
          <div id={errorId} className={`textarea-error ${errorClassName}`.trim()} role="alert">
            {error}
          </div>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
