/**
 * Shared type definitions for Boring UI components
 */

export type Size = "sm" | "md" | "lg";
export type Variant = "primary" | "secondary" | "danger" | "outline" | "ghost";
export type ColorVariant = "success" | "warning" | "error" | "info" | "default";

export interface HTMLAttributes {
  className?: string;
  style?: React.CSSProperties;
  [key: string]: any;
}

export type AriaLive = "polite" | "assertive" | "off";
