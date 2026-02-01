# Boring-UI Migration Implementation Stories (Updated)

Epic: kurt-core-6vql
Total stories: 29

## Phase 1: Package Setup

### kurt-core-6vql.26: Define boring-ui repo topology and dev workflow
Priority: P1 | Type: task

First story - defines how everything works:
- Document repo structure (separate vs monorepo)
- Configure npm link / yalc for local development
- Setup build watch mode
- Document workspace linking workflow
- CI/CD pipeline for boring-ui

---

### kurt-core-6vql.28: Define compatibility matrix and peer dependencies
Priority: P2 | Type: task

Setup compatibility requirements:
- Document supported React versions (17.x, 18.x)
- Document supported Vite/bundler versions
- Configure peerDependencies correctly
- Test installation in clean environment
- Add engines field to package.json

---

### kurt-core-6vql.1: Setup boring-ui as npm package
Priority: P1 | Type: task
Depends on: .26, .28

Configure boring-ui repository for npm publishing:
- Add package.json with name, version, exports
- Configure Vite library mode for building
- Setup entry point (src/index.js)
- Configure peer dependencies (React, etc.)

---

### kurt-core-6vql.2: Create component index exports
Priority: P1 | Type: task
Depends on: .1

Create clean export structure:
- Export all components from src/index.js
- Named exports for each component
- Re-export types and utilities
- Ensure tree-shaking works correctly

---

### kurt-core-6vql.3: Setup CSS/styles export strategy
Priority: P1 | Type: task
Depends on: .1

Define how styles are exported:
- CSS modules vs global CSS
- Theme variables export
- Optional styles import path
- Document style integration

---

### kurt-core-6vql.24: Generate TypeScript declarations for boring-ui
Priority: P1 | Type: task
Depends on: .1, .2

Configure tsconfig for declaration generation:
- Generate .d.ts files for all components
- Export types from package index
- Ensure proper IDE autocompletion support

---

## Phase 2: Component Refactoring

### kurt-core-6vql.4: Make FileTree configurable via props
Priority: P2 | Type: task
Depends on: .2, .3

Make FileTree reusable across projects:
- Accept sections config as prop (not hardcoded)
- Configurable icons and labels
- Event callbacks for selection, context menu
- Support custom section types
- Export as standalone component

### Acceptance Criteria
- FileTree renders with empty/custom config
- All events fire correctly
- No hardcoded kurt-core references

---

### kurt-core-6vql.5: Make Header configurable via props
Priority: P2 | Type: task
Depends on: .2, .3

Make Header component reusable:
- Accept branding (logo, title) as props
- Configurable navigation items
- Slot support for custom actions
- Theme-aware styling
- Export as standalone component

### Acceptance Criteria
- Header renders with custom branding
- Navigation items are configurable
- Theme switching works

---

### kurt-core-6vql.6: Make DockLayout configurable
Priority: P2 | Type: task
Depends on: .2, .3

Make DockLayout/DockView reusable:
- Accept panel configuration as props
- Configurable persistence key
- Panel render callbacks
- Default layout configuration
- Export as standalone component

### Acceptance Criteria
- Layout persists to configurable storage key
- Panels resize correctly
- Custom panel content renders

---

### kurt-core-6vql.7: Extract ChatPanel as standalone component
Priority: P2 | Type: task
Depends on: .2, .3

Make ChatPanel reusable:
- Accept message handlers as props
- Configurable input area
- Support custom message rendering
- Event callbacks for send, clear
- Export as standalone component

### Acceptance Criteria
- Messages display correctly
- Send callback fires with input
- Custom message renderer works

---

### kurt-core-6vql.8: Extract Terminal component with configuration
Priority: P2 | Type: task
Depends on: .2, .3

Make Terminal component reusable:
- Accept theme/styling props
- Configurable command handlers
- Event callbacks for command execution
- Support custom prompt styling
- Export as standalone component

### Acceptance Criteria
- Commands execute via callback
- Custom prompt styling applies
- Theme colors work

---

### kurt-core-6vql.9: Extract ThemeToggle as configurable component
Priority: P2 | Type: task
Depends on: .2, .3

Make ThemeToggle reusable:
- Accept theme list as prop
- Custom icons per theme
- Callback for theme changes
- Storage key configurable
- Export from boring-ui package

### Acceptance Criteria
- Theme list is configurable
- Change callback fires
- Storage key works

---

### kurt-core-6vql.10: Extract UserMenu as configurable component
Priority: P2 | Type: task
Depends on: .2, .3

Make UserMenu reusable:
- Accept user data as props
- Configurable menu items
- Callback handlers for actions
- Support custom avatar rendering
- Export from boring-ui package

### Acceptance Criteria
- Menu items are configurable
- Action callbacks fire
- Avatar renders correctly

---

### kurt-core-6vql.25: Create boring-ui config type definitions
Priority: P2 | Type: task
Depends on: .24

Define configuration interfaces:
- BoringUIConfig interface
- FileTreeConfig type with sections, icons
- ChatPanelConfig type with handlers
- DockLayoutConfig type with panel definitions
- Export all config types

### Acceptance Criteria
- All config types exported
- IDE autocompletion works
- Types match component props

---

### kurt-core-6vql.29: Add accessibility checks to components
Priority: P2 | Type: task
Depends on: .4, .6, .9, .10

Ensure components are accessible:
- FileTree: keyboard navigation, ARIA roles, focus management
- DockLayout: focus management, resize handles keyboard accessible
- ChatPanel: screen reader support, live regions
- ThemeToggle/UserMenu: keyboard accessible menus
- Add axe-core or similar for automated checks

