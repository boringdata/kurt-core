# Testing GitHub App Integration

This guide walks through testing the complete GitHub App integration flow locally.

## Prerequisites

1. **GitHub App** - Register a GitHub App for testing
2. **Webhook proxy** - For receiving webhooks locally (ngrok or smee.io)
3. **Kurt API server** - Running locally with database
4. **Environment variables** - GitHub App credentials

## Step 1: Register GitHub App

### Create Test GitHub App

1. Go to https://github.com/settings/apps/new
2. Fill in:
   - **Name**: `kurt-editor-test` (or any unique name)
   - **Homepage URL**: `http://localhost:8000`
   - **Webhook URL**: (leave blank for now, will update later)
   - **Webhook secret**: Generate random string (save this)

3. **Permissions** - Set repository permissions:
   - Contents: Read & Write
   - Metadata: Read-only

4. **Subscribe to events**:
   - Installation
   - Installation repositories

5. Click **Create GitHub App**

6. Generate a private key:
   - Scroll down to "Private keys"
   - Click "Generate a private key"
   - Save the downloaded `.pem` file

7. Note your App ID (shown at top of page)

## Step 2: Set Up Webhook Proxy

GitHub needs to reach your local server. Use ngrok or smee.io:

### Option A: ngrok (Recommended)

```bash
# Install ngrok
brew install ngrok

# Start tunnel to local API server
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

### Option B: smee.io

1. Go to https://smee.io/
2. Click "Start a new channel"
3. Copy the webhook proxy URL
4. Install smee client:
   ```bash
   npm install -g smee-client
   ```
5. Start forwarding:
   ```bash
   smee --url https://smee.io/YOUR_CHANNEL --path /api/webhooks/github --port 8000
   ```

## Step 3: Update GitHub App Webhook URL

1. Go back to your GitHub App settings
2. Update **Webhook URL** to:
   - ngrok: `https://YOUR_SUBDOMAIN.ngrok.io/api/webhooks/github`
   - smee.io: Use the smee channel URL
3. Save changes

## Step 4: Configure Environment

Create `.env` file in worktree:

```bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core-github-app

cat > .env <<EOF
# GitHub App Credentials
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY=$(cat /path/to/your-app.pem)
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Database
DATABASE_URL=postgresql://localhost/kurt_test
# Or use SQLite for testing:
# DATABASE_URL=sqlite:///./test.db
EOF
```

**Note**: For multi-line private key:
```bash
export GITHUB_APP_PRIVATE_KEY=$(cat your-app.pem)
```

## Step 5: Start the API Server

```bash
# Activate virtual environment
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core-github-app
source .venv/bin/activate

# Run database migrations
uv run alembic upgrade head

# Start FastAPI server
uv run uvicorn kurt.web.api.server:app --reload --port 8000
```

Server should be running at http://localhost:8000

## Step 6: Test Workspace Creation

Create a workspace via API:

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Documentation",
    "slug": "test-docs",
    "github_owner": "YOUR_GITHUB_USERNAME",
    "github_repo": "test-repo",
    "github_default_branch": "main"
  }' | jq
```

**Expected response**:
```json
{
  "workspace_id": "ws-abc123",
  "slug": "test-docs",
  "install_url": "https://github.com/apps/kurt-editor-test/installations/new?state=ws-abc123",
  "message": "Please install the Kurt Editor GitHub App to continue"
}
```

Save the `workspace_id` and `install_url`.

## Step 7: Install GitHub App

1. Open the `install_url` in your browser
2. Select the repository you specified (or create a test repo first)
3. Click **Install & Authorize**
4. GitHub will redirect you (you can close the tab)

**Behind the scenes**:
- GitHub sends a webhook to your server
- The webhook handler links the `installation_id` to your workspace

## Step 8: Verify Installation

Check that the installation was linked:

```bash
curl http://localhost:8000/api/workspaces/test-docs/github/status | jq
```

**Expected response** (if installed):
```json
{
  "installed": true,
  "installation_id": 12345,
  "repositories": [
    {
      "name": "test-repo",
      "full_name": "YOUR_USERNAME/test-repo"
    }
  ]
}
```

**If not installed yet**:
```json
{
  "installed": false,
  "message": "GitHub App not installed for this workspace"
}
```

## Step 9: Test Token Retrieval

The backend should now be able to get access tokens:

```python
# In Python shell or test script
from kurt.github import github_app
import asyncio

