# Boring UI Components Library

Complete component library for the Boring UI system. All components are:
- **Type-safe**: Full TypeScript support
- **Accessible**: WCAG 2.1 AA compliant
- **Customizable**: Extensive prop support
- **Production-ready**: Thoroughly tested

## Infrastructure Components

### Portal (Story AA)
Renders content outside the DOM hierarchy. Essential for modals, dropdowns, tooltips.

```tsx
import { Portal } from '@/ui/components';

<Portal>
  <Modal>...</Modal>
</Portal>
```

**Features:**
- Renders to custom container or body
- Automatic cleanup
- Optional id/className

### FocusTrap (Story AB)
Traps keyboard focus within a container for modals and dialogs.

```tsx
import { FocusTrap } from '@/ui/components';

<FocusTrap active={isOpen} onEscapeKey={handleClose}>
  <Modal>...</Modal>
</FocusTrap>
```

**Features:**
- Tab cycling within container
- Escape key handling
- Restore focus on unmount
- Automatic focusable element detection

### Positioning (Story AC)
Calculate and apply positions for floating elements.

```tsx
import { calculatePosition, applyPosition, useFloating } from '@/ui/components';

const position = calculatePosition(referenceEl, floatingEl, {
  placement: 'bottom',
  offset: [0, 8],
});
applyPosition(floatingEl, position);
```

**Features:**
- 12 placement options
- Viewport boundary detection
- Custom offsets
- Auto-adjustment for off-screen elements

---

## Display Components

### Pagination (Story Q)
Navigate through pages of content.

```tsx
import { Pagination } from '@/ui/components';

<Pagination
  currentPage={page}
  totalPages={totalPages}
  onPageChange={setPage}
/>
```

**Props:**
- `currentPage`: Current page number (1-indexed)
- `totalPages`: Total number of pages
- `onPageChange`: Callback when page changes
- `siblingsCount`: Pages to show on each side of current
- `showFirstLast`: Show first/last buttons

**Accessibility:**
- Keyboard navigation (arrow keys, Enter)
- ARIA labels on all buttons
- Current page indication with `aria-current="page"`

### Skeleton (Story R)
Loading placeholders for content.

```tsx
import { Skeleton, SkeletonCard, SkeletonText } from '@/ui/components';

<Skeleton height={20} width="100%" />
<SkeletonCard count={3} />
<SkeletonText lines={3} />
```

**Components:**
- `Skeleton`: Individual placeholder
- `SkeletonGroup`: Multiple placeholders
- `SkeletonCard`: Card-shaped placeholder
- `SkeletonText`: Text line placeholders
- `SkeletonTable`: Table structure placeholder

**Props:**
- `width`: Width of skeleton
- `height`: Height of skeleton
- `radius`: Border radius (none, small, medium, large, full)
- `variant`: Shape type (text, circle, rect)
- `animation`: Animation (pulse, wave, none)

### Spinner (Story S)
Animated loading indicator.

```tsx
import { Spinner, LoadingOverlay } from '@/ui/components';

<Spinner size="medium" variant="ring" />
<LoadingOverlay isVisible={isLoading} message="Loading..." />
```

**Components:**
- `Spinner`: Rotating spinner
- `LoadingOverlay`: Full-page overlay
- `InlineSpinner`: Spinner with text

**Props:**
- `size`: small, medium, large
- `variant`: ring, dots, bar
- `color`: Custom color
- `label`: Accessible label

---

## User Components

### Avatar (Story T)
User avatar with image, initials, or icon fallback.

```tsx
import { Avatar, AvatarGroup } from '@/ui/components';

<Avatar src="user.jpg" alt="John Doe" status="online" />
<Avatar initials="JD" />
<AvatarGroup
  avatars={[
    { src: 'user1.jpg' },
    { initials: 'JD' },
  ]}
/>
```

**Components:**
- `Avatar`: Single avatar
- `AvatarGroup`: Grouped avatars
- `AvatarWithBadge`: Avatar with badge

