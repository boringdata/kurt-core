# Design: User Avatar and Workspace Menu

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Top Bar                                                     │
│  ┌──────────────────────────────────────────────┬─────────┐ │
│  │                                              │ [☀] [J] │ │
│  └──────────────────────────────────────────────┴─────────┘ │
│                                          Theme ↑    ↑ Avatar│
└─────────────────────────────────────────────────────────────┘

Avatar Click → Dropdown Menu:
┌─────────────────────────┐
│ My Workspace            │  ← workspace name (read-only)
├─────────────────────────┤
│ Manage workspace    →   │  ← link to management
└─────────────────────────┘
```

## Data Flow

```
App.jsx mount
    │
    ▼
GET /api/me
    │
    ▼
┌─────────────────────────────────────┐
│ Response (cloud mode):              │
│ {                                   │
│   is_cloud_mode: true,              │
│   user: { email: "j@x.com", id },   │
│   workspace: { id, name: "Acme" }   │
│ }                                   │
└─────────────────────────────────────┘
    │
    ▼
Render: ThemeToggle + UserMenu(email, workspace)

┌─────────────────────────────────────┐
│ Response (local mode):              │
│ { is_cloud_mode: false }            │
└─────────────────────────────────────┘
    │
    ▼
Render: ThemeToggle only
```

## Component Structure

```jsx
// UserMenu.jsx
<div className="user-menu">
  <button className="user-avatar" onClick={toggle}>
    {email[0].toUpperCase()}
  </button>
  {isOpen && (
    <div className="user-menu-dropdown">
      <div className="user-menu-workspace">{workspaceName}</div>
      <button onClick={onManage}>Manage workspace</button>
    </div>
  )}
</div>
```

## API Endpoint

```python
@app.get("/api/me")
async def get_current_user_info(request: Request):
    if not is_cloud_auth_enabled():
        return {"is_cloud_mode": False}

    user = get_authenticated_user(request)
    if not user:
        return {"is_cloud_mode": True, "user": None}

    # Fetch workspace name from DB or cache
    workspace = get_workspace(user.workspace_id)

    return {
        "is_cloud_mode": True,
        "user": {"email": user.email, "id": user.user_id},
        "workspace": {"id": user.workspace_id, "name": workspace.name}
    }
```

## Styling Approach

Use existing design tokens from `unify-webapp-theme`:
- `--color-bg-secondary` for avatar background
- `--color-text-primary` for avatar letter
- `--radius-md` for avatar border-radius
- `--shadow-md` for dropdown shadow

## Future Extensions

1. **Workspace switcher**: Add workspace list to dropdown if user has multiple
2. **Avatar upload**: Replace letter with user-uploaded image
3. **Inline settings**: Add theme toggle inside menu, remove from top bar
