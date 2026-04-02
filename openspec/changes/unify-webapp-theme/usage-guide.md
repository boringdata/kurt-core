# Design Token Usage Guide

This guide explains how to use the Kurt design token system for consistent styling and dark/light theme support.

## Quick Reference

### Colors

```css
/* Backgrounds */
var(--color-bg-primary)      /* Main background */
var(--color-bg-secondary)    /* Secondary panels */
var(--color-bg-tertiary)     /* Tertiary/nested elements */
var(--color-bg-hover)        /* Hover state */
var(--color-bg-active)       /* Active/pressed state */

/* Text */
var(--color-text-primary)    /* Primary text */
var(--color-text-secondary)  /* Secondary/muted text */
var(--color-text-tertiary)   /* Tertiary/placeholder text */
var(--color-text-inverse)    /* Text on dark backgrounds */

/* Borders */
var(--color-border)          /* Standard borders */
var(--color-border-strong)   /* Emphasized borders */

/* Semantic Colors */
var(--color-accent)          /* Primary accent (orange) */
var(--color-accent-hover)    /* Accent hover state */
var(--color-success)         /* Success/positive */
var(--color-warning)         /* Warning/caution */
var(--color-error)           /* Error/danger */
var(--color-info)            /* Information */

/* Code */
var(--color-pre-bg)          /* Code block background */
var(--color-pre-text)        /* Code block text */
var(--color-code-bg)         /* Inline code background */
```

### Typography

```css
var(--font-sans)     /* UI text: Inter, system fonts */
var(--font-mono)     /* Code: JetBrains Mono, Fira Code */

var(--text-xs)       /* 12px */
var(--text-sm)       /* 14px */
var(--text-base)     /* 16px */
var(--text-lg)       /* 18px */
var(--text-xl)       /* 20px */
```

### Spacing

```css
var(--space-0)   /* 0 */
var(--space-1)   /* 4px */
var(--space-2)   /* 8px */
var(--space-3)   /* 12px */
var(--space-4)   /* 16px */
var(--space-6)   /* 24px */
var(--space-8)   /* 32px */
```

### Border Radius

```css
var(--radius-sm)   /* 4px */
var(--radius-md)   /* 8px */
var(--radius-lg)   /* 12px */
var(--radius-xl)   /* 16px */
```

### Shadows

```css
var(--shadow-sm)   /* Subtle shadow */
var(--shadow-md)   /* Medium shadow */
var(--shadow-lg)   /* Large shadow */
var(--shadow-xl)   /* Extra large shadow */
```

### Transitions

```css
var(--transition-fast)    /* 150ms ease */
var(--transition-normal)  /* 200ms ease */
var(--transition-slow)    /* 300ms ease */
```

## Usage Examples

### Basic Component

```jsx
// Button component using design tokens
const Button = ({ children, variant = 'primary' }) => (
  <button
    style={{
      backgroundColor: variant === 'primary'
        ? 'var(--color-accent)'
        : 'var(--color-bg-secondary)',
      color: variant === 'primary'
        ? 'var(--color-text-inverse)'
        : 'var(--color-text-primary)',
      padding: 'var(--space-2) var(--space-4)',
      borderRadius: 'var(--radius-md)',
      border: '1px solid var(--color-border)',
      fontFamily: 'var(--font-sans)',
      fontSize: 'var(--text-sm)',
      cursor: 'pointer',
      transition: 'background var(--transition-fast)',
    }}
  >
    {children}
  </button>
)
```

### Card Component

```jsx
const Card = ({ title, children }) => (
  <div
    style={{
      backgroundColor: 'var(--color-bg-primary)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-lg)',
      padding: 'var(--space-4)',
      boxShadow: 'var(--shadow-sm)',
    }}
  >
    <h3 style={{
      color: 'var(--color-text-primary)',
      marginBottom: 'var(--space-2)',
    }}>
      {title}
    </h3>
    <div style={{ color: 'var(--color-text-secondary)' }}>
      {children}
    </div>
  </div>
)
```

### Status Badge

```jsx
const StatusBadge = ({ status }) => {
  const colors = {
    success: {
      bg: 'var(--color-success-light)',
      text: 'var(--color-success)',
    },
    warning: {
      bg: 'var(--color-warning-light)',
      text: 'var(--color-warning)',
    },
    error: {
      bg: 'var(--color-error-light)',
      text: 'var(--color-error)',
    },
  }

  const { bg, text } = colors[status] || colors.success

  return (
    <span
      style={{
        backgroundColor: bg,
        color: text,
        padding: 'var(--space-1) var(--space-2)',
        borderRadius: 'var(--radius-sm)',
        fontSize: 'var(--text-xs)',
        fontWeight: 500,
      }}
    >
      {status}
    </span>
  )
}
```

### Code Block

```jsx
const CodeBlock = ({ code, language }) => (
  <pre
    style={{
      backgroundColor: 'var(--color-pre-bg)',
      color: 'var(--color-pre-text)',
      padding: 'var(--space-3)',
      borderRadius: 'var(--radius-md)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-sm)',
      overflow: 'auto',
    }}
  >
    <code>{code}</code>
  </pre>
)
```

## CSS Usage

### In styles.css

```css
.my-component {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  transition: background var(--transition-fast);
}

.my-component:hover {
  background: var(--color-bg-hover);
}

.my-component:active {
  background: var(--color-bg-active);
}
```

## Theme Switching

The theme is controlled via the `data-theme` attribute on `<html>`:

```html
<html data-theme="dark">
```

### Using the Theme Hook

```jsx
import { useTheme } from '../hooks/useTheme'

function MyComponent() {
  const { theme, toggleTheme, setTheme } = useTheme()

  return (
    <button onClick={toggleTheme}>
      Current theme: {theme}
    </button>
  )
}
```

### Theme Provider Setup

Wrap your app with `ThemeProvider`:

```jsx
import { ThemeProvider } from './hooks/useTheme'

function App() {
  return (
    <ThemeProvider>
      <YourApp />
    </ThemeProvider>
  )
}
```

## Best Practices

1. **Always use design tokens** - Never hardcode colors, use `var(--color-*)` tokens
2. **Use semantic tokens** - Prefer `--color-success` over `--color-green`
3. **Include transitions** - Use `--transition-*` for interactive states
4. **Test both themes** - Verify components look good in light and dark modes
5. **Use appropriate contrast** - Ensure text is readable (WCAG AA: 4.5:1)

## Adding New Tokens

If you need a new token:

1. Add it to `:root` in `styles.css` (light mode)
2. Add dark mode override in `[data-theme="dark"]`
3. Use semantic naming: `--color-{category}-{variant}`
4. Document the token in this guide
