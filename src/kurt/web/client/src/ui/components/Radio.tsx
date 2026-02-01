import React, { forwardRef } from 'react';
import { RadioProps, RadioGroupProps } from '../types/checkbox';
import './Radio.css';

/**
 * Radio component with label and description support
 * WCAG 2.1 AA compliant
 */
export const Radio = forwardRef<HTMLInputElement, RadioProps>(
  (
    {
      label,
      description,
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
    const radioId = id || `radio-${Math.random().toString(36).substr(2, 9)}`;

    const radioClassName = [
      'radio',
      disabled && 'radio--disabled',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div className={`radio-wrapper ${wrapperClassName}`.trim()}>
        <input
          ref={ref}
          id={radioId}
          type="radio"
          className={radioClassName}
          disabled={disabled}
          checked={checked}
          onChange={onChange}
          {...props}
        />

        {label && (
          <label htmlFor={radioId} className={`radio-label ${labelClassName}`.trim()}>
            <span className="radio-control">
              <span className="radio-indicator"></span>
            </span>
            <div className="radio-content">
              <span className="radio-label-text">{label}</span>
              {description && (
                <span className={`radio-description ${descriptionClassName}`.trim()}>
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

Radio.displayName = 'Radio';

/**
 * RadioGroup component for managing mutually exclusive radio buttons
 */
export const RadioGroup = forwardRef<HTMLDivElement, RadioGroupProps>(
  (
    {
      label,
      items,
      value,
      onChange,
      disabled = false,
      direction = 'vertical',
      className = '',
    },
    ref
  ) => {
    const groupId = `radio-group-${Math.random().toString(36).substr(2, 9)}`;
    const name = `radio-group-${groupId}`;

    return (
      <div
        ref={ref}
        className={`radio-group radio-group--${direction} ${className}`.trim()}
        role="radiogroup"
        aria-labelledby={label ? groupId : undefined}
      >
        {label && (
          <div id={groupId} className="radio-group-label">
            {label}
          </div>
        )}
        <div className="radio-group-items">
          {items.map((item) => (
            <Radio
              key={item.value}
              name={name}
              value={item.value}
              label={item.label}
              description={item.description}
              checked={value === item.value}
              onChange={(e) => {
                if (e.currentTarget.checked) {
                  onChange?.(item.value);
                }
              }}
              disabled={disabled || item.disabled}
            />
          ))}
        </div>
      </div>
    );
  }
);

RadioGroup.displayName = 'RadioGroup';