async def test_token():
    token = await github_app.get_workspace_token("ws-abc123")
    print(f"Token: {token[:20]}...")  # Print first 20 chars
    return token

asyncio.run(test_token())
```

Or test via API endpoint (add this endpoint for testing):

```bash
curl http://localhost:8000/api/workspaces/test-docs/github/token | jq
```

## Step 10: Test Repository Access

Verify the backend can access your repo using the installation token:

```python
from kurt.github import github_app
import httpx
import asyncio

async def test_repo_access(workspace_id, owner, repo):
    token = await github_app.get_workspace_token(workspace_id)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Files: {[f['name'] for f in response.json()]}")

asyncio.run(test_repo_access("ws-abc123", "YOUR_USERNAME", "test-repo"))
```

## Troubleshooting

### Webhook Not Received

1. **Check ngrok/smee is running**:
   ```bash
   curl https://YOUR_SUBDOMAIN.ngrok.io/api/webhooks/github
   ```
   Should return 405 Method Not Allowed (GET not supported)

2. **Check webhook deliveries** in GitHub App settings:
   - Go to your app settings → "Advanced" tab
   - See recent deliveries and responses

3. **Check server logs**:
   ```bash
   # FastAPI logs should show:
   INFO: POST /api/webhooks/github HTTP/1.1
   ```

### Installation Not Linked

Check database directly:

```sql
-- PostgreSQL
SELECT * FROM workspaces WHERE slug = 'test-docs';

-- SQLite
sqlite3 test.db "SELECT * FROM workspaces WHERE slug = 'test-docs';"
```

Verify `github_installation_id` is set.

### Token Retrieval Fails

1. **Check installation ID is set** in workspace
2. **Check private key format** - Should be multi-line PEM:
   ```
   -----BEGIN RSA PRIVATE KEY-----
   MIIEpAIBAAKCAQEA...
   ...
   -----END RSA PRIVATE KEY-----
   ```
3. **Test JWT generation**:
   ```python
   from kurt.github.app_client import GitHubAppClient
   client = GitHubAppClient()
   jwt_token = client.generate_jwt()
   print(f"JWT: {jwt_token[:50]}...")
   ```

### Permission Errors

If you get 403/404 from GitHub API:
1. Check app has correct permissions (Contents: Read & Write)
2. Check app is installed on the specific repository
3. Check token hasn't expired (should auto-refresh)

## Testing Checklist

- [ ] GitHub App registered
- [ ] Webhook proxy running (ngrok/smee)
- [ ] Environment variables set
- [ ] Database migrated
- [ ] API server running
- [ ] Workspace created via API
- [ ] GitHub App installed via browser
- [ ] Webhook received and processed
- [ ] Installation linked to workspace
- [ ] Access token retrieved successfully
- [ ] Repository access working

## Automated Testing

For unit tests without real GitHub App:

```python
# See src/kurt/github/tests/test_app_client.py
# Uses mocked jwt.encode() and httpx.AsyncClient

pytest src/kurt/github/tests/test_app_client.py -v
```

## Production Deployment

When deploying to production:

1. **Update webhook URL** to your production domain
2. **Use real database** (PostgreSQL, not SQLite)
3. **Secure webhook secret** - Use strong random value
4. **Environment variables** - Use secrets manager
5. **HTTPS required** - GitHub requires HTTPS for webhooks
6. **Monitor webhook deliveries** - Check GitHub App settings
