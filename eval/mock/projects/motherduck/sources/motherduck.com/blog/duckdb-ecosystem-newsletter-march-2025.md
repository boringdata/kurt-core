---
title: duckdb-ecosystem-newsletter-march-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-march-2025
indexed_at: '2025-11-25T19:57:42.562823'
content_hash: 6441541188c73c38
has_code_examples: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# DuckDB Ecosystem: March 2025

2025/03/07 - 8 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

Hello. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB, delivered straight to your inbox.

In this March issue, I gathered 10 links highlighting the updates and news from the ecosystem of DuckDB. This time, we have a gsheet extension that reads and writes data to GSheets, as well as Duckberg reading from Iceberg tables. We explore zero-cost data stacks that you can build for no cost or use DuckDB distributed.

If you have feedback, news, or any insights, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1690556744956.jpeg&w=3840&q=75)

### Runji Wang

Runji Wang from Beijing, China, enjoys developing low-level systems using Rust, including but not limited to operating systems, storage systems, database systems, and stream processing systems. Visit his GitHub for more details: [GitHub](https://github.com/wangrunji0408).

He recently contributed to Smallpond through DeepSeek, a lightweight framework for distributing compute with DuckDB (more on that below!).

Thanks for your contribution, and welcome to the flock!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [Announcing DuckDB 1.2.0](https://duckdb.org/2025/02/05/announcing-duckdb-120)

**TL;DR:** DuckDB 1.2.0 is out for a couple of weeks and introduced significant features, optimizations, and compatibility improvements, enhancing data handling and performance.

DuckDB version 1.2.0, codenamed “Histrionicus,” presents a suite of technical enhancements, including new features like ALTER TABLE ... ADD PRIMARY KEY, support for Latin-1 and UTF-16 encodings in CSVs, multi-byte delimiters, and improved Parquet compression options. The release also addresses breaking changes, such as an updated random function and changes in map indexing behavior. Find the full features in the above link or on [GitHub](https://github.com/duckdb/duckdb/releases/tag/v1.2.0).

Note that DuckDB 1.2.1 was just released yesterday. You can check the full changelog [here](https://github.com/duckdb/duckdb/releases/tag/v1.2.1).

### [Reading and Writing Google Sheets in DuckDB](https://duckdb.org/2025/02/26/google-sheets-community-extension)

**TL;DR:** The GSheets community extension for DuckDB enables seamless reading and writing of Google Sheets, enhancing workflow automation possibilities.

The GSheets extension in DuckDB allows users to securely interact with Google Sheets for both ad-hoc queries and automated workflows. The extension leverages in-browser OAuth for authentication, simplifying the process to just logging into Google, while scheduled tasks can utilize DuckDB Secrets for persistent authentication. The extension supports reading specific sheets and ranges using additional parameters, with the ability to adjust data type inference and manage headers via SQL commands. Example code snippets such as `INSTALL gsheets FROM community;`, `LOAD gsheets;`, and `COPY (FROM range(10)) TO 'https://docs.google.com/spreadsheets/d/...?' (FORMAT gsheet);` illustrate the syntax for installing and using the extension. This integration allows us data practitioners to automate data exports and imports, enhancing productivity and reducing manual data handling efforts.

### [The Zero Cost Stack](https://rasmusnes.com/posts/stock-advisor-stack/)

**TL;DR:** Building a zero-cost data engineering stack with DuckDB and MotherDuck for efficient data storage and analytics.

Rasmus discusses using DuckDB for local development and MotherDuck for production storage, achieving a seamless switch between the two with a simple configuration toggle. By utilizing `INSERT OR REPLACE INTO` for idempotency, the solution maintains only the latest data, ensuring efficient storage use. DuckDB's lightweight compression significantly minimizes disk usage, fitting the entire dataset within MotherDuck's free tier limits. The stack also integrates Go for data extraction and loading, leveraging GitHub Actions for orchestration, running on a public repository with 4-vCPU, 16GiB runners. Streamlit serves as the dashboarding tool, directly querying MotherDuck for real-time analytics. Takeaway: Demonstrates how combining open-source tools and strategic cloud service choices can build a robust data pipeline with no operational cost. Code available on [GitHub](https://github.com/rasnes/stock-advisor).

### [Duckberg: Python package for querying iceberg data through duckdb](https://github.com/slidoapp/duckberg)

**TL;DR:** Duckberg leverages the power of PyIceberg and DuckDB to facilitate efficient querying of large Iceberg datasets using a Python package.

Duckberg combines PyIceberg and DuckDB to provide a Pythonic approach for querying large Iceberg datasets stored on blob storage. The package supports various Iceberg catalog types like REST, SQL, Hive, Glue, and DynamoDB. Key features include listing tables and partitions and executing SQL queries on data lake files that contain the necessary data, thus optimizing query performance. For example, `db.select(sql=query).read_pandas()` retrieves data into a Pandas DataFrame.

### [Try DuckDB for SQL on Pandas](https://youtu.be/8SYQtpSk_OI?si=L74qJTRMuKu0PuQd)

**TL;DR**: This video shows how DuckDB seamlessly integrates SQL querying with Python DataFrames.

Arjan demonstrates how DuckDB provides a unique workflow where developers can easily transition between DataFrames and SQL within a single tool. The 20 minutes video showcases multiple implementation patterns, including executing SQL directly on DataFrames using Python variable references (duckdb.query(df) with special SQL syntax like SELECT \* FROM df), creating in-memory or persistent connections via duckdb.connect(), and explicitly registering DataFrames as tables with connection.register().  He highlights DuckDB's extended SQL capabilities with examples of DESCRIBE, EXPLAIN, and SUMMARIZE commands for analyzing table structure, query execution plans, and statistical summaries. The practical implementation shown is available on [GitHub](https://github.com/ArjanCodes/examples/tree/main/2025/duckdb).

### [Exploring UK Environment Agency data in DuckDB and Rill](https://rmoff.net/2025/02/28/exploring-uk-environment-agency-data-in-duckdb-and-rill/)

**TL;DR:** Showcasing the efficient ingest and analysis of UK Environment Agency data, showcasing the power of DuckDB for rapid prototyping and Rill for visualization.

Robin uses DuckDB to load and transform JSON data from the UK Environment Agency's flood monitoring API. The process involves creating staging tables using the read\_json function in DuckDB, such as `CREATE TABLE readings_stg AS SELECT * FROM read_json('https://environment.data.gov.uk/flood-monitoring/data/readings');`. By unnesting JSON arrays, Robin transforms these into more query-friendly formats, enabling joins across tables like readings, measures, and stations to enrich the data. The article highlights a potential pitfall with the API's default 500-record limit, addressed using query parameters like ?today to fetch fuller datasets, resulting in over 170k readings, adjusting `maximum_object_size` to handle larger JSON files. Robin visualizes it with Rill and comments that it's an interactive dashboard tool with a fast and intuitive setup.

### [DuckDB goes distributed? DeepSeek’s smallpond takes on Big Data](https://mehdio.substack.com/p/duckdb-goes-distributed-deepseeks)

**TL;DR:** DeepSeek's smallpond extends DuckDB's capabilities to distributed computing, offering new possibilities for handling large datasets.

DeepSeek has introduced [smallpond](https://github.com/deepseek-ai/smallpond), a new framework that leverages DuckDB to achieve distributed computing by integrating with the Ray framework. This approach allows DuckDB to process large datasets by distributing the workload across multiple nodes. The framework uses a Directed Acyclic Graph (DAG) execution model, which optimizes operations by deferring computation until necessary. For instance, operations like write\_parquet(), to\_pandas(), or compute() trigger the execution. Each task is executed in its own DuckDB instance using Ray’s parallel execution capabilities, sorting 110.5TiB of data in just over 30 minutes. Practical Guide: Data volume under 10 TB is "likely unnecessary" and potentially "slower than vanilla DuckDB", according to [Mike](https://www.definite.app/blog/smallpond), as well as the complexity of setting up 3FS (DeepSeek's storage layer) which is impractical for most analytics use cases.

### [DuckDB vs. coreutils](https://szarnyasg.org/posts/duckdb-vs-coreutils/)

**TL;DR:** DuckDB performs competitively against UNIX tools in processing large CSV files, particularly when leveraging multi-threading in larger datasets.

In a recent comparison, DuckDB demonstrated its ability to efficiently handle CSV file operations typically managed by UNIX commands like wc -l, particularly when leveraging multi-threading capabilities. Gábor conducted benchmarks using a range of datasets, from 300 MB to 15 GB, showing DuckDB's SQL execution with `SELECT count() FROM read_csv(...)` can outperform traditional tools under certain conditions. For example, on a large Linux server, **DuckDB processed 108 million lines in 2.2 seconds** compared to the single-threaded wc at 3.2 seconds. However, when GNU Parallel was used to multi-thread the wc command, it reduced processing time to 0.5 seconds, surpassing DuckDB. While DuckDB's parallel CSV reader is highly efficient, performance gains can vary based on the environment and toolchain.

### [FastAPI Integration with DuckDB](https://github.com/buremba/duckdb-fastapi/)

**TL;DR:** DuckDB FastAPI enables bidirectional integration between REST APIs and DuckDB queries.

This experimental package offers two key functionalities: (1) Automatically generate REST endpoints from your DuckDB macros with `CREATE MACRO get_sample() AS TABLE SELECT 1 as t` becoming available at /macro/get\_sample; and (2) Query FastAPI endpoints directly from DuckDB using `ATTACH 'http://localhost:8000/.duckdb' AS myapi; SELECT * FROM myapi.get_item('123');`. The integration works in both directions - creating APIs from DuckDB macros and accessing FastAPI endpoints as DuckDB tables - providing a seamless SQL interface to REST services.

### [New DuckDB Newsletter: Learn DuckDB by example](https://learningduckdb.com/newsletters/welcome-to-learning-duckdb/)

**TL;DR:** New Newsletter "Learning DuckDB by example". The #1 edition highlights recent developments and practical SQL tips for enhancing analytical database performance, showcasing queries with [SQL Workbench](https://sql-workbench.com/) (Online Data Analysis & Data Visualizations).

The newsletter focuses on four main categories: SQL Tips & Tricks, which includes a list of useful SQL queries and their explanations. Tobias also shares DuckDB community news and interesting articles/resources. Check it out at [Learning DuckDB](https://learningduckdb.com/).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Panel: Scaling DuckDB to TBs and PBs with Smallpond, MotherDuck and homegrown solutions](https://lu.ma/5946jam3)

**Tuesday, March 11 10:30 EST - Online**

​DeepSeek's smallpond has taken the data world by storm with its distributed DuckDB capabilities and impressive 110TB benchmarks. But what are your real options for scaling DuckDB today?

​Join our expert panel featuring Jordan Tigani (CEO, MotherDuck), Jake Thomas (Data Foundations, Okta), and Mehdi Ouazza (Data Engineer, MotherDuck) as they cut through the hype and discuss scaling strategies from single-node powerhouses to distributed architectures.

### [Build a Real-Time CDC Pipeline with Estuary & MotherDuck](https://lu.ma/5789p0ru)

**Thursday, March 27 9AM PST - Online**

​Want to seamlessly move data from your transactional database to a fast, serverless analytics engine?

​Join MotherDuck and Estuary for a live webinar where we’ll show you how to build a real-time Change Data Capture (CDC) pipeline.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-march-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-march-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-march-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-march-2025/#upcoming-events)

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

[![DuckDB, MotherDuck, and Estuary: A Match Made for Your Analytics Architecture](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FEstuary_blog_4b9b0c4ce0.png&w=3840&q=75)](https://motherduck.com/blog/estuary-streaming-cdc-replication/)

[2025/03/06 - Daniel Palma, Emily Lucek](https://motherduck.com/blog/estuary-streaming-cdc-replication/)

### [DuckDB, MotherDuck, and Estuary: A Match Made for Your Analytics Architecture](https://motherduck.com/blog/estuary-streaming-cdc-replication)

Stream data to MotherDuck with Estuary

[![Using MotherDuck at MotherDuck: Loading Data from Postgres with DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsocial_md_at_md_8925335f69.png&w=3840&q=75)](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/)

[2025/03/07 - Jacob Matson, Andrew Witten](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/)

### [Using MotherDuck at MotherDuck: Loading Data from Postgres with DuckDB](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck)

Duckfooding MotherDuck with the postgres scanner

[View all](https://motherduck.com/blog/)

Authorization Response