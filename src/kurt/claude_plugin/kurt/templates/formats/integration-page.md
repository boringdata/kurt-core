# Integration Page Template

## Overview
- **Purpose:** Technical page explaining how to integrate with specific technology/platform
- **Length:** 1000-1500 words + code examples
- **Audience:** Developers implementing the integration
- **Success metrics:** Setup completion rate, time to first integration, support tickets

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Tone:**
- Technical: [Casual / Professional / Academic]
- Clarity: [Straightforward / Detailed / Comprehensive]
- Voice: [Active / Passive]

**Technical depth:**
- Code examples: [Full files / Snippets / Minimal]
- Explanations: [Step-by-step / Assumed knowledge / Brief]
- Troubleshooting: [Comprehensive / Common issues / Minimal]

**DO/DON'T Examples (from their actual content):**

✅ **DO:** "[Copy 2-3 sentences from their integration docs that exemplify style]"
- Why this works: [Reason - clear, comprehensive, etc.]

❌ **DON'T:** "[Contrasting example - too vague, missing details, etc.]"
- Reason: [Why they avoid this - confusing, incomplete, etc.]

---

## Research Requirements

**Types of information needed for integration page:**

1. **Integration partner details** - The technology you're integrating with
   - Find: `kurt content list --url-contains /integrations/`
   - Research: `kurt research query "[partner technology] integration best practices"`
   - Or provide: Partner documentation, API specs, SDKs

2. **Existing integration examples** - How other integrations are documented
   - Find: `kurt content list --with-topic "integration"`
   - Search: `kurt content search "integration"`
   - Or provide: Examples of well-documented integrations

3. **Use cases** - Why customers need this integration
   - Find: `kurt content search "use case"`
   - Research: `kurt research search --source reddit --query "[your-product] [partner] integration"`
   - Or provide: Customer requests, sales feedback

4. **Technical requirements** - What's needed to make this work
   - Find: `kurt content list --with-technology "[partner-tech]"`
   - Or provide: API documentation, authentication requirements, rate limits

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Partner technology:**
```bash
# Research partner platform
kurt research query "[partner technology] API documentation"
kurt research query "[partner technology] developer resources"
```

**Your integration docs:**
```bash
# Find existing integration pages for style
kurt content search "integration"
kurt content list --with-topic "integration"

# Discover what integrations exist
kurt content list --url-contains /integrations/
```

**Technical details:**
```bash
# Find technical documentation
kurt content list --with-content-type reference
kurt content search "API"
```

**If insufficient sources: Ask user for partner API docs, authentication details, or example integration code**

---

## Structure

```markdown
---
project: project-name
document: integration-page-[partner-name]
format_template: /kurt/templates/formats/integration-page.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/[partner]-api-docs.md
    purpose: "partner API reference"
  - path: /sources/integration-examples/
    purpose: "example integration implementations"
  - path: /sources/your-api-docs.md
    purpose: "your product API details"

outline:
  overview:
    sources: []
    purpose: "what this integration does and why"
  prerequisites:
    sources: [/sources/[partner]-api-docs.md]
    purpose: "what users need before starting"
  setup-guide:
    sources: [/sources/[partner]-api-docs.md, /sources/your-api-docs.md]
    purpose: "step-by-step configuration"
  code-examples:
    sources: [/sources/integration-examples/]
    purpose: "working implementation examples"
  use-cases:
    sources: []
    purpose: "common scenarios and solutions"
  troubleshooting:
    sources: []
    purpose: "common issues and fixes"
---

# [Your Product] + [Partner] Integration

**Last updated:** YYYY-MM-DD
**Integration type:** [Bidirectional / One-way / Event-driven / API-based]
**Difficulty:** [Beginner / Intermediate / Advanced]
**Setup time:** ~[X] minutes

---

## Overview

### What This Integration Does

[1-2 paragraphs explaining what becomes possible when these two systems work together]

**Key capabilities:**
- **[Capability 1]:** [What it enables - e.g., "Sync customer data in real-time"]
- **[Capability 2]:** [What it enables - e.g., "Trigger workflows based on events"]
- **[Capability 3]:** [What it enables - e.g., "Centralize reporting across platforms"]

### How It Works

```
[Simple diagram or text explanation of data flow]