**Props:**
- `src`: Image URL
- `alt`: Alt text
- `initials`: Fallback initials
- `size`: small, medium, large, xl
- `status`: online, offline, away, none
- `showStatus`: Display status indicator

### Dropdown (Story U)
Accessible menu component with keyboard navigation.

```tsx
import { Dropdown, DropdownMenu } from '@/ui/components';

<Dropdown
  trigger="Menu"
  items={[
    { id: 'edit', label: 'Edit' },
    { id: 'delete', label: 'Delete', divider: true },
  ]}
  onSelect={(id) => console.log(id)}
/>
```

**Components:**
- `Dropdown`: Complete dropdown menu
- `DropdownMenu`: Menu content
- `DropdownTrigger`: Trigger button

**Features:**
- Arrow key navigation
- Click outside to close
- Keyboard support (Enter, Escape)
- Disabled items
- Dividers and icons

---

## Layout Components

### Container (Story V)
Max-width constrained container.

```tsx
import { Container } from '@/ui/components';

<Container maxWidth="lg" center>
  <h1>Page Title</h1>
</Container>
```

### Grid
CSS Grid layout wrapper.

```tsx
import { Grid } from '@/ui/components';

<Grid columns={3} gap="16px">
  {items.map(item => <div key={item.id}>{item}</div>)}
</Grid>
```

### Flex
Flexbox layout wrapper.

```tsx
import { Flex } from '@/ui/components';

<Flex justify="between" align="center" gap="12px">
  <div>Left</div>
  <div>Right</div>
</Flex>
```

### Stack (VStack, HStack)
Convenient flex wrapper with gap.

```tsx
import { Stack, VStack, HStack } from '@/ui/components';

<VStack spacing="12px">
  <div>Item 1</div>
  <div>Item 2</div>
</VStack>

<HStack spacing="8px">
  <button>Cancel</button>
  <button>Submit</button>
</HStack>
```

**Props:**
- `direction`: vertical, horizontal
- `spacing`: Gap between items
- `gap`: Flex gap
- `justify`: Alignment (start, end, center, between, around, evenly)
- `align`: Items alignment (start, end, center, baseline, stretch)

---

## Progress Components

### ProgressBar (Story W)
Visual progress indicator.

```tsx
import { ProgressBar, CircularProgress, SteppedProgress } from '@/ui/components';

<ProgressBar value={65} label="Upload" variant="primary" />
<CircularProgress value={75} />
<SteppedProgress current={2} total={5} />
```

**Components:**
- `ProgressBar`: Linear progress bar
- `CircularProgress`: Circular progress
- `SteppedProgress`: Step-based progress
- `ProgressGroup`: Multiple stacked bars

**Props:**
- `value`: Progress value (0-100)
- `variant`: primary, success, warning, danger
- `height`: Bar height
- `striped`: Add striped pattern
- `animated`: Animate striped

---

## Separator Components

### Divider (Story X)
Visual separator between content.

```tsx
import { Divider, SectionDivider, TextDivider } from '@/ui/components';

<Divider />
<Divider label="Or" />
<Divider direction="vertical" />
<SectionDivider title="Section" />
<TextDivider text="Separator" />
```

**Components:**
- `Divider`: Basic separator
- `SectionDivider`: Section break
- `TextDivider`: Divider with text
- `BorderBox`: Box with borders

**Props:**
- `direction`: horizontal, vertical
- `variant`: solid, dashed, dotted
- `color`: Line color
- `thickness`: Line thickness
- `label`: Text in center

---

## Icon Components

### Icon (Story Y)
Icon wrapper with sizing and styling.

```tsx
import { Icon, IconButton } from '@/ui/components';

<Icon icon={<StarIcon />} size="medium" color="#f59e0b" />
<IconButton icon={<TrashIcon />} onClick={handleDelete} />
```

**Components:**
- `Icon`: Icon wrapper
- `IconButton`: Clickable icon
- `IconButtonGroup`: Group of buttons
- `IconWithText`: Icon with text
- `IconBadge`: Icon with badge

