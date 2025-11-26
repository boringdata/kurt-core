---
title: scaling-duckdb-with-ducklings
content_type: blog
source_url: https://motherduck.com/blog/scaling-duckdb-with-ducklings
indexed_at: '2025-11-25T19:57:17.009614'
content_hash: 31a47966ffadbd25
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# How MotherDuck Scales DuckDB in the Cloud vertically and horizontally

2025/04/16 - 5 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

In the very first days of MotherDuck as a company, back before the co-founders had even met in person to kick off the company in mid-2022, we realized we needed a name to call the DuckDB instances we were running on behalf of users in the cloud. The idea behind the name MotherDuck, in the first place, was that we were marshaling a flock of DuckDB instances. What does a _mother_ duck manage? "Ducklings", of course. The name stuck, and MotherDuck's DuckDB instances became Ducklings.

## How is a Duckling different from a standard Data Warehouse instance?

Most data warehouses are built as monoliths, where every user in the organization shares the same data warehouse compute resources. Unless this warehouse is over-provisioned (calling all admins with 3XL instances out there!), it often begins to crack under high concurrency. Many analysts know the pain of trying to run a query while someone else is running a giant report, and having their workload slow to a crawl.

![legacy_data_warehouse.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Flegacy_data_warehouse_fcd5053295.png&w=3840&q=75)

## Per-user Tenancy for Internal Analytics / BI

MotherDuck’s approach with Ducklings is very different. Instead of all users sharing the same instance, each user gets their own Duckling which handles their workload and automatically shuts down if not being used.

![motherduck_data_warehouse.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmotherduck_data_warehouse_e933633b2e.png&w=3840&q=75)

And, of course, all users are accessing a consistent view of the data warehouse shared either throughout the organization or with individual users in the org.

## Vertical Scaling: Configurable per-user

Is your CEO complaining that _they_ need more compute? Each Duckling can be scaled up or down to meet the needs of the user.

