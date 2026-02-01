/**
 * Chip component - pill-shaped interactive component
 * Supports color variants, icons, and removable state
 * Can be selectable for filtering/tags
 * WCAG 2.1 AA compliant
 */

import React from "react";
import { ColorVariant, Size } from "../../shared/types";
import "./Chip.css";

export interface ChipProps
  extends React.HTMLAttributes<HTMLButtonElement> {
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
  /** Make chip selectable/toggleable */
  selectable?: boolean;
  /** Whether chip is selected (for selectable chips) */
  selected?: boolean;
  /** Callback when chip is toggled (for selectable chips) */
  onToggle?: (selected: boolean) => void;
  /** Chip content */
  children?: React.ReactNode;
  /** Custom className */
  className?: string;
}

const Chip = React.forwardRef<HTMLButtonElement, ChipProps>(
  (
    {
      variant = "default",
      size = "md",
      icon,
      removable = false,
      onRemove,
      selectable = false,
      selected = false,
      onToggle,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (removable && e.currentTarget.querySelector(".chip-remove")?.contains(e.target as Node)) {
        return; // Let remove button handle it
      }
      if (selectable && onToggle) {
        onToggle(!selected);
      }
      props.onClick?.(e);
    };

    const classes = [
      "chip",
      `chip-${variant}`,
      `chip-${size}`,
      removable && "chip-removable",
      selectable && "chip-selectable",
      selectable && selected && "chip-selected",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <button
        ref={ref}
        type="button"
        className={classes}
        onClick={handleClick}
        aria-pressed={selectable ? selected : undefined}
        aria-label={selectable ? `Toggle ${children}` : undefined}
        {...props}
      >
        {icon && <span className="chip-icon">{icon}</span>}
        {children && <span className="chip-text">{children}</span>}
        {removable && (
          <button
            className="chip-remove"
            onClick={(e) => {
              e.stopPropagation();
              onRemove?.();
            }}
            aria-label={`Remove ${children || "chip"}`}
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
      </button>
    );
  }
);

Chip.displayName = "Chip";

export default Chip;
