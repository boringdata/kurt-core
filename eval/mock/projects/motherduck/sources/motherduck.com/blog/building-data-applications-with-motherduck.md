---
title: building-data-applications-with-motherduck
content_type: blog
source_url: https://motherduck.com/blog/building-data-applications-with-motherduck
indexed_at: '2025-11-25T19:56:16.427162'
content_hash: dd30a68ea3346d04
has_code_examples: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Build sub-second data applications with MotherDuck’s Wasm SDK

2024/04/24 - 7 min read

BY

[Tino Tereshko](https://motherduck.com/authors/tino-tereshko/)

Developers across every industry are increasingly embedding powerful insights directly into their applications as interactive, data-driven analytics components.

Data generated inside any application can help provide actionable insights, reduce costs, and increase operational efficiency. But that data must first be collected, processed, enriched, and centralized for consumption. Historically, this data may have existed in disparate systems or BI dashboards, requiring users to jump between applications to operationalize this valuable data. Using analytics components, this data is surfaced back into the application itself, reducing context-switching and empowering better decision-making.

While once considered nice-to-have features inside niche industries, analytics components now represent a powerful competitive advantage and are quickly becoming table stakes across enterprise and consumer applications alike. **All applications are becoming data applications.**

Building Data Apps with MotherDuck - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Building Data Apps with MotherDuck](https://www.youtube.com/watch?v=JjmOv-W9zzo)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

Full screen is unavailable. [Learn More](https://support.google.com/youtube/answer/6276924)

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=JjmOv-W9zzo&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 1:25

•Live

•

## Building and maintaining data applications is still _really_ ducking hard

Take, for example, an e-commerce application that wants to show merchants their stores’ sales by day and by state for the last 30 days to help them gain some directional awareness about their sales performance across the country.

We could run this query directly against the application’s transactional database, but we quickly realize transactional databases are not optimized for these sorts of queries.

```sql
Copy code

select d.d_date           as sale_date,
       ca.ca_state        as state,
       sum(cs.cs_net_paid)as total_sales
from   catalog_sales cs
       inner join customer c
               on c.c_customer_sk = cs.cs_ship_customer_sk
       inner join customer_address ca
               on ca.ca_address_sk = c.c_current_addr_sk
       inner join date_dim d
               on cs.cs_sold_date_sk = d.d_date_sk
where  d.d_date between current_date - interval '30' day and current_date
       and merchant_id = 'a3e4400'
group  by d.d_date,
          ca.ca_state
order  by d.d_date,
          ca.ca_state;
```

This query, which involves a modest sales table of just 40M records, will take over eight seconds on a decently sized machine! Today's end users won’t wait around for insights that take far too long to load. Worse yet, these types of queries can hog precious resources in our transactional database and may even disrupt critical operations like writing or updating records.

In an effort to decrease latency, we might move these queries over to a cloud data warehouse: after all, they’re optimized for analytics. This same query now takes about three seconds against a modern cloud data warehouse. **But as we increase the number of concurrent queries, we start to see that even a well provisioned cloud data warehouse can only handle a few of these queries at once.**

This latency and concurrency limit may be useable for an [internal BI dashboard](https://motherduck.com/learn-more/modern-data-warehouse-use-cases/), but it won’t scale to hundreds or thousands of users who might be in an application at any given moment. Serving hundreds or thousands of concurrent users of a data application with a cloud data warehouse requires serious engineering effort to balance concurrency, latency, and cost.

Delivering performance to users of all shapes and sizes likely requires routing some of them to dedicated, right-sized resources while bin-packing the rest in a large mainframe-like box, all while scaling these resources up and down to handle an influx in traffic. The operational overhead of managing this deployment at scale can quickly become cumbersome and expensive. Under-provisioning resources results in higher latency, and over-provisioning results in higher costs.At its core, slow query performance is a [physics problem with a predictable hierarchy of bottlenecks](https://motherduck.com/learn-more/diagnose-fix-slow-queries/) that begins with inefficient data access.

![Routing users to appropriate resources](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fresource_contention_e1deff2b53.png&w=3840&q=75)

**Even after we optimize the way these queries are handled, developers still have to build an enormous amount of application code to power data-driven components.** The client must encode a series of metrics, dimensions, and filters as a request to a server endpoint. The server handles this request by generating the equivalent SQL and executing the query against the data store, returning a serialized version of the data set. The client parses this response and passes the resulting data to the component for its initial rendering.

![3-tier architecture process flow](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F3_tier_arch_process_flow_f1a15eb27b.png&w=3840&q=75)

The interactive nature of these components means that users can typically manipulate the data by filtering or slicing and dicing it by different dimensions. Each interaction could potentially trigger another expensive, slow round-trip request to the server, often resulting in 5 to 10 seconds for a component to refresh. This latency might be acceptable in traditional BI dashboards but is often too slow for actionable insights in a data application.

In an effort to reduce the costly round-trip request on every interaction, developers will have to build a client-side data model that can efficiently apply transformations to the data set to prevent this request lifecycle from happening again. This requires duplicating a lot of the server's functionality, but often without a powerful SQL engine to apply these transformations.

While data-driven functionality has become table stakes, building data applications today is still an arduous effort for engineering teams. The resulting features are slow, brittle, and expensive to build and maintain.

What if you could deliver data applications capable of refreshing 60 times per second against large-scale data sets - faster than you can _blink_? What if you could make your dashboards as interactive as video games? What if you could run this workload for a fraction of what it would normally cost you, with fewer headaches? [MotherDuck’s unique hybrid architecture](https://motherduck.com/docs/architecture-and-capabilities/) is the future, and we invite you to join us in building the data applications of the future that haven't even been feasible until now!

## A unique architecture that lowers cost and latency

MotherDuck provides every user of a data application with their own vertically scaling instance of [DuckDB](https://duckdb.org/), a fast, in-process analytical database, and executes queries against MotherDuck’s scalable, fully managed, and secure storage system.

Giving each user their own instance of DuckDB, or "duckling," allows complex analytics queries to be executed faster and more efficiently, with higher concurrency than traditional warehouses.

Further, MotherDuck only [charges](https://motherduck.com/pricing/) you for the seconds that any given user is querying data. Developers no longer have to worry about ensuring enough compute resources are available, if users are being routed to appropriately sized resources, or if under utilized resources are lingering around.

![motherduck_routing.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmotherduck_routing_23ea7a7349.png&w=3840&q=75)

## Introducing the MotherDuck Wasm SDK

[The MotherDuck Wasm SDK](https://motherduck.com/docs/data-apps/) introduces game-changing performance and developer ergonomics for data applications. Just install the SDK, and suddenly your client speaks the lingua franca of analytics: SQL.

```vbnet
Copy code

import { MDConnection } from '@motherduck/wasm-client';

const conn = MDConnection.create({
    mdToken: "...",
});

const result = await conn.evaluateStreamingQuery(`
    select d.d_date           as sale_date,
        ca.ca_state        as state,
        sum(cs.cs_net_paid)as total_sales
    from   catalog_sales cs
    inner join customer c
            on c.c_customer_sk = cs.cs_ship_customer_sk
    inner join customer_address ca
            on ca.ca_address_sk = c.c_current_addr_sk
    inner join date_dim d
            on cs.cs_sold_date_sk = d.d_date_sk
    where  d.d_date between current_date - interval '30' day and current_date
    and merchant_id = 'a3e4400'
    group  by d.d_date,
    ca.ca_state
    order  by d.d_date,
    ca.ca_state;
`);
```

A [dual engine, hybrid execution model](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/) directly queries MotherDuck’s performant and secure infrastructure for large data sets while utilizing your powerful laptop to operate on local data. With MotherDuck's [novel, Wasm-powered 1.5-tier architecture](https://motherduck.com/product/app-developers/#architecture), DuckDB runs both in the browser and on the server, enabling components to load faster to deliver instantaneous filtering, aggregation, or slicing and dicing of your data.

![1_5_architecture.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F1_5_architecture_f73f2c95b2.png&w=3840&q=75)

## Start Building

Current MotherDuck users can see the SDK in action by trying out the [Column Explorer](https://motherduck.com/blog/introducing-column-explorer/) or [viewing our interactive analytics demo](https://motherduckdb.github.io/wasm-client/mosaic-integration/). Refer to the [documentation](https://motherduck.com/docs/authenticating-to-motherduck/#authentication-using-a-service-token) to learn how to retrieve a service token and view the demo.

### **Try MotherDuck for free: no credit card required**

To get started, [head over to the docs](https://motherduck.com/docs/data-apps/). Feel free to share your feedback with us on [Slack](https://slack.motherduck.com/)! If you’d like to discuss your use case in more detail, please [connect with us](mailto:quack@motherduck.com) \- we’d love to learn more about what you’re building.

### TABLE OF CONTENTS

[Building and maintaining data applications is still really ducking hard](https://motherduck.com/blog/building-data-applications-with-motherduck/#building-and-maintaining-data-applications-is-still-really-ducking-hard)

[A unique architecture that lowers cost and latency](https://motherduck.com/blog/building-data-applications-with-motherduck/#a-unique-architecture-that-lowers-cost-and-latency)

[Introducing the MotherDuck Wasm SDK](https://motherduck.com/blog/building-data-applications-with-motherduck/#introducing-the-motherduck-wasm-sdk)

[Start Building](https://motherduck.com/blog/building-data-applications-with-motherduck/#start-building)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Why Python Developers Need DuckDB (And Not Just Another DataFrame Library)](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fwhy_pythondev_1_22167e31bf.png&w=3840&q=75)](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries/)

[2025/10/08 - Mehdi Ouazza](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries/)

### [Why Python Developers Need DuckDB (And Not Just Another DataFrame Library)](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries)

Understand why a database is much more than just a dataframe library

[![DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_4_1_b6209aca06.png&w=3840&q=75)](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)

[2025/10/09 - Alex Monahan, Garrett O'Brien](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)

### [DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/blog/announcing-duckdb-141-motherduck)

MotherDuck now supports DuckDB 1.4.1 and DuckLake 0.3, with new SQL syntax, faster sorting, Iceberg interoperability, and more. Read on for the highlights from these major releases.

[View all](https://motherduck.com/blog/)

Authorization Response