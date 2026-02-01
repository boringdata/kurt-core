/**
 * Badge component - non-interactive label
 * Supports color variants and icon support
 * WCAG 2.1 AA compliant
 */

import React from "react";
import { ColorVariant, Size } from "../../shared/types";
import "./Badge.css";

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement> {
  /** Color variant */
  variant?: ColorVariant;
  /** Size variant */
  size?: Exclude<Size, "lg">;
  /** Icon to display before text */
  icon?: React.ReactNode;
  /** Badge content */
  children?: React.ReactNode;
  /** Custom className */
  className?: string;
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      variant = "default",
      size = "md",
      icon,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    const classes = [
      "badge",
      `badge-${variant}`,
      `badge-${size}`,
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <span ref={ref} className={classes} {...props}>
        {icon && <span className="badge-icon">{icon}</span>}
        {children && <span className="badge-text">{children}</span>}
      </span>
    );
  }
);

Badge.displayName = "Badge";

export default Badge;
