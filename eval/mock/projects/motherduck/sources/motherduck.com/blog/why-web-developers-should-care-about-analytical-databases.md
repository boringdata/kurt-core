---
title: why-web-developers-should-care-about-analytical-databases
content_type: blog
source_url: https://motherduck.com/blog/why-web-developers-should-care-about-analytical-databases
indexed_at: '2025-11-25T19:56:17.316211'
content_hash: 68e641614fc6b692
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Why web developers should care about analytical databases

2024/12/18 - 6 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

If you’re building web apps—whether frontend or backend—you’re probably fine using Postgres or another transactional database for most use cases. But as soon as your app needs data-intensive features, like an analytics dashboard for users or insights on product usage, things can [slow down](https://motherduck.com/learn-more/fix-slow-bi-dashboards/). That’s because transactional databases aren’t built for complex analytical queries.

In the past, you would often hand this off to a separate team with a specialized setup, but today, infrastructure is more straightforward, and SQL has become the go-to tool for analytics.

In this blog, we’ll quickly cover what analytical databases are, when to use them, how to move data from your OLTP database, and a practical examples of using an OLAP cloud service like MotherDuck, directly in your Vercel application.

If you prefer watching over reading :

Why web developers should care about analytical databases - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Why web developers should care about analytical databases](https://www.youtube.com/watch?v=DUTCdseUTAc)

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

[Watch on](https://www.youtube.com/watch?v=DUTCdseUTAc&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 8:49

•Live

•

## What are analytical databases

Analytical databases, or OLAP (Online Analytical Processing) databases, are designed for querying and analyzing large datasets. Unlike transactional databases like Postgres, which is excellent at handling fast, small-scale operations like creating or updating records, OLAP databases are optimized for heavy, read-intensive operations.

![img1](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fwebdevelopers_olap_00_01_30_13_Still003_ac80210e4d.png&w=3840&q=75)

They’re built for complex queries, like calculating averages across millions of rows, filtering data by multiple criteria, or aggregating metrics over time. They’re also much faster at these operations because they store and process data differently, typically using columnar storage.

![img2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fwebdevelopers_olap_00_01_41_13_Still004_6e15dc6cab.png&w=3840&q=75)

In short, OLAP databases are ideal for scenarios where you need to crunch large datasets to find trends, patterns, or insights.

## When to use analytical databases

First, it’s important to note that it’s perfectly fine to start prototyping your analytics use cases on your current transactional database, like Postgres.
Many analytical projects begin like that, especially for smaller datasets or simple reporting.

However, as your app grows and the complexity or volume of data increases, you’ll likely hit [performance bottlenecks](https://motherduck.com/learn-more/diagnose-fix-slow-queries/). That’s when you should consider moving to an analytical database, as you don’t want these analytical queries consuming your entire database's resources.

That's when you should consider moving to an analytical database, as you don't want these analytical queries consuming your entire database's resources. This doesn't mean replacing your existing systems; instead, many teams adopt a [two-tier architecture with a lean, modern data warehouse](https://motherduck.com/learn-more/modern-data-warehouse-use-cases/) that acts as a high-performance serving layer for live applications.

![img3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fwebdevelopers_olap_00_02_20_11_Still005_8129e5490c.png&w=3840&q=75)

Here are some common scenarios for analytical databases:

1. **User-Facing Analytics Dashboards:** If your app needs to show users detailed analytics, like tracking usage trends or performance metrics, OLAP databases make it easy to generate fast, interactive reports.
2. **Product Insights:** If you want to understand how users are interacting with your app—like which features are most popular or what leads to churn—OLAP databases let you run exploratory queries efficiently.
3. **Combining Data Sources:** If you need to merge data from multiple systems—like CRM data with app usage data—an analytical database simplifies this process by handling large, diverse datasets.

These are not exclusive use cases but the most common ones you might see.

## How to move data to your analytical database

There are three common methods.

### 1\. ETL Pipelines

ETL stands for Extract, Transform, Load. This is a common approach to move data. You extract it from your OLTP database, clean or reformat it, and load it into your OLAP database. You typically have a process (in Python or whataever have you), that would move the data.
There are two classic approaches:

- **Directly to OLAP system:** You can process and load your data directly into the analytical database.
- **Offload to Object Storage:** You can write your data to an object storage system like S3. This gives you more flexibility to process the data later , be free on the processing tool you wanna use instead of leveraging the OLAP database directly.

### 2\. **Real-Time Streaming:**

If you need live updates for dashboards or analytics, you can use real-time streaming tools like Kafka or AWS Kinesis to move data continuously.
These event streaming services often integrate with Change Data Capture (CDC) tools to track and stream changes in real time. They are excellent for capturing incremental updates and syncing them efficiently into your OLAP database.

### 3\. Direct Querying

Some OLAP systems allow direct queries on your transactional database without moving data or relying on another process.

For example:

- **[DuckDB’s Postgres Scanner:](https://duckdb.org/docs/extensions/postgres.html)** DuckDB can connect directly to Postgres to run analytical queries on your existing data.
- **[pg\_duckdb Extension:](https://github.com/duckdb/pg_duckdb)** This is a new Postgres extension that embeds DuckDB directly inside Postgres, allowing you to leverage DuckDB’s analytical capabilities without additional infrastructure and to connect to MotherDuck.

Each method depends on your app’s needs. Real-time streaming is ideal for live dashboards, ETL is great for batch analytics, and direct querying works well for smaller-scale use cases, as it's really easy to get started.

## Using MotherDuck (OLAP database) directly in Vercel

Let’s dive into an example of connecting your web application to an OLAP database in your data stack using Vercel and its native integration with MotherDuck, which runs DuckDB in the cloud.

In this use case, we’ll hydrate analytical data stored in MotherDuck to feed directly into your application.

With the native integration, you can create a MotherDuck account without ever leaving Vercel, streamlining the process with a single platform for both setup and billing.

Simply head to [the template listing](https://vercel.com/templates/next.js/next-js-motherduck-wasm-analytics-quickstart), where you can easily deploy a ready-made template with just a few clicks or install the integration into an existing project.

In this demo, we’re showcasing a Vercel data dashboard—and as you’ll notice, it’s incredibly fast and responsive.

Your browser does not support the video tag.

Here’s why:

1. It leverages [MotherDuck](https://motherduck.com/) Cloud for handling larger queries.
2. It uses [DuckDB Wasm](https://duckdb.org/docs/api/wasm/overview.html), enabling an analytical database to run directly in the browser. This approach takes advantage of the client’s processing power, reducing extra I/O traffic.

The result? It provides a smoother experience for users and lower computing costs for developers.

## Conclusion

To wrap up, analytical databases unlock a world of possibilities for web developers. They help you handle data-intensive features like user dashboards, gain deeper insights into your product, and combine data from multiple sources—all without overloading your transactional database.

With modern tools and SQL as a common language, setting up these workflows has never been easier. So, the next time your OLTP database is struggling, think about OLAP.

Start using [MotherDuck for free today](https://motherduck.com/get-started/), and explore our [documentation on the Vercel integration](https://motherduck.com/docs/integrations/web-development/vercel/)!

Keep quacking and keep coding.

### TABLE OF CONTENTS

[What are analytical databases](https://motherduck.com/blog/why-web-developers-should-care-about-analytical-databases/#what-are-analytical-databases)

[When to use analytical databases](https://motherduck.com/blog/why-web-developers-should-care-about-analytical-databases/#when-to-use-analytical-databases)

[How to move data to your analytical database](https://motherduck.com/blog/why-web-developers-should-care-about-analytical-databases/#how-to-move-data-to-your-analytical-database)

[Using MotherDuck directly in Vercel](https://motherduck.com/blog/why-web-developers-should-care-about-analytical-databases/#using-motherduck-directly-in-vercel)

[Conclusion](https://motherduck.com/blog/why-web-developers-should-care-about-analytical-databases/#conclusion)

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