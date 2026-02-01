/**
 * Button component with variants, sizes, and states
 * Supports primary, secondary, danger, outline, and ghost variants
 * Includes loading state with spinner, icon support, and disabled state
 * WCAG 2.1 AA compliant
 */

import React from "react";
import { Variant, Size } from "../../shared/types";
import "./Button.css";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style variant */
  variant?: Variant;
  /** Button size */
  size?: Size;
  /** Display loading state with spinner */
  loading?: boolean;
  /** Icon component or element (placed left of text) */
  icon?: React.ReactNode;
  /** Icon placed on right side instead of left */
  iconRight?: React.ReactNode;
  /** Optional href to make button act like a link */
  href?: string;
  /** Link target (_blank, _self, etc) */
  target?: string;
  /** Custom className to merge with internal styles */
  className?: string;
  /** Button content */
  children?: React.ReactNode;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      icon,
      iconRight,
      href,
      target,
      disabled = false,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    // Build class names
    const classes = [
      "btn",
      `btn-${variant}`,
      `btn-${size}`,
      loading && "btn-loading",
      disabled && "btn-disabled",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    // If href is provided, render as anchor element
    if (href && !disabled && !loading) {
      return (
        <a
          href={href}
          target={target}
          className={classes}
          rel={target === "_blank" ? "noopener noreferrer" : undefined}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              window.location.href = href;
            }
          }}
        >
          {icon && <span className="btn-icon btn-icon-left">{icon}</span>}
          {children && <span className="btn-text">{children}</span>}
          {iconRight && (
            <span className="btn-icon btn-icon-right">{iconRight}</span>
          )}
        </a>
      );
    }

    return (
      <button
        ref={ref}
        type="button"
        disabled={disabled || loading}
        className={classes}
        aria-disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        {loading && <span className="btn-spinner" aria-hidden="true" />}
        {icon && !loading && (
          <span className="btn-icon btn-icon-left">{icon}</span>
        )}
        {children && <span className="btn-text">{children}</span>}
        {iconRight && !loading && (
          <span className="btn-icon btn-icon-right">{iconRight}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
