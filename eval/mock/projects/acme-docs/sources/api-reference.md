---
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
curl https://api.acme.dev/v1/users \
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
