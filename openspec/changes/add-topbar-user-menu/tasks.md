# Tasks: Add User Avatar and Workspace Menu

## Implementation Order

### Phase 1: Backend - User Context Endpoint

- [ ] **1.1** Add `/api/me` endpoint to `server.py`
  - Returns: `{ user: { email, id }, workspace: { id, name }, is_cloud_mode: bool }`
  - In local mode: `{ is_cloud_mode: false }`
  - In cloud mode: extract from JWT via `get_authenticated_user()`

- [ ] **1.2** Add test for `/api/me` endpoint
  - Test local mode returns `is_cloud_mode: false`
  - Test cloud mode returns user/workspace info

### Phase 2: Frontend - User Menu Component

- [ ] **2.1** Create `UserMenu.jsx` component
  - Avatar: circle with first letter of email (uppercase)
  - Dropdown on click: workspace name, "Manage workspace" button
  - Uses design tokens from theme system

- [ ] **2.2** Add UserMenu styles to `styles.css`
  - Avatar circle (32px, theme colors)
  - Dropdown menu (positioned below avatar)
  - Hover/active states

### Phase 3: Integration

- [ ] **3.1** Update `App.jsx` top bar
  - Fetch `/api/me` on mount
  - If `is_cloud_mode`: show UserMenu + ThemeToggle
  - If local: show ThemeToggle only (current behavior)

- [ ] **3.2** Wire "Manage workspace" action
  - Opens workspace management (kurt-cloud URL or modal - TBD)
  - For now: `window.open()` to cloud dashboard

### Phase 4: Validation

- [ ] **4.1** Manual test: local mode shows theme toggle only
- [ ] **4.2** Manual test: cloud mode shows avatar + menu
- [ ] **4.3** Manual test: menu shows correct workspace name
- [ ] **4.4** Manual test: "Manage workspace" navigates correctly

## Dependencies
- Requires auth middleware active in cloud mode
- Uses existing `AuthUser` from `auth.py`

## Parallel Work
- Tasks 1.1-1.2 (backend) can run parallel to 2.1-2.2 (frontend component)
- Task 3.x requires both phases complete