### Acceptance Criteria
- All components pass axe-core audit
- Keyboard navigation works
- ARIA roles are correct
- Focus management is proper

---

## Phase 3: Kurt-Core Integration

### kurt-core-6vql.11: Add boring-ui as npm dependency to kurt-core
Priority: P2 | Type: task
Depends on: .2, .3, .24

Integration setup:
- Add boring-ui package to package.json
- Configure import paths
- Verify build process works
- Update vite/webpack config if needed

---

### kurt-core-6vql.27: CSS/theming integration strategy for kurt-core
Priority: P2 | Type: task
Depends on: .3, .11

Ensure styles work correctly:
- Document CSS import strategy for consumers
- Theme variable namespace to avoid collisions
- CSS ordering requirements
- Style bundling configuration
- Verify theme variables work in kurt-core

### Acceptance Criteria
- Theme variables don't conflict
- Styles load in correct order
- No CSS collisions

---

### kurt-core-6vql.12: Replace FileTree with boring-ui import
Priority: P2 | Type: task
Depends on: .11, .4

Integration:
- Import FileTree from boring-ui
- Pass kurt-core specific config as props
- Remove local FileTree component
- Verify file browsing works correctly

### Acceptance Criteria
- File tree displays correctly
- Selection events work
- Context menu works

---

### kurt-core-6vql.13: Replace Header with boring-ui import
Priority: P2 | Type: task
Depends on: .11, .5

Integration:
- Import Header from boring-ui
- Pass kurt-core branding/nav as props
- Remove local Header component
- Verify navigation works correctly

### Acceptance Criteria
- Header displays kurt-core branding
- Navigation works
- Theme toggle works

---

### kurt-core-6vql.14: Replace DockLayout with boring-ui import
Priority: P2 | Type: task
Depends on: .11, .6

Integration:
- Import DockLayout from boring-ui
- Configure panel layout for kurt-core
- Remove local DockLayout/DockView components
- Verify panel resizing and persistence works

### Acceptance Criteria
- Panels resize correctly
- Layout persists across sessions
- All kurt-core panels render

---

### kurt-core-6vql.15: Replace ChatPanel with boring-ui import
Priority: P2 | Type: task
Depends on: .11, .7

Integration:
- Import ChatPanel from boring-ui
- Wire up to kurt-core message handlers
- Remove local ChatPanel component
- Verify chat functionality works

### Acceptance Criteria
- Messages display correctly
- Send/receive works
- Chat history works

---

### kurt-core-6vql.16: Replace Terminal with boring-ui import
Priority: P2 | Type: task
Depends on: .11, .8

Integration:
- Import Terminal from boring-ui
- Configure command handlers
- Remove local Terminal component
- Verify command execution works

### Acceptance Criteria
- Commands execute correctly
- Output displays properly
- Styling matches theme

---

### kurt-core-6vql.17: Replace ThemeToggle/UserMenu with boring-ui imports
Priority: P2 | Type: task
Depends on: .11, .9, .10

Integration:
- Import ThemeToggle, UserMenu from boring-ui
- Pass kurt-core user context
- Remove local components
- Verify theme switching and user menu work

### Acceptance Criteria
- Theme switching works
- User menu displays correctly
- Actions trigger correctly

---

## Phase 4: Testing and Migration

### kurt-core-6vql.18: Create boring-ui component unit tests
Priority: P2 | Type: task
Depends on: .4, .5, .6, .7, .8, .9, .10, .29

Testing:
- Add vitest/jest setup to boring-ui
- Unit tests for all components
- Snapshot tests for visual components
- Accessibility tests with axe-core

### Acceptance Criteria
- All components have tests
- Coverage > 80%
- Accessibility tests pass

---

### kurt-core-6vql.19: Create boring-ui Storybook documentation
Priority: P2 | Type: task
Depends on: .4, .5, .6, .7, .8, .9, .10

Documentation:
- Setup Storybook in boring-ui
- Create stories for each component
- Document props and usage
- Add interactive examples

### Acceptance Criteria
- Every component has stories
- Props are documented
- Examples are interactive

---

### kurt-core-6vql.20: Integration tests for kurt-core with boring-ui
Priority: P2 | Type: task
Depends on: .12, .13, .14, .15, .16, .17

Testing:
- Test FileTree with real file data
- Test ChatPanel message flow
- Test DockLayout panel persistence
- Test Header navigation
- Test Terminal commands
- Test theme switching
- Verify no regressions in UI behavior

### Acceptance Criteria
- All integration points tested
- No regressions from local components
- E2E tests pass

---

### kurt-core-6vql.21: Remove deprecated local components from kurt-core
Priority: P3 | Type: task
Depends on: .12, .13, .14, .15, .16, .17, .20

Cleanup:
- Remove all local component files replaced by boring-ui
- Clean up unused CSS/styles
- Remove dead imports
- Verify build still works

### Acceptance Criteria
- No duplicate component code
- Build succeeds
- No unused files remain

---

### kurt-core-6vql.23: Update boring-ui README with usage examples
Priority: P3 | Type: task
Depends on: .18, .19

Documentation (before publish):
- Installation instructions
- Quick start guide
- Component API reference
- Configuration examples
- Migration guide for existing projects

### Acceptance Criteria
- All components documented
- Code examples work
- Migration guide is complete

---

### kurt-core-6vql.22: Publish boring-ui v1.0.0 to npm
Priority: P3 | Type: task
Depends on: .21, .23

Release:
- Finalize package.json metadata
- Set version to 1.0.0
- npm publish to registry
- Create GitHub release with changelog

### Acceptance Criteria
- Package published successfully
- npm install works
- GitHub release created
