import React, { forwardRef, useEffect, useRef } from 'react';
import { CheckboxProps, CheckboxGroupProps } from '../types/checkbox';
import './Checkbox.css';

/**
 * Checkbox component with label and description support
 * Supports indeterminate state
 * WCAG 2.1 AA compliant
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  (
    {
      label,
      description,
      indeterminate = false,
      className = '',
      labelClassName = '',
      descriptionClassName = '',
      wrapperClassName = '',
      id,
      disabled = false,
      checked,
      onChange,
      ...props
    },
    ref
  ) => {
    const checkboxId = id || `checkbox-${Math.random().toString(36).substr(2, 9)}`;
    const internalRef = useRef<HTMLInputElement>(null);

    // Handle indeterminate state
    useEffect(() => {
      if (internalRef.current) {
        internalRef.current.indeterminate = indeterminate;
      }
    }, [indeterminate]);

    const checkboxClassName = [
      'checkbox',
      disabled && 'checkbox--disabled',
      indeterminate && 'checkbox--indeterminate',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div className={`checkbox-wrapper ${wrapperClassName}`.trim()}>
        <input
          ref={ref || internalRef}
          id={checkboxId}
          type="checkbox"
          className={checkboxClassName}
          disabled={disabled}
          checked={checked}
          onChange={onChange}
          aria-checked={indeterminate ? 'mixed' : undefined}
          {...props}
        />

        {label && (
          <label htmlFor={checkboxId} className={`checkbox-label ${labelClassName}`.trim()}>
            <span className="checkbox-control">
              <svg className="checkbox-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
            <div className="checkbox-content">
              <span className="checkbox-label-text">{label}</span>
              {description && (
                <span className={`checkbox-description ${descriptionClassName}`.trim()}>
                  {description}
                </span>
              )}
            </div>
          </label>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

/**
 * CheckboxGroup component for managing multiple related checkboxes
 */
export const CheckboxGroup = forwardRef<HTMLDivElement, CheckboxGroupProps>(
  (
    {
      label,
      items,
      value = [],
      onChange,
      disabled = false,
      direction = 'vertical',
      className = '',
    },
    ref
  ) => {
    const groupId = `checkbox-group-${Math.random().toString(36).substr(2, 9)}`;

    const handleChange = (itemValue: string | number, checked: boolean) => {
      const newValue = checked
        ? [...value, itemValue]
        : value.filter((v) => v !== itemValue);
      onChange?.(newValue);
    };

    return (
      <div
        ref={ref}
        className={`checkbox-group checkbox-group--${direction} ${className}`.trim()}
        role="group"
        aria-labelledby={label ? groupId : undefined}
      >
        {label && (
          <div id={groupId} className="checkbox-group-label">
            {label}
          </div>
        )}
        <div className="checkbox-group-items">
          {items.map((item) => (
            <Checkbox
              key={item.value}
              label={item.label}
              description={item.description}
              checked={value.includes(item.value)}
              onChange={(e) => handleChange(item.value, e.currentTarget.checked)}
              disabled={disabled || item.disabled}
            />
          ))}
        </div>
      </div>
    );
  }
);

CheckboxGroup.displayName = 'CheckboxGroup';
