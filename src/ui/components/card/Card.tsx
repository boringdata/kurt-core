/**
 * Card component with flexible sections
 * Supports CardHeader, CardBody, CardFooter with elevation/shadow variants
 * WCAG 2.1 AA compliant
 */

import React from "react";
import "./Card.css";

export type ShadowVariant = "none" | "sm" | "md" | "lg";

export interface CardProps
  extends React.HTMLAttributes<HTMLDivElement> {
  /** Shadow/elevation variant */
  shadow?: ShadowVariant;
  /** Add border to card */
  bordered?: boolean;
  /** Custom className */
  className?: string;
  /** Card content */
  children?: React.ReactNode;
  /** Make card clickable */
  clickable?: boolean;
  /** Padding size */
  padding?: "sm" | "md" | "lg";
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      shadow = "md",
      bordered = false,
      className = "",
      children,
      clickable = false,
      padding = "md",
      ...props
    },
    ref
  ) => {
    const classes = [
      "card",
      `card-shadow-${shadow}`,
      bordered && "card-bordered",
      clickable && "card-clickable",
      `card-padding-${padding}`,
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div
        ref={ref}
        className={classes}
        role={clickable ? "button" : "article"}
        tabIndex={clickable ? 0 : undefined}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

export interface CardHeaderProps
  extends React.HTMLAttributes<HTMLDivElement> {
  /** Header content */
  children?: React.ReactNode;
  /** Custom className */
  className?: string;
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className = "", children, ...props }, ref) => {
    const classes = ["card-header", className].filter(Boolean).join(" ");

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);

CardHeader.displayName = "CardHeader";

export interface CardBodyProps
  extends React.HTMLAttributes<HTMLDivElement> {
  /** Body content */
  children?: React.ReactNode;
  /** Custom className */
  className?: string;
}

export const CardBody = React.forwardRef<HTMLDivElement, CardBodyProps>(
  ({ className = "", children, ...props }, ref) => {
    const classes = ["card-body", className].filter(Boolean).join(" ");

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);

CardBody.displayName = "CardBody";

export interface CardFooterProps
  extends React.HTMLAttributes<HTMLDivElement> {
  /** Footer content */
  children?: React.ReactNode;
  /** Custom className */
  className?: string;
}

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className = "", children, ...props }, ref) => {
    const classes = ["card-footer", className].filter(Boolean).join(" ");

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);

CardFooter.displayName = "CardFooter";

export default Card;
