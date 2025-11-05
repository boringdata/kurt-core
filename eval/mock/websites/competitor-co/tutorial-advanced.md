---
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
