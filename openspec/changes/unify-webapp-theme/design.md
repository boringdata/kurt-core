# Design: Unified Theme System

## Context
The Kurt web UI currently uses hardcoded colors and inconsistent styling across components. Users increasingly expect dark mode support. Claude.ai's chat interface provides a polished, modern reference design.

## Goals
- Consistent visual language across all components
- Dark/light mode with system preference detection
- Easy theming via CSS custom properties
- Minimal JavaScript overhead (CSS-first approach)

## Non-Goals
- Multiple color themes beyond dark/light
- User-customizable accent colors
- Component library extraction (keep inline)

## Decisions

### 1. CSS Custom Properties (CSS Variables)
**Decision**: Use CSS custom properties for all design tokens.

**Why**:
- No build step required
- Native browser support
- Runtime theme switching without JS
- Easy to override per-component

**Alternatives considered**:
- CSS-in-JS (styled-components): Adds bundle size, requires React context
- Tailwind CSS: Would require significant refactor, adds complexity
- SCSS variables: Compile-time only, no runtime switching

### 2. Theme Switching Mechanism
**Decision**: Use `data-theme` attribute on `<html>` element.

```css
:root { --bg-primary: #ffffff; }
[data-theme="dark"] { --bg-primary: #1a1a1a; }
```

**Why**:
- Single attribute controls entire theme
- Works with CSS-only (no JS required for initial render)
- SSR-friendly

### 3. Reference Design: Claude.ai Chat
**Decision**: Match Claude.ai's visual style for familiarity.

Key characteristics to adopt:
- **Font**: Clean sans-serif (Söhne or similar, fallback to system)
- **Border-radius**: Generous (12-16px for cards, 8px for buttons)
- **Colors**: Warm neutrals, subtle contrast, soft shadows
- **Spacing**: Generous whitespace, clear hierarchy
- **Messages**: Subtle background distinction, no harsh borders

### 4. Color Palette Strategy
**Decision**: Semantic color tokens, not raw values.

```css
/* Semantic tokens */
--color-bg-primary: var(--gray-50);
--color-bg-secondary: var(--gray-100);
--color-text-primary: var(--gray-900);
--color-text-secondary: var(--gray-600);
--color-border: var(--gray-200);
--color-accent: var(--orange-500);

/* Raw palette (reference only) */
--gray-50: #fafafa;
--gray-900: #171717;
```

### 5. Typography Scale
**Decision**: Match Claude.ai proportions.

```css
--font-sans: 'Inter', -apple-system, system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

--text-xs: 0.75rem;    /* 12px */
--text-sm: 0.875rem;   /* 14px */
--text-base: 1rem;     /* 16px */
--text-lg: 1.125rem;   /* 18px */
--text-xl: 1.25rem;    /* 20px */
```

### 6. Persistence
**Decision**: localStorage with system preference fallback.

```js
const getInitialTheme = () => {
  const stored = localStorage.getItem('theme');
  if (stored) return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large CSS refactor | Incremental migration, one component at a time |
| Broken dark mode in edge cases | Visual regression testing with screenshots |
| Performance impact of many CSS vars | Minimal - browsers optimize custom properties |

## Migration Plan
1. Add design tokens to `styles.css` (non-breaking)
2. Add theme toggle infrastructure (hidden behind flag if needed)
3. Migrate components incrementally, prioritizing chat panel
4. Remove old hardcoded styles once migration complete
5. Enable dark mode by default

## Resolved Questions
- **Terminal panels**: Follow user's app-level theme choice (not always dark)
- **Code block syntax highlighting**: Sync with app theme (light syntax in light mode, dark syntax in dark mode)