[Your Product] <--[Event/Data]--> [Partner Platform]

Example flow:
1. User performs action in [Your Product]
2. Webhook triggers event to [Partner]
3. [Partner] processes and responds
4. Result synced back to [Your Product]
```

### Common Use Cases

**Use Case 1: [Scenario Name]**
[Brief description of who this helps and what they accomplish]

**Use Case 2: [Scenario Name]**
[Brief description of who this helps and what they accomplish]

**Use Case 3: [Scenario Name]**
[Brief description of who this helps and what they accomplish]

---

## Prerequisites

**Before you begin, you'll need:**

### From [Partner Platform]:
- [ ] Active [Partner] account ([Plan level required])
- [ ] API credentials ([Where to find them - link to their docs])
- [ ] Required permissions: [List specific permissions]
- [ ] Optional: [Webhook endpoint setup / OAuth app configured]

### From [Your Product]:
- [ ] Active account ({{PLAN_LEVEL_IF_REQUIRED}})
- [ ] API key (Find in: {{YOUR_DASHBOARD_LOCATION}})
- [ ] Permissions: {{REQUIRED_PERMISSIONS}}

### Technical Requirements:
- [ ] Programming language: [If applicable - Node.js, Python, etc.]
- [ ] Dependencies: [SDK, libraries, packages needed]
- [ ] Network: [Firewall rules, whitelisted IPs if needed]

---

## Setup Guide

### Step 1: Configure [Partner Platform]

**1.1 Create API Credentials**

Navigate to [Partner > Settings > API] and create new credentials:

```bash
# If CLI-based
partner-cli auth create --name "your-product-integration"

# Or via their dashboard:
# 1. Go to Settings > Integrations
# 2. Click "Create New API Key"
# 3. Copy the key (shown only once)
```

**1.2 Set Permissions**

Required scopes for this integration:
- `scope:read` - Read access to [resource]
- `scope:write` - Write access to [resource]
- `webhooks:manage` - Create and manage webhooks

**1.3 Configure Webhook (if applicable)**

Set up webhook endpoint to receive events:

```
Webhook URL: https://your-domain.com/webhooks/partner-name
Events to subscribe:
  - event.created
  - event.updated
  - event.deleted
```

### Step 2: Configure [Your Product]

**2.1 Add Integration**

In [Your Product] dashboard:
1. Navigate to Integrations > [Partner]
2. Click "Connect"
3. Paste [Partner] API credentials:
   - API Key: `pk_xxx`
   - API Secret: `sk_xxx`

**2.2 Set Sync Options**

Configure what data to sync:

```yaml
# Example configuration
sync_settings:
  direction: bidirectional  # or one-way
  resources:
    - customers: enabled
    - orders: enabled
    - products: disabled
  sync_interval: 5m  # 5 minutes
```

**2.3 Test Connection**

Verify the connection works:

```bash
# Using your CLI
your-product-cli integrations test partner-name

# Expected output:
✓ Connection successful
✓ Credentials valid
✓ Webhook configured
```

### Step 3: Implement Integration (Code)

**3.1 Install Dependencies**

```bash
# Node.js example
npm install @your-product/sdk @partner/sdk

# Python example
pip install your-product-sdk partner-sdk
```

**3.2 Initialize Clients**

```javascript
// JavaScript/Node.js example
const YourProduct = require('@your-product/sdk');
const Partner = require('@partner/sdk');

const yourProduct = new YourProduct({
  apiKey: process.env.YOUR_PRODUCT_API_KEY
});

const partner = new Partner({
  apiKey: process.env.PARTNER_API_KEY,
  apiSecret: process.env.PARTNER_API_SECRET
});
```

**3.3 Sync Data**

Example: Sync customer data from [Partner] to [Your Product]

```javascript
// Fetch customers from Partner
const partnerCustomers = await partner.customers.list({
  limit: 100,
  created_after: '2024-01-01'
});

// Sync to Your Product
for (const customer of partnerCustomers.data) {
  await yourProduct.customers.createOrUpdate({
    external_id: customer.id,
    email: customer.email,
    name: customer.name,
    metadata: {
      partner_source: 'partner-name',
      partner_customer_id: customer.id
    }
  });
}

