---
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
