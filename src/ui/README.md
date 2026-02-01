# Boring UI Components Library

A comprehensive, accessible React component library built with TypeScript and CSS.

## Components

### Story F: Button Component

The Button component provides a versatile, accessible button with multiple variants and sizes.

**Features:**
- Variants: primary, secondary, danger, outline, ghost
- Sizes: small, medium, large
- States: normal, loading, disabled
- Icon support (left/right placement)
- Link button support (href)
- Full keyboard navigation
- WCAG 2.1 AA compliant

**Usage:**
```tsx
import { Button } from '@/ui/components';

<Button variant="primary" size="md">Click me</Button>
<Button variant="danger" loading>Processing...</Button>
<Button icon={<Icon />}>Download</Button>
<Button href="https://example.com" target="_blank">Visit</Button>
```

### Story G: Card Component

The Card component provides a flexible container with optional header, body, and footer sections.

**Features:**
- Shadow variants: none, small, medium, large
- Optional border
- Flexible padding
- Clickable cards with keyboard support
- Responsive design
- WCAG 2.1 AA compliant

**Usage:**
```tsx
import { Card, CardHeader, CardBody, CardFooter } from '@/ui/components';

<Card shadow="md">
  <CardHeader>Title</CardHeader>
  <CardBody>Content here</CardBody>
  <CardFooter><Button>Save</Button></CardFooter>
</Card>
```

### Story H: Badge, Tag, and Chip Components

Three related components for displaying labels, tags, and interactive elements.

**Badge:**
- Non-interactive label
- Color variants: default, success, warning, error, info
- Sizes: small, medium
- Icon support

**Usage:**
```tsx
import { Badge } from '@/ui/components';

<Badge variant="success">Complete</Badge>
<Badge variant="error" icon={<Icon />}>Failed</Badge>
```

**Tag:**
- Interactive label with optional remove button
- Color variants: default, success, warning, error, info
- Sizes: small, medium
- Icon support
- Removable functionality

**Usage:**
```tsx
import { Tag } from '@/ui/components';

<Tag removable onRemove={() => removeTag()}>
  React
</Tag>
```

**Chip:**
- Pill-shaped interactive component
- Color variants: default, success, warning, error, info
- Selectable/toggleable state
- Removable with remove button
- Icon support

**Usage:**
```tsx
import { Chip } from '@/ui/components';

<Chip
  selectable
  selected={isSelected}
  onToggle={(selected) => handleToggle(selected)}
>
  React
</Chip>

<Chip removable onRemove={() => removeChip()}>
  JavaScript
</Chip>
```

## Accessibility

All components follow WCAG 2.1 AA standards:
- Proper semantic HTML
- ARIA attributes (aria-label, aria-disabled, aria-pressed, etc.)
- Keyboard navigation support
- Focus visible states
- Color contrast compliance
- Screen reader support

## Styling

Components use CSS for styling with:
- CSS variables for theming
- Dark mode support
- Responsive design
- Smooth transitions
- No external CSS-in-JS dependencies

## Testing

All components include comprehensive test suites:
- Unit tests for rendering
- Interaction tests
- Accessibility tests
- Keyboard navigation tests
- Component composition tests

## Storybook

All components have Storybook stories for documentation and development:

```bash
npm run storybook
```

Then visit `http://localhost:6006` to view the component library.

## Development

### File Structure

```
src/ui/
├── components/
│   ├── button/
│   │   ├── Button.tsx
│   │   ├── Button.css
│   │   ├── Button.test.tsx
│   │   ├── Button.stories.tsx
│   │   └── index.ts
│   ├── card/
│   │   ├── Card.tsx
│   │   ├── Card.css
│   │   ├── Card.test.tsx
│   │   ├── Card.stories.tsx
│   │   └── index.ts
│   ├── badge-tag-chip/
│   │   ├── Badge.tsx
│   │   ├── Badge.css
│   │   ├── Badge.test.tsx
│   │   ├── Badge.stories.tsx
│   │   ├── Tag.tsx
│   │   ├── Tag.css
│   │   ├── Tag.test.tsx
│   │   ├── Tag.stories.tsx
│   │   ├── Chip.tsx
│   │   ├── Chip.css
│   │   ├── Chip.test.tsx
│   │   ├── Chip.stories.tsx
│   │   └── index.ts
│   └── index.ts
└── shared/
    └── types.ts
```

### Adding New Components

1. Create component folder: `src/ui/components/<component-name>/`
2. Create component file with TypeScript types
3. Create CSS file with styling
4. Create test file with comprehensive tests
5. Create Storybook stories
6. Export in index.ts files

## Performance

- Components are optimized for performance
- CSS is minified and bundled separately
- No unnecessary re-renders
- Proper ref forwarding
- Tree-shakeable exports

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

When adding new components:
1. Follow the TypeScript conventions used in existing components
2. Write comprehensive tests (90%+ coverage target)
3. Include Storybook stories for all variants
4. Ensure WCAG 2.1 AA accessibility
5. Add dark mode support in CSS
6. Document usage in this README

## License

MIT
