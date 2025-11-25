---
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
