/**
 * List and ListItem component types and interfaces
 */

export type ListType = 'ul' | 'ol';

export interface ListProps {
  /** Items to render */
  items?: React.ReactNode[];
  /** Children elements (used if items not provided) */
  children?: React.ReactNode;
  /** List type: ordered or unordered */
  type?: ListType;
  /** Enable dividers between items */
  divided?: boolean;
  /** Custom className */
  className?: string;
  /** Compact spacing variant */
  compact?: boolean;
  /** Role for accessibility */
  role?: string;
}

export interface ListItemProps {
  /** Primary content/title */
  children?: React.ReactNode;
  /** Avatar element */
  avatar?: React.ReactNode;
  /** Icon element */
  icon?: React.ReactNode;
  /** Subtitle or secondary text */
  subtitle?: React.ReactNode;
  /** Description or additional content */
  description?: React.ReactNode;
  /** Content slot for custom middle content */
  content?: React.ReactNode;
  /** Action slot (right side, e.g., buttons, icons) */
  action?: React.ReactNode;
  /** Whether the item is clickable */
  clickable?: boolean;
  /** Callback when item is clicked */
  onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
  /** Disabled state */
  disabled?: boolean;
  /** Selected state */
  selected?: boolean;
  /** Show divider below item */
  divider?: boolean;
  /** Custom className */
  className?: string;
  /** Custom content className */
  contentClassName?: string;
  /** Href for link behavior */
  href?: string;
  /** Target for link */
  target?: string;
  /** Rel for link */
  rel?: string;
  /** Whether item is active/highlighted */
  active?: boolean;
}

export interface AvatarProps {
  /** Avatar URL or initials */
  src?: string;
  /** Alternative text for image */
  alt?: string;
  /** Avatar size */
  size?: 'sm' | 'md' | 'lg';
  /** Background color for initials */
  color?: string;
  /** Initials/fallback text */
  initials?: string;
}

export interface ListIconProps {
  /** Icon element */
  children?: React.ReactNode;
  /** Icon size */
  size?: 'sm' | 'md' | 'lg';
  /** Custom className */
  className?: string;
}
