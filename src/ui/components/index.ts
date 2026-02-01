/**
 * Boring UI Components - Complete Component Library
 *
 * This is the main entry point for all UI components.
 * Includes infrastructure components and all reusable UI elements.
 */

// Infrastructure Components (Story AA, AB, AC)
export { Portal } from './Portal';
export { FocusTrap } from './FocusTrap';
export {
  calculatePosition,
  applyPosition,
  useFloating,
  type Placement,
  type Position,
  type PopperOptions,
} from './Positioning';

// Component Stories (Q-Z)

// Story Q: Pagination
export { default as Pagination } from './Pagination';

// Story R: Skeleton/Loading
export {
  default as Skeleton,
  SkeletonGroup,
  SkeletonCard,
  SkeletonText,
  SkeletonTable,
} from './Skeleton';

// Story S: Spinner/Loading indicator
export {
  default as Spinner,
  LoadingOverlay,
  InlineSpinner,
} from './Spinner';

// Story T: Avatar
export {
  default as Avatar,
  AvatarGroup,
  AvatarWithBadge,
} from './Avatar';

// Story U: Dropdown/Menu
export {
  default as Dropdown,
  DropdownMenu,
  DropdownTrigger,
} from './Dropdown';

// Story V: Layout utilities
export {
  default as Container,
  Grid,
  Flex,
  Stack,
  VStack,
  HStack,
  Spacer,
  LayoutDivider,
} from './Layout';

// Story W: Progress Bar
export {
  default as ProgressBar,
  SteppedProgress,
  CircularProgress,
  ProgressGroup,
} from './ProgressBar';

// Story X: Divider/Separator
export {
  default as Divider,
  SectionDivider,
  TextDivider,
  BorderBox,
} from './Divider';

// Story Y: Icon and Icon Button
export {
  default as Icon,
  IconButton,
  IconButtonGroup,
  IconWithText,
  IconBadge,
} from './Icon';

// Story Z: Tooltip and Popover
export {
  default as Tooltip,
  Popover,
  InfoIcon,
  HoverCard,
} from './Tooltip';

export default {
  Portal,
  FocusTrap,
  Positioning: { calculatePosition, applyPosition, useFloating },
  Pagination,
  Skeleton,
  Spinner,
  Avatar,
  Dropdown,
  Container,
  ProgressBar,
  Divider,
  Icon,
  Tooltip,
};