console.log(`Synced ${partnerCustomers.data.length} customers`);
```

**3.4 Handle Webhooks**

Receive and process events from [Partner]:

```javascript
// Express.js webhook endpoint
app.post('/webhooks/partner-name', async (req, res) => {
  // Verify webhook signature
  const signature = req.headers['partner-signature'];
  const isValid = partner.webhooks.verify(req.body, signature);

  if (!isValid) {
    return res.status(401).send('Invalid signature');
  }

  const event = req.body;

  // Handle different event types
  switch (event.type) {
    case 'customer.created':
      await handleCustomerCreated(event.data);
      break;
    case 'customer.updated':
      await handleCustomerUpdated(event.data);
      break;
    case 'customer.deleted':
      await handleCustomerDeleted(event.data);
      break;
  }

  res.status(200).send('OK');
});

async function handleCustomerCreated(customer) {
  await yourProduct.customers.create({
    external_id: customer.id,
    email: customer.email,
    name: customer.name
  });
}
```

### Step 4: Test Integration

**4.1 Create Test Data**

Create test record in [Partner]:

```bash
# Using Partner CLI or dashboard
partner-cli customers create \
  --email test@example.com \
  --name "Test Customer"
```

**4.2 Verify Sync**

Check that data appears in [Your Product]:

```bash
your-product-cli customers list --filter "external_id=partner_xxx"
```

**4.3 Test Bidirectional Sync (if applicable)**

Make change in [Your Product], verify it syncs to [Partner]

---

## Common Use Cases

### Use Case 1: [Specific Scenario]

**Goal:** [What user wants to accomplish]

**Example:** [Concrete scenario - e.g., "Automatically create support tickets when customer submits feedback"]

**Implementation:**

```javascript
// Code example showing this specific use case
async function syncFeedbackToTickets() {
  const feedback = await partner.feedback.list({ status: 'new' });

  for (const item of feedback.data) {
    await yourProduct.tickets.create({
      title: `Customer Feedback: ${item.subject}`,
      description: item.message,
      priority: item.rating < 3 ? 'high' : 'normal',
      source: 'partner-integration',
      customer_id: item.customer_id
    });
  }
}
```

### Use Case 2: [Specific Scenario]

**Goal:** [What user wants to accomplish]

**Implementation:**

```javascript
// Code example
```

---

## Configuration Options

### Sync Settings

**Sync Direction:**
- `one-way`: [Your Product] → [Partner] only
- `bidirectional`: Changes sync both ways
- `partner-to-you`: [Partner] → [Your Product] only

**Sync Frequency:**
- `real-time`: Webhook-based instant sync
- `interval`: Poll every X minutes (5m, 15m, 1h)
- `manual`: Trigger sync via API or dashboard

**Field Mapping:**

Customize how fields map between systems:

```yaml
field_mappings:
  partner.customer.email → yourproduct.user.email
  partner.customer.full_name → yourproduct.user.name
  partner.customer.company → yourproduct.user.organization
```

### Advanced Options

**Rate Limiting:**
```javascript
// Handle Partner API rate limits
const config = {
  rateLimit: {
    maxRequests: 100,
    perSeconds: 60
  },
  retryOnRateLimit: true,
  maxRetries: 3
};
```

**Error Handling:**
```javascript
// Configure how to handle sync errors
const errorConfig = {
  onError: 'retry',  // or 'skip', 'halt'
  retryAttempts: 3,
  retryDelay: 5000,  // ms
  notifyOnFailure: true
};
```

---

## Troubleshooting

### Common Issues

**Issue 1: Authentication Failed**

**Error message:**
```
401 Unauthorized: Invalid API credentials
```

**Cause:** API key incorrect or expired

**Solution:**
1. Verify API key in [Partner] dashboard
2. Regenerate key if needed
3. Update credentials in [Your Product] settings
4. Test connection again

**Issue 2: Webhook Not Receiving Events**

**Symptoms:** No data syncing, webhook endpoint not being hit

**Debugging steps:**
```bash
# Check webhook is registered
partner-cli webhooks list

# Test webhook endpoint manually
curl -X POST https://your-domain.com/webhooks/partner-name \
  -H "Content-Type: application/json" \
  -d '{"type":"test","data":{}}'

