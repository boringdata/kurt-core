---
title: using-sql-in-your-data-lake-with-duckdb-iceberg-dbt-and-motherduck
content_type: tutorial
source_url: https://motherduck.com/videos/using-sql-in-your-data-lake-with-duckdb-iceberg-dbt-and-motherduck
indexed_at: '2025-11-25T20:44:04.481855'
content_hash: be64f2e7730b2abc
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Using SQL in Your Data Lake with DuckDB, Iceberg, dbt, and MotherDuck - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Using SQL in Your Data Lake with DuckDB, Iceberg, dbt, and MotherDuck](https://www.youtube.com/watch?v=FMVgwGh8RQA)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

More videos

## More videos

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=FMVgwGh8RQA&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 24:43

•Live

•

dbtMeetupSQL

# Using SQL in Your Data Lake with DuckDB, Iceberg, dbt, and MotherDuck

2025/01/17

Hey there data folks! Jacob Matson from MotherDuck's DevRel team here. Let me tell you about my recent obsession: using SQL more effectively across your entire data workflow. If you're like me, you've probably wondered why our data stacks often force us to switch between different tools and languages when SQL is the one language we all speak. What if we could just stick with SQL across the board? That's exactly what I've been exploring by combining DuckDB, MotherDuck, Apache Iceberg, and dbt.

## The Dynamic Duo: DuckDB and MotherDuck

For those who haven't waddled into DuckDB's waters yet, it's an in-process OLAP query engine – think of it as SQLite's analytically-minded cousin. It's remarkably lightweight (just a single binary) that runs practically anywhere: Mac, Linux, Windows, and even in browsers via WASM. What makes DuckDB particularly useful is its built-in parallelism – write one SQL query, and it efficiently uses all your CPU cores to process it. Plus, its SQL dialect is based on PostgreSQL, so it feels familiar from the start.

One of DuckDB's standout features is its extension ecosystem. These extensions let DuckDB read from and write to numerous data sources and formats – Parquet, CSVs, JSON, and as we'll see later, even Google Sheets and Apache Iceberg tables.

So what's MotherDuck? We've taken the open-source DuckDB and built a serverless cloud service around it. Unlike distributed systems that scale out, we scale up on single nodes. This approach makes practical sense when you consider that single-node hardware capabilities (AWS instances with up to 32TB RAM and nearly 900 vCPUs) are growing faster than most datasets. With MotherDuck, you get DuckDB's local speed plus remote querying, persistent storage, and collaboration in the cloud.

Here's an interesting tidbit: in a recent survey, 23% of DuckDB users identified as software engineers. That's telling – we've found a SQL dialect that developers actually like using! When everyone in your organization speaks the same data language, those handoffs between business analysts, data analysts, data engineers, and software engineers become much smoother.

## Adding Apache Iceberg to the Mix

For modern data architectures handling large datasets in data lakes, an open table format like Apache Iceberg proves essential. It offers schema evolution (table structures can change without breaking things), time travel (accessing historical versions of your data), and ACID-like transaction properties directly on your data lake storage like S3 or Google Cloud Storage.

The neat part is that DuckDB and MotherDuck integrate with Iceberg through a simple extension. Here's how easily you can get started from your DuckDB CLI:

```sql
Copy code

-- Install and Load the Iceberg extension (if not autoloaded by MotherDuck)
INSTALL 'iceberg';
LOAD 'iceberg';

-- (Optional) Install and Load the HTTPFS extension to access remote filesystems like S3
INSTALL 'httpfs';
LOAD 'httpfs';

-- Query an Iceberg table stored on S3 directly
FROM iceberg_scan('s3://us-prd-motherduck-open-datasets/iceberg/tpcds/default.db/call_center/', ALLOW_MOVED_PATHS=TRUE);
```

The key function here is `iceberg_scan`, which points to an S3 path where our Iceberg table resides. The `ALLOW_MOVED_PATHS=TRUE` parameter helps DuckDB resolve paths correctly if files have been moved or restructured.

The practical benefit? Anyone on your team – analyst, data engineer, or developer – can tap into the same governed, version-controlled dataset in your data lake using straightforward SQL. No context switching or learning complex APIs just to read data.

## Local-to-Cloud Integration with MotherDuck

This is where things get particularly interesting. While you can query Iceberg tables directly from your local DuckDB instance, for large datasets, you'll often want the compute to happen closer to the data in the cloud. MotherDuck makes this seamless.

From your local DuckDB shell, you simply "attach" to your MotherDuck account:

```sql
Copy code

-- This command connects your local DuckDB session to your MotherDuck service
ATTACH 'md:';
```

Once attached, your local DuckDB client works as a lightweight interface to your MotherDuck environment. You can execute queries that run within MotherDuck, right next to your data in AWS (assuming your S3 buckets are in the same region as MotherDuck).

For example, creating a table in MotherDuck sourced directly from an Iceberg table in S3:

```sql
Copy code

-- Create a table in your MotherDuck database from an Iceberg source
CREATE OR REPLACE TABLE my_db.main.call_center AS
FROM iceberg_scan('s3://us-prd-motherduck-open-datasets/iceberg/tpcds/default.db/call_center/', ALLOW_MOVED_PATHS=TRUE);
```

The naming convention `my_db.main.call_center` refers to a database within your MotherDuck account, with `call_center` as the new table name.

When you run this statement, the data is read from Iceberg in S3 and written into a native DuckDB table within MotherDuck, all happening efficiently in the cloud while your local machine just orchestrates it. This minimizes network overhead for large data transfers. In my testing, even with the small 30-row example table (imagine millions in a real scenario), the data loaded noticeably faster because the heavy lifting happened in AWS rather than pulling data to my laptop.

You can then query this table either from your local CLI or directly within the MotherDuck UI (which runs DuckDB in your browser using WASM – pretty cool, right?).

## Transforming Data with dbt: DataOps Best Practices

Reading data is just the beginning – most real-world data workflows involve transformations. This is where dbt (data build tool) comes in, allowing you to define data transformations using SQL models that promote version control, modularity, and testing for your pipelines.

With DuckDB and MotherDuck, you can build an efficient dbt workflow:

**Raw Layer (Views on Iceberg):** Define dbt sources pointing to your Iceberg tables in S3, then create dbt models materialized as views. These views in MotherDuck will directly query the underlying Iceberg data upon access – ideal for your "bronze" or raw data layer.

In your dbt project, a source YAML might look like:

```yaml
Copy code

# models/sources.yml
version: 2

sources:
 - name: raw_iceberg_data
   schema: my_iceberg_sources # A conceptual schema
   tables:
     - name: call_center_iceberg
       meta:
         external_location: "iceberg_scan('s3://us-prd-motherduck-open-datasets/iceberg/tpcds/default.db/call_center/', ALLOW_MOVED_PATHS=TRUE);"
```

And a model materialized as a view:

```sql
Copy code

-- models/raw/raw_call_center.sql
{{ config(materialized='view') }}

SELECT * FROM {{ source('raw_iceberg_data', 'call_center_iceberg') }}
```

**Transformations (SQL Models):** Write your business logic and transformations as standard dbt SQL models, which dbt will compile into appropriate SQL queries for DuckDB/MotherDuck.

**Gold Layer (Materialized Tables in MotherDuck):** For your final, curated datasets (your "gold" layer), materialize these dbt models as tables in MotherDuck. This persists the transformed data in MotherDuck's native format, offering excellent performance for downstream analytics and applications.

```sql
Copy code

-- models/gold/dim_call_center_summary.sql
{{ config(materialized='table') }}

SELECT
   c_call_center_sk,
   c_first_name,
   COUNT(*) AS total_records_in_source -- Example transformation
FROM {{ ref('raw_call_center') }}
GROUP BY ALL
```

Running `dbt build` executes these models. The views pointing to Iceberg will be created in MotherDuck, and the queries for materialized tables will pull data from Iceberg (via the views), transform it, and store the results as optimized tables within MotherDuck. I was able to build a dbt project based on the TPC-DS dataset (about 40GB in Iceberg) in MotherDuck in about 12-15 minutes, which was a pleasant surprise.

This approach gives you a clean separation: Iceberg for your large, evolving data lake storage, and MotherDuck for performant querying, transformation execution, and serving refined data.

## Beyond the Database: Extension Power

The SQL-centric approach extends beyond querying and transforming. DuckDB's extension ecosystem lets you integrate your data with other tools and systems using just a few lines of SQL.

### Serving Data Over HTTP

Need to quickly expose some data via an API? DuckDB has an httpserver extension:

```sql
Copy code

-- In your DuckDB CLI
INSTALL httpserver FROM community;
LOAD httpserver;

-- Start a simple HTTP server from within DuckDB
SELECT httpserve_start('0.0.0.0', 8080, '');
```

Once the server is running, you can curl it to get query results as JSON:

```bash
Copy code

curl -X POST -d "SELECT 1" "http://localhost:8080"
```

```bash
Copy code

curl -X POST -d "FROM my_db.call_center"
```

This queries the call\_center table we created in MotherDuck and returns the first 10 rows as JSON. Imagine creating quick analytics endpoints or data feeds for other services with just SQL!

### Exporting Data to Google Sheets

How often have you been asked for data in a spreadsheet? The gsheets extension makes this remarkably straightforward:

```sql
Copy code

-- In your DuckDB CLI
INSTALL gsheets from community;
LOAD gsheets;

-- Create a secret for OAuth with Google Sheets
CREATE SECRET (
   TYPE gsheet,
   -- You'll usually be prompted for credentials or a token
);

-- Write data from a MotherDuck table to a Google Sheet
COPY (
   FROM my_db.call_center
) TO 'YOUR_GOOGLE_SHEET_ID' (
   FORMAT ghseet
);
```

Just like that, data from your MotherDuck tables can be piped directly into a Google Sheet. That CFO report due every Monday? Now you can automate it with a few quacks of SQL.

## Real-World Impact & Use Cases

So what does all this mean in practice?

**Enhanced Cross-Team Collaboration:** With SQL as the common denominator, analysts, data engineers, and software developers can finally speak the same language. Handoffs become smoother, and everyone can contribute to and understand the data pipeline.

**Scalability and Flexibility:** DuckDB's in-process speed works great for local development and smaller tasks, while MotherDuck's serverless architecture lets you scale up effortlessly for massive datasets and complex queries in the cloud. You get the right tool for the job without changing your SQL approach.

**Practical Extensibility:** The rich extension ecosystem (HTTP server, Google Sheets, Excel, spatial analysis, and many more) means you can connect DuckDB and MotherDuck to virtually anything, automating workflows in creative ways.

## Getting Started

Ready to try this out yourself?

1. **Install DuckDB:** Head over to the [DuckDB Official Website](https://duckdb.org/) to install it locally. It's as simple as `pip install duckdb` or using brew.

2. **Sign Up for MotherDuck:** Explore the [MotherDuck Documentation](https://motherduck.com/docs/) and sign up for a free account to experience the serverless cloud capabilities.

3. **Learn About Apache Iceberg:** Check out the [Apache Iceberg Documentation](https://iceberg.apache.org/docs/) to understand its features and how to set up Iceberg tables.

4. **Explore dbt Integration:** If you're new to dbt, the [dbt Docs](https://docs.getdbt.com/) are a great place to start learning how to build SQL-based data transformations.

5. **Experiment with Extensions:** The [DuckDB Extensions page](https://duckdb.org/docs/extensions/overview.html) lists available extensions. Try a few out!


As you get more comfortable, consider how you can automate your data pipelines fully – perhaps by scheduling dbt runs or creating dynamic analytics endpoints using the HTTP extension.

## Conclusion: SQL Simplicity

By combining DuckDB's local speed and rich SQL dialect, MotherDuck's serverless deployment and collaborative features, Iceberg's robust open table format, and dbt's transformation capabilities, teams can create a streamlined, SQL-centric workflow. This stack works for everything from local ad-hoc analytics to cloud-scale data processing and innovative integrations like direct exports to Google Sheets.

Using SQL across different roles and parts of the data stack doesn't just simplify individual tasks; it removes friction and fosters collaboration. It shows that sometimes, the most practical tools, elegantly combined, can solve complex data challenges most effectively. Give it a try – I think you'll find this approach surprisingly powerful for your data workflows.

...SHOW MORE

## Related Videos

[!["Instant SQL Mode - Real Time Feedback to Make SQL Data Exploration Fly" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FG_Se_B_Sox_AW_Fg_HD_f4fddaa9ab.jpg&w=3840&q=75)](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly/)

[2025-04-23](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly/)

### [Instant SQL Mode - Real Time Feedback to Make SQL Data Exploration Fly](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly)

Hamilton Ulmer shares insights from MotherDuck's Instant SQL Mode, exploring how real-time query result previews eliminate the traditional write-run-debug cycle through client-side parsing and DuckDB-WASM caching.

SQL

Talk

MotherDuck Features

[!["DuckDB: Run dbt build with sub-second execution times" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_03_26_at_3_40_16_PM_c6e3a8096f.png&w=3840&q=75)\\
\\
24:06](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times/)

[2025-03-13](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times/)

### [DuckDB: Run dbt build with sub-second execution times](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times)

Whether you're new to DuckDB or looking to optimize your workflows, this session will provide practical insights to help you leverage its full potential.

YouTube

Data Pipelines

dbt

MotherDuck Features

[!["Why web developers should care about analytical databases" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmaxresdefault_2_a87303b686.jpg&w=3840&q=75)\\
\\
08:48](https://motherduck.com/videos/why-web-developers-should-care-about-analytical-databases/)

[2024-12-11](https://motherduck.com/videos/why-web-developers-should-care-about-analytical-databases/)

### [Why web developers should care about analytical databases](https://motherduck.com/videos/why-web-developers-should-care-about-analytical-databases)

You often start your web application with an OLTP database like Postgres, but should you crunch your analytics there? In this video, ‪Mehdi explains what OLAP databases are, when to use them, and more.

YouTube

Wasm

SQL

[View all](https://motherduck.com/videos/)

Authorization Response