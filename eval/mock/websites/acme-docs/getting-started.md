---
title: "Getting Started with ACME"
url: https://docs.acme-corp.com/getting-started
date: 2024-10-25
category: tutorial
difficulty: beginner
time: 10 minutes
---

# Getting Started

Build and deploy your first API with ACME in under 10 minutes.

## Prerequisites

- Node.js 18+ or Python 3.9+
- npm or pip installed
- An ACME account (sign up at acme-corp.com/signup)

## Installation

### Node.js

```bash
npm install -g acme-cli
```

### Python

```bash
pip install acme-sdk
```

## Create Your First API

### 1. Initialize Project

```bash
acme init my-first-api
cd my-first-api
```

This creates:
```
my-first-api/
├── acme.config.json   # Configuration
├── api/
│   └── hello.js       # Your first endpoint
└── .env.example       # Environment variables
```

### 2. Write Your Endpoint

Open `api/hello.js`:

```javascript
export default async function handler(req) {
  return {
    message: 'Hello, ACME!',
    timestamp: new Date().toISOString()
  };
}
```

### 3. Test Locally

```bash
acme dev
```

Your API is now running at `http://localhost:3000`

Test it:
```bash
curl http://localhost:3000/hello
# {"message":"Hello, ACME!","timestamp":"2024-11-01T10:30:00.000Z"}
```

### 4. Deploy to Production

```bash
acme deploy
```

Output:
```
✓ Building...
✓ Deploying to edge...
✓ Configuring SSL...
✓ Done!

URL: https://my-first-api.acme.dev
```

That's it! Your API is live globally.

## Next Steps

- [API Reference](https://docs.acme-corp.com/api-reference) - Full API docs
- [Authentication Guide](https://docs.acme-corp.com/guide-authentication) - Secure your API
- [Advanced Patterns](https://docs.acme-corp.com/guide-advanced) - Middleware, caching, rate limiting

## Common Issues

**Q: Deploy fails with "Authentication error"**

A: Run `acme login` to authenticate.

**Q: Local dev server won't start**

A: Check if port 3000 is in use: `lsof -i :3000`

**Q: Changes not reflecting after deploy**

A: Clear your CDN cache: `acme cache clear`

## Get Help

- [Discord Community](https://discord.gg/acme)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/acme)
- Email: support@acme-corp.com