# Check webhook logs in Partner dashboard
```

**Common causes:**
- Firewall blocking incoming webhooks
- HTTPS certificate invalid
- Webhook URL incorrect
- Signature verification failing

**Issue 3: Data Not Syncing**

**Cause:** Field mapping mismatch or missing permissions

**Solution:**
1. Check field mappings are correct
2. Verify required permissions/scopes enabled
3. Check sync logs: `your-product-cli integrations logs partner-name`
4. Enable debug mode for detailed logging

### Debug Mode

Enable detailed logging to troubleshoot:

```javascript
const yourProduct = new YourProduct({
  apiKey: process.env.API_KEY,
  debug: true,  // Enable debug logging
  logLevel: 'verbose'
});
```

### Getting Help

**Documentation:**
- [Your Product] integration docs: [URL]
- [Partner] API docs: [URL]

**Support:**
- Email: support@yourproduct.com
- Community: [Slack/Discord/Forum URL]
- Partner support: [Partner support URL]

---

## Security Best Practices

**Protect API Credentials:**
- Never commit credentials to version control
- Use environment variables
- Rotate keys regularly
- Use separate keys for dev/staging/production

**Webhook Security:**
- Always verify webhook signatures
- Use HTTPS only
- Validate payload structure
- Implement rate limiting

**Data Privacy:**
- Only sync necessary data
- Respect user consent and preferences
- Follow data retention policies
- Encrypt sensitive data in transit and at rest

---

## Limits & Quotas

**[Partner] API Limits:**
- Rate limit: [X] requests per [minute/hour]
- Concurrent connections: [X]
- Webhook events: [X] per [minute/hour]

**[Your Product] Limits:**
- API calls: [X] per [minute/hour]
- Webhooks: [X] per [minute/hour]
- Data sync: [X MB/records per day]

**Recommendations:**
- Batch requests when possible
- Implement exponential backoff for retries
- Cache frequently accessed data
- Monitor usage to avoid hitting limits

---

## Next Steps

**After setup:**
1. Monitor initial sync to ensure data flows correctly
2. Set up alerting for sync failures
3. Review and optimize field mappings
4. Document custom configurations for your team

**Advanced:**
- Explore additional [Partner] API endpoints
- Build custom workflows triggered by events
- Set up bi-directional sync for additional resources
- Automate deployment with Infrastructure as Code

**Related Integrations:**
- [Related Integration 1] - [Why it complements this]
- [Related Integration 2] - [Why it complements this]

```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/integration-[partner-name].md`

**Step 1: YAML frontmatter + outline**
- List all major sections
- Map sources (partner API docs, your API docs, examples)
- Set status: `outline`

**Step 2: Research partner platform**
- Review partner's API documentation
- Understand authentication mechanisms
- Identify webhook/event systems
- Note rate limits and quotas

**Step 3: Identify use cases**
- Talk to customers about why they need this integration
- Review support tickets or sales requests
- Identify 2-3 common scenarios

**Step 4: Implement and test**
- Build working integration code
- Test all steps in the setup guide
- Document common errors encountered
- Capture actual error messages

**Step 5: Write setup guide**
- Document exact steps taken
- Include all necessary credentials/permissions
- Provide working code examples
- Screenshot key configuration screens

**Step 6: Add troubleshooting**
- Document issues encountered during testing
- Include actual error messages and solutions
- Test with fresh environment to catch setup issues

---

## Customizing This Template (One-Time Setup)

**Complete the [CUSTOMIZATION NEEDED] section by:**

1. **Find 2-3 existing integration pages:**
```bash
kurt content search "integration"
kurt content list --with-topic "integration"
kurt content list --url-contains /integrations/
```

2. **Analyze their style:**
- How technical are the explanations?
- How detailed are code examples?
- How comprehensive is troubleshooting?

3. **Extract DO/DON'T examples:**
- Find 2-3 sentences that exemplify their integration doc style
- Note what makes them effective

4. **Update the [CUSTOMIZATION NEEDED] section** with:
- Technical tone preferences
- Code example style (full files vs snippets)
- Explanation depth
- DO/DON'T examples from actual integration docs

**This customization is done ONCE, then this template is reused for all future integration pages.**
