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
  - For now: `console.log("Manage workspace clicked", workspaceId)` as stub
  - Future: opens workspace management modal or navigates to kurt-cloud dashboard
  - Add TODO comment in code for future implementation

### Phase 4: Unit Tests

- [ ] **4.1** Add unit test for `/api/me` endpoint
  - Test local mode returns `{ is_cloud_mode: false }`
  - Test cloud mode with auth returns user + workspace
  - Test cloud mode without auth returns `{ is_cloud_mode: true, user: null }`

- [ ] **4.2** Add unit test for `UserMenu.jsx` component
  - Test avatar renders first letter of email
  - Test dropdown opens on click
  - Test dropdown closes on outside click
  - Test workspace name displays correctly

### Phase 5: E2E Validation (via Claude Chrome Plugin)

- [ ] **5.1** E2E test: local mode
  - Navigate to web UI
  - Verify only theme toggle visible in top bar
  - Verify no avatar present

- [ ] **5.2** E2E test: cloud mode
  - Navigate to web UI (with auth)
  - Verify avatar displays with correct letter
  - Click avatar → verify dropdown opens
  - Verify workspace name in dropdown
  - Click "Manage workspace" → verify console.log or alert (stub action)

## Dependencies
- Requires auth middleware active in cloud mode
- Uses existing `AuthUser` from `auth.py`

## Parallel Work
- Tasks 1.1-1.2 (backend) can run parallel to 2.1-2.2 (frontend component)
- Task 3.x requires both phases complete
