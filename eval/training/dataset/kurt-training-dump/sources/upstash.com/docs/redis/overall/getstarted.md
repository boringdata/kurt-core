---
title: Getting Started - Upstash Documentation
url: https://upstash.com/docs/redis/overall/getstarted
hostname: upstash.com
description: Create an Upstash Redis database in seconds
sitename: Upstash Documentation
date: 2025-11-11
---
**highly available, infinitely scalable**Redis-compatible database:

- 99.99% uptime guarantee with auto-scaling (
[Prod Pack](https://upstash.com/docs/redis/overall/enterprise#prod-pack-features)) - Ultra-low latency worldwide
- Multi-region replication
- Durable, persistent storage without sacrificing performance
- Automatic backups
- Optional SOC-2 compliance, encryption at rest and much more

## 1. Create an Upstash Redis Database

Once you’re logged in, create a database by clicking`+ Create Database`

in the upper right corner. A dialog opens up:
**Database Name:**Enter a name for your database.

**Primary Region and Read Regions:**For optimal performance, select the Primary Region closest to where most of your writes will occur. Select the read region(s) where most of your reads will occur. Once you click

`Next`

and select a plan, your database is running and ready to connect:
## 2. Connect to Your Database

You can connect to Upstash Redis with any Redis client. For simplicity, we’ll use`redis-cli`

. See the [Connect Your Client](https://upstash.com/howto/connectclient)section for connecting via our TypeScript or Python SDKs and other clients. The Redis CLI is included in the official Redis distribution. If you don’t have Redis installed, you can get it

[here](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/). Connect to your database and execute commands on it:

**New: Manage Upstash Redis From Cursor (optional)**Manage Upstash Redis databases from Cursor and other AI tools by using our

[MCP server](https://upstash.com/docs/redis/integrations/mcp).