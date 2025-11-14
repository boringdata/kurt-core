#!/usr/bin/env python3
"""Generate all mock data files for eval scenarios.

This script creates realistic mock content for testing Kurt agent behavior.
Run: python eval/generate_mock_data.py
"""

from pathlib import Path

# This script is in eval/mock/, so the mock directory is the parent directory
MOCK_DIR = Path(__file__).parent

# Mock content templates
MOCK_FILES = {
    # ACME Docs (already have getting-started.md)
    "websites/acme-docs/api-reference.md": """---
title: "API Reference"
url: https://docs.acme-corp.com/api-reference
date: 2024-10-20
category: reference
---

# API Reference

Complete reference for the ACME API.

## Authentication

Include your API key in the `Authorization` header:

```bash
curl https://api.acme.dev/v1/users \\
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Endpoints

### GET /v1/users

List all users.

**Parameters:**
- `limit` (optional): Number of results (default: 10, max: 100)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "users": [
    {"id": "usr_123", "name": "John Doe", "created_at": "2024-01-01T00:00:00Z"}
  ],
  "total": 150,
  "has_more": true
}
```

### POST /v1/users

Create a new user.

**Body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com"
}
```

**Response:**
```json
{
  "id": "usr_124",
  "name": "Jane Smith",
  "email": "jane@example.com",
  "created_at": "2024-11-01T10:00:00Z"
}
```

### GET /v1/users/:id

Retrieve a specific user.

**Response:**
```json
{
  "id": "usr_123",
  "name": "John Doe",
  "email": "john@example.com",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Error Handling

All errors return JSON with `error` and `message` fields:

```json
{
  "error": "not_found",
  "message": "User not found",
  "status": 404
}
```

## Rate Limits

- **Free tier:** 100 requests/minute
- **Pro tier:** 1,000 requests/minute
- **Team tier:** 10,000 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1635724800
```
""",
    "websites/acme-docs/guide-authentication.md": """---
title: "Authentication Guide"
url: https://docs.acme-corp.com/guide-authentication
date: 2024-10-18
category: guide
---

# Authentication

Secure your ACME API with authentication.

## API Keys

Generate an API key from your dashboard: https://dashboard.acme-corp.com/keys

### Using API Keys

Include in the `Authorization` header:

```javascript
fetch('https://api.acme.dev/v1/users', {
  headers: {
    'Authorization': 'Bearer sk_live_abc123...'
  }
});
```

### Key Types

- **Test keys** (`sk_test_...`): For development
- **Live keys** (`sk_live_...`): For production

## JWT Tokens

For user-specific operations, use JWT tokens.

### Generate Token

```javascript
import { acme } from '@acme/sdk';

const token = await acme.auth.createToken({
  userId: 'usr_123',
  expiresIn: '7d'
});
```

### Verify Token

```javascript
const decoded = await acme.auth.verifyToken(token);
console.log(decoded.userId); // 'usr_123'
```

## OAuth 2.0

For third-party integrations.

### Authorization Flow

1. Redirect user to: `https://acme.dev/oauth/authorize?client_id=...`
2. User approves
3. Receive code at your redirect URI
4. Exchange code for token

```bash
curl -X POST https://api.acme.dev/oauth/token \\
  -d client_id=YOUR_CLIENT_ID \\
  -d client_secret=YOUR_SECRET \\
  -d code=AUTHORIZATION_CODE \\
  -d grant_type=authorization_code
```

## Security Best Practices

1. **Never expose keys in client-side code**
2. **Rotate keys regularly** (quarterly recommended)
3. **Use environment variables** for key storage
4. **Enable IP allowlisting** in dashboard
5. **Monitor API usage** for anomalies
""",
    "websites/acme-docs/guide-advanced.md": """---
title: "Advanced Patterns"
url: https://docs.acme-corp.com/guide-advanced
date: 2024-10-15
category: guide
---

# Advanced Patterns

## Middleware

Add logic that runs before your handlers.

```javascript
// middleware/auth.js
export default async function authMiddleware(req, next) {
  const token = req.headers.authorization?.split(' ')[1];

  if (!token) {
    return { error: 'Unauthorized', status: 401 };
  }

  req.user = await verifyToken(token);
  return next();
}

// api/protected.js
import { withMiddleware } from '@acme/sdk';
import authMiddleware from '../middleware/auth';

export default withMiddleware(authMiddleware, async (req) => {
  return { user: req.user };
});
```

## Caching

Cache responses at the edge.

```javascript
export const config = {
  cache: {
    ttl: 300, // 5 minutes
    key: (req) => `users-${req.query.id}`,
    vary: ['Authorization'] // Different cache per user
  }
};

export default async function handler(req) {
  // This response is cached
  return await db.users.find(req.query.id);
}
```

## Rate Limiting

Protect your API from abuse.

```javascript
export const config = {
  rateLimit: {
    window: '1m',
    max: 100,
    keyGenerator: (req) => req.ip
  }
};
```

## Background Jobs

Run tasks asynchronously.

```javascript
import { queue } from '@acme/sdk';

export default async function handler(req) {
  const user = await db.users.create(req.body);

  // Run async
  await queue.add('send-welcome-email', {
    userId: user.id,
    email: user.email
  });

  return user;
}
```

## Webhooks

Receive events from ACME.

```javascript
import { verifyWebhook } from '@acme/sdk';

export default async function webhook(req) {
  // Verify signature
  const valid = verifyWebhook(req.body, req.headers['acme-signature']);

  if (!valid) {
    return { error: 'Invalid signature', status: 401 };
  }

  const { type, data } = req.body;

  if (type === 'user.created') {
    await handleNewUser(data);
  }

  return { received: true };
}
```
""",
    "websites/acme-docs/troubleshooting.md": """---
title: "Troubleshooting"
url: https://docs.acme-corp.com/troubleshooting
date: 2024-10-10
category: support
---

# Troubleshooting

Common issues and solutions.

## Deploy Failures

### "Authentication error"

**Cause:** Not logged in or expired session.

**Fix:**
```bash
acme login
acme deploy
```

### "Build failed: Module not found"

**Cause:** Missing dependency in package.json.

**Fix:**
```bash
npm install <missing-module>
acme deploy
```

### "Deploy timeout"

**Cause:** Large bundle or slow network.

**Fix:**
```bash
acme deploy --timeout 600  # 10 minutes
```

## Runtime Errors

### "500 Internal Server Error"

**Debug:**
```bash
acme logs --tail 100
```

Look for:
- Uncaught exceptions
- Database connection errors
- Timeout issues

### "429 Too Many Requests"

**Cause:** Rate limit exceeded.

**Fix:**
- Upgrade your plan
- Implement client-side rate limiting
- Add caching

## Performance Issues

### "Slow response times"

**Check:**
1. Database query performance
2. External API latency
3. Bundle size

**Optimize:**
```bash
# Analyze bundle
acme analyze

# Enable caching
export const config = { cache: { ttl: 300 } };
```

### "High memory usage"

**Fix:**
- Stream large responses
- Implement pagination
- Clear unused variables

## Getting Help

1. Check [Status Page](https://status.acme-corp.com)
2. Search [Discord](https://discord.gg/acme)
3. Email support@acme-corp.com
""",
    "websites/acme-docs/changelog.md": """---
title: "Changelog"
url: https://docs.acme-corp.com/changelog
date: 2024-11-01
category: release-notes
---

# Changelog

## v2.0.0 (2024-09-15)

### Added
- 15 new edge locations
- Real-time debugging tools
- Advanced analytics dashboard
- One-command deploy

### Changed
- 3x faster cold starts (12ms avg)
- 60% lower P99 latency

### Fixed
- Memory leak in connection pooling
- Edge caching inconsistencies

## v1.5.0 (2024-07-10)

### Added
- Webhook support
- Custom domain SSL automation
- Team collaboration features

### Fixed
- Deploy timeout issues
- Log streaming bugs

## v1.0.0 (2024-03-01)

Initial public release.
""",
    "websites/acme-docs/sitemap.xml": """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://docs.acme-corp.com/getting-started</loc><priority>1.0</priority></url>
  <url><loc>https://docs.acme-corp.com/api-reference</loc><priority>0.9</priority></url>
  <url><loc>https://docs.acme-corp.com/guide-authentication</loc><priority>0.8</priority></url>
  <url><loc>https://docs.acme-corp.com/guide-advanced</loc><priority>0.7</priority></url>
  <url><loc>https://docs.acme-corp.com/troubleshooting</loc><priority>0.6</priority></url>
  <url><loc>https://docs.acme-corp.com/changelog</loc><priority>0.5</priority></url>
</urlset>
""",
    # ==========================================================================
    # COMPETITOR WEBSITE (for competitive analysis scenarios)
    # ==========================================================================
    "websites/competitor-co/feature-comparison.md": """---
title: "ACME vs Others - Feature Comparison"
url: https://competitor-co.com/feature-comparison
date: 2024-10-01
category: comparison
---

# Feature Comparison: Us vs. The Competition

See how we stack up against ACME and other platforms.

## Speed & Performance

| Feature | Us | ACME | Others |
|---------|-------|------|--------|
| Cold start time | **8ms** | 12ms | 25ms |
| P99 latency | **45ms** | 78ms | 120ms |
| Edge locations | **50+** | 35 | 15 |
| Auto-scaling | ✅ | ✅ | ⚠️ Limited |

## Developer Experience

| Feature | Us | ACME | Others |
|---------|-------|------|--------|
| CLI setup time | **30 sec** | 2 min | 5 min |
| Deploy time | **15 sec** | 45 sec | 2 min |
| Local dev server | ✅ Hot reload | ✅ Basic | ❌ |
| TypeScript support | ✅ Native | ⚠️ Plugin | ❌ |

## Pricing

| Tier | Us | ACME | Others |
|------|-------|------|--------|
| Free | 1M requests | 100K requests | 50K requests |
| Pro | $29/mo | $49/mo | $99/mo |
| Team | $99/mo | $199/mo | $299/mo |

## Why Choose Us?

### 40% Faster
Our edge network is optimized for speed. We achieve **8ms cold starts** vs. ACME's 12ms.

### Better DX
Setup in 30 seconds, deploy in 15 seconds. ACME takes 2+ minutes for initial setup.

### More Affordable
Get 10x more free tier requests. Our Pro plan is $20/mo cheaper than ACME.

### Superior TypeScript
Native TypeScript support with full type inference. ACME requires additional plugins.

## Migration from ACME

Switching from ACME? We have automated migration tools:

```bash
npx migrate-from-acme
```

This will:
1. Convert ACME config to our format
2. Update API calls
3. Migrate environment variables
4. Deploy to our platform

Takes less than 5 minutes.

## Customer Testimonials

> "We migrated from ACME and saw 2x faster response times immediately. The migration took 10 minutes."
> - Sarah Chen, CTO at DataFlow

> "Switching saved us $500/month on our API infrastructure costs."
> - Mike Rodriguez, Lead Engineer at StreamAPI
""",
    "websites/competitor-co/pricing.md": """---
title: "Pricing - Simple, Transparent, Affordable"
url: https://competitor-co.com/pricing
date: 2024-09-28
category: pricing
---

# Pricing

## Free Tier
**Perfect for side projects**

- 1,000,000 requests/month
- 100GB bandwidth
- 10 deployments/day
- Community support
- All edge locations

**$0/month forever**

## Pro Tier
**For growing teams**

- 10,000,000 requests/month
- 1TB bandwidth
- Unlimited deployments
- Email support (24h response)
- Custom domains
- Advanced analytics
- Priority edge routing

**$29/month**

## Team Tier
**For organizations**

Everything in Pro, plus:

- 100,000,000 requests/month
- 10TB bandwidth
- Phone support (4h response)
- SSO / SAML
- Team collaboration features
- Audit logs
- SLA guarantee (99.99%)
- Dedicated account manager

**$99/month**

## Enterprise
**Custom solutions**

- Custom request limits
- Dedicated infrastructure
- 24/7 phone support
- Custom SLA
- Professional services
- Training & onboarding

**Contact sales**

## Add-ons

- **Extra bandwidth:** $0.10/GB
- **Extra requests:** $0.50/million
- **Advanced security:** $49/month

## FAQ

**Q: Can I change plans anytime?**
A: Yes, upgrade or downgrade anytime. Changes are prorated.

**Q: What happens if I exceed my limits?**
A: We'll send you an email notification. You can upgrade or purchase add-ons.

**Q: Do you offer non-profit discounts?**
A: Yes! 50% off for verified non-profits and open source projects.

**Q: Is there a free trial for paid plans?**
A: Yes, 14-day free trial for Pro and Team tiers. No credit card required.
""",
    "websites/competitor-co/tutorial-basics.md": """---
title: "Tutorial: Your First API in 5 Minutes"
url: https://competitor-co.com/tutorial-basics
date: 2024-09-20
category: tutorial
difficulty: beginner
---

# Your First API in 5 Minutes

## Step 1: Install CLI

```bash
npm install -g ourplatform-cli
```

## Step 2: Login

```bash
ourplatform login
```

## Step 3: Create Project

```bash
ourplatform create hello-api
cd hello-api
```

This creates:
```
hello-api/
├── config.yml
├── functions/
│   └── hello.ts
└── package.json
```

## Step 4: Write Your Function

The CLI already created a starter function. Open `functions/hello.ts`:

```typescript
export default async (req: Request) => {
  return Response.json({
    message: 'Hello from the edge!',
    timestamp: new Date().toISOString(),
    location: req.cf?.colo // Edge location
  });
};
```

## Step 5: Test Locally

```bash
ourplatform dev
```

Visit `http://localhost:3000/hello`:

```json
{
  "message": "Hello from the edge!",
  "timestamp": "2024-11-01T10:00:00.000Z",
  "location": "SFO"
}
```

## Step 6: Deploy

```bash
ourplatform deploy
```

Output:
```
✓ Building functions...
✓ Deploying to 50+ edge locations...
✓ Configuring DNS...
✓ Done in 15 seconds!

URL: https://hello-api.ourplatform.dev
```

That's it! Your API is live globally.

## Next Steps

- [Add authentication](https://competitor-co.com/tutorial-advanced#auth)
- [Connect a database](https://competitor-co.com/tutorial-advanced#database)
- [Add rate limiting](https://competitor-co.com/tutorial-advanced#rate-limiting)
""",
    "websites/competitor-co/tutorial-advanced.md": """---
title: "Advanced Tutorial: Authentication, Database, Caching"
url: https://competitor-co.com/tutorial-advanced
date: 2024-09-15
category: tutorial
difficulty: advanced
---

# Advanced Tutorial

## Authentication {#auth}

Add JWT authentication to your API.

### Install Dependencies

```bash
npm install @ourplatform/auth
```

### Create Auth Middleware

```typescript
import { verifyToken } from '@ourplatform/auth';

export async function authMiddleware(req: Request) {
  const token = req.headers.get('Authorization')?.replace('Bearer ', '');

  if (!token) {
    return Response.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const user = await verifyToken(token);
  if (!user) {
    return Response.json({ error: 'Invalid token' }, { status: 401 });
  }

  return { user };
}
```

### Use in Your Functions

```typescript
import { authMiddleware } from '../middleware/auth';

export default async (req: Request) => {
  const auth = await authMiddleware(req);
  if (auth instanceof Response) return auth; // Error response

  return Response.json({
    message: `Hello ${auth.user.name}!`
  });
};
```

## Database {#database}

Connect to Postgres, MySQL, or any database.

```typescript
import { createClient } from '@ourplatform/database';

const db = createClient(process.env.DATABASE_URL);

export default async (req: Request) => {
  const users = await db.query('SELECT * FROM users LIMIT 10');
  return Response.json({ users });
};
```

### Connection Pooling

We automatically handle connection pooling at the edge:

```typescript
export const config = {
  database: {
    pool: {
      min: 2,
      max: 10,
      idleTimeout: 30000
    }
  }
};
```

## Caching {#caching}

Cache responses at the edge for better performance.

```typescript
export const config = {
  cache: {
    ttl: 300, // 5 minutes
    key: (req) => new URL(req.url).pathname,
    vary: ['Authorization'] // Different cache per user
  }
};

export default async (req: Request) => {
  // This response is cached for 5 minutes
  const data = await fetch('https://api.example.com/slow-endpoint');
  return Response.json(data);
};
```

## Rate Limiting {#rate-limiting}

Protect your API from abuse.

```typescript
export const config = {
  rateLimit: {
    window: 60, // 1 minute
    max: 100, // 100 requests per minute
    keyGenerator: (req) => req.headers.get('X-API-Key') || req.ip
  }
};
```

When limit is exceeded, returns:
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 45
}
```
""",
    "websites/competitor-co/case-study.md": """---
title: "Case Study: How StreamAPI Cut Costs by 60%"
url: https://competitor-co.com/case-study
date: 2024-09-01
category: case-study
---

# Case Study: StreamAPI

## The Challenge

StreamAPI is a real-time data platform serving 10M requests/day. They were using ACME but faced:

- High costs ($2,000/month for their traffic)
- Slow response times (P99 latency: 250ms)
- Complex deployment process (15+ minute deploys)
- Limited analytics and debugging tools

## The Solution

StreamAPI migrated to our platform in October 2024.

### Migration Process

1. **Automated migration** (10 minutes)
   - Converted ACME config format
   - Updated API endpoints
   - Migrated environment variables

2. **Testing** (2 hours)
   - Ran integration tests
   - Load testing with production traffic
   - Validated all edge cases

3. **Gradual rollout** (1 week)
   - Started with 10% of traffic
   - Monitored performance metrics
   - Scaled to 100% after 3 days

Total migration time: **1 week from start to 100% migration**

## Results

### Cost Savings: 60%

Before (ACME):
- $2,000/month base plan
- $500/month overage fees
- **Total: $2,500/month**

After (Our Platform):
- $99/month Team plan
- $200/month bandwidth add-ons
- $500/month for extra requests
- **Total: $799/month**

**Savings: $1,701/month ($20,412/year)**

### Performance Improvements

| Metric | Before (ACME) | After (Us) | Improvement |
|--------|---------------|------------|-------------|
| P50 latency | 120ms | 45ms | **62% faster** |
| P99 latency | 250ms | 89ms | **64% faster** |
| Cold start | 18ms | 8ms | **56% faster** |
| Deploy time | 15 min | 20 sec | **98% faster** |
| Uptime | 99.9% | 99.99% | **10x better** |

### Developer Experience

"The deployment experience is night and day. We went from 15-minute deploys to 20 seconds. Our engineers can ship features 10x faster now." - Mike Rodriguez, Lead Engineer

### Business Impact

- **Customer satisfaction:** Up 25% (faster response times)
- **Developer productivity:** Up 40% (faster deploys)
- **Infrastructure costs:** Down 60%
- **Incident response time:** Down 80% (better debugging tools)

## Key Takeaways

1. **Migration is easy:** Automated tools made migration painless
2. **Performance gains are real:** 60%+ latency improvements across the board
3. **Cost savings are significant:** $20K/year saved on infrastructure
4. **Developer happiness matters:** Faster deploys = happier engineers

## Get Started

Want similar results? [Start your free trial](https://competitor-co.com/signup) or [talk to our team](https://competitor-co.com/contact).
""",
    "websites/competitor-co/sitemap.xml": """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://competitor-co.com/feature-comparison</loc><priority>1.0</priority></url>
  <url><loc>https://competitor-co.com/pricing</loc><priority>0.9</priority></url>
  <url><loc>https://competitor-co.com/tutorial-basics</loc><priority>0.8</priority></url>
  <url><loc>https://competitor-co.com/tutorial-advanced</loc><priority>0.8</priority></url>
  <url><loc>https://competitor-co.com/case-study</loc><priority>0.7</priority></url>
</urlset>
""",
    # ==========================================================================
    # CMS DATA (for CMS integration scenarios)
    # ==========================================================================
    "cms/sanity/types.json": """{
  "types": [
    {
      "name": "article",
      "title": "Article",
      "type": "document",
      "fields": [
        {"name": "title", "type": "string", "title": "Title"},
        {"name": "slug", "type": "slug", "title": "Slug"},
        {"name": "author", "type": "reference", "to": [{"type": "author"}]},
        {"name": "publishedAt", "type": "datetime", "title": "Published at"},
        {"name": "body", "type": "array", "of": [{"type": "block"}]},
        {"name": "excerpt", "type": "text", "title": "Excerpt"},
        {"name": "tags", "type": "array", "of": [{"type": "string"}]},
        {"name": "featured", "type": "boolean", "title": "Featured"}
      ]
    },
    {
      "name": "author",
      "title": "Author",
      "type": "document",
      "fields": [
        {"name": "name", "type": "string", "title": "Name"},
        {"name": "bio", "type": "text", "title": "Bio"},
        {"name": "avatar", "type": "image", "title": "Avatar"}
      ]
    }
  ]
}""",
    "cms/sanity/query-results.json": """{
  "result": [
    {
      "_id": "article-1",
      "_type": "article",
      "title": "10 Best Practices for API Design",
      "slug": {"current": "api-design-best-practices"},
      "author": {"_ref": "author-1", "name": "Sarah Chen"},
      "publishedAt": "2024-10-15T10:00:00Z",
      "excerpt": "Learn how to design APIs that developers love to use.",
      "tags": ["api-design", "best-practices", "engineering"],
      "featured": true,
      "_createdAt": "2024-10-10T09:00:00Z",
      "_updatedAt": "2024-10-15T10:00:00Z"
    },
    {
      "_id": "article-2",
      "_type": "article",
      "title": "Scaling Your Microservices Architecture",
      "slug": {"current": "scaling-microservices"},
      "author": {"_ref": "author-2", "name": "Mike Rodriguez"},
      "publishedAt": "2024-10-20T14:00:00Z",
      "excerpt": "Strategies for scaling microservices to handle millions of requests.",
      "tags": ["microservices", "scaling", "architecture"],
      "featured": false,
      "_createdAt": "2024-10-18T11:00:00Z",
      "_updatedAt": "2024-10-20T14:00:00Z"
    },
    {
      "_id": "article-3",
      "_type": "article",
      "title": "Introduction to Serverless Functions",
      "slug": {"current": "intro-serverless-functions"},
      "author": {"_ref": "author-1", "name": "Sarah Chen"},
      "publishedAt": "2024-11-01T09:00:00Z",
      "excerpt": "Get started with serverless computing and edge functions.",
      "tags": ["serverless", "edge-computing", "tutorial"],
      "featured": true,
      "_createdAt": "2024-10-28T08:00:00Z",
      "_updatedAt": "2024-11-01T09:00:00Z"
    }
  ],
  "ms": 45,
  "query": "*[_type == 'article'] | order(publishedAt desc)"
}""",
    "cms/sanity/article-1.json": """{
  "_id": "article-1",
  "_type": "article",
  "_rev": "v1-abc123",
  "_createdAt": "2024-10-10T09:00:00Z",
  "_updatedAt": "2024-10-15T10:00:00Z",
  "title": "10 Best Practices for API Design",
  "slug": {
    "_type": "slug",
    "current": "api-design-best-practices"
  },
  "author": {
    "_ref": "author-1",
    "_type": "reference"
  },
  "publishedAt": "2024-10-15T10:00:00Z",
  "body": [
    {
      "_type": "block",
      "style": "normal",
      "children": [{"_type": "span", "text": "Designing great APIs is both an art and a science. Here are 10 best practices we've learned from building APIs at scale."}]
    },
    {
      "_type": "block",
      "style": "h2",
      "children": [{"_type": "span", "text": "1. Use RESTful Conventions"}]
    },
    {
      "_type": "block",
      "style": "normal",
      "children": [{"_type": "span", "text": "Follow REST principles: GET for reading, POST for creating, PUT/PATCH for updating, DELETE for removing."}]
    }
  ],
  "excerpt": "Learn how to design APIs that developers love to use.",
  "tags": ["api-design", "best-practices", "engineering"],
  "featured": true
}""",
    "cms/sanity/article-2.json": """{
  "_id": "article-2",
  "_type": "article",
  "_rev": "v1-def456",
  "_createdAt": "2024-10-18T11:00:00Z",
  "_updatedAt": "2024-10-20T14:00:00Z",
  "title": "Scaling Your Microservices Architecture",
  "slug": {
    "_type": "slug",
    "current": "scaling-microservices"
  },
  "author": {
    "_ref": "author-2",
    "_type": "reference"
  },
  "publishedAt": "2024-10-20T14:00:00Z",
  "body": [
    {
      "_type": "block",
      "style": "normal",
      "children": [{"_type": "span", "text": "As your application grows, scaling microservices becomes critical. Here's how we scaled to handle 10M requests/day."}]
    },
    {
      "_type": "block",
      "style": "h2",
      "children": [{"_type": "span", "text": "Horizontal Scaling"}]
    },
    {
      "_type": "block",
      "style": "normal",
      "children": [{"_type": "span", "text": "Add more instances of your services behind a load balancer. We use Kubernetes for orchestration."}]
    }
  ],
  "excerpt": "Strategies for scaling microservices to handle millions of requests.",
  "tags": ["microservices", "scaling", "architecture"],
  "featured": false
}""",
    "cms/sanity/publish-response.json": """{
  "transactionId": "tx-publish-789",
  "results": [
    {
      "id": "article-1",
      "operation": "create",
      "document": {
        "_id": "article-1",
        "_type": "article",
        "_rev": "v1-abc123",
        "title": "New Article Published",
        "_createdAt": "2024-11-01T10:00:00Z"
      }
    }
  ],
  "documentIds": ["article-1"],
  "transactionTime": "2024-11-01T10:00:00.123Z"
}""",
    # ==========================================================================
    # RESEARCH APIs (for research & competitive analysis scenarios)
    # ==========================================================================
    "research/perplexity-ai-trends.json": """{
  "id": "pplx-12345",
  "model": "llama-3.1-sonar-large-128k-online",
  "created": 1730462400,
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "Based on recent industry trends and discussions, here are the top 5 AI/ML topics gaining traction in late 2024:\\n\\n1. **Large Language Model (LLM) Fine-tuning and RAG**: Developers are increasingly adopting retrieval-augmented generation (RAG) patterns to ground LLM responses in proprietary data. Fine-tuning smaller models for specific tasks is becoming more accessible.\\n\\n2. **AI Agents and Autonomous Systems**: Multi-agent frameworks like LangGraph and AutoGPT are enabling AI systems to perform complex tasks autonomously. This includes code generation, research synthesis, and workflow automation.\\n\\n3. **Multimodal AI**: Models that can process text, images, audio, and video together (like GPT-4V and Gemini) are enabling new applications in content creation, accessibility, and education.\\n\\n4. **Edge AI and On-Device Models**: Running smaller LLMs on edge devices for privacy and latency benefits. Frameworks like ONNX Runtime and TensorFlow Lite are making this more practical.\\n\\n5. **AI Ethics and Governance**: As AI deployment scales, there's growing focus on responsible AI practices, bias mitigation, explainability, and regulatory compliance (EU AI Act, etc.).\\n\\nSources: [1] Hacker News discussions Oct-Nov 2024 [2] AI research papers on arXiv [3] Industry reports from Gartner and McKinsey"
      },
      "delta": {
        "role": "assistant",
        "content": ""
      }
    }
  ],
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 285,
    "total_tokens": 327
  }
}""",
    "research/perplexity-fastapi.json": """{
  "id": "pplx-67890",
  "model": "llama-3.1-sonar-large-128k-online",
  "created": 1730462500,
  "choices": [
    {
      "index": 0,
      "finish_reason": "stop",
      "message": {
        "role": "assistant",
        "content": "Here's a comprehensive overview of FastAPI based on recent sources:\\n\\n**What is FastAPI?**\\nFastAPI is a modern, high-performance Python web framework for building APIs. It's built on Starlette (ASGI) and Pydantic, offering automatic API documentation, type checking, and async support.\\n\\n**Key Features:**\\n1. **Fast**: One of the fastest Python frameworks (comparable to NodeJS and Go)\\n2. **Type hints**: Uses Python type hints for validation and auto-docs\\n3. **Async support**: Native async/await support for I/O operations\\n4. **Auto documentation**: Automatic OpenAPI (Swagger) and ReDoc docs\\n5. **Dependency injection**: Built-in DI system for clean code\\n\\n**Common Use Cases:**\\n- RESTful APIs for web/mobile apps\\n- Microservices architecture\\n- Machine learning model serving\\n- Real-time data streaming APIs\\n\\n**Getting Started:**\\n```python\\nfrom fastapi import FastAPI\\napp = FastAPI()\\n\\n@app.get('/')\\nasync def root():\\n    return {'message': 'Hello World'}\\n```\\n\\n**Ecosystem:**\\n- Production deployment: Uvicorn, Gunicorn\\n- ORMs: SQLAlchemy, Tortoise ORM\\n- Testing: pytest with TestClient\\n\\nSources: [1] FastAPI documentation [2] Python Weekly discussions [3] Real Python tutorials"
      },
      "delta": {
        "role": "assistant",
        "content": ""
      }
    }
  ],
  "usage": {
    "prompt_tokens": 35,
    "completion_tokens": 312,
    "total_tokens": 347
  }
}""",
    "research/reddit-dataeng.json": """{
  "kind": "Listing",
  "data": {
    "after": "t3_abc123",
    "dist": 25,
    "children": [
      {
        "kind": "t3",
        "data": {
          "title": "What's the best way to orchestrate data pipelines in 2024?",
          "author": "data_engineer_99",
          "created_utc": 1730390400,
          "score": 342,
          "num_comments": 87,
          "url": "https://www.reddit.com/r/dataengineering/comments/xyz/",
          "selftext": "Our team is evaluating Airflow, Dagster, and Prefect. Looking for experiences with these tools at scale. We process ~10TB/day.",
          "subreddit": "dataengineering",
          "upvote_ratio": 0.95
        }
      },
      {
        "kind": "t3",
        "data": {
          "title": "Dagster vs Airflow - Real world comparison after using both",
          "author": "pipeline_expert",
          "created_utc": 1730304000,
          "score": 428,
          "num_comments": 123,
          "url": "https://www.reddit.com/r/dataengineering/comments/abc/",
          "selftext": "After migrating from Airflow to Dagster, here's what we learned. TLDR: Dagster's asset-based approach is game-changing for data quality.",
          "subreddit": "dataengineering",
          "upvote_ratio": 0.97
        }
      },
      {
        "kind": "t3",
        "data": {
          "title": "How to handle schema evolution in data lakes?",
          "author": "lakehouse_builder",
          "created_utc": 1730217600,
          "score": 215,
          "num_comments": 56,
          "url": "https://www.reddit.com/r/dataengineering/comments/def/",
          "selftext": "We're using Delta Lake on S3. Schema changes are causing pipeline failures. What's the best practice for backwards compatibility?",
          "subreddit": "dataengineering",
          "upvote_ratio": 0.92
        }
      }
    ]
  }
}""",
    "research/reddit-python.json": """{
  "kind": "Listing",
  "data": {
    "after": "t3_def456",
    "dist": 25,
    "children": [
      {
        "kind": "t3",
        "data": {
          "title": "Python 3.13 released with major performance improvements",
          "author": "pythonista_pro",
          "created_utc": 1730476800,
          "score": 1542,
          "num_comments": 287,
          "url": "https://www.reddit.com/r/Python/comments/ghi/",
          "selftext": "JIT compilation is finally here! Seeing 2-3x speedups in CPU-bound code. This is huge for ML workloads.",
          "subreddit": "Python",
          "upvote_ratio": 0.98
        }
      },
      {
        "kind": "t3",
        "data": {
          "title": "Best practices for structuring large Python projects?",
          "author": "code_architect",
          "created_utc": 1730390400,
          "score": 823,
          "num_comments": 156,
          "url": "https://www.reddit.com/r/Python/comments/jkl/",
          "selftext": "Working on a 100K+ LOC Python monorepo. Looking for advice on module organization, dependency management, and testing strategies.",
          "subreddit": "Python",
          "upvote_ratio": 0.94
        }
      },
      {
        "kind": "t3",
        "data": {
          "title": "FastAPI vs Django REST Framework in 2024",
          "author": "api_developer",
          "created_utc": 1730304000,
          "score": 645,
          "num_comments": 201,
          "url": "https://www.reddit.com/r/Python/comments/mno/",
          "selftext": "Comparing these two for a new microservices project. FastAPI's async support is tempting, but DRF has more mature ecosystem. Thoughts?",
          "subreddit": "Python",
          "upvote_ratio": 0.91
        }
      }
    ]
  }
}""",
    "research/hackernews-top.json": """[
  38942156,
  38941823,
  38941567,
  38940892,
  38940234,
  38939876,
  38939123,
  38938765,
  38938234,
  38937891
]""",
    # ==========================================================================
    # ANALYTICS DATA (for analytics-driven scenarios)
    # ==========================================================================
    "analytics/top-pages.json": """{
  "query": "top_pages",
  "period": "last_30_days",
  "results": [
    {
      "source_url": "https://acme-corp.com/blog-post-1",
      "title": "How to Build Scalable APIs",
      "pageviews": 15420,
      "unique_visitors": 12350,
      "avg_time_on_page": 285,
      "bounce_rate": 0.42,
      "conversions": 234,
      "rank": 1,
      "trend": "up",
      "change_percent": 15.3
    },
    {
      "source_url": "https://docs.acme-corp.com/getting-started",
      "title": "Getting Started with ACME",
      "pageviews": 12890,
      "unique_visitors": 10240,
      "avg_time_on_page": 420,
      "bounce_rate": 0.35,
      "conversions": 567,
      "rank": 2,
      "trend": "up",
      "change_percent": 22.1
    },
    {
      "source_url": "https://acme-corp.com/pricing",
      "title": "Pricing - ACME Corp",
      "pageviews": 9876,
      "unique_visitors": 8234,
      "avg_time_on_page": 180,
      "bounce_rate": 0.28,
      "conversions": 892,
      "rank": 3,
      "trend": "stable",
      "change_percent": 2.4
    },
    {
      "source_url": "https://docs.acme-corp.com/api-reference",
      "title": "API Reference",
      "pageviews": 8543,
      "unique_visitors": 6789,
      "avg_time_on_page": 540,
      "bounce_rate": 0.38,
      "conversions": 156,
      "rank": 4,
      "trend": "up",
      "change_percent": 8.7
    },
    {
      "source_url": "https://acme-corp.com/blog-post-2",
      "title": "Announcing ACME 2.0",
      "pageviews": 7234,
      "unique_visitors": 6123,
      "avg_time_on_page": 195,
      "bounce_rate": 0.45,
      "conversions": 89,
      "rank": 5,
      "trend": "down",
      "change_percent": -5.2
    }
  ],
  "generated_at": "2024-11-01T10:00:00Z"
}""",
    "analytics/bottom-pages.json": """{
  "query": "bottom_pages",
  "period": "last_30_days",
  "results": [
    {
      "source_url": "https://docs.acme-corp.com/troubleshooting",
      "title": "Troubleshooting",
      "pageviews": 456,
      "unique_visitors": 389,
      "avg_time_on_page": 320,
      "bounce_rate": 0.67,
      "conversions": 12,
      "rank": 1,
      "trend": "down",
      "change_percent": -15.3,
      "issues": ["high bounce rate", "low conversions"]
    },
    {
      "source_url": "https://acme-corp.com/blog-post-3",
      "title": "10 Tips for Developer Experience",
      "pageviews": 523,
      "unique_visitors": 445,
      "avg_time_on_page": 145,
      "bounce_rate": 0.72,
      "conversions": 8,
      "rank": 2,
      "trend": "down",
      "change_percent": -22.4,
      "issues": ["low engagement", "high bounce rate", "short time on page"]
    },
    {
      "source_url": "https://docs.acme-corp.com/changelog",
      "title": "Changelog",
      "pageviews": 612,
      "unique_visitors": 534,
      "avg_time_on_page": 90,
      "bounce_rate": 0.58,
      "conversions": 5,
      "rank": 3,
      "trend": "stable",
      "change_percent": -2.1,
      "issues": ["low conversions", "short time on page"]
    }
  ],
  "generated_at": "2024-11-01T10:00:00Z"
}""",
    "analytics/trending-pages.json": """{
  "query": "trending_pages",
  "period": "last_7_days",
  "results": [
    {
      "source_url": "https://docs.acme-corp.com/getting-started",
      "title": "Getting Started with ACME",
      "pageviews": 3245,
      "growth_rate": 0.35,
      "velocity": "accelerating",
      "rank": 1,
      "traffic_sources": {
        "organic": 0.45,
        "social": 0.30,
        "direct": 0.15,
        "referral": 0.10
      }
    },
    {
      "source_url": "https://acme-corp.com/blog-post-1",
      "title": "How to Build Scalable APIs",
      "pageviews": 2876,
      "growth_rate": 0.28,
      "velocity": "steady",
      "rank": 2,
      "traffic_sources": {
        "organic": 0.52,
        "social": 0.25,
        "direct": 0.18,
        "referral": 0.05
      }
    },
    {
      "source_url": "https://docs.acme-corp.com/api-reference",
      "title": "API Reference",
      "pageviews": 1923,
      "growth_rate": 0.22,
      "velocity": "steady",
      "rank": 3,
      "traffic_sources": {
        "organic": 0.60,
        "social": 0.10,
        "direct": 0.20,
        "referral": 0.10
      }
    }
  ],
  "generated_at": "2024-11-01T10:00:00Z"
}""",
    "analytics/declining-pages.json": """{
  "query": "declining_pages",
  "period": "last_30_days",
  "results": [
    {
      "source_url": "https://acme-corp.com/blog-post-3",
      "title": "10 Tips for Developer Experience",
      "pageviews": 523,
      "decline_rate": -0.22,
      "velocity": "declining",
      "rank": 1,
      "possible_reasons": [
        "Content outdated (published 3 months ago)",
        "Low social shares",
        "High bounce rate (72%)",
        "Poor SEO ranking (dropped from page 1 to page 3)"
      ],
      "recommendations": [
        "Update with 2024 examples",
        "Add more visual content",
        "Improve SEO optimization",
        "Promote on social media"
      ]
    },
    {
      "source_url": "https://docs.acme-corp.com/troubleshooting",
      "title": "Troubleshooting",
      "pageviews": 456,
      "decline_rate": -0.15,
      "velocity": "declining",
      "rank": 2,
      "possible_reasons": [
        "Platform improved (fewer errors)",
        "Better documentation elsewhere",
        "High bounce rate (67%)"
      ],
      "recommendations": [
        "Add FAQ section",
        "Include video tutorials",
        "Link from error messages"
      ]
    },
    {
      "source_url": "https://acme-corp.com/blog-post-2",
      "title": "Announcing ACME 2.0",
      "pageviews": 7234,
      "decline_rate": -0.05,
      "velocity": "slowing",
      "rank": 3,
      "possible_reasons": [
        "Announcement is old news (1 month ago)",
        "Natural decline after launch spike"
      ],
      "recommendations": [
        "Follow-up post with user stories",
        "Case study showing ACME 2.0 impact"
      ]
    }
  ],
  "generated_at": "2024-11-01T10:00:00Z"
}""",
    "analytics/domain-summary.json": """{
  "domain": "acme-corp.com",
  "period": "last_30_days",
  "summary": {
    "total_pageviews": 54892,
    "unique_visitors": 42150,
    "avg_time_on_site": 245,
    "bounce_rate": 0.45,
    "conversion_rate": 0.034,
    "total_conversions": 1432
  },
  "traffic_sources": {
    "organic": 0.48,
    "direct": 0.22,
    "social": 0.18,
    "referral": 0.12
  },
  "top_pages": 5,
  "bottom_pages": 3,
  "trending_pages": 3,
  "declining_pages": 3,
  "content_health": {
    "excellent": 5,
    "good": 8,
    "needs_improvement": 3,
    "poor": 2
  },
  "recommendations": [
    "Update declining pages (3 pages identified)",
    "Optimize bottom performers (3 pages with high bounce rates)",
    "Promote trending content on social media",
    "Create more content similar to top performers"
  ],
  "generated_at": "2024-11-01T10:00:00Z"
}""",
}


def generate_all():
    """Generate all mock data files."""
    count = 0
    for rel_path, content in MOCK_FILES.items():
        file_path = MOCK_DIR / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content.strip() + "\n")
        count += 1
        print(f"✅ Created {rel_path}")

    print(f"\n✅ Generated {count} mock files")
    print(f"📁 Mock data location: {MOCK_DIR}")


if __name__ == "__main__":
    generate_all()
