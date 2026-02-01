import React, { forwardRef, useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { SelectProps, SelectOption } from '../types/select';
import './Select.css';

/**
 * Select component with support for single and multi-select
 * Includes keyboard navigation and search functionality
 * WCAG 2.1 AA compliant with proper accessibility attributes
 */
export const Select = forwardRef<HTMLDivElement, SelectProps>(
  (
    {
      options = [],
      groups,
      value,
      label,
      hint,
      error,
      required = false,
      hasError = !!error,
      placeholder = 'Select an option...',
      searchable = false,
      multi = false,
      open: controlledOpen,
      onOpenChange,
      onChange,
      searchPlaceholder = 'Search...',
      noOptionsMessage = 'No options available',
      className = '',
      labelClassName = '',
      hintClassName = '',
      errorClassName = '',
      wrapperClassName = '',
      disabled = false,
      id,
      ...props
    },
    ref
  ) => {
    const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;
    const hintId = hint ? `${selectId}-hint` : undefined;
    const errorId = error ? `${selectId}-error` : undefined;
    const listboxId = `${selectId}-listbox`;

    const [isOpen, setIsOpen] = useState(controlledOpen ?? false);
    const [searchTerm, setSearchTerm] = useState('');
    const [highlightedIndex, setHighlightedIndex] = useState(-1);
    const containerRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);
    const listboxRef = useRef<HTMLDivElement>(null);

    // Sync controlled open state
    useEffect(() => {
      if (controlledOpen !== undefined) {
        setIsOpen(controlledOpen);
      }
    }, [controlledOpen]);

    // Focus search input when opened
    useEffect(() => {
      if (isOpen && searchable && searchInputRef.current) {
        searchInputRef.current.focus();
      }
    }, [isOpen, searchable]);

    // Filter options based on search
    const filteredOptions = useMemo(() => {
      if (!searchable || !searchTerm) return options;
      const term = searchTerm.toLowerCase();
      return options.filter(
        (opt) =>
          String(opt.label).toLowerCase().includes(term) ||
          String(opt.value).toLowerCase().includes(term)
      );
    }, [options, searchable, searchTerm]);

    // Get selected option
    const selectedOption = useMemo(() => {
      if (!value) return null;
      return options.find((opt) => opt.value === value);
    }, [value, options]);

    const handleOpen = useCallback(() => {
      if (!disabled) {
        const newOpen = !isOpen;
        setIsOpen(newOpen);
        onOpenChange?.(newOpen);
        setSearchTerm('');
      }
    }, [isOpen, disabled, onOpenChange]);

    const handleSelect = useCallback(
      (option: SelectOption) => {
        if (option.disabled) return;

        if (multi && Array.isArray(value)) {
          const newValue = value.includes(option.value as never)
            ? (value as any[]).filter((v) => v !== option.value)
            : [...value, option.value];
          onChange?.(newValue);
        } else {
          onChange?.(option.value);
          setIsOpen(false);
          onOpenChange?.(false);
        }
      },
      [value, multi, onChange, onOpenChange]
    );

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent) => {
        if (!isOpen) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleOpen();
          }
          return;
        }

        switch (e.key) {
          case 'Escape':
            e.preventDefault();
            setIsOpen(false);
            onOpenChange?.(false);
            break;
          case 'ArrowDown':
            e.preventDefault();
            setHighlightedIndex((prev) =>
              prev < filteredOptions.length - 1 ? prev + 1 : prev
            );
            break;
          case 'ArrowUp':
            e.preventDefault();
            setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
            break;
          case 'Enter':
            e.preventDefault();
            if (highlightedIndex >= 0) {
              handleSelect(filteredOptions[highlightedIndex]);
            }
            break;
          case 'Tab':
            setIsOpen(false);
            onOpenChange?.(false);
            break;
          default:
            if (searchable && e.key.length === 1) {
              setSearchTerm((prev) => prev + e.key);
            }
        }
      },
      [isOpen, filteredOptions, highlightedIndex, handleOpen, handleSelect, searchable, onOpenChange]
    );

    // Close on click outside
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (
          containerRef.current &&
          !containerRef.current.contains(event.target as Node)
        ) {
          setIsOpen(false);
          onOpenChange?.(false);
        }
      };

      if (isOpen) {
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
          document.removeEventListener('mousedown', handleClickOutside);
        };
      }
    }, [isOpen, onOpenChange]);

    const ariaDescribedBy = [hintId, hasError ? errorId : undefined]
      .filter(Boolean)
      .join(' ') || undefined;

    const selectClassName = [
      'select',
      disabled && 'select--disabled',
      hasError && 'select--error',
      isOpen && 'select--open',
      className,
    ]
      .filter(Boolean)
      .join(' ');

    return (
      <div ref={ref} className={`select-wrapper ${wrapperClassName}`.trim()}>
        {label && (
          <label htmlFor={selectId} className={`select-label ${labelClassName}`.trim()}>
            {label}
            {required && <span className="select-required" aria-label="required">*</span>}
          </label>
        )}

        <div
          ref={containerRef}
          className={selectClassName}
          role="combobox"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-owns={listboxId}
          aria-controls={listboxId}
          aria-disabled={disabled}
        >
          <button
            id={selectId}
            type="button"
            className="select-trigger"
            onClick={handleOpen}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            aria-label={typeof label === 'string' ? label : undefined}
            aria-describedby={ariaDescribedBy}
            aria-invalid={hasError}
            aria-required={required}
          >
            <span className="select-trigger-text">
              {selectedOption ? selectedOption.label : placeholder}
            </span>
            <svg
              className="select-trigger-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          {isOpen && (
            <div
              ref={listboxRef}
              id={listboxId}
              className="select-content"
              role="listbox"
              aria-label={typeof label === 'string' ? label : undefined}
            >
              {searchable && (
                <input
                  ref={searchInputRef}
                  type="text"
                  className="select-search"
                  placeholder={searchPlaceholder}
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setHighlightedIndex(0);
                  }}
                  onKeyDown={handleKeyDown}
                  aria-label="Search options"
                />
              )}

              <div className="select-options">
                {filteredOptions.length === 0 ? (
                  <div className="select-no-options">{noOptionsMessage}</div>
                ) : (
                  filteredOptions.map((option, index) => (
                    <button
                      key={option.value}
                      type="button"
                      className={[
                        'select-option',
                        option.disabled && 'select-option--disabled',
                        highlightedIndex === index && 'select-option--highlighted',
                        value === option.value && 'select-option--selected',
                      ]
                        .filter(Boolean)
                        .join(' ')}
                      onClick={() => handleSelect(option)}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      disabled={option.disabled}
                      role="option"
                      aria-selected={value === option.value}
                    >
                      {multi && Array.isArray(value) && (
                        <input
                          type="checkbox"
                          checked={value.includes(option.value as never)}
                          onChange={() => {}}
                          aria-hidden="true"
                          tabIndex={-1}
                        />
                      )}
                      <div className="select-option-content">
                        <span className="select-option-label">{option.label}</span>
                        {option.description && (
                          <span className="select-option-description">{option.description}</span>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {hint && (
          <div id={hintId} className={`select-hint ${hintClassName}`.trim()}>
            {hint}
          </div>
        )}

        {error && hasError && (
          <div id={errorId} className={`select-error ${errorClassName}`.trim()} role="alert">
            {error}
          </div>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';
