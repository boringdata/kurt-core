---
title: announcing-motherduck-general-availability-data-warehousing-with-duckdb
content_type: blog
source_url: https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb
indexed_at: '2025-11-25T19:56:19.426175'
content_hash: baf2faf8b3f47cb9
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Announcing MotherDuck General Availability: Data Warehousing with DuckDB at Scale

2024/06/11 - 7 min read

BY
MotherDuck team

Over the last year, thousands of users have tested, validated and helped improve MotherDuck as a serverless data warehouse and backend for interactive apps. We’ve now solidified the product, pricing, partnerships, support teams and internal business processes needed to reach an important milestone: General Availability (GA).

MotherDuck and DuckDB are making analytics ducking awesome for the 99% of users who do not need a complex data infrastructure and for whom [big data is truly dead](https://motherduck.com/blog/big-data-is-dead/). MotherDuck now has many customers in production experiencing the simplicity and efficiency of DuckDB with the collaboration and scale of a serverless cloud data warehouse.

![MotherDuck goes GA summary](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmotherduck_goes_ga_embed_smaller_woline_56d7780de8.jpg&w=3840&q=75)

## Production-ready DuckDB

Just last week, DuckDB Labs announced that DuckDB has reached 1.0.0 and is now committed to backwards compatibility. In our [post congratulating the DuckDB team](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release), we outlined why database nerds love DuckDB: performance, innovation velocity, versatility, ease of use, rich and user-friendly SQL, and extreme portability. Thanks to DuckDB, analytics can run virtually anywhere, liberated from the shackles of complex and expensive distributed systems. As an embedded database, it’s the perfect ‘Lego’ building block that can snap into any process just by linking in a library. These same characteristics led us to build a cloud data warehouse on top of DuckDB and in collaboration with the creators.

## Simple, Multiplayer at Scale

MotherDuck makes it simple to start uploading and querying your data, whether it sits on your local machine, in blob storage or even on the web. The data can be in many different formats, including parquet, csv, json, Iceberg and Delta Lake. Your local DuckDB can work seamlessly with MotherDuck using [Dual Execution](https://motherduck.com/product/#:~:text=Hybrid,%20Dual%20Query%20Execution), with parts of your queries running locally and other parts scaling to the cloud.

The cloud creates unique opportunities for sharing data. MotherDuck allows you to upload your data and share a named snapshot with your colleagues in two lines of SQL. Although snapshots can be very useful to have a consistent view of your data across the team for tasks like building machine learning models, snapshots can also be automatically updated. Now with MotherDuck GA, shares can be [restricted to your organization and easily discoverable](https://motherduck.com/docs/key-tasks/sharing-data/sharing-within-org).

A cloud data warehouse needs to scale for all your users and applications. MotherDuck eliminates fighting over common resources by assigning separate, isolated compute instances to each user and simplifying administration and costs for organizations. These compute instances individually scale up to handle workloads of many terabytes for some of our customers. They also scale down to zero when they’re not being used, so you don’t pay when you’re not actively running queries.

## Unmatched Efficiency of Pricing and Execution

Customers have frequently referenced [high costs for status-quo cloud data warehouses](https://motherduck.com/learn-more/modern-data-warehouse-playbook/) as a big concern. Because of the efficiency of DuckDB’s query engine and MotherDuck’s scale-up architecture, we’re able to offer [pricing](https://motherduck.com/product/pricing/) that is often an order of magnitude lower than other alternatives

Not only is the pricing competitive, but it’s also fine-grained and efficient. By billing at second-level granularity, you only pay for the cloud CPU time you actually use. And, when we’re able to take advantage of your local compute through Dual Execution, you don’t pay at all.

> “With MotherDuck working to solve amazing problems through data, our behaviors have changed because we know we don't have to pay enormous costs every time we run a query, so we've got almost limitless performance,” said Ravi Chandra, Chief Technology Officer at Dexibit.

## Backed by a World-Class Team

The team building MotherDuck hails from some of the top companies in data: Google BigQuery, Snowflake, Databricks, SingleStore and more. We’re united by shared values and a shared mission to make analytics ducking awesome.

Our friends at Looker were known to have the best customer success organization in the data industry: the Department of Customer Love, founded by [Margaret Rosas](https://www.linkedin.com/in/mrosas/). Margaret has joined us at MotherDuck to lead our [customer success team](https://motherduck.com/customer-support/), the Hatchery, where our customers are nurtured and taught to fly.

As we go GA, we also wanted to consolidate engineering under a single leader who can help us scale the team. ​​We’ve asked [Frances Perry](https://www.linkedin.com/in/frances-perry/) to lead our engineering organization. Frances came to us from Google where she was an engineering director on Google Compute Engine, built Google’s internal data processing infrastructure and also released that infrastructure to the world as Cloud Dataflow.

## Now SOC 2 Certified

We know that [trust and security](https://motherduck.com/trust-and-security/) are critical as you choose a data warehouse to power your business. We leverage a defense in-depth strategy, maintain operational security processes, and build customer trust through certified auditor attestations.

MotherDuck successfully underwent an audit for SOC 2 Type I, which evaluates our systems relevant to security, availability, and confidentiality. With this attestation completed, we have a Type II planned for later in 2024.

To continue strengthening internal processes and controls, [Myoung Kang](https://www.linkedin.com/in/myoungkang/) has joined the company full-time as Head of Operations. Myoung is a renowned startup veteran who has worked for many companies, including Notion, Convex, and Preset where she was interim CFO.

## Expanded Modern Duck Stack

MotherDuck partners with more than [50 leading companies and technologies](https://motherduck.com/ecosystem/) to make the [Modern Duck Stack](https://motherduck.com/product/#ecosystem). Alongside MotherDuck GA, we’re excited to announce that some of the most requested BI, data integration and data observability tools have been added to the flock.

- **Tableau**: 60,000 companies globally rely on Tableau (part of Salesforce) for data visualization. Tableau Desktop and Server now support MotherDuck, with Tableau Cloud support coming later this year. The connector can be easily found on the [Tableau Exchange](https://exchange.tableau.com/products/1021)
- **PowerBI**: 5 million organizations worldwide use Microsoft Power BI for data visualization, including 97% of Fortune 500. The [MotherDuck connector](https://motherduck.com/docs/integrations/bi-tools/powerbi) for Power BI is officially launched, and MotherDuck has been accepted to the Microsoft for Startups Founders Hub program
- **Fivetran**: Fivetran is the leader in data integration for the modern data stack, powering 5,000 customers. The [MotherDuck destination](https://fivetran.com/docs/destinations/motherduck) connector was developed in close collaboration with the Fivetran engineering team, and is now an official Fivetran destination.
- **Monte Carlo**: Monte Carlo, the leader in data observability, has built a [MotherDuck integration](https://docs.getmontecarlo.com/docs/motherduck). It allows our customers to monitor their databases and look for anomalies through custom SQL rules, which can be created in either the UI wizard and/or programmatically via monitors as code.

## New Startup Program with $10k in Credits

MotherDuck has partnered with leading VC firms to offer $10k in credits to eligible startups in need of a data warehouse or backend for their data apps. Early stage startups with up to 300 employees and less than $100M in funding can submit a [short application](https://motherduck.com/startups/).

## Take Flight with MotherDuck - Now GA

If you don’t already have a MotherDuck account, visit [app.motherduck.com](https://app.motherduck.com/) to get started. We have a [fully-featured 30-day free trial of the Standard Plan](https://motherduck.com/product/pricing/) and a forever Free Plan available for ongoing usage.

> “Our data pipelines used to take eight hours. Now they're taking eight minutes, and I see a world where they take eight seconds. This is why we made the big bet on DuckDB and MotherDuck. It's only possible with DuckDB and MotherDuck,” said Jim O'Neill, Co-founder and CTO at FinQore.

If you’re not quite ready to get started, you can [learn more](https://motherduck.com/product/) about the product, [browse our docs](https://motherduck.com/docs/), and read about how [FinQore](https://motherduck.com/case-studies/saasworks/), [Dexibit](https://motherduck.com/case-studies/dexibit/) and [Mosaic](https://motherduck.com/case-studies/dominik-moritz/) use MotherDuck.

We also have an upcoming [live demo and discussion](https://motherduck.com/getting-started-with-motherduck/) on **Tuesday, June 18th at 10am Pacific**.

Lastly, if you’re in San Francisco, [join us to celebrate](https://www.eventbrite.com/e/motherducking-party-after-dataai-summit-san-francisco-tickets-901904038257) tonight at our MotherDuck’ing Party happening alongside the Data + AI Summit.

### TABLE OF CONTENTS

[Production-ready DuckDB](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/#production-ready-duckdb)

[Simple, Multiplayer at Scale](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/#simple-multiplayer-at-scale)

[Unmatched Efficiency of Pricing and Execution](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/#unmatched-efficiency-of-pricing-and-execution)

[Backed by a World-Class Team](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/#backed-by-a-world-class-team)

[Now SOC 2 Certified](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/#now-soc-2-certified)

[Expanded Modern Duck Stack](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/#expanded-modern-duck-stack)

[New Startup Program with $10k in Credits](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/#new-startup-program-with-10k-in-credits)

[Take Flight with MotherDuck - Now GA](https://motherduck.com/blog/announcing-motherduck-general-availability-data-warehousing-with-duckdb/#take-flight-with-motherduck-now-ga)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Feu_launch_blog_b165ff2751.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-in-europe/)

[2025/09/24 - Garrett O'Brien, Sheila Sitaram](https://motherduck.com/blog/motherduck-in-europe/)

### [MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/blog/motherduck-in-europe)

Serverless analytics built on DuckDB, running entirely in the EU.

[![DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_4_1_b6209aca06.png&w=3840&q=75)](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)

[2025/10/09 - Alex Monahan, Garrett O'Brien](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)

### [DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/blog/announcing-duckdb-141-motherduck)

MotherDuck now supports DuckDB 1.4.1 and DuckLake 0.3, with new SQL syntax, faster sorting, Iceberg interoperability, and more. Read on for the highlights from these major releases.

[View all](https://motherduck.com/blog/)

Authorization Response