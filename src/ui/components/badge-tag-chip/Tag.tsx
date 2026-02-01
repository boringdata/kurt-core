/**
 * Tag component - interactive label with optional remove functionality
 * Supports color variants, icons, and removable state
 * WCAG 2.1 AA compliant
 */

import React from "react";
import { ColorVariant, Size } from "../../shared/types";
import "./Tag.css";

export interface TagProps
  extends React.HTMLAttributes<HTMLDivElement> {
  /** Color variant */
  variant?: ColorVariant;
  /** Size variant */
  size?: Exclude<Size, "lg">;
  /** Icon to display before text */
  icon?: React.ReactNode;
  /** Show remove button */
  removable?: boolean;
  /** Callback when remove button is clicked */
  onRemove?: () => void;
  /** Tag content */
  children?: React.ReactNode;
  /** Custom className */
  className?: string;
}

const Tag = React.forwardRef<HTMLDivElement, TagProps>(
  (
    {
      variant = "default",
      size = "md",
      icon,
      removable = false,
      onRemove,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    const classes = [
      "tag",
      `tag-${variant}`,
      `tag-${size}`,
      removable && "tag-removable",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div ref={ref} className={classes} role="group" {...props}>
        {icon && <span className="tag-icon">{icon}</span>}
        {children && <span className="tag-text">{children}</span>}
        {removable && (
          <button
            className="tag-remove"
            onClick={onRemove}
            aria-label={`Remove ${children || "tag"}`}
            type="button"
          >
            <svg
              width="1em"
              height="1em"
              viewBox="0 0 16 16"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M.293.293a1 1 0 011.414 0L8 6.586 14.293.293a1 1 0 111.414 1.414L9.414 8l6.293 6.293a1 1 0 01-1.414 1.414L8 9.414l-6.293 6.293a1 1 0 01-1.414-1.414L6.586 8 .293 1.707a1 1 0 010-1.414z" />
            </svg>
          </button>
        )}
      </div>
    );
  }
);

Tag.displayName = "Tag";

export default Tag;
