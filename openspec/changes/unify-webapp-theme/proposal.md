# Change: Unify Web App Theme with Dark/Light Mode

## Why
The Kurt web UI has inconsistent styling across components (fonts, border-radius, colors, spacing). Users expect modern apps to support dark mode. The goal is to unify the visual design using Claude.ai chat interface as the reference style.

## What Changes
- Create CSS custom properties (design tokens) for colors, typography, spacing, and radii
- Implement dark mode and light mode with system preference detection
- Add theme toggle UI component
- Refactor all components to use design tokens instead of hardcoded values
- Update fonts to match Claude.ai style (clean sans-serif, subtle mono for code)
- Standardize border-radius (softer, more rounded corners like Claude)
- Unify spacing scale and component sizing

## Impact
- Affected specs: `web-ui` (new capability spec)
- Affected code:
  - `src/kurt/web/client/src/styles.css` - Design tokens and base styles
  - `src/kurt/web/client/src/components/chat/styles.css` - Chat component styles
  - All `.jsx` components - Remove inline styles, use CSS classes
  - `src/kurt/web/client/src/App.jsx` - Theme provider and toggle
