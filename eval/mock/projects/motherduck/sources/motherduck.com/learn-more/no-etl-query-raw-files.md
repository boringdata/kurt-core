---
title: 'No-ETL: Query Raw CSV & JSON Files Directly with SQL'
content_type: guide
description: Skip complex ETL. Learn the No-ETL method for startups to query multiple
  raw CSV, JSON, & Parquet files directly with SQL. Get insights in minutes, not months.
published_date: '2025-10-17T00:00:00'
source_url: https://motherduck.com/learn-more/no-etl-query-raw-files
indexed_at: '2025-11-25T20:37:09.260086'
content_hash: 317312307e45ea1c
has_step_by_step: true
has_narrative: true
---

# The No-ETL Playbook: How to Query Raw CSV & JSON Files Directly with SQL

For startups and small companies, your most valuable data, like customer sign-ups, sales transactions, and product usage logs, is likely scattered across hundreds of local files like CSVs, Excel spreadsheets, and JSON logs. The conventional wisdom says you need to build a complex and expensive **Extract, Transform, Load (ETL)** pipeline before you can even begin to analyze it. But for a lean team that needs to move fast, this approach is a trap. It’s slow, rigid, and drains precious engineering resources before you’ve asked your first question.

What if you could skip the pipeline and go straight to the insights?

A modern, **"No-ETL"** approach allows you to do just that. Instead of spending months building a complex data infrastructure, you can use simple SQL to query your raw data files directly where they live, on your laptop or in cloud storage. This guide will show you how this lean, serverless method turns fragmented files into a powerful, queryable database in minutes, not months. You will learn why traditional ETL is a bottleneck, how to get immediate answers from your raw files, and how to consolidate thousands of fragmented files into a single, high-performance database, all while unifying data across your local machine and the cloud.

## Why Are Traditional Data Pipelines a Trap for Startups?

For decades, the path from data to decision was a one-way street paved with ETL. This process involves extracting data from various sources, transforming it into a rigid, predefined schema, and loading it into a central data warehouse. While this model can work for large enterprises with stable processes, it creates a "pipeline city" that demands constant maintenance and becomes a major bottleneck for agile startups that need to pivot quickly.

The "No-ETL" philosophy flips this script entirely. Instead of moving all your data to a central processing location, you bring the processing power directly to your data. By pointing SQL at the files you already have, you can eliminate 80-90% of the traditional pipeline steps. This approach, powered by MotherDuck's serverless engine, allows teams to [consolidate data from dozens of sources in days, not months](https://motherduck.com/learn-more/modern-data-warehouse-playbook/).

