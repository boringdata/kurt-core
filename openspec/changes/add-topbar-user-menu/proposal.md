# Change: Add User Avatar and Workspace Menu to Top Bar

## Why
In cloud mode, users have workspace context (workspace name, members, etc.) but no way to see or manage it from the web UI. The current top bar only shows a theme toggle, missing critical user/workspace information.

## What Changes
- Add user avatar (first letter of email) to top bar in cloud mode
- Add dropdown menu with: workspace name, "Manage workspace" link
- Keep current behavior in local mode (theme toggle only)
- Fetch user/workspace info from `/api/me` endpoint (new)

## Impact
- Affected code:
  - `src/kurt/web/client/src/App.jsx` - Top bar enhancement
  - `src/kurt/web/client/src/components/UserMenu.jsx` - New component
  - `src/kurt/web/client/src/styles.css` - Avatar and menu styles
  - `src/kurt/web/api/server.py` - New `/api/me` endpoint
- No database changes
- No breaking changes

## Out of Scope
- Workspace switcher (future)
- Photo upload for avatar (future)
- Full workspace settings page (link to external management for now)
