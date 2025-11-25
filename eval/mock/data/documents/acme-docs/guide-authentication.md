---
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
curl -X POST https://api.acme.dev/oauth/token \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_SECRET \
  -d code=AUTHORIZATION_CODE \
  -d grant_type=authorization_code
```

## Security Best Practices

1. **Never expose keys in client-side code**
2. **Rotate keys regularly** (quarterly recommended)
3. **Use environment variables** for key storage
4. **Enable IP allowlisting** in dashboard
5. **Monitor API usage** for anomalies
