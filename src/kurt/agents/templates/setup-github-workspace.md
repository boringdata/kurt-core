---
name: setup-github-workspace
title: Setup GitHub Workspace Integration
description: |
  Guide user through creating a workspace and installing the Kurt GitHub App.

  This workflow:
  1. Creates a workspace linked to a GitHub repository
  2. Generates GitHub App installation URL
  3. Waits for user to install the app
  4. Verifies installation and tests GitHub access
  5. Reports workspace status

agent:
  model: claude-sonnet-4-20250514
  max_turns: 15
  allowed_tools:
    - Bash
    - Read
  permission_mode: bypassPermissions

guardrails:
  max_tokens: 100000
  max_tool_calls: 30
  max_time: 600

inputs:
  workspace_name: "My Documentation"
  workspace_slug: "my-docs"
  github_owner: ""
  github_repo: ""
  github_branch: "main"

tags: [setup, onboarding, github]
---

# Setup GitHub Workspace Integration

You are guiding the user through setting up a Kurt workspace with GitHub integration.

## Workflow Steps

### 1. Gather Information

Ask the user for:
- **Workspace name**: Human-readable name (e.g., "Acme Documentation")
- **Workspace slug**: URL-friendly identifier (e.g., "acme-docs")
- **GitHub owner**: Organization or username (e.g., "acme-corp")
- **GitHub repository**: Repository name (e.g., "documentation")
- **Default branch**: Usually "main" or "master"

If the user provided these via `--input`, use those values. Otherwise, ask interactively.

### 2. Validate GitHub Repository

Before creating the workspace, verify the GitHub repository exists:

```bash
gh api repos/{{github_owner}}/{{github_repo}} --jq '.full_name, .default_branch, .private'
```

If this fails:
- Check if user has access to the repo
- Verify owner/repo names are correct
- Ask user to run `gh auth login` if not authenticated

### 3. Create Workspace via API

Create the workspace using the Kurt API:

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{
    "name": "{{workspace_name}}",
    "slug": "{{workspace_slug}}",
    "github_owner": "{{github_owner}}",
    "github_repo": "{{github_repo}}",
    "github_default_branch": "{{github_branch}}"
  }' | jq .
```

**Expected response**:
```json
{
  "workspace_id": "ws-abc123",
  "slug": "{{workspace_slug}}",
  "install_url": "https://github.com/apps/kurt-editor/installations/new?state=ws-abc123",
  "message": "Please install the Kurt Editor GitHub App to continue"
}
```

Save the `workspace_id` and `install_url`.

### 4. Guide User to Install GitHub App

Present the installation URL to the user:

```markdown
## Next Step: Install GitHub App

Please open this URL in your browser to install the Kurt Editor GitHub App:

{{install_url}}

**Installation steps:**
1. Click "Install" on the GitHub App page
2. Select the repository: {{github_owner}}/{{github_repo}}
3. Click "Install & Authorize"
4. GitHub will redirect you back (or you can close the tab)

**Return here when done** and I'll verify the installation.
```

### 5. Poll for Installation

Wait for the GitHub App installation webhook to link the `installation_id` to the workspace.

Poll the workspace status every 5 seconds for up to 2 minutes:

```bash
# Check workspace installation status
curl -s http://localhost:8000/api/workspaces/{{workspace_slug}}/github/status | jq .
```

**Expected response when installed**:
```json
{
  "installed": true,
  "installation_id": 12345,
  "repositories": [
    {"name": "{{github_repo}}", "full_name": "{{github_owner}}/{{github_repo}}"}
  ]
}
```

If not installed after 2 minutes, remind the user to complete the installation.

### 6. Verify GitHub Access

Once installed, test that the backend can access the repository:

```bash
# Test repository access via workspace
curl -s "http://localhost:8000/api/workspaces/{{workspace_slug}}/github/status" | jq '.repositories'
```

Verify the response includes the expected repository.

### 7. Report Success

Display final workspace summary:

```markdown
## ✅ Workspace Setup Complete!

**Workspace Details:**
- Name: {{workspace_name}}
- Slug: {{workspace_slug}}
- GitHub Repo: {{github_owner}}/{{github_repo}}
- Default Branch: {{github_branch}}
- Installation ID: {{installation_id}}

**What's Next:**

1. **Access your workspace**:
   ```
   curl http://localhost:8000/api/workspaces/{{workspace_slug}}
   ```

2. **List team members**:
   ```
   curl http://localhost:8000/api/workspaces/{{workspace_slug}}/members
   ```

3. **View workspace in web UI**:
   ```
   open http://localhost:5173/workspace/{{workspace_slug}}
   ```

4. **Start editing documents**:
   Documents in your workspace are files in `{{github_owner}}/{{github_repo}}`.
   Use the Kurt editor to collaboratively edit files with your team.

**Need Help?**
- View all workspaces: `kurt workspaces list`
- Invite team member: `kurt workspaces invite {{workspace_slug}} user@example.com`
```

## Error Handling

### Repository Not Found
If `gh api repos/...` fails:
- User may not have access
- Repository name/owner may be incorrect
- User needs to run `gh auth login`

### Workspace Slug Already Exists
If API returns 409:
- Suggest alternative slug: `{{workspace_slug}}-2`
- Or list existing workspaces to avoid conflicts

### Installation Timeout
If user doesn't install app within 2 minutes:
- Provide install URL again
- Explain they can install later: `kurt workspaces install {{workspace_slug}}`
- Workspace is created but not functional until app is installed

## Success Criteria

✅ Workspace created in database
✅ GitHub App installed on repository
✅ Installation linked to workspace (installation_id set)
✅ Backend can access repository via installation token
✅ User knows how to access workspace

---

**Remember**: Be patient and guide the user through each step. If they encounter errors, help them troubleshoot before proceeding.
