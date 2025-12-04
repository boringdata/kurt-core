---
title: duckdb-ecosystem-newsletter-february-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2025
indexed_at: '2025-11-25T19:58:04.514479'
content_hash: 84d5ff1772f0dc90
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# DuckDB Ecosystem: February 2025

2025/02/09 - 9 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

Hello. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB, delivered straight to your inbox.

In this February issue, I’ve curated ten insightful links and highlighted key takeaways from DuckCon #6 in Amsterdam. This edition explores DuckDB’s latest features, including UNION ALL BY NAME and new community-driven extensions like **Airport for Arrow Flight**. Additionally, I cover practical benchmarks comparing DuckDB with tools like **DataFusion** and **UNIX coreutils**, along with exciting developments in real-time data processing (Debezium) and cloud integrations with platforms such as Databricks and MotherDuck.

PS: DuckDB 1.2 is out! And MotherDuck added support at the same time as its release!

If you have feedback, news, or any insights, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1728511492903.jpeg&w=3840&q=75)

### Daniel Beach

Daniel Beach is a senior Data engineer and a an active writer in the data engineering community through [data engineering central](https://dataengineeringcentral.substack.com/) and [confession data guy](https://www.confessionsofadataguy.com/).

He doesn’t write to please people—he writes to share the truth as he sees it.  He prefers to share his firsthand experience, working hands-on with tools and processes. If something doesn’t work on the first try, it’s probably a sign of valuable UX feedback rather than just user error.

Several of his blog posts have already been shared in this newsletter, so it was about time! Thank you for your contribution to the DuckDB community!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [DuckCon \#6 in Amsterdam](https://www.youtube.com/live/Sb9DFclZRpg?si=oLjuG07s_D7yyrBQ&t=1178)

DuckCon #6 took place last week in Amsterdam with great community [talks](https://duckdb.org/events/2025/01/31/duckcon6/), fantastic gatherings, and discussions during the breaks (I was there 🥳). Some highlights are:

- Mark [talked](https://www.youtube.com/live/Sb9DFclZRpg?si=hhnUcnqbbuVtJml-&t=1673) about how DuckDB has achieved significant performance gains. Gábor successfully [ran TPC-H](https://duckdb.org/2024/12/06/duckdb-tpch-sf100-on-mobile.html) at scale factor 300 (roughly 300GB of input data) on a Raspberry Pi, while scale factor 30,000 was achieved on a 96-core machine. The upcoming DuckDB v1.2 "Harlequin" release will feature improved CSV reader performance, enhanced SQL CLI autocomplete, various performance optimizations, and a new C API for easier extension development.
- The community showed impressive talks with [Rusty's "Airport" extension](https://www.youtube.com/live/Sb9DFclZRpg?si=Pd2jo55ihiBqtgYi&t=2135), enabling DuckDB to interact with Apache Arrow Flight servers for Delta Lake integration with **write support**, and Daniel ten Wolde's [SQL/PGQ extension](https://www.youtube.com/live/Sb9DFclZRpg?si=VxJUnpFMokZliPgJ&t=8773) implementing the SQL:2023 property graph query standard, which outperforms Neo4j in certain benchmarks by 10-100x on analytical queries.
- Sam Jewell from Grafana Labs [shared](https://www.youtube.com/live/Sb9DFclZRpg?si=9XX_9N6v7kyGx-Jg&t=9559) essential security considerations when implementing DuckDB in production environments, particularly regarding the CLI's dot commands and file access capabilities. The team also announced their focus on **lakehouse** format support for the upcoming year, with Mark indicating this would be a significant development priority.

DuckDB's extension ecosystem is maturing rapidly. The new C API and Airport extension make it easier to develop community extensions, while the core DuckDB engine continues to impress with its performance capabilities.

### [Definite: Duck Takes Flight](https://www.definite.app/blog/duck-takes-flight)

**TL;DR:** Mike discusses using Apache Arrow Flight to implement concurrent read/write operations in DuckDB.

DuckDB is limited by its inability to support concurrent writers and simultaneous reads during writes, which poses challenges for near real-time analytics. Ritchie introduces a solution by leveraging **Arrow Flight**, **enabling multiple writers** to send data while simultaneously executing queries. The core implementation consists of a Flight server class, where data can be registered and queried using the do\_put and do\_get methods. For example, the do\_get method executes a query and fetches an Arrow table, allowing for real-time data processing. Ritchie emphasizes that this architecture facilitates parallel data loading and querying without the traditional limitations of DuckDB.

### [Real-time Data Replication with Debezium and Python](https://debezium.io/blog/2025/02/01/real-time-data-replication-with-debezium-and-python/)

**TL;DR:** This article explores setting up a real-time Change Data Capture (CDC) pipeline using Debezium and Python, loading data into DuckDB via dlt.

Ismail showcases the integration of Java-based Debezium with a Python environment to capture change data from a PostgreSQL database and load it into a DuckDB using pydbzengine. The pipeline leverages Debezium to monitor PostgreSQL transaction logs, producing change event streams. These events are then consumed by a Python-based dlt pipeline that uses pydbzengine, simplifying configuring and running Debezium within Python. The code showcases setting up a PostgreSQL container using Testcontainers and configuring Debezium with a Java Properties object, specifying details like connector class and offset storage.

### [DuckDB Database File as a New Standard for Sharing Data?](https://medium.com/@josef.machytka/duckdb-database-file-as-a-new-standard-for-sharing-data-cabaa1c6edeb)

**TL;DR:** DuckDB offers a promising solution for data sharing by encapsulating large datasets into a single compressed database file, simplifying data transfer processes.

In a detailed exploration, Josef examines DuckDB's potential to become the new data-sharing standard, particularly highlighting its efficiency in handling large datasets. DuckDB's ability to store data in a columnar format similar to Parquet allows for significant compression, especially with numerical data. For instance, a 10 GB CSV of string data resulted in an **11 GB** PostgreSQL table (size on the disk) and **14 GB** DuckDB database file, whereas a similar numerical dataset was compressed to a **15 GB** PostgreSQL table and just **2.8 GB**. This suggests that while DuckDB may initially appear less efficient for string-heavy datasets, it excels with numerical data. Integration with PostgreSQL and MySQL was straightforward, facilitating seamless data transfers without complex export-import processes.

### [DuckDB vs. Datafusion](https://performancede.substack.com/p/duckdb-vs-datafusion)

**TL;DR:** This article compares DuckDB and DataFusion, an ongoing comparison focusing on their SQL capabilities and performance characteristics.

Matt discusses the growing trend of using Rust-based tooling in data processing, highlighting the choice of Apache DataFusion as a backend by organizations like Databricks and the Apache Iceberg team. He presents benchmark results showing Rust's efficiency, noting it could write 1 billion rows in under 3 seconds. The article includes code examples illustrating the ease of use for DuckDB and DataFusion, such as the syntax for reading and exporting data. For instance, exporting to Parquet requires just one line of code in both engines. While both tools offer comparable syntax, Matt concludes that DuckDB has **a richer SQL feature set**. As a practical takeaway, if you're developing a Rust-based API and need a SQL engine, DataFusion might be the logical choice; however, for more advanced SQL features, DuckDB remains superior.

### [DuckDB processing remote (s3) JSON files](https://dataengineeringcentral.substack.com/p/duckdb-processing-remote-s3-json?r=cxg56&utm_campaign=post&utm_medium=web&triedRedirect=true)

**TL;DR:** Processing remote JSON files stored in S3, highlighting its potential as a versatile SQL tool for data engineering tasks.

The article by Daniel explores the integration of DuckDB with remote JSON files stored in AWS S3, emphasizing its ease of use and efficiency. DuckDB's READ\_JSON() function is pivotal, allowing automatic configuration flag inference from JSON files. This function simplifies complex data processing tasks, traditionally involving cumbersome data transformations using tools like PySpark or AWS Glue. Daniel illustrates this by querying JSON files using minimal code and achieving effective results **without the need for intermediate data format conversions**. The practical takeaway for database engineers is DuckDB's ability to streamline SQL operations on JSON files directly from S3, reducing code complexity and execution time and making it an appealing choice for handling large-scale JSON datasets in cloud environments. "DuckDB rarely disappoints with its integrations", Daniel notes, underscoring its position as a reliable tool for modern data engineering challenges.

### [Local dev and cloud prod for faster dbt development](https://motherduck.com/blog/dual-execution-dbt/)

**TL;DR:** Speed up dbt development using local dev and cloud prod setups with DuckDB and MotherDuck.

Jacob highlights a dual execution setup using DuckDB locally and MotherDuck in the cloud to enhance dbt development speed. By configuring the dbt profile for dual execution, where the local environment uses path: local.db and the cloud environment uses path: "md:jdw", developers can leverage local resources for faster iterations. Jacob provides code snippets for setting up dbt profiles and conditionally sampling data using Jinja, such as from {{ source("tpc-ds", "catalog\_sales") }} {% if [target.name](http://target.name/) == 'local' %} using sample 1 % {% endif %}. This method keeps datasets under a million rows for local development while utilizing the cloud for larger datasets. A practical takeaway is the accelerated development cycle, with an approximate 5X increase in dbt run speeds by minimizing local data size and optimizing compute resources.

### [Access Databricks UnityCatalog from DuckDB](https://www.codecentric.de/wissens-hub/blog/access-databricks-unitycatalog-from-duckdb)

**TL;DR:** Accessing Databricks UnityCatalog data using DuckDB improves efficiency by bypassing Spark for direct delta file reads.

The article by Matthias discusses leveraging DuckDB to query data from Databricks UnityCatalog. It highlights two primary methods: using PySpark to read data into Arrow format and querying it with DuckDB or directly reading delta files from storage with DuckDB, which avoids Spark's overhead. The direct method involves using Databricks' temporary table credentials API to secure access to storage, allowing DuckDB to handle "larger than memory" datasets efficiently. This is achieved by setting SET azure\_transport\_option\_type = 'curl'; in DuckDB to ensure proper certificate handling. Matthias points out that DuckDB's ability to directly interact with data stored in UnityCatalog without Spark intermediation enhances performance, particularly for **data not fitting into memory**.

### [Vertical Stacking as the Relational Model Intended: UNION ALL BY NAME](https://duckdb.org/2025/01/10/union-by-name.html)

**TL;DR:** UNION ALL BY NAME enhances vertical stacking by matching columns by name, supporting evolving schemas, and improving performance.

This feature allows you to combine two SQL queries stacking automatically, aligning by name, as opposed to UNION ALL, where the order needs to be the same for each dataset you combine. This feature is especially relevant when dealing with **evolving schemas in data lakes** or combining datasets with different column orders. It simplifies operations by automatically filling missing columns with NULL values, reducing the need for explicit schema management.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Local Dev to Cloud Prod](https://lu.ma/0die8ual?utm_source=eventspage)

**13 February, Online - 6 PM PT**

​Join us to discover how MotherDuck simplifies your development experience by eliminating the friction between local development and cloud production environments

### [Getting Started with MotherDuck](https://lu.ma/sz64bg9b)

**20 February, Online**

Looking to get started with MotherDuck and DuckDB? Join us for a live session to learn how MotherDuck makes analytics fun, frictionless, and ducking awesome!

### [Fast & Scalable Analytics Pipelines with MotherDuck & dltHub](https://lu.ma/79a7lysr?utm_source=eventspage)

**26 February, Online**

Explore how dltHub's Python-based ETL capabilities, paired with MotherDuck, empower you to effortlessly build fast, scalable analytics pipelines from local development to cloud-native production.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2025/#upcoming-events)

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

[![MotherDuck for Business Analytics: GDPR, SOC 2 Type II, Tiered Support, and New Plan Offerings](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FPricing_v2_1_f4d4004588.png&w=3840&q=75)](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/)

[2025/02/11 - Sheila Sitaram](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/)

### [MotherDuck for Business Analytics: GDPR, SOC 2 Type II, Tiered Support, and New Plan Offerings](https://motherduck.com/blog/introducing-motherduck-for-business-analytics)

Introducing new features designed to better support businesses looking for their first data warehouse, including SOC 2 Type II and GDPR compliance, tiered support, read scaling, and a new Business Plan.

[![How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFabi_blog_023f05dd0e.png&w=3840&q=75)](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/)

[2025/02/12 - Marc Dupuis](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/)

### [How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis)

Interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai

[View all](https://motherduck.com/blog/)

Authorization Response