---
title: announcing-mega-giga-instance-sizes-huge-scale
content_type: blog
source_url: https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale
indexed_at: '2025-11-25T19:56:38.218331'
content_hash: 16a72a7b2d67e0db
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Introducing Mega and Giga Ducklings: Scaling Up, Way Up

2025/07/17 - 4 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

As DuckDB continues to prove it can scale from your laptop to the cloud and make even big data feel small, more of you are pushing the limits of what’s possible — more complex aggregations, gnarlier joins, tighter deadlines. Jumbo ducklings got us far and are big enough for the [vast majority of customers](https://motherduck.com/blog/redshift-files-hunt-for-big-data/). While our focus is on the horizontal scale out architectures possible with [per-user tenancy](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/#scaling-up-isnt-the-only-way), sometimes you just need a bigger hammer to get the job done.

Meet our newest feathered friends: **Mega** and **Giga** ducklings.

![Duckling Sizes](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckling_size_banner_v2_f3d99a5ff3.png&w=3840&q=75)

These new instance sizes are built for the **largest, toughest, most complex data transformations** DuckDB can handle — and then some.

Like their smaller siblings, Mega and Giga instances are fully managed, ephemeral, and optimized for DuckDB. But they bring **more memory and more compute**, so your queries can go faster and finish sooner — even under serious load.

## Mega ducklings: For Demanding Workloads at a Larger Scale

**Mega ducklings** are designed for when your workloads have outgrown Jumbo and you need more power — not eventually, but _right now_.

> **"An extremely large instance for when you need complex transformations done quickly."**

**Use a Mega when:**

- Your queries are too complex or your data volume is too high for Jumbo to handle — especially **in crunch time**
- You’re running a **weekly job that rebuilds all your tables**, and it has to run in **minutes, not hours**
- One customer has **10x the data** of everyone else, and they still expect subsecond response times

Under the hood, Mega unlocks more **in-memory execution**, handles larger joins and aggregations without spilling, whether you’re reading from your MotherDuck storage, Parquet files or your shiny new DuckLake.

## Giga ducklings: When Nothing Else Will Work

**Giga ducklings** are our largest instance sizes, purpose-built for **the toughest of transformations**.

> **"Largest instances enable the toughest of transformations to run faster."**

**Request a Giga when:**

- Your data workload is **so complex or so massive** that nothing else will work
- You’re running a **one-time job to restate revenue for the last 10 years** — and it needs to be correct and fast
- You need a growth path **beyond Mega**, because your **data volume and complexity just grew 10x**

Giga gives DuckDB an environment with maximum compute and memory — ideal for **very complex joins**, **deeply nested CTEs**, and **long-range analytical backfills**. It’s not for every job — but when you need it, you _really_ need it.

## Scaling up isn't the only way

Scaling up to larger instance sizes (ducklings) is only one of the [many ways MotherDuck scales data warehousing workloads](https://motherduck.com/blog/scaling-duckdb-with-ducklings/).

Most data warehouses are built as monoliths, where every user in the organization shares the same data warehouse compute resources. These monoliths often begin to crack under high concurrency. At the core of MotherDuck's architecture is [per-user tenancy](https://motherduck.com/blog/scaling-duckdb-with-ducklings/#how-is-a-duckling-different-from-a-standard-data-warehouse-instance), in which each user (or customer, in the case of customer-facing analytics) gets their own duckling that's configurable in size. So you might use one of the new Mega instances for some complicated transformations in your data pipelines, but still rely upon Standard instances to serve most of your users. Each instance is provisioned on demand and managed for you.

There may be cases where per-user tenancy isn't as natural. For example, [business intelligence (BI) tools](https://motherduck.com/ecosystem/?category=Business+Intelligence) typically share a single database connection but then may have dozens of users running queries at the same time. This would ordinarily break the "one-user-per-duckling" pattern.

MotherDuck’s [read scaling](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/read-scaling/) is designed for these types of cases – providing an extra boost in compute through horizontal scaling and maintaining the pattern of “one-user-per-duckling!”

## Available on the Business Plan

These new duckling sizes are available on the instance plan. Megas are completely self-serve. If you want access to Gigas, please [quack with us](https://motherduck.com/contact-us/product-expert/?a=get-gigas) about what you're building.

### TABLE OF CONTENTS

[Mega ducklings: For Demanding Workloads at a Larger Scale](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/#mega-ducklings-for-demanding-workloads-at-a-larger-scale)

[Giga ducklings: When Nothing Else Will Work](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/#giga-ducklings-when-nothing-else-will-work)

[Scaling up isn't the only way](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/#scaling-up-isnt-the-only-way)

[Available on the Business Plan](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/#available-on-the-business-plan)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![The Data Engineer Toolkit: Infrastructure, DevOps, and Beyond](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumb_de_50b9010e13.png&w=3840&q=75)](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/)

[2025/07/03 - Simon Späti](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/)

### [The Data Engineer Toolkit: Infrastructure, DevOps, and Beyond](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops)

A comprehensive guide to advanced data engineering tools covering everything from SQL engines and orchestration platforms to DevOps, data quality, AI workflows, and the soft skills needed to build production-grade data platforms.

[![This Month in the DuckDB Ecosystem: July 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_2_32a9339cef.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2025/)

[2025/07/08 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2025/)

### [This Month in the DuckDB Ecosystem: July 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2025)

DuckDB Monthly #31: Kafka Integration, Browser-Based Analytics, and Lake Format Innovations

[View all](https://motherduck.com/blog/)

Authorization Response