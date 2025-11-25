---
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