**Props:**
- `icon`: SVG element or component
- `size`: small, medium, large, xl
- `color`: Custom color
- `variant`: default, primary, danger, ghost
- `loading`: Show spinner
- `disabled`: Disable button

---

## Information Components

### Tooltip (Story Z)
Brief information on hover/click.

```tsx
import { Tooltip, Popover } from '@/ui/components';

<Tooltip content="Click to save" placement="top">
  <button>Save</button>
</Tooltip>

<Popover trigger={<button>Help</button>} title="Help">
  <p>This is helpful information.</p>
</Popover>
```

**Components:**
- `Tooltip`: Hover information
- `Popover`: Click information
- `InfoIcon`: Info icon with tooltip
- `HoverCard`: Hover-triggered card

**Props:**
- `content`: Tooltip text
- `trigger`: Trigger element
- `placement`: top, bottom, left, right
- `delay`: Show delay (ms)
- `triggerMode`: hover, click, focus

---

## Accessibility (WCAG 2.1 AA)

All components include:
- **ARIA attributes**: Proper roles, labels, states
- **Keyboard navigation**: Full keyboard support
- **Focus management**: Visible focus indicators
- **Color contrast**: Meets AA standards
- **Screen reader support**: Descriptive labels
- **Semantic HTML**: Proper element usage

### Common Patterns

**Buttons:**
```tsx
<button aria-label="Delete item" />
```

**Menus:**
```tsx
<div role="menu" aria-label="Actions">
  <button role="menuitem">Edit</button>
</div>
```

**Modals:**
```tsx
<div role="dialog" aria-modal="true">
  <h2 id="dialog-title">Dialog Title</h2>
</div>
```

**Progress:**
```tsx
<div role="progressbar" aria-valuenow={50} aria-valuemin={0} aria-valuemax={100} />
```

---

## Styling

All components use Tailwind CSS classes. Customize via:

1. **Tailwind configuration** - Extend theme colors/spacing
2. **CSS custom properties** - For global theming
3. **className prop** - Per-component customization
4. **style prop** - Inline styles when needed

```tsx
<Pagination className="custom-pagination" />

<Container style={{ maxWidth: '1200px' }} />
```

---

## Type Definitions

All components export TypeScript types:

```tsx
import type {
  PaginationProps,
  SkeletonProps,
  SpinnerProps,
  AvatarProps,
  DropdownProps,
  ContainerProps,
  ProgressBarProps,
  DividerProps,
  IconProps,
  TooltipProps,
} from '@/ui/components';
```

---

## Usage Examples

### Form with Layout

```tsx
import { VStack, Container, Input, Button } from '@/ui/components';

<Container maxWidth="sm">
  <VStack spacing="16px">
    <Input label="Name" />
    <Input label="Email" type="email" />
    <Button>Submit</Button>
  </VStack>
</Container>
```

### Modal with Dropdown

```tsx
import { Modal, Dropdown, Button } from '@/ui/components';

<Modal isOpen={isOpen} onClose={handleClose}>
  <Modal.Header>Actions</Modal.Header>
  <Dropdown
    trigger={<Button>Options</Button>}
    items={[...]}
    onSelect={handleAction}
  />
</Modal>
```

### Loading States

```tsx
import { Spinner, SkeletonCard, Pagination } from '@/ui/components';

{isLoading ? (
  <SkeletonCard count={3} />
) : (
  <>
    {items.map(item => <Card key={item.id}>{item}</Card>)}
    <Pagination currentPage={page} totalPages={totalPages} />
  </>
)}
```

---

## Performance

- **Lazy loading**: Components render on demand
- **Memoization**: Prevent unnecessary re-renders
- **Portal efficiency**: Only one portal per type
- **Animation performance**: GPU-accelerated transforms
- **Bundle size**: Tree-shakeable exports

---

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Contributing

When adding new components:
1. Ensure WCAG 2.1 AA compliance
2. Add TypeScript types
3. Write unit tests
4. Create Storybook stories
5. Document accessibility features
6. Update this README

---

**Version**: 1.0.0
**Last Updated**: February 2026
