---
title: duckdb-ecosystem-newsletter-may-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-may-2025
indexed_at: '2025-11-25T19:57:59.322574'
content_hash: d028906925fe72ec
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# DuckDB Ecosystem: May 2025

2025/05/08 - 7 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

I hope you're doing well. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB, delivered straight to your inbox.

In this May issue, I gathered 10 links highlighting updates and news from DuckDB's ecosystem. This time, we have exciting innovations like SQL-based 3D graphics, Reddit discussions around DuckDB, geospatial capabilities, Metabase integration, and performance optimizations for working with JSON and Parquet files. Check out this edition below.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1625133792218.jpeg&w=3840&q=75)

### Robin Moffatt

[Robin](https://www.linkedin.com/in/robinmoffatt/) is a technologist whose career spans from COBOL to Kafka!

Beyond the code, he’s a skilled communicator and prolific tech content creator, blogging since 2009. Recently, Robin has published several insightful posts exploring DuckDB, including:

[\- Building a data pipeline with DuckDB](https://rmoff.net/2025/03/20/building-a-data-pipeline-with-duckdb/)

[\- Exploring UK Environment Agency data in DuckDB and Rill](https://rmoff.net/2025/02/28/exploring-uk-environment-agency-data-in-duckdb-and-rill/)

You can find more of Robin’s writing at [rmoff.net](https://rmoff.net/).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [Metabase DuckDB Driver shipped as 3rd party plugin](https://github.com/motherduckdb/metabase_duckdb_driver)

**TL;DR:** The metabase\_duckdb\_driver plugin enables Metabase (BI tool) to use DuckDB as a data source, allowing direct SQL queries on Parquet files and in-memory databases.

The open-source metabase\_duckdb\_driver plugin allows Metabase to connect to DuckDB databases, supporting both file-based and in-memory (:memory:) modes.  A key feature is the ability to directly query Parquet files without loading data into a database. For example, a query can be executed directly from the Metabase SQL editor. The driver also supports using DuckDB in-memory, which can help process data without persisting.

### [Normalizing Repeated JSON Fields in FDA Drug Data Using DuckDB](https://justni.com/2025/04/02/normalizing-repeated-json-fields-from-fda-drug-data-using-duckdb/)

**TL;DR:** Normalizing nested JSON fields in the FDA drug event dataset using DuckDB. A practical showcase of increasing significant performance can be achieved by creating lookup tables for repeated values.

Chris encountered performance bottlenecks due to high cardinality nested fields within the FDA's raw JSON data. To address this, he created tables that normalized nested JSON with unique values and IDs, reducing the original query from several minutes to just 0.166 seconds. A practical takeaway: This is a good example of how normalizing high-cardinality JSON fields in DuckDB can substantially improve query performance with indexing and scanning less data, especially when dealing with large, semi-structured datasets.

### [FlockMTL: Beyond Quacking: Deep Integration of Language Models and RAG into DuckDB](https://arxiv.org/pdf/2504.01157)

**TL;DR:** Researchers have developed FlockMTL, an open-source DuckDB extension that deeply integrates language models and retrieval-augmented generation capabilities directly into SQL workflows.

FlockMTL introduces model-driven scalar and aggregate functions that enable SQL queries to perform semantic operations like classification, summarization, and re-ranking using LLMs. The extension introduces two new first-class schema objects — MODEL and PROMPT — alongside traditional TABLE objects, allowing resource independence when updating models or prompts without changing application logic. Find the [GitHub repo](https://github.com/dsg-polymtl/flockmtl) and [DuckDB extension](https://duckdb.org/community_extensions/extensions/flockmtl.html) in these links.

### [Abusing DuckDB-WASM by making SQL draw 3D graphics (Sort Of)](https://www.hey.earth/posts/duckdb-doom)

**TL;DR:** Text-based Doom clone running entirely in DuckDB-WASM, implementing raycasting and game physics through SQL queries at 6-7 FPS in the browser.

Patrick's project uses DuckDB-WASM to manage game state, collision detection, and 3D rendering through SQL queries. The wild part and innovation lie in the render\_3d\_frame SQL VIEW, which employs recursive CTEs for raycasting and perspective correction and uses JavaScript for orchestration and Z-buffer sprite handling. **A practical takeaway:** This demonstrates DuckDB-WASM's potential for unconventional applications beyond traditional data analytics. Find source code on [GitHub](https://github.com/patricktrainer/duckdb-doom).

### [DuckDB is Probably the Most Important Geospatial Software of the Last Decade](https://www.dbreunig.com/2025/05/03/duckdb-is-the-most-impactful-geospatial-software-in-a-decade.html)

**TL;DR:** DuckDB's spatial extension significantly lowers the barrier to entry for geospatial data analysis within SQL.

The Geospatial extension statically bundles standard FOSS GIS packages, including the PROJ database, and offers them across multiple platforms, including WASM, eliminating transitive dependencies (except libc). This allows users to convert between geospatial formats using GDAL and perform transformations via SQL. 📝: Spatial join optimization was recently merged on the dev branch.

### [Instant SQL is here: Speedrun ad-hoc queries as you type](https://motherduck.com/blog/introducing-instant-sql/)

**TL;DR:** MotherDuck introduces Instant SQL, a feature for real-time query result previews as you type, leveraging DuckDB's architecture and query rewriting capabilities.

Instant SQL, available in MotherDuck and the [DuckDB Local UI](https://duckdb.org/docs/stable/extensions/ui.html), speeds up query building and debugging by providing result set previews that update instantly as the SQL is typed. A key feature includes CTE inspection capabilities as a time-saver for debugging complex SQL queries. A central component uses DuckDB's JSON extension to obtain an abstract syntax tree (AST) from SELECT statements via a SQL scalar function, enabling parser-powered features.

An alternative connection method uses the Amazon SageMaker Lakehouse (AWS Glue Data Catalog) Iceberg REST Catalog endpoint: `ATTACH 'account_id:s3tablescatalog/namespace_name' AS (TYPE iceberg, ENDPOINT_TYPE glue);.` The extension also supports Iceberg's schema evolution, allowing users to follow changes in the table's schema.

### [Some serious questions regarding DuckDB on Reddit: r/dataengineering](https://sh.reddit.com/r/dataengineering/comments/1kaq8cq/i_have_some_serious_question_regarding_duckdb)

**TL;DR:** Insights from the data engineering community on a Reddit discussion around DuckDB.

The discussion reveals that DuckDB is **used in production** for tasks like ingesting various file formats, online interactive spatial queries using spatial extension, applying custom logic to arrays with lambdas, and performing repeated joins on smaller datasets. It's also favored for local analysis and for handling poorly formatted CSV files. Some users integrate DuckDB with Ray for distributed chunk processing. This discussion showcases DuckDB's versatility (as [discussed](https://motherduck.com/blog/duckdb-enterprise-5-key-categories/) in an earlier article).

### [Merge Parquet with DuckDB](https://emilsadek.com/blog/merge-parquet-duckdb/)

**TL;DR:** Use DuckDB to efficiently merge multiple Parquet files into one file, optionally performing data transformations during the process.

The article demonstrates how DuckDB can consolidate multiple Parquet files into one. The process involves using DuckDB's SQL interface to read Parquet files via a glob pattern. The read\_parquet function offers parameters like filename = true to add a column indicating the source file for each row and union\_by\_name to handle differing schemas across files. Showcases show data transformations with hashing with md5,  column renaming, and the COPY statement to write the transformed data into a single Parquet file.

### [DuckDB's CSV Reader and the Pollock Robustness Benchmark: Into the CSV Abyss](https://duckdb.org/2025/04/16/duckdb-csv-pollock-benchmark.html)

**TL;DR:** DuckDB's CSV reader achieves top ranking in the [Pollock Benchmark](https://www.vldb.org/pvldb/vol16/p1870-vitagliano.pdf) due to its robustness in handling non-standard CSV files.

DuckDB's CSV parser prioritizes reliability alongside speed and ease of use. The parser's flexibility is demonstrated through options like strict\_mode = false, which allows parsing CSVs with unescaped quotes or inconsistent column counts, and null\_padding = true, which handles missing values.  Setting these options will enable DuckDB to correctly read 99.61% of data from the Pollock Benchmark files. The blog post details how to use DuckDB's CSV reader to handle common CSV errors and achieve a valid result from faulty CSV files.

### [My browser WASM’t prepared for this. Using DuckDB, Apache Arrow and Web Workers in real life](https://motifanalytics.medium.com/my-browser-wasmt-prepared-for-this-using-duckdb-apache-arrow-and-web-workers-in-real-life-e3dd4695623d)

**TL;DR:** Motif Analytics explores using DuckDB WASM, Apache Arrow, and Web Workers for in-browser analytics, highlighting performance trade-offs and schema consistency challenges.

Przemyslaw details the implementation of an in-browser analytics tool leveraging DuckDB WASM for SQL queries, Apache Arrow for data interchange between Web Workers, and Web Workers for parallel processing and highlighting real-world challenges in maintaining schema consistency when using multiple Arrow tables from different workers. It addresses limitations like the 4GB memory limit in Chrome for WASM and potential bugs in the WASM. Takeaway: Despite all of this, DuckDB WASM is currently one of the fastest (if not the fastest) engines for querying fully in-browser.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Getting Started with MotherDuck](https://lu.ma/9xfs8lng)

**Thu, May 08 09:30 PST - Online**

​​​Looking to get started with MotherDuck and DuckDB? Join us for a live session to learn how MotherDuck makes analytics fun, frictionless, and ducking awesome!

### [Stay in Flow with MotherDuck's Instant SQL](https://lu.ma/7lklecbm)

**May 14 09:30 PST - Online**

See how MotherDuck's Instant SQL breaks through traditional development barriers by providing real-time results as you type.

### [ODSC East: Making Big Data Feel Small with DuckDB](https://odsc.com/boston/schedule/)

**May 15 - In-person \[US - San Francisco\]**

Ryan Boyd, co-founder at MotherDuck, will speak at ODSC East. Learn how well an “embedded database” scales! DuckDB is being used in production to process terabytes and petabytes of data.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-may-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-may-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-may-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-may-2025/#upcoming-events)

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

[![Instant SQL is here: Speedrun ad-hoc queries as you type](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fstatic_thumbnail_instant_SQL_3d5144f534.png&w=3840&q=75)](https://motherduck.com/blog/introducing-instant-sql/)

[2025/04/23 - Hamilton Ulmer](https://motherduck.com/blog/introducing-instant-sql/)

### [Instant SQL is here: Speedrun ad-hoc queries as you type](https://motherduck.com/blog/introducing-instant-sql)

Type, see, tweak, repeat! Instant SQL is now in Preview in MotherDuck and the DuckDB Local UI. Bend reality with SQL superpowers to get real-time query results as you type.

[![MotherDuck lands on Tableau Cloud: Live, Fast Analytics Unleashed](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FTableau_Cloud_52bd53b821.png&w=3840&q=75)](https://motherduck.com/blog/tableau-cloud-motherduck/)

[2025/05/06 - Jacob Matson](https://motherduck.com/blog/tableau-cloud-motherduck/)

### [MotherDuck lands on Tableau Cloud: Live, Fast Analytics Unleashed](https://motherduck.com/blog/tableau-cloud-motherduck)

Use MotherDuck to power your Tableau Cloud, Server, and Desktop dashboards.

[View all](https://motherduck.com/blog/)

Authorization Response