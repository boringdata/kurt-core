---
title: "How to Build Scalable APIs: Lessons from Processing 10B Requests"
url: https://acme-corp.com/blog/how-to-build-scalable-apis
date: 2024-10-20
author: Jordan Kim
role: CTO & Co-founder
tags: [architecture, scaling, performance]
reading_time: 12 min
description: "We scaled ACME from zero to 10 billion API requests per month. Here's what we learned about building systems that scale."
---

# How to Build Scalable APIs: Lessons from Processing 10B Requests

When we launched ACME 18 months ago, we processed about 50,000 API requests per day. Last month, we crossed **10 billion requests**.

That's a 5,000x increase.

Here's what we learned about building APIs that actually scale—and the mistakes we made along the way.

## The Core Principles

Before we dive into tactics, let's cover the fundamentals. Every scalable system we've built follows these principles:

### 1. **Stateless by Default**

Your API handlers should be pure functions. Same input → same output, every time.

```typescript
// ❌ Bad: Stateful handler
let requestCount = 0;

app.get('/users', async (req) => {
  requestCount++; // Don't do this
  return db.users.find();
});

// ✅ Good: Stateless handler
app.get('/users', async (req) => {
  return db.users.find();
});
```

**Why it matters:** Stateless handlers can be horizontally scaled infinitely. Add more instances, get more capacity. It's that simple.

### 2. **Fail Fast**

Don't let slow requests block fast ones. Set aggressive timeouts and fail gracefully.

```typescript
const user = await db.users.find(id, {
  timeout: 100 // 100ms max
});

if (!user) {
  throw new NotFoundError('User not found', { statusCode: 404 });
}
```

We learned this the hard way: one slow database query can cascade into a full system outage. Timeouts saved us multiple times.

### 3. **Cache Aggressively**

If you're computing the same result twice, you're doing it wrong.

```typescript
// Cache at multiple layers
const user = await cache.wrap(`user:${id}`, () => {
  return db.users.find(id);
}, { ttl: 300 }); // 5 minutes
```

Our rule: **Cache at the edge, cache in the app, cache in the database.** Redundancy in caching is a feature, not a bug.

## Architecture Patterns That Scale

### The CDN Edge Layer

90% of our requests never hit our servers. They're served from Cloudflare's edge network.

**What we cache at the edge:**
- Static assets (obviously)
- Immutable API responses (with `Cache-Control: immutable`)
- Authenticated responses (with `Vary: Authorization`)

**Pro tip:** You can cache personalized content at the edge if you structure your cache keys correctly:

```typescript
// Cache key: userId + endpoint + params
const cacheKey = `v1:${userId}:${endpoint}:${hash(params)}`;
```

### The Connection Pool Pattern

Database connections are expensive. Connection pools are your friend.

```typescript
const pool = new Pool({
  min: 10,        // Always have 10 ready
  max: 100,       // Scale up to 100
  idleTimeout: 30000,  // Drop idle after 30s
  acquireTimeout: 5000 // Fail if can't acquire in 5s
});
```

**Key insight:** Monitor your connection pool metrics. If you're constantly at max connections, you have a scaling problem—not a pool size problem.

### The Circuit Breaker Pattern

When a downstream service fails, don't keep hammering it. Give it time to recover.

```typescript
const breaker = new CircuitBreaker(fetchUserService, {
  timeout: 3000,
  errorThreshold: 50,     // Open after 50% errors
  resetTimeout: 30000      // Try again after 30s
});

try {
  const user = await breaker.fire(userId);
} catch (err) {
  // Circuit is open, fail fast
  return cachedUser || defaultUser;
}
```

This pattern alone prevented 3 major outages in our first year.

## Performance Optimization

### N+1 Queries: The Silent Killer

This is the #1 performance issue we see in production APIs.

```typescript
// ❌ Bad: N+1 queries
const posts = await db.posts.findAll();
for (const post of posts) {
  post.author = await db.users.find(post.authorId); // N queries!
}

// ✅ Good: Single query with join
const posts = await db.posts.findAll({
  include: [{ model: User, as: 'author' }]
});
```

**How we catch these:** We log every database query in development with execution time. If we see repeated similar queries, it's a red flag.

### Batch Operations

If you're looping over HTTP requests, you're doing it wrong.