This shift dramatically accelerates your time-to-insight and slashes operational costs. Processing a 100MB CSV file on your laptop is instantaneous and costs nothing, whereas using a traditional cloud warehouse incurs charges for compute time and network data transfer. Companies that adopt this lean model report [ 70-90% cost reductions](https://motherduck.com/learn-more/modern-data-warehouse-playbook/) compared to traditional cloud data warehouses.

### How Did Five Startups Slash Data Prep Time from Hours to Minutes?

The benefits of abandoning premature ETL aren't just theoretical. Startups across various industries have replaced slow, brittle pipelines and overloaded databases with MotherDuck’s query-in-place model, leading to dramatic improvements in speed, cost, and agility. These changes often lead to huge improvements, not just small percentage gains.

| Company & Industry | Previous State & Pain Point | Transformation with MotherDuck | Quantified Outcome |
|---|---|---|---|
Finqore (FinTech) | 8-hour data pipelines using Postgres for complex financial data and a heavy reliance on manual Excel processes. | Replaced Postgres to process and unify data directly, enabling a real-time metrics explorer and AI agents. |
8 hours to 8 minutes |

**Gardyn**(IoT / AgTech)[Pipeline time cut from](https://motherduck.com/case-studies/gardyn/)at 10x lower cost than other data warehouses.**over 24 hours to under 1 hour****UDisc**(Sports Tech)[dbt job time reduced from](https://motherduck.com/case-studies/udisc-motherduck-sports-management/), and typical queries dropped from minutes to**6 hours to 30 minutes****5 seconds**.**Dexibit**(Analytics)[Analytical query times reduced from](https://motherduck.com/case-studies/dexibit/), eliminating traditional data warehouse costs.**minutes to a few seconds****Layers**(SaaS)[dashboards loading in](https://motherduck.com/case-studies/layers-multi-tenant-data-warehouse/).**110 ms**## How Can You Get Instant Answers from Excel & CSV Files?

For many teams, valuable data is trapped in local spreadsheets. The traditional path to analyzing this data, which includes manual imports, database setup, and schema definition, is slow and frustrating. MotherDuck eliminates this friction by allowing you to query CSV and Excel files directly with SQL, just as if they were database tables.

This is powered by DuckDB's [ read_csv_auto](https://duckdb.org/docs/stable/data/csv/auto_detection.html) and

[functions, which automatically infer column names, data types, and file dialects (like delimiters) by sampling the file. This](https://duckdb.org/docs/stable/guides/file_formats/excel_import.html)

`read_xlsx`

**schema-on-read**capability means a non-technical user can go from a local file to a powerful SQL query in seconds, without writing any

`CREATE TABLE`

statements or managing a database server.For a local CSV file, a query is as simple as this:

Copy code

```
SELECT
product_category,
SUM(sale_amount) AS total_sales
FROM 'transactions.csv'
GROUP BY ALL
ORDER BY total_sales DESC;
```


MotherDuck [automatically detects the columns and their types](https://duckdb.org/docs/stable/data/csv/overview.html), allowing you to filter, aggregate, and sort on the fly. This direct-query capability extends to files stored in cloud object storage and [even Google Sheets](https://motherduck.com/docs/key-tasks/data-warehousing/Replication/spreadsheets/), providing a unified way to access spreadsheet data wherever it lives.

### What About Messy Spreadsheets? How to Handle Common Pitfalls in SQL

"Wild" CSV and Excel files often have inconsistencies. Instead of spending time on manual cleanup, you can handle these common issues directly in your SQL query using optional parameters.

| Pitfall | Problem Description | SQL Solution with MotherDuck |
|---|---|---|
Incorrect Delimiter | A CSV file uses a pipe (`|` ) or semicolon (`;` ) instead of a comma, causing columns to be misread. | Use the
`delim` parameter |

`read_csv('data.csv', delim = '|')`

.**Inconsistent Date Formats**`MM/DD/YYYY`

or `DD-Mon-YY`

.[to provide the exact format string:](https://duckdb.org/docs/stable/data/csv/overview.html)`dateformat`

parameter`read_csv('data.csv', dateformat = '%m/%d/%Y')`

.**Header and Footer Rows**[to select only the data cells:](https://duckdb.org/docs/stable/guides/file_formats/excel_import.html)`range`

parameter`range = 'A5:Z100'`

.**Mixed Data Types**[, then use](https://duckdb.org/docs/stable/guides/file_formats/excel_import.html)`all_varchar = true`

`TRY_CAST()`

in your `SELECT`

statement to safely convert types.## How Do I Turn Thousands of Fragmented Files into a Single Database?

A common challenge for growing companies is data fragmentation, where analytics data is spread across thousands of individual files in cloud storage like Amazon S3. MotherDuck sidesteps complex ingestion jobs by [treating an entire folder of files as a single, queryable database table](https://duckdb.org/docs/stable/data/multiple_files/overview.html).

By using SQL with glob patterns, you can instantly query a whole collection of Parquet, CSV, or JSON files directly in S3. For example, the following query will scan all Parquet files for the year 2025, no matter how many subdirectories they are in, and treat them as one large table:

Copy code

```
SELECT
event_type,
COUNT(*) AS event_count
FROM read_parquet('s3://my-bucket/logs/2025/**/*.parquet')
GROUP BY event_type;
```


This is a high-performance feature, not just a convenience. MotherDuck’s query engine [pushes down filters and projections to the file level](https://duckdb.org/docs/stable/data/parquet/overview.html), minimizing the amount of data read from cloud storage and reducing costs. For even greater efficiency, organizing files using [ Hive-style partitioning](https://duckdb.org/docs/stable/guides/performance/how_to_tune_workloads.html) (e.g.,

`/year=2025/month=10/`

) allows the engine to skip entire folders that don’t match a query’s `WHERE`

clause, dramatically reducing scan time and cost.## How Can I Join Local Files with Data in the Cloud?

Startups rarely have their data in one neat location. You might have recent sales data in a CSV on your laptop, historical logs in an S3 bucket, and user profiles in a managed database. MotherDuck’s [ Dual Execution feature](https://motherduck.com/docs/concepts/architecture-and-capabilities/) unifies these fragmented datasets into a single analytical layer without requiring you to move the data first.

When your local DuckDB client is connected to MotherDuck, they form a distributed system where the query optimizer [intelligently routes parts of your query to where the data lives](https://motherduck.com/videos/339/bringing-duckdb-to-the-cloud-dual-execution-explained/). A query on a local file runs entirely on your machine's resources. A query on a large S3 file runs in the MotherDuck cloud to use its scale. Most powerfully, a join between the two is automatically optimized to minimize data transfer.

An analyst can prototype a query by joining a local spreadsheet with a massive cloud table. MotherDuck is smart enough to automatically push filters down to the local file, send only the small, filtered result to the cloud, and perform the final join there. This [avoids the slow and costly process of uploading entire local files](https://motherduck.com/learn-more/fix-slow-bi-dashboards/) just to perform a join. The entire process is smooth, and you simply write standard SQL.

## How Can You Explore Data Before Building a Formal Pipeline?

The schema-on-read approach is powerful because it lets you [explore and understand your data before committing](https://motherduck.com/duckdb-book-summary-chapter5/) to a rigid transformation pipeline. This "explore-then-model" workflow de-risks data projects by allowing you to assess data quality, discover hidden patterns, and validate business assumptions upfront. With MotherDuck, you can use a suite of simple SQL commands to profile your raw CSV, JSON, and Parquet files directly.

### How Can You See the Structure of Your JSON and Parquet Files Automatically?

MotherDuck provides powerful functions to look inside the structure of your semi-structured and columnar files without manually parsing them.

For **Parquet files**, you can [query the file’s internal metadata directly](https://duckdb.org/docs/stable/data/parquet/metadata.html) to see column names, types, and nullability. This is very helpful for understanding the data you've received from a partner or another system.

Copy code

```
SELECT * FROM parquet_schema('your_file.parquet');
```


For **JSON files**, the [ read_json_auto function automatically infers a schema](https://duckdb.org/docs/stable/data/json/loading_json.html), representing nested objects as

`STRUCT`

s and arrays as `LIST`

s. You can see this inferred schema by creating a temporary table and describing it:Copy code

```
CREATE TABLE temp_json AS SELECT * FROM read_json_auto('api_response.json');
DESCRIBE temp_json;
```


### How Can You Use SQL to Explore JSON Data Without Knowing Its Structure?

JSON's nested, schema-less nature makes it notoriously difficult to analyze with traditional SQL. MotherDuck lets you [explore and query deeply nested JSON files immediately](https://motherduck.com/blog/analyze-json-data-using-sql/), even with zero prior knowledge of their structure.

You can instantly navigate the nested structure using simple **dot notation** (e.g., `SELECT user.name.first FROM 'users.json'`

) and flatten complex arrays into rows using the ** UNNEST** function. This turns what was once a painful data preparation task into a simple, interactive exploration process.

Copy code

```
-- Explore nested JSON and flatten an array of items into separate rows
SELECT
order_id,
customer.id AS customer_id,
item.product_id::INTEGER,
item.quantity::INTEGER
FROM read_json_auto('orders.json'), UNNEST(line_items) AS t(item);
```


## Is the "No-ETL" Approach a Permanent Solution?

For a lean team, building a full-blown ETL pipeline too early is a strategic error. It locks you into a rigid structure before you fully understand your data's value or how your business questions will evolve. The "No-ETL" approach is a better starting point for most startups.

However, "No-ETL" does not mean "Never-ETL." As your company matures and your data processes become more standardized, certain triggers justify introducing a more formalized, lightweight EL(T) process, where raw data is loaded into cloud storage and then transformed within the warehouse. You should consider this change when you need things like **repeatability for audits**, such as for financial reporting or compliance. It also becomes valuable when you need to improve **performance on complex joins** for frequently-run dashboards, or when business operations depend on [ strict data freshness SLAs](https://motherduck.com/learn-more/modern-data-warehouse-use-cases/) of minutes, not hours. Finally, as your team grows, a formalized model is essential for

[, allowing you to systematically clean data or mask PII before exposing it to a wider audience.](https://motherduck.com/blog/motherduck-kestra-etl-pipelines/)

**data governance at scale**This **progressive modeling pattern**, which involves starting with raw files, creating semantic views, and only materializing tables when necessary, allows your data architecture to evolve with your business, not against it.

## Your Path Forward: From Files to Insights

The message for startups is clear: stop building pipelines and start asking questions. The modern, No-ETL approach used by MotherDuck removes the friction between your data and your decisions. By letting your entire team query raw files directly with the SQL they already know, you unlock a level of speed and agility that traditional data stacks simply cannot match. Start by exploring your local files, scale to the cloud, and let your data architecture grow with your business needs. The power to be data-driven is no longer locked behind complex engineering projects. It's right there in your files, waiting for a query.

Start using MotherDuck now!

## FAQS

### Do I really need an ETL pipeline if I’m just getting started?

For most startups, no. A "No-ETL" approach lets you query raw CSV, JSON, and Excel files directly with SQL. This is faster and cheaper, allowing you to get insights immediately without building complex infrastructure.

### How can I analyze data in Excel and CSV files without hassle?

You can use SQL to query local Excel and CSV files as if they were database tables. Modern tools like DuckDB automatically detect columns and data types, so you can go from a spreadsheet to analysis in seconds without any setup.

### How do I query thousands of files in a folder as a single database?

Use SQL with glob patterns (e.g., `FROM 's3://bucket/logs/**/*.parquet'`

). This treats an entire folder of files in cloud storage as one large, queryable table, eliminating the need for complex data ingestion jobs.

### Can I explore my data before building an ETL pipeline?

Yes, this is a key benefit of the No-ETL approach. By querying raw files directly, you can profile data quality, discover patterns, and validate assumptions with SQL before committing to a rigid transformation model.

### How can I see the structure of my JSON and Parquet files automatically?

Use simple SQL commands. For Parquet, `parquet_schema('file.parquet')`

reveals the schema. For JSON, `read_json_auto()`

infers the structure, which you can view with a `DESCRIBE`

command on the query result.

### Why is schema design so difficult for startups?

Startups evolve rapidly, causing data sources and business needs to change constantly. A rigid, upfront schema (schema-on-write) becomes a bottleneck. A flexible, schema-on-read approach is better as it applies structure at query time.