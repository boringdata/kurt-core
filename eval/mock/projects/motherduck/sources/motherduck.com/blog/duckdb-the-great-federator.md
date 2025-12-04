---
title: duckdb-the-great-federator
content_type: blog
source_url: https://motherduck.com/blog/duckdb-the-great-federator
indexed_at: '2025-11-25T19:58:18.622062'
content_hash: 03b2907ba9fd3b07
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# DuckDB, the great federator?

2024/01/04 - 13 min read

BY

[Christophe Oudar](https://motherduck.com/authors/christophe-oudar/)

Moving data sounds straightforward, but it’s increasingly becoming a significant challenge. With the surge in data creation and the diversity of data types, integrating different systems is turning into a major hurdle. In this blog, we’ll explore how we’ve reached this complex juncture and examine the solutions available today, with a special focus on federated queries. This approach promises to minimize data movement and streamline our data infrastructure. We’ll delve into a practical example, demonstrating how emerging technologies like DuckDB can be instrumental in this context.

## A growing ecosystem of standards

Software engineering has been producing regularly new data storage format, databases or data system. There’s now so many kinds of data sources that a good chunk of data engineers is about plugging sources to sinks.

![Alt text for the image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fstandards_f761c1393c.png&w=3840&q=75)_XKCD comics about standards_

For instance, most data platforms will have to handle:

- **Structured Data**: This type of data is highly organized and formatted. Examples include data stored in SQL databases, spreadsheets, or CSV files.
- **Semi-structured Data**: It doesn’t have a strict structure like structured data but contains some level of organization. Examples include JSON, XML, log files, and NoSQL databases.
- **Unstructured Data**: This data doesn’t have a predefined structure and doesn’t fit neatly into tables. Examples include text data, images, videos, audio files, social media posts, and documents.

The primary focus of data engineers revolves around connecting those diverse data sources to generate valuable datasets that fuel algorithms, services, or dashboards.

## Standard approaches

### A plumber job challenge

I’ve developed multiple customized jobs aimed at transferring data seamlessly across various platforms, such as:

- Moving data between MySQL and BigQuery
- Integrating Kafka with BigQuery
- Synchronizing data between S3 and BigQuery
- And more…

Enhancing these jobs with new features and ensuring they offer broad support requires significant effort. However, the real challenge lies in the ongoing maintenance, which demands extensive time investment due to several factors:

- Numerous dependencies, potentially conflicting
- Evolving APIs of languages and frameworks
- Managing the deployment and runtime environments of those jobs

These needs are not unique to just a few companies; they have become increasingly demanding within the continuously maturing data engineering ecosystem. Consequently, some engineers have taken the initiative to develop frameworks and SaaS solutions to address these challenges, saving us invaluable hours of labor.

These data integration systems excel in extracting data and effectively mapping data types to their respective destinations.

### Data integration systems

In recent years, there has been a notable emergence of tools and platforms designed to facilitate the interoperability of data sources. Among these, certain managed data integration platforms, such as Fivetran, have stood out by offering an extensive array of integrations spanning databases, file formats, and APIs. They streamline the process of ingesting data from CRM platforms like Salesforce, eliminating the requirement for programming expertise.

However, these platforms have their limitations, employing a generic approach that may not cater to every user’s specific requirements. This becomes evident when there’s a need to access certain options, APIs, or authentication patterns that aren’t supported by these platforms. Whether it’s due to the necessity for customization, concerns about privacy, or cost considerations, open-source software (OSS) alternatives like Meltano, Airbyte, or dlt have emerged as viable solutions.

### Replication freshness

Let’s consider a scenario where we’re enhancing an analytics UI for a large-scale ecommerce corporation, displaying product lists alongside metrics like page views and the quantity of products added to carts. When our operations team introduces a new item for sale and accesses the UI, they naturally expect to see the latest addition. However, if our data replication occurs only once every hour, there’s a likelihood that the newly added item might not immediately appear. In such cases, implementing a “last updated at” warning becomes necessary to communicate that some items might not be visible. One potential workaround involves creating two separate views to ensure the visibility and update of newly created items.

Traditional data integration systems are typically not optimized for real-time replication. To address the latency in replication, there are real-time solutions available, such as change data capture platforms like Debezium. These platforms enable streaming data from databases to systems like Kafka, which then manages the task of materializing the current state of data in your data lake. This approach works seamlessly when integrated with platforms like Iceberg, which supports time travel features. However, setting up these solutions can be quite labor-intensive, especially if opting against managed solutions like Tabular.

Alternatively, managed solutions like Datastream exist, offering data replication onto platforms such as BigQuery. Yet, these solutions come with their own limitations, such as restricted support for schema changes.

### Full database replication

If dealing with a vast database, you might want to extract only a portion of the rows, as replicating the entire dataset demands considerable time, computational resources, and storage that could be conserved.

Consider a scenario where you’re managing a multi-tenant database and need to synchronize only select segments of it. However, depending on how you’ve implemented the segmentation (whether at the database, table, or row level), achieving the desired filtering might be challenging due to constraints within the data integration platform. Furthermore, these tools lack a universal method to apply filters, and customizing filters for different connectors becomes necessary.

## Enter Federated Queries

Federated queries present a robust resolution to the integration challenge. Fundamentally, they facilitate effortless retrieval and manipulation of data from diverse sources, enabling applications to gather insights from databases, file systems, APIs, and beyond. This unified perspective eliminates the necessity for intricate ETL procedures or data migrations. Achieving such queries often involves the utilization of addons or extensions known as **Foreign Data Wrappers**.

## Foreign data wrappers ecosystem

Foreign data wrappers have a longstanding history in the tech landscape, with examples such as mysql\_fdw (Postgres’ MySQL foreign data wrapper) dating back to 2011. Various databases like Postgres and query engines such as Trino have adopted connectors for external tables, yet the level of integration across platforms can significantly differ. Depending on the target, the capabilities for pushdown operations can vary widely. For instance, employing a foreign data wrapper around an RDBMS like MySQL often brings features such as:

- Column pushdown
- Predicate pushdown
- Join pushdown
- Aggregate pushdown
- Limit offset pushdown

Postgres’ MySQL FDW already encompasses all these pushdown techniques. However, when dealing with file-based access like JSON, the engine handling the data source must manage the actual data operations. In such cases, the engine takes on the majority of the workload, emphasizing efficiency, especially when constructing latency-sensitive applications.

## What about DuckDB?

DuckDB stands out in its capacity: its drivers open up an in-process OLAP query engine, equipped with an advanced SQL language, compatible with a wide array of applications. Moreover, DuckDB provides the capability to craft potent extensions, empowering developers to link various data sources using high-performance languages such as C++ or Rust. Though creating those connectors require some effort, the end users can enjoy a natural developer experience on the SQL end.

Many of these extensions, fostered by DuckDB Labs and its community, function as foreign data wrappers tailored for DuckDB. Examples include those designed for Postgres, MySQL, or Athena. While some are in their early stages and may not yet fully support pushdowns, the development of advanced features is actively underway.

What distinguishes DuckDB from larger platforms like Trino or Clickhouse? DuckDB excels with small and medium-sized datasets due to its single-machine architecture and in-process methodology, drastically reducing response times. Adding to this advantage is its effortless setup process: simply integrate the DuckDB driver into your application and seamlessly connect databases using SQL, treating them as if they were native.

### A quick example

Let’s demonstrate the previously quoted example in action. Suppose the product data resides in a MySQL database, while the analytics data is stored as a DuckDB file on S3. Firstly, let’s load the extensions and connect to the databases. The procedure would resemble the following SQL commands:

```ini
Copy code

INSTALL mysql_scanner;
INSTALL httpfs;

LOAD mysql_scanner;
LOAD httpfs;

CALL load_aws_credentials();

ATTACH 'host=127.0.0.1 user=root port=3306 database=product_db' AS product_db (TYPE MYSQL_SCANNER);

ATTACH 's3://<bucket>/product_stats.db' (READ_ONLY);
```

As you can observe, once the connections are established and initialized with the database attachments, we can retrieve the actual data seamlessly, as if the data were co-located:

```sql
Copy code

SELECT product.id, product.name, product_stats.views_count, product_stats.in_basket_count
FROM product_db.product
JOIN product_stats.product_stats ON product.id = product_stats.product_id
WHERE product.name LIKE "%duck%"
LIMIT 100 OFFSET 0
```

With this approach in place, the developer’s journey becomes significantly smoother when tasked with implementing a product that necessitates filtering, pagination, and sorting functionalities.

### An experiment

In a recent endeavor, I brought an idea to life by constructing a proof of concept on two MySQL servers, mirroring the previous approach. The steps were as follows:

- I initiated a connection pool from a Scala application to DuckDB, laying the groundwork for the database attachments.
- I crafted a query to unify two tables, each residing in a separate database.
- I executed the query, parsed the resulting data, and returned the content.

The response time clocked in at approximately five seconds. While this isn’t overly lengthy, it’s worth noting that bypassing DuckDB and opting for requests and in-memory joins could potentially trim this down to a brisk 200 milliseconds, given that each query takes about 70 milliseconds on a standalone SQL client.

You might be curious about the factors contributing to this duration. Here are a few insights:

- To push down predicates, the extension fetches the table schema information prior to constructing the actual MySQL query. Although this information is cached post the initial request, failing to run a pre-cache request for table schemas could tack on an extra 2–3 seconds to your response time.
- All requests are encapsulated in a transaction, which could introduce unnecessary overhead.
- Depending on the nature of the request, the absence of a connection pool might lead to sequential database queries, thereby slowing down the process.
- Lastly, I observed that executing the full request, once the schema was cached, took around 2.5 seconds (as measured by the time command in bash), while the profiling details reported a response time of approximately 1.5 seconds on DuckDB.

There’s ample scope for enhancement, but it’s crucial to remember that we’re still navigating the nascent stages of the DuckDB extensions ecosystem.

## Going further

As I’ve been architecting solutions across diverse data scopes, the concept of abstracting query federation has been a recurring idea. In a large organization that values team autonomy, it’s not uncommon to encounter numerous databases when building a cross-functional feature. There are several patterns to simplify this complexity, with semantic layers often being the most effective for maintaining consistent definitions. However, there are scenarios where semantic layers may not be the ideal choice. For instance, your database or some of its features may not be supported, or the time and cost associated with semantic layers may not be feasible.

In such cases, employing views, particularly DuckDB views, can be a powerful alternative. Here’s why:

- Views allow you to encapsulate actual data source accesses, leveraging the robust SQL features of DuckDB.
- View definitions can be stored within the DuckDB database format, making it convenient to share across applications that need access to these definitions.
- The flexibility of views allows you to interchange the actual data sources behind the definitions. This is because the references are tied to the database alias used during attachment. This means you can maintain the same definitions whether you’re referencing an online database like Postgres or its table dumps in Parquet. This can be particularly useful when building unit tests on your view logic, as you can simply use a different offline source to keep your test stack and fixtures straightforward.
- The versatility of views extends to creating views from other views. This can be beneficial when you want to layer abstractions and allow teams and projects to have their own isolated DuckDB view definitions. You can then consolidate these by attaching each of these DuckDB view definitions once again, or even merge them by copying them into your own.

## Limitations

The potential of DuckDB as a federated query layer is immense, but the extensions, such as **duckdb\_mysql**, need to enhance their support for advanced pushdowns to truly excel. For example, the current filter pushdown is rather rudimentary and only works with a single value, not a list. I’ve been [exploring ways to bolster support for more pushdown features](https://github.com/duckdb/duckdb_mysql/pull/10). Additionally, as previously discussed, eager fetching of schemas could be beneficial to mitigate the cold start effect. In pursuit of this, I’ve been [probing the addition of a specific function](https://github.com/duckdb/duckdb_mysql/pull/15) to facilitate this. There’s undoubtedly more ground to cover, so if you’re intrigued and want to contribute to these developments, your input would be most welcome!

## The silver bullet?

DuckDB boasts numerous impressive use cases, and data source federation stands out among them. However, is it the ultimate solution for all scenarios? Let’s delve into situations where it fits perfectly and where it might not be the most suitable choice.

When to consider using DuckDB for data source federation:

- Building APIs that rely on multiple data sources while aiming for a responsive latency (< 1s).
- Conducting exploration or troubleshooting that necessitates quick correlation across various data sources.
- Creating small to medium-sized data rollups that merge fact and dimensional data from diverse sources, eliminating the need for replication concerns.

When it might not be the best choice:

- Handling joins with exceptionally large data volumes (e.g., > 1 TB of data, a scenario where DuckDB might not have been thoroughly stress-tested on a very large VM).
- Requiring advanced pushdowns/features on foreign data wrappers that are still in an immature stage (e.g., Iceberg integration).
- Needing access to a data source for which no ongoing development is underway and lacking the capacity or expertise to create it.
- Operating on a specific setup that DuckDB (or its extensions) does not support or isn’t optimized for. For instance, some extensions are not built to run on some linux ARM versions.
- Demanding extremely low latency (i.e., < 100ms).
- Expecting a high volume of simultaneous client requests performing similar queries concurrently.

## Conclusion

Federated queries offer an excellent solution for managing diverse data sources, and I strongly believe that DuckDB will become increasingly accessible and significant in the coming months. However, it’s crucial to clearly define your use cases, as this approach may occasionally prove counterproductive. Nonetheless, when it aligns with your needs, DuckDB offers a multitude of advantages: enhanced performance, advanced SQL functionalities, and convenient methods for testing logic using mock data. Whether opting for DuckDB or another platform, witnessing data infrastructure tools expand their support by incorporating more data sources or refining pushdown logics is a gratifying development. Hence, it’s worth considering for your upcoming data engineering projects due to its practicality.

For those intrigued by DuckDB, exploring [MotherDuck](https://motherduck.com/) as a SaaS platform to test and manage the runtime could be beneficial! Although the team [plans to introduce additional extensions in the future](https://motherduck.com/docs/architecture-and-capabilities/#considerations-and-limitations), you can already gain insight into DuckDB’s capabilities by utilizing sources like Parquet or CSV.

### TABLE OF CONTENTS

[A growing ecosystem of standards](https://motherduck.com/blog/duckdb-the-great-federator/#a-growing-ecosystem-of-standards)

[Standard approaches](https://motherduck.com/blog/duckdb-the-great-federator/#standard-approaches)

[Enter Federated Queries](https://motherduck.com/blog/duckdb-the-great-federator/#enter-federated-queries)

[Foreign data wrappers ecosystem](https://motherduck.com/blog/duckdb-the-great-federator/#foreign-data-wrappers-ecosystem)

[What about DuckDB?](https://motherduck.com/blog/duckdb-the-great-federator/#what-about-duckdb)

[Going further](https://motherduck.com/blog/duckdb-the-great-federator/#going-further)

[Limitations](https://motherduck.com/blog/duckdb-the-great-federator/#limitations)

[The silver bullet?](https://motherduck.com/blog/duckdb-the-great-federator/#the-silver-bullet)

[Conclusion](https://motherduck.com/blog/duckdb-the-great-federator/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Introducing FixIt: an unreasonably effective AI error fixer for SQL](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ffixit_social_47f52f8fb0.png&w=3840&q=75)](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/)

[2024/01/03 - Till Döhmen, Hamilton Ulmer](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/)

### [Introducing FixIt: an unreasonably effective AI error fixer for SQL](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer)

FixIt will correct mistakes in your SQL queries based on the schema and DuckDB syntax. Based on a large language model (LLM).

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response