```typescript
// ❌ Bad: Sequential requests
for (const id of userIds) {
  await notifyUser(id); // Waits for each
}

// ✅ Good: Parallel batch
await Promise.all(
  userIds.map(id => notifyUser(id))
);

// ✅ Better: Actual batch API
await notifyUsers(userIds); // Single request
```

**Our rule:** If an operation happens more than once, it needs a batch API.

### Compression

We compress all responses > 1KB with Brotli. This reduced our bandwidth costs by 60%.

```typescript
app.use(compression({
  threshold: 1024,      // 1KB minimum
  level: 6,             // Brotli level
  filter: (req, res) => {
    // Don't compress images, videos, already compressed
    return !res.getHeader('Content-Encoding');
  }
}));
```

## Monitoring & Observability

You can't scale what you can't measure. These are the metrics we track:

**Request-level metrics:**
- Latency (P50, P95, P99, P99.9)
- Error rate (by status code)
- Request rate (per endpoint)

**Resource metrics:**
- CPU usage (per container)
- Memory usage (with leak detection)
- Connection pool stats

**Business metrics:**
- API calls per customer
- Endpoint popularity
- Feature usage

**Our setup:** OpenTelemetry → Prometheus → Grafana. We get alerts in Slack for anything abnormal.

## Common Scaling Mistakes

### Mistake #1: Premature Optimization

Don't optimize for 1M users when you have 100. Build for your actual scale + 10x headroom.

We over-engineered our initial architecture. It took 3 months longer to launch and most of the "scale" features went unused for a year.

### Mistake #2: Ignoring Database Indexes

This sounds basic, but we've seen it countless times:

```sql
-- ❌ Bad: No index on foreign key
SELECT * FROM posts WHERE author_id = 123; -- Full table scan!

-- ✅ Good: Index on foreign key
CREATE INDEX idx_posts_author_id ON posts(author_id);
SELECT * FROM posts WHERE author_id = 123; -- Index scan
```

**Every foreign key needs an index.** No exceptions.

### Mistake #3: Synchronous External Calls

Never make synchronous calls to external services in your request path.

```typescript
// ❌ Bad: Blocking request
app.post('/users', async (req) => {
  const user = await db.users.create(req.body);
  await sendWelcomeEmail(user); // Blocks response!
  return user;
});

// ✅ Good: Async with queue
app.post('/users', async (req) => {
  const user = await db.users.create(req.body);
  queue.add('sendWelcomeEmail', { userId: user.id }); // Non-blocking
  return user;
});
```

Use job queues (we use BullMQ) for anything that doesn't need to happen in-line.

## Load Testing

We load test every major feature before launch. Here's our process:

**1. Establish baseline**
```bash
# Current production capacity
k6 run --vus 1000 --duration 5m baseline.js
```

**2. Test new feature**
```bash
# Does it maintain performance?
k6 run --vus 1000 --duration 5m feature-test.js
```

**3. Find breaking point**
```bash
# Where does it fail?
k6 run --vus 1000 --duration 30m --ramp-up 5m stress-test.js
```

**Our rule:** Every endpoint must handle 10x our current peak traffic before we ship it.

## The Real Secret to Scaling

Here's what we learned after 10 billion requests:

**Scaling isn't about technology.** It's about discipline.

- Write stateless code from day one
- Monitor everything
- Load test before shipping
- Fix performance issues immediately (they compound)
- Cache aggressively
- Use boring, proven technology

We use Postgres, Redis, Node.js, and Cloudflare. Nothing exotic. The magic isn't in the stack—it's in how you use it.

## Resources

If you want to dive deeper:

- **[High Performance Browser Networking](https://hpbn.co/)** - Ilya Grigorik
- **[Designing Data-Intensive Applications](https://dataintensive.net/)** - Martin Kleppmann
- **[Systems Performance](http://www.brendangregg.com/sysperfbook.html)** - Brendan Gregg

## Try ACME

Want to see these patterns in action? We built ACME to make scalable APIs accessible to every developer.

[Start building](https://acme-corp.com/signup) → Deploy in 5 minutes → Scale to millions of requests.

---

*Jordan Kim is the CTO and co-founder of ACME. He previously worked on edge infrastructure at Vercel and platform engineering at Stripe.*

**Questions?** Join our [Discord community](https://discord.gg/acme) or reach out on Twitter [@jordankdev](https://twitter.com/jordankdev).