MotherDuck [has three Duckling sizes](https://motherduck.com/product/pricing/): Pulse, Standard and Jumbo.

![duckling_sizes.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckling_sizes_dc9bc51fe2.png&w=3840&q=75)

_Author’s note: We have a multi-terabyte data warehouse at MotherDuck and our CEO, Jordan, is able to use the smallest Ducklings, called Pulses to understand what is going on in the business every day_

![duckling_size_example.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckling_size_example_8a972f4865.png&w=3840&q=75)

## Horizontal Read Scaling: Configurable per-user

Sometimes the data warehouse doesn't know the identity of the end users. For example, BI tools typically share a single database connection but then may have dozens of users running queries at the same time. This would ordinarily break the "one-user-per-duckling" pattern.

MotherDuck’s [read scaling](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/read-scaling/) is designed for these types of cases – providing an extra boost in compute through horizontal scaling and maintaining the pattern of “one-user-per-duckling!”

![duckling_read_scaling.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckling_read_scaling_64da81363c.png&w=3840&q=75)

## Duckling-powered Customer-facing Analytics

Customer-facing analytics use cases have different requirements than an analytics stack built to power your internal data teams. It often starts with a simple customer ask – eg “I want to see a dashboard of revenue trends” – which engineering implements on top of the transactional database (like Postgres). Eventually, with more customer demands and growth, your transactional database is on fire. You’re spending all day experimenting with different indexes or blocked by an eng team that owns database configuration and you’re searching for an analytics solution.

![traditional_app.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ftraditional_app_641d5f371e.png&w=3840&q=75)

MotherDuck’s per-user tenancy model is especially powerful for these types of applications. Each customer can have their own Duckling(s) with isolated data, mitigating many types of security concerns with multitenant databases. Since each user has their own Duckling(s), you can rid yourself of scale anxiety and know that MotherDuck will always be ready to handle new customers as fast as your sales team can sign deals.

![data_app_scaling_motherduck.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdata_app_scaling_motherduck_f7a1861ed4.png&w=3840&q=75)

As we saw with the internal data analytics use case, you can configure the Duckling size per customer, enabling you to offer higher levels of service and scale to your most important customers.

## Scaling from your Duckling back to the Laptop

Historically, laptops were extremely under-powered and you needed to scale to the cloud to get fast compute resources. With laptops now being as powerful as supercomputers of yesteryear, we still scale to the cloud for 24x7 availability, sharing/collaboration, and centralized data management, but the powerful chips on our laps are underutilized.

With MotherDuck, you can scale your workloads back to your laptop to take advantage of local compute power and zero-latency in combination with the power offered by your cloud-based Duckling. This happens automatically in the MotherDuck UI to enable the quick aggregation and filtering of data in the Column Explorer. The MotherDuck SQL query planner automatically decides whether to bring the compute to the data or the data to the compute. We call this [Dual Execution](https://motherduck.com/docs/key-tasks/running-hybrid-queries/) and we wrote a [CIDR paper](https://www.cidrdb.org/cidr2024/papers/p46-atwal.pdf) on this technology (formerly called hybrid query execution).

As you build your own applications, you can decide whether to take advantage of client-side compute and zero latency queries using Dual Execution, or have all the compute happen on MotherDuck’s servers.

## Go launch your flock of Ducklings

MotherDuck makes it easy to scale from megabytes to terabytes with a combination of per-user Duckling tenancy, vertical scaling to more powerful Ducklings, horizontal scaling to more Ducklings and dual execution. These scaling techniques enable the super-efficient DuckDB SQL engine to power internal data analytics as well as customer-facing analytics with ease.

[Try MotherDuck today](https://app.motherduck.com/?auth_flow=signup) with our 21-day free trial. And, if you want to learn more about how others (including Okta and smallpond) are scaling data workloads using DuckDB, watch our [recent panel of experts discussing scale](https://motherduck.com/webinar/scaling-duckdb-panel-ondemand/).

> "We've now got these new levers for performance scaling because we can split and store the data and query efficiently as needed. If we need to handle a load spike or a huge amount of queries, we can spin up more ducklings on demand."
>
> [Ravi Chandra, CTO @ Dexibit](https://motherduck.com/case-studies/dexibit/)

### TABLE OF CONTENTS

[How is a Duckling different from a standard Data Warehouse instance?](https://motherduck.com/blog/scaling-duckdb-with-ducklings/#how-is-a-duckling-different-from-a-standard-data-warehouse-instance)

[Per-user Tenancy for Internal Analytics / BI](https://motherduck.com/blog/scaling-duckdb-with-ducklings/#per-user-tenancy-for-internal-analytics-bi)

[Vertical Scaling: Configurable per-user](https://motherduck.com/blog/scaling-duckdb-with-ducklings/#vertical-scaling-configurable-per-user)

[Horizontal Read Scaling: Configurable per-user](https://motherduck.com/blog/scaling-duckdb-with-ducklings/#horizontal-read-scaling-configurable-per-user)

[Duckling-powered Customer-facing Analytics](https://motherduck.com/blog/scaling-duckdb-with-ducklings/#duckling-powered-customer-facing-analytics)

[Scaling from your Duckling back to the Laptop](https://motherduck.com/blog/scaling-duckdb-with-ducklings/#scaling-from-your-duckling-back-to-the-laptop)

[Go launch your flock of Ducklings](https://motherduck.com/blog/scaling-duckdb-with-ducklings/#go-launch-your-flock-of-ducklings)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Close the Loop: Faster Data Pipelines with MCP, DuckDB & AI](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmcp_blog_e4bfe2279d.png&w=3840&q=75)](https://motherduck.com/blog/faster-data-pipelines-with-mcp-duckdb-ai/)

[2025/04/15 - Mehdi Ouazza](https://motherduck.com/blog/faster-data-pipelines-with-mcp-duckdb-ai/)

### [Close the Loop: Faster Data Pipelines with MCP, DuckDB & AI](https://motherduck.com/blog/faster-data-pipelines-with-mcp-duckdb-ai)

How the MCP can accelerate data engineering workflows by connecting AI copilots directly to data tools like DuckDB

[![Streaming in the Fast Lane: Oracle CDC to MotherDuck Using Estuary](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FEstuary_blog_new_4509d479b7.png&w=3840&q=75)](https://motherduck.com/blog/streaming-oracle-to-motherduck/)

[2025/04/17 - Emily Lucek](https://motherduck.com/blog/streaming-oracle-to-motherduck/)

### [Streaming in the Fast Lane: Oracle CDC to MotherDuck Using Estuary](https://motherduck.com/blog/streaming-oracle-to-motherduck)

Ducks and estuaries go together. So it’s no surprise that MotherDuck, a cloud data warehouse, pairs well with Estuary, a data pipeline platform.

[View all](https://motherduck.com/blog/)

Authorization Response