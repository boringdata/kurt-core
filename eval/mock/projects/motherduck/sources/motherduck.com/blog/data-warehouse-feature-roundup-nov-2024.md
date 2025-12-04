---
title: data-warehouse-feature-roundup-nov-2024
content_type: blog
source_url: https://motherduck.com/blog/data-warehouse-feature-roundup-nov-2024
indexed_at: '2025-11-25T19:57:10.556721'
content_hash: 4f829b09e8008753
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Improved Control and Ergonomics on MotherDuck

2024/11/25 - 3 min read

BY

[Sheila Sitaram](https://motherduck.com/authors/sheila-sitaram/)

At MotherDuck, we’ve been hard at work on new features to give you better tools for managing your accounts, scaling your applications, and handling individual queries. This month's Feature Roundup highlights recent updates designed to empower you with more control over your data and queries for a seamless, efficient experience.

Let’s dive in.

## Query Monitoring and Management Functions

MotherDuck now provides the ability to [monitor](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/connection-management/monitor-connections/) and [interrupt](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/connection-management/interrupt-connections/) active server connections with two new functions in Preview.

Database activity monitoring gives users a real-time view of their active connections to understand their current load and database usage. `md_active_server_connections` is a table function that lists all server-side connections with active transactions.

Quickly identify long-running queries and problematic connections to support resource optimization and monitor active transactions to prevent disruptions during schema changes or database maintenance.
Furthermore, users can now interrupt active transactions on a server-side connection with the `md_interrupt_server_connection` scalar function. Doing so will fail / rollback the active transaction while allowing the connection to be used for future transactions and queries.

Together, these functions support a complete workflow for understanding query performance and interrupting ad-hoc or erroneous queries without requiring a fresh connection setup. In a multi-user context, [Org Admins](https://motherduck.com/docs/key-tasks/managing-organizations/#roles) can identify problematic queries from one user and use `client_connection_id` from the active server connections returned with `md_active_server_connections` to interrupt the stalled connection using `md_interrupt_server_connection`, all without impacting other users or services that rely on that same connection.

## Specify Attach Mode for Streamlined Connections to MotherDuck

MotherDuck now saves you time when you only need to connect to a single database by allowing you to specify the attach mode when connecting.

MotherDuck’s data warehouse [sharing model](https://motherduck.com/docs/key-tasks/sharing-data/sharing-overview/) operates at the database level. Shares are read-only databases that are purpose-built for data collaboration and ad-hoc analytics. These zero-copy clones help savvy data leaders and small teams derive insights without directly accessing the production dataset. Shares can be [attached](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/attach-share/) and [updated](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/update-share/) manually or automatically by the Share’s creator.

Specifying `attach_mode={single|workspace}` lets you tailor your connection to your needs. Single database attach mode simplifies the connection process when you are only working with a single database by streamlining your workflow and removing unnecessary setup steps.

Use `attach_mode=single` in scenarios where you only need to query a single database. It simplifies the connection by ensuring no additional workspace context or databases are involved.

To access multiple databases as part of cross-database workflows, use `attach_mode=workspace` instead.

The value of specifying attach mode ultimately comes down to intent. Being explicit ensures MotherDuck can optimize the connection behavior for your use case to streamline operations.

## In-Memory Queries are (even more!) Efficient and Powerful

As part of our commitment to continuous improvement, our Platform team is constantly tuning our infrastructure to give you the best experience possible. MotherDuck’s [architecture](https://motherduck.com/docs/architecture-and-capabilities/) is built around the power of scaling up with highly efficient and scalable single nodes.

MotherDuck now enables you to run larger queries in-memory so you can handle more complex workloads and data-intensive queries with ease.

## Take Flight

Let us know how you’re using MotherDuck: Share your success stories and feedback with us on [Slack](https://join.slack.com/t/motherduckcommunity/shared_invite/zt-2hh1g7kec-Z9q8wLd_~alry9~VbMiVqA). If you’d like to discuss your use case in more detail, please [connect with us](https://motherduck.com/contact-us/sales/) \- we’d love to learn more about what you’re building and how we can make your MotherDuck experience even better.

Happy querying!

### TABLE OF CONTENTS

[Query Monitoring and Management Functions](https://motherduck.com/blog/data-warehouse-feature-roundup-nov-2024/#query-monitoring-and-management-functions)

[Specify Attach Mode for Streamlined Connections to MotherDuck](https://motherduck.com/blog/data-warehouse-feature-roundup-nov-2024/#specify-attach-mode-for-streamlined-connections-to-motherduck)

[In-Memory Queries are Efficient and Powerful](https://motherduck.com/blog/data-warehouse-feature-roundup-nov-2024/#in-memory-queries-are-efficient-and-powerful)

[Take Flight](https://motherduck.com/blog/data-warehouse-feature-roundup-nov-2024/#take-flight)

Subscribe to DuckDB Newsletter

E-mail

Subscribe to other MotherDuck news

Submit

Subscribe

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![From Data Lake to Lakehouse: Can DuckDB be the best portable data catalog?](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_catalog_51d1dc1d0c.png&w=3840&q=75)](https://motherduck.com/blog/from-data-lake-to-lakehouse-duckdb-portable-catalog/)

[2024/11/14 - Mehdi Ouazza](https://motherduck.com/blog/from-data-lake-to-lakehouse-duckdb-portable-catalog/)

### [From Data Lake to Lakehouse: Can DuckDB be the best portable data catalog?](https://motherduck.com/blog/from-data-lake-to-lakehouse-duckdb-portable-catalog)

Discover how catalog became crucial for Lakehouse and how DuckDB can help as a catalog

[![How to Extract Analytics from Bluesky, the New Open Social Network](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_bsky2_239933cbc2.png&w=3840&q=75)](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky/)

[2024/11/20 - Simon Späti, Mehdi Ouazza](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky/)

### [How to Extract Analytics from Bluesky, the New Open Social Network](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky)

Discover how to build data pipelines to get insights from Bluesky

[View all](https://motherduck.com/blog/)

Authorization Response