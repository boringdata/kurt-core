---
title: 15-companies-duckdb-in-prod
content_type: blog
source_url: https://motherduck.com/blog/15-companies-duckdb-in-prod
indexed_at: '2025-11-25T19:57:06.637080'
content_hash: 6f18cdaab30ea909
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# 15+ Companies Using DuckDB in Production: A Comprehensive Guide

2024/11/12 - 24 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

From Fortune 500 companies processing trillions of security records to innovative startups building interactive data tools, DuckDB is revolutionizing how organizations handle analytical workloads. Building on our exploration of DuckDB's core capabilities in [Part 1](https://motherduck.com/blog/duckdb-enterprise-5-key-categories/), this guide showcases production implementations and promising experimental applications across five key categories.

![img0](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FOverview_duckdb_in_prod_2_346cb14512.png&w=3840&q=75)

Each example demonstrates practical implementations, gained performance, and architectural decisions that drive business value. While some cases are included for inspiration and aren't yet production-ready, every implementation offers valuable insights whether you're looking to adopt DuckDB in your production stack or exploring possibilities for your next project.

Quick Navigation Guide

To help you navigate the long article, use this guide to find examples and use cases most relevant to you.


**🌐 [Zero-Copy](https://motherduck.com/blog/15-companies-duckdb-in-prod/#zero-copy-virtualized-sql-connector)**

- Spare Cores: Cloud Infrastructure Price Analysis
- Hugging Face: 150k+ Dataset Access
- Watershed: Enterprise Data Lake Migration
- Ibis & PRQL: Framework Integration

**🚀 [Lightweight Compute](https://motherduck.com/blog/15-companies-duckdb-in-prod/#lightweight-compute-single-node-compute)**

- MDS in a Box: Complete Data Stack
- NSW Education: Multi-Tool Integration
- Datadex: Local-First Data Platform
- GoodData: Concurrent User Performance

**⚡ [Pipeline Processing](https://motherduck.com/blog/15-companies-duckdb-in-prod/#pipeline-high-performance-data-processing)**

- FinQore (formerly SaaSWorks): 8hr → 8min Pipeline
- dlt: ELT Pipeline Integration

**🖥️ [Interactive Data Apps](https://motherduck.com/blog/15-companies-duckdb-in-prod/#embedded-interactive-data-apps)**

- Evidence: Universal SQL Engine
- Rill & Mode: Visual Analytics Platform
- Hex: 5-10x Faster Notebook Analytics
- DuckDB-NSQL: Text-to-SQL Model

**🔒 [Enterprise Security](https://motherduck.com/blog/15-companies-duckdb-in-prod/#secure-enterprise-data-handling)**- Okta: 7.5T Records Processing
- DuckLake: Unity Catalog Integration
- QuackScience: On-Demand OLAP Server
- Atlan: Replacing Apache Spark by DuckDB

## Zero-Copy: Virtualized SQL Connector

The first one may be the most powerful category. DuckDB's capability for handling zero-copy data sharing and virtualizing queries.

### Direct SQL Access to External Data Sources

This chapter contains three different direct access examples.

#### SQL-Based API Integration

The easiest zero-copy approach is to **query an API** directly with SQL. For example, the below is reading GitHub stars for DuckDB from GitHub API:

```sh
Copy code

❯ duckdb
v1.1.1 af39bd0dcf
Enter ".help" for usage hints.
Connected to a transient in-memory database.
Use ".open FILENAME" to reopen on a persistent database.
D SELECT stargazers_count
    FROM read_json('https://api.github.com/repos/duckdb/duckdb');
┌──────────────────┐
│ stargazers_count │
│      int64       │
├──────────────────┤
│            23620 │
└──────────────────┘
```

Companies have built businesses using these features. For example, [Spare Cores](https://sparecores.com/), a three-person startup, built a cloud infrastructure price comparison service: one that compares 200,000+ different server prices on AWS, GCP, Azure, and Hetzner and benchmarks them. They use DuckDB to [query these files](https://x.com/GergelyOrosz/status/1848321611918672077) from public APIs.

#### AI Dataset Access with Hugging Face Integration (`hf://`)

DuckDB now [offers](https://duckdb.org/2024/05/29/access-150k-plus-datasets-from-hugging-face-with-duckdb.html) direct access to over 150,000 AI datasets hosted on Hugging Face through the `hf://` protocol. This integration allows users to query datasets using simple SQL syntax like `SELECT * FROM 'hf://datasets/username/dataset/path'`, with support for various formats, including CSV, JSONL, and Parquet files when working with data.

Users can configure authentication using DuckDB's Secrets Manager with their Hugging Face token for secured access to private datasets. The protocol also supports versioning through branch specifications (e.g., `@branch_name`) and glob patterns for querying multiple files simultaneously, making it an efficient tool for AI researchers and developers working with large-scale machine learning datasets.

### Data Lake Solutions

A very popular use case is data lake solutions with DuckDB; here, we look at two different ways of doing so.

#### Enterprise Data Lake Migration: Watershed Case Study

Watershed's [implementation](https://youtu.be/DOkzlDp00vo?si=eecJT6auK5fndxhV) of leveraging DuckDB's lightweight yet powerful database for production workloads. Their scale is significant, with 12% of customers having datasets exceeding 1 million rows and their largest customer dataset reaching 17 million rows (approximately 750MB in Parquet format). After facing challenges with PostgreSQL's maintenance, migrations, and query performance at scale, they implemented DuckDB as their solution for carbon footprint analytics.

Their architecture works as follows: The Parquet files are stored on GCS, users request analytics, the server translates requests into SQL queries, and DuckDB executes queries as the compute layer. The performance gained, and optimization included implementing byte caching to address initial slow query performance with approximately **10x faster performance**. Essentially, they now successfully handle the 75k daily queries on an enterprise scale, eliminating the need for complete query caching strategies.

Beyond their primary analytics use case, Watershed also utilizes DuckDB for data pipeline operations, including converting activity data into carbon footprint data, and as an internal tool for querying Parquet files, benefiting from recent improvements in write speed performance.

#### Building Data Lake from Scratch

There are some excellent write-ups on how to build a data lake fully on DuckDB. With its virtualization layer, you can directly query all your files on S3. It runs anywhere; no SaaS is required.

It's fast with its feature-rich capabilities, matching many typical data warehouses in its feature set. It can run locally, so your tests can use the same engine as production. It plays nicely with Python and has many built-in features and extensions. Dagster wrote a great [article](https://dagster.io/blog/duckdb-data-lake) titled "What would it take to replace our cloud data warehouses or data lakes with DuckDB?"

DuckDB's ability to efficiently handle Parquet files on S3 makes it particularly powerful for data lake architectures. It supports advanced features like compression, predicate pushdown, and HTTP RANGE reads - meaning it only scans the parts of files it needs. With its deep SQL/Pandas integration and ability to efficiently access remote datasets, DuckDB offers a refreshingly simple yet powerful approach to building data lakes. Modern computers are powerful enough that many organizations can effectively run their analytics workloads on a single machine, making DuckDB an attractive option for those seeking a more straightforward, more maintainable data stack without sacrificing performance or features. See also the update with [MotherDuck](https://dagster.io/blog/poor-mans-datalake-motherduck), which is making collaboration easier.

Mimoune built one by [implementing](https://datamonkeysite.com/2023/02/23/implementing-a-poor-mans-lakehouse-in-azure) a Poor Man's Lakehouse in **Azure** using DuckDB as the preparation stage. The implementation demonstrated the performance - processing 60 million rows from a 3GB dataset with 22 complex queries in just 2 minutes 37 seconds on a minimal 1-core VM costing only 8 cents per hour. This shows DuckDB's potential as a cost-effective solution for organizations with moderate data volumes. It offers an alternative to more expensive big data solutions when they might be overkill for the actual workload.

### Framework Integration with Ibis and PRQL

There are exciting extensions to DuckDB which extensively integrate the data ecosystem. For example:

- [Ibis](https://github.com/ibis-project/ibis): The portable Python dataframe library
- [PRQL](https://github.com/PRQL/prql) with the [DuckDK Extension](https://github.com/ywelsch/duckdb-prql): A modern language for transforming data.

These allow writing transformations in Ibis or PRQL and executing them with DuckDB or any other compute supported by the framework. The advantage here is that you have generalist, declarative language to define transformations but can still use DuckDB's power for the execution part. Besides that, you could also easily switch to Druid, ClickHouse, or others with these libraries.

For example, Gil Forsyth [mentions](https://www.youtube.com/watch?v=cCHME7eXAhk) processing 1.1 billion rows of PyPI package data using DuckDB through Ibis in about 38 seconds on a laptop, using only about 1GB of RAM and 20 logical cores. Gil notes that even on slower laptops, the query would still be completed successfully due to the low memory usage, which takes longer to execute.

## Lightweight Compute: Single-Node Compute

DuckDB for lightweight, SQL-based analytical tasks in a single-node environment. This has many benefits, sometimes connected with the followed pipeline category, but we focus on local development and testing capabilities as analytical solutions.

### Modern Data Stack Implementation

For example, having an end-to-end data stack based on open-source, also called MDS in a box, is a perfect use-case where DuckDB can be used as light-weight compute, either as a single data store or as computing SQL's on dbt, for example, or querying within the BI tools your S3 or other sources—everything running on a single laptop.

There are great examples of these concepts, including the inception article by Jacob on [Modern Data Stack in a Box](https://duckdb.org/2022/10/12/modern-data-stack-in-a-box.html) with DuckDB, where he uses Meltano, dbt, and Apache Superset besides DuckDB. This runs at [mdsinabox.com](https://mdsinabox.com/).

Another exciting one is by the [New South Wales Department of Education](https://davidgriffiths-data.medium.com/data-stack-in-a-box-new-south-wales-department-of-education-ft-e2bd12840d3e), which features DuckDB, Dagster, dbt, dlt, and Evidence to power their new data portal. Or David's local-first open data platform, where he uses DuckDB to provide a serverless data platform called [Datadex](https://github.com/datonic/datadex). David runs the stack in [production](https://filecoindataportal.xyz/) with MotherDuck and GitHub Actions.

### Local-First Development and Testing

This is a vast real-time production use case. However, it's hard to find examples as it's done in the background. Testing locally, 100 times a day, before going into production can save much money and speed up testing cycles. Spinning up a cluster, running the deployment scrips, and publishing large docker images is unnecessary.

On Reddit, someone [stated](https://www.reddit.com/r/dataengineering/comments/1ao16gb/comment/kpxm4ad/) that for dbt users with BigQuery warehouses, DuckDB enables **efficient local testing** by isolating BigQuery-specific code into ephemeral models and [mocking them in dbt](https://github.com/EqualExperts/dbt-unit-testing/tree/v0.4.12/#different-ways-to-build-mock-values). This approach keeps warehouse-specific code thin and untested while enabling comprehensive testing of core business logic locally. Some developers also use SQLGlot with DuckDB to test BigQuery SQL locally—so-called **unit-testing** without warehouse dependencies.

Someone else [said](https://www.reddit.com/r/dataengineering/comments/1g6ilg0/comment/lsnivvs/) they're using it in combination with Ibis and Snowflake. For tests, they patch the Snowflake connection with a connection to a local DuckDB test database. This works quite well, although you won’t catch all errors. Or quickly query Snowflake tables locally without the Warehouse, with [universql](https://github.com/buremba/universql).

Another use case is **data diffs**, which [quickly compare datasets](https://www.youtube.com/watch?v=-k5p_mFMyK4) using SQL queries. DuckDB has one of the fastest Parquet/CSV readers, integration with Postgres and others through plugins, and easy-to-work-with CSV, all of which make It super **developer-friendly** and suited for fast iterative development and testing.

### Composable Python Query Relations

An intriguing feature or use case I found with Python integration is its relational API. When writing queries in Python, DuckDB returns a "relation" object (an abstract representation of the query) rather than immediately materializing the total result. This relation can be stored in a variable and used in subsequent queries, making SQL more **composable**. The query planner optimizes the final composite relation, allowing for better performance.

Ned [mentions](https://youtu.be/_nA3uDx1rlg?si=JJNkEf0YCX1WLgCx), "You get this lazy representation of your query that will until you ask it fully to materialize or just peek at the first bit, it won't evaluate anything." Viewing in a notebook shows only the first 10,000 records by default for preview purposes.

### Large-Scale Configuration Management

Reading large config files on the fly is another small but powerful use case. Chris [used](https://x.com/horizonchasers/status/1848336625073311861) a C# desktop app that collects large amounts of configuration and performance data. They load it into DuckDB and then send it to their cloud processing engine for report generation. They are impressed with it and are looking at other use cases.

[Matthew](https://www.linkedin.com/feed/update/urn:li:activity:7254066800416501760?commentUrn=urn%3Ali%3Acomment%3A%28activity%3A7254066800416501760%2C7254240994085285889%29) does similar with handling large result sets and querying everything from files to iceberg tables at Coginiti.

### Multi-User Performance Management

GoodData's [comprehensive](https://medium.com/gooddata-developers/is-motherduck-producktion-ready-a3a0347715c5) evaluation of DuckDB and MotherDuck for production use offers another compelling example of DuckDB's enterprise readiness. Through rigorous testing of over 700 analytics-focused test cases developed over 15 years, GoodData found MotherDuck outperforming Snowflake and PostgreSQL in performance tests, particularly for analytical workloads with relatively small data volumes and parallel query execution.

However, GoodData's testing also revealed essential considerations for production deployment, including non-blocking limitations with ISO date arithmetic, a lack of query cancellation, and one blocker with downloading runtime extensions every time, some of which are resolved by now. Despite limitations, they concluded that MotherDuck is production-ready for analytics use cases, particularly praising its **efficiency in handling concurrent users and analytical queries**.

## Pipeline: High-Performance Data Processing

The category focuses on DuckDB's use in data processing pipelines and ETL workflows.

### Enterprise ETL Optimization: FinQore (formerly SaaSWorks) Case Study

At [FinQore (formerly SaaSWorks)](https://motherduck.com/case-studies/saasworks/), implementing DuckDB transformed their data pipeline performance from eight hours to just eight minutes, with the potential for further optimization to seconds. Their production system processes complex financial data from multiple source systems, a task that traditionally required manual Excel (btw [Excels Never Dies](https://www.notboring.co/p/excel-never-dies)) reconciliation even for sophisticated businesses. They are replacing their Postgres datasets with DuckDB, particularly for front-end operations, due to DuckDB's fast performance for analytical workloads.

The [medallion showcase example](https://practicaldataengineering.substack.com/p/building-data-pipeline-using-duckdb) with (Bronze → Silver → Gold) shows a data pipeline's impressive performance handling complex transformation, processing nested JSON, and transforming nearly 6 million records across 24 Parquet files in under a minute. The architecture leverages DuckDB's in-memory processing capabilities while maintaining data integrity through carefully designed partitioning schemes and atomic writes.

### ELT Pipeline Integration with dlt

Extending capabilities and speed of a data pipeline initial load. Exporting and importing data from Postgres to Postgres can be non-straightforward, especially if you need to track schema changes, delta load, etc.

Therefore, using a tool made for ELT, something like dlt, is better. But what if the initial load from Postgres to Postgres must be improved? Changing the export as parquet and import to Postgres with an in-memory DuckDB speeded up the process order of magnitude. The parquet has been written but imported via `ATTACH` cmd in DuckDB, which imports parquet files into Postgres directly. We ended up using [this in production](https://dlthub.com/docs/examples/postgres_to_postgres) when I was at Bedag.

### Cost-Efficient Pipeline Design

Cost-efficient data pipelines have mainly three parts: optimizing data processing, storage, and workload management. According to [Joseph](https://www.startdataengineering.com/post/cost-effective-pipelines/), DuckDB excels in these areas, offering a powerful in-memory processing engine that can efficiently handle datasets up to 100+GB on a single machine. When combined with ephemeral VMs, DuckDB enables significantly **reduced** data processing costs.

Its ability to leverage the full power of a VM's resources and fast read and write operations through C++ extensions optimizes data pipelines' processing and storage aspects. Furthermore, DuckDB contributes to **efficient workload** management by **simplifying** the development, testing, and debugging process. Its integration with Python creates an accessible work environment, leading to faster development cycles and easier maintenance. Streamlines ETL operations, enabling organizations to process large volumes of data cost-effectively without the overhead of managing distributed systems.

## Embedded: Interactive Data Apps

A newer use case that DuckDB allows is an embedded engine in various products and platforms. Below are examples of how it can be embedded in an interactive data app.

### Interactive Analytics Platforms

Here are examples of embedding DuckDB into dashboards, notebooks, or use cases integrated with WebAssembly.

#### Dashboard Analytics

Most of you have seen DuckDB embedded into a BI tool. This allows us to query data interactively on the server. Instead of transferring data to the server, DuckDB brings the data to the app, and most filtering can happen directly within the app on the server. We can avoid latency paging data in most use cases. Production use cases that illustrate strengths are **Rill, Evidence, Mode, Hex, Mosaic, and Count** in this category.

Evidence built its query engine [Universal SQL](https://evidence.dev/blog/why-we-built-usql) with DuckDB’s WebAssembly, which empowers interactivity, supports multiple data sources, and delivers extraordinary performance.

On the other hand, Rill [chose](https://www.rilldata.com/blog/why-we-built-rill-with-duckdb) DuckDB as its data connector because of its uniquely high performance for analytics queries. They chose it over SQLite, a more mature DB, because its internal benchmarking shows that DuckDB outperforms SQLite on various analytics queries by order of magnitude (ranging from 3x to 30x).

Mode [switched](https://mode.com/blog/how-we-switched-in-memory-data-engine-to-duck-db-to-boost-visual-data-exploration-speed) its engine to DuckDB to boost visual data exploration speed. Mosaic, a simple, fast in-browser analytics tool, uses MotherDuck, which enables users to [offload](https://motherduck.com/case-studies/dominik-moritz/) computation to a server when needed. Mosaic was able to build a [Mosaic demo](https://github.com/domoritz/mosaic-motherduck), which allowed Dominik to explore 18 million data points from the [Gaia dataset](https://gea.esac.esa.int/archive/) in the browser. There was no need to download the data locally.

Count also [ships](https://docs.count.co/querying-data/local-cells) with a local database built on DuckDB. If you choose to set a cell's data source to "local," the queries for that cell will be run in your browser.

#### Notebook-based Analytics

Another embedded use case is [Hex](https://hex.tech/), a notebook-based analytical solution like Jupyter Notebook.

They [recently](https://hex.tech/blog/lazy-dataframes/) migrated their cell backends to a new DuckDB-based architecture that directly queries Arrow data stored remotely in S3 instead of materializing data frames into local memory. Performance improvements are variable based on project complexity, but we’ve seen **5-10x speedups** in execution times for specific project types.

Under the hood, they used DuckDB in the kernel, running queries on top of Pandas data frames, allowing for SQL queries where necessary. They use the trio's speed: **DuckDB, Arrow, and S3**. In addition to speed improvements, there are also convenience improvements (limitations to Pandas format or even Python runtime).

[Observable Framework](https://observablehq.com/) uses DuckDB for its [notebooks](https://observablehq.com/documentation/notebooks/) on the Observable data visualization platform.

#### WebAssembly Implementations

[WebAssembly (Wasm)](https://webassembly.org/) is an open standard that enables the execution of binary code on the web. This format allows developers to leverage the performance of languages like C, C++, and Rust in web development.

Take **Figma**, for example. In 2017, they brought Photoshop into the browser and used it to [reduce](https://www.figma.com/blog/webassembly-cut-figmas-load-time-by-3x/) the load by 3x. Use cases like Count and others use Wasm, too, have already been mentioned

Reading the database schema of the parquet is not optimal, as you need to download the file and read it in a notebook or something similar. Christopher [shows](https://youtu.be/eqyIiWMbXv4?si=Pntyg-hPefZb_Z25) a demo in BigQuery of how you can do it entirely inside the browser with a mouse hover

Another exciting is the government of South Australia use of [duckdb-wasm](https://github.com/duckdb/duckdb-wasm) for its [climate change dashboard](https://www.environment.sa.gov.au/climate-viewer/).

### Developer Tools

Besides dashboards and notebooks, here are examples of DuckDB integrated into our dev tools and databases.

#### SQL Workbench Integration

Besides real-time analytical dashboards, we also have IDE, workbench-like analytics built on top of DuckDB.

MotherDucks web UI is such, enabling notebook, SQL IDE, database, and interactive results explorer. The notebook, for example, supports **instant-feedback SQL editing**, aka "query-as-you-type," with duckdb-wasm for local-first caching and MotherDuck as the backend to enable keystroke-fast resultset previews.

[SQL Workbench](https://sql-workbench.com/) uses the same DuckDB library for running queries on local or remote data, being able to show data as tables or visually as graphs, and sharing queries via URLs.

There are more like that, such as [Sekuel Playground](https://sekuel.com/playground/), [CSVFiddle](https://csvfiddle.io/),  [QuackDB](https://quackdb.com/), and [WhatTheDuck](https://whattheduck.incentius.com/).

#### Command-Line Solutions

Not SQL IDEs, but online shells or cmd lines exist, too. For example, [Online DuckDB Shell](https://shell.duckdb.org/) is an online DuckDB shell powered by WebAssembly. [Codapi](https://codapi.org/duckdb/) embeds executable code snippets directly into your product documentation, online course, or blog post.

#### Database Engine Integration

Besides DuckDB being embedded in the browser, bringing the data to the data app, we also have [pg\_duckdb](https://github.com/duckdb/pg_duckdb), which is a Postgres extension that embeds DuckDB's columnar-vectorized analytics engine and features into Postgres. Recommended to build high-performance analytics and data-intensive applications. Essentially, having an [HTAP Database](https://en.wikipedia.org/wiki/Hybrid_transactional/analytical_processing) combines OLTP with OLAP with no need for ETL. This is possible because of the light single binary that DuckDB comes with.

### AI Integration Solutions

Lastly, in this category, we can also embed AI with DuckDB.

With the [duckdb-nsql](https://ollama.com/library/duckdb-nsql), a 7B parameter **text-to-SQL** model that is lightweight and enables DucKDB SQL assistance features at lower latency, primarily focusing on analytical queries / SELECT statements. Check out [how to use](https://tobilg.com/chat-with-a-duck) Ollama before discussing SQL Workbench.

Or use the [integrated `prompt()` function](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/) within SQL, a new feature that MotherDuck's IDE provides. There are many more Retrieval-Augmented Generation (RAG use cases people mentioned, e.g. for its cosine similarity function and to store doc embeddings.

TIP : Check many more examples on the Awesome DuckDB List

The list features a plethora of tools powered by DuckDB, such as resources, client APIs, web clients, libraries, SQL clients and IDE, projects, and integrations. Check out the [Awesome DuckDB List](https://github.com/davidgasquez/awesome-duckdb#libraries-powered-by-duckdb).


## Secure: Enterprise Data Handling

The last category, enterprise secure-level data handling, is growing rapidly and is critically important. These examples demonstrate DuckDB's secure data processing capabilities. This is a relatively new way of using DuckDB, but it has lots of potential, as data can live within an app if needed.

### Security Platform Implementation: Okta Case Study

Okta [manages](https://youtu.be/TrmJilG4GXk?si=w-dwBHDW4LZnL6B4) a security-focused data platform to efficiently manage high-volume secure data. The focus was processing complex data logs from multiple sources (e.g., AWS CloudTrail, VPC flow logs) for **security monitoring, anomaly detection**, and downstream workflow triggering. DuckDB played a crucial role in optimizing data processing costs and performance.

DuckDB proved to be an ideal solution for **scalable, cost-efficient embedded OLAP** in security-heavy workloads. Its ability to handle high data volumes, integrate seamlessly into cloud workflows (via Lambda and S3), and reduce reliance on expensive cloud warehouses (like Snowflake) makes it a powerful tool for modern data platforms, especially in environments where dynamic data processing is critical.
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg1_dfc8e8559e.png&w=3840&q=75)

This case highlights how DuckDB can effectively process and optimize security data workloads upstream of traditional data warehouses, reducing costs while maintaining high performance. Okta handles sensitive data and uses DuckDB to process sensitive security data.

In six months, their defensive cyber operations team processed 7.5 trillion records across 130 million files using thousands of concurrent DuckDB instances, handling data spikes from 1.5 TB to 50 TB per day without infrastructure changes. This approach dramatically reduced their data processing costs from $2,000/day with Snowflake while maintaining system robustness and security.

### Data Governance Integration: DuckLake with Unity Catalog

Integrating the data governance unity catalog with DuckDB is a good practice for getting to an enterprise data platform and handling data more securely. Xebia documented their [journey](https://xebia.com/blog/ducklake-a-journey-to-integrate-duckdb-with-unity-catalog/) to use synergies between DuckDB and the OSS Unity Catalog.

![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg2_2cdc2a88f4.png&w=3840&q=75)

They called it the "DuckLake". Unlike the data lakes we will discuss in the first chapter of zero-copy, this approach focuses on metadata and integrating the data stack.

DuckLake combines data governance capabilities and DuckDB's analytical power through Unity Catalog integration. The solution provides centralized metadata management and will soon support enhanced security features (with RBAC coming in Unity Catalog 0.2.0). While currently limited to read-only operations due to delta-kernel-rs dependencies, workarounds exist through dbt-duckdb and custom tooling for write operations.

The DuckLake approach offers a practical path forward for enterprises seeking to maintain control over their data assets while leveraging DuckDB's performance. The integration handles everything from schema definitions to access patterns, creating a robust foundation for secure data operations—even as the ecosystem matures with upcoming features and improvements.

### On-Demand Server Deployment

Another security improvement is not only bringing the database to the app, but the whole server. With the [HTTP API Server Extension](https://github.com/quackscience/duckdb-extension-httpserver), we can quickly spawn a server as part of our analytics environment when needed and shut down when finished—an HTTP OLAP server on-demand.

Other benefits include avoiding requiring Docker or a long-running process, which minimizes setup difficulty. Or it can replace a complex Spark cluster if data works for DuckDB but still uses the unique [Spark dataframe API](https://duckdb.org/docs/api/python/spark_api). For example, Atlan [replaced](https://youtu.be/rveaJWvD_zk?si=A9FlRGlMP4gSkuQp) their Spark with DuckDB, orchestrated with ArgoCD, and improved performance to ~2.3x faster than PySpark at the pod level.

## How to Implement DuckDB in Your Enterprise

After reviewing this extensive guide on production and innovative use cases, how can you start with DuckDB?

[Check the installation instructions](https://motherduck.com/docs/getting-started/) for various clients (CLI, Python, R, etc.), or visit [MotherDuck](https://app.motherduck.com/) to get started instantly with the UI. The best way to understand is through hands-on experience. Import a CSV, wrangle some data, execute some queries, visualize a large local data set, or read distributed files from S3. Use a current bottleneck at work, where speed is insufficient, and try DuckDB.

In most cases, you will be surprised at how easy and well-thought-through it is and how it simplifies the overall data architecture. If you need to scale up or mitigate high peaks, look at MotherDuck, which offers Dual Query Execution.

Let's examine how MotherDuck implements these features.

### Cloud Integration: MotherDuck's Advantages

MotherDuck wrote the paper about [dual execution](https://motherduck.com/blog/cidr-paper-hybrid-query-processing-motherduck/). Its backbone is the differential storage and its powerful UI. Let's explore them below.

#### Hybrid Query Processing Architecture

Extensive research in columnar systems, including vectorized compute, decoupled storage, file formats, query plans, and join optimization, has led to **[differential storage](https://motherduck.com/blog/differential-storage-building-block-for-data-warehouse/)**.

At its core, the differential storage operates as a [FUSE-based system](https://en.wikipedia.org/wiki/Filesystem_in_Userspace) that represents database states through sequences of immutable "layers", each capturing changes between checkpoints. This design enables zero-copy database cloning, concurrent reads across hosts, and git-style operations for database management. The system combines fast EFS writes with S3 storage for performance and cost-effectiveness, enabling [1-5-Tier Architecture](https://motherduck.com/product/app-developers/) for embedded interactive analytics.

Moreover, MotherDuck enables the multiplayer experience of having a single file without the need for tedious synchronization with your team. The data can be shared with a single link with [MotherDuck shares](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/create-share/).

#### Interactive Development Environment

MotherDuck provides a comprehensive development environment that combines several powerful features. **[WebAssembly (WASM) SDK](https://motherduck.com/product/app-developers/#webassembly-wasm-sdk)** enables running DuckDB directly in browsers while maintaining cloud integration, allowing developers to create fast data experiences by balancing client and server-side processing.

Through **Dual Query Execution**, applications can leverage local compute and cloud resources to optimize performance and costs. The platform includes a **Notebook-like UI** that provides an intuitive interface for browsing data catalogs, developing SQL with auto-complete and FixIt features, and exploring results interactively through Column Explorer.

Built on a **Strong DuckDB ecosystem**, it seamlessly integrates with over 25+ modern data stack tools for import, orchestration, and business intelligence, making it a versatile platform for building data-driven applications.

If you're curious, you can start using [MotherDuck for free](https://motherduck.com/get-started/).

## Future Outlook: The Evolution of DuckDB

As we've seen, DuckDB has emerged as a data processing powerhouse, with real-world implementations demonstrating its impact across five key categories. From Fortune 500 companies to innovative startups, organizations are leveraging DuckDB's capabilities: Watershed achieved 10x performance gains in carbon analytics through zero-copy SQL, FinQore (formerly SaaSWorks) reduced pipeline processing from 8 hours to 8 minutes, and Okta efficiently processed 7.5 trillion security records at the enterprise level. Hex's 5-10x speedups in notebook execution and GoodData's superior concurrent user performance further validate DuckDB's versatility across interactive applications and lightweight compute scenarios.

With the ecosystem's rapid evolution, we also see **future trends** that will likely continue, like browser-based analytics through WebAssembly, AI integration via implementations like Hugging Face's dataset access, and hybrid architectures. These advancements also showcase and explain the diverse use of DuckDB beyond traditional analytics into new territories compared to the common database system.

As computing power grows and local processing capabilities expand, DuckDB's **simplicity, performance, and versatility** position it uniquely in the data landscape. Whether embedding in interactive applications, powering ETL workflows, or handling enterprise-scale security data, DuckDB has proven its ability to deliver substantial performance gains while significantly reducing operational complexity and costs. I'm personally very curious about where this road will lead, but I'm optimistic that it will make the lives of many engineers out there easier.

Big Thanks for all the Feedback ❤️

Thanks to all who gave [invaluable](https://x.com/sspaeti/status/1848299384783491507) [feedback](https://www.linkedin.com/posts/sspaeti_im-writing-about-duckdb-production-use-cases-activity-7254066800416501760-kxKi?utm_source=share&utm_medium=member_desktop) and pointers to where DuckDB is used.


### TABLE OF CONTENTS

[Zero-Copy: Virtualized SQL Connector](https://motherduck.com/blog/15-companies-duckdb-in-prod/#zero-copy-virtualized-sql-connector)

[Lightweight Compute: Single-Node Compute](https://motherduck.com/blog/15-companies-duckdb-in-prod/#lightweight-compute-single-node-compute)

[Pipeline: High-Performance Data Processing](https://motherduck.com/blog/15-companies-duckdb-in-prod/#pipeline-high-performance-data-processing)

[Embedded: Interactive Data Apps](https://motherduck.com/blog/15-companies-duckdb-in-prod/#embedded-interactive-data-apps)

[Secure: Enterprise Data Handling](https://motherduck.com/blog/15-companies-duckdb-in-prod/#secure-enterprise-data-handling)

[How to Implement DuckDB in Your Enterprise](https://motherduck.com/blog/15-companies-duckdb-in-prod/#how-to-implement-duckdb-in-your-enterprise)

[Future Outlook: The Evolution of DuckDB](https://motherduck.com/blog/15-companies-duckdb-in-prod/#future-outlook-the-evolution-of-duckdb)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: November 2024](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fseptember_2024_23312061de.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2024/)

[2024/11/04 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2024/)

### [This Month in the DuckDB Ecosystem: November 2024](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2024)

DuckDB Monthly: Unity catalog, drugDB and more!

[![Quacking at the Edge: DuckDB on Raspberry Pi](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumb_fd0ddd2f0b.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-on-edge-raspberry-pi/)

[2024/11/07 - Jordan Tigani](https://motherduck.com/blog/duckdb-on-edge-raspberry-pi/)

### [Quacking at the Edge: DuckDB on Raspberry Pi](https://motherduck.com/blog/duckdb-on-edge-raspberry-pi)

Using MotherDuck’s Dual Query execution on a Raspberry Pi to play a quack sound when users sign up for our service.

[View all](https://motherduck.com/blog/)

Authorization Response