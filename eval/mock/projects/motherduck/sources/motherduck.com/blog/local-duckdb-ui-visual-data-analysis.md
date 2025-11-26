---
title: local-duckdb-ui-visual-data-analysis
content_type: tutorial
source_url: https://motherduck.com/blog/local-duckdb-ui-visual-data-analysis
indexed_at: '2025-11-25T19:57:06.287183'
content_hash: 7b95153901365328
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Meet the New DuckDB Local UI: Analyze Data Visually, Right Where It Lives

2025/05/12 - 6 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

Let's talk about something we all know too well: the staring contest with your terminal window as you squint at table outputs, trying to make sense of your data through DuckDB's CLI. Don't get me wrong— I love the CLI, it's powerful, but sometimes you are wondering if there's a better way to visualize what you're working with.

In case you missed the announcement, DuckDB Labs, alongside our team at MotherDuck, hatched something that might make your analytical life considerably more pleasant: a dedicated local DuckDB User Interface. It's essentially a SQL notebook environment designed specifically for exploring and analyzing data with DuckDB, running right on your machine. You can work with local data, data hosted in cloud object stores like S3, data stored in MotherDuck and even data in Postgres databases!

## Why Would a Terminal-Loving Data Engineer Want a UI?

DuckDB's strength has always been its ability to process data at impressive speeds, directly within your application or locally, often reading files without complicated ingestion pipelines. But let's be honest—when you're trying to understand a new dataset, typing `SELECT * FROM table LIMIT 100` for the tenth time in the CLI starts feeling rather... inefficient. And DuckDB’s [“Friendly SQL”](https://duckdb.org/docs/stable/sql/dialect/friendly_sql.html) project can only go so far in making it feel better.

The new UI addresses this by providing:

- A **notebook interface** that feels familiar if you've used Jupyter, but tailored specifically for SQL and DuckDB workflows
- An **integrated data catalog** that lets you browse databases, tables, and schema information without writing boilerplate queries
- **Visual diagnostics** that show column distributions, null percentages, and other stats at a glance
- **Direct querying of local or remote files** (Parquet, CSV, JSON, etc.) with the same simplicity you expect from DuckDB
- **Optional connection to MotherDuck** for hybrid local/cloud workflows when you need it
- **Live SQL acceleration** for SQL query results as–you-type, thanks to Instant SQL.

It's about removing friction from that critical "getting to know your data" phase that precedes more complex analysis or pipeline building.

## Waddling into Action: Getting Started

Setting up the DuckDB UI is refreshingly straightforward. It's packaged as a DuckDB extension, so you just need the DuckDB CLI installed:

For macOS users (via Homebrew):

```bash
Copy code

brew install duckdb
```

For Linux/macOS/WSL (via the new install script):

```arduino
Copy code

curl -s https://install.duckdb.org | sh
```

For other platforms, check out the official [DuckDB installation guide](https://duckdb.org/docs/installation/) for Windows instructions and pre-compiled binaries.

Once DuckDB is installed and in your PATH, launching the UI is as simple as:

```
Copy code

duckdb -ui
```

Behind the scenes, DuckDB checks if the [`duckdb_ui`](https://duckdb.org/docs/stable/extensions/ui.html) extension is installed, downloads it if needed (along with dependencies like the [`httpfs`](https://duckdb.org/docs/stable/extensions/httpfs/overview.html) extension for remote file access), starts a local web server, and opens your browser. Just like that, you're looking at your new SQL notebook environment.

## **Taking a Tour of Your New Data Pond**

The interface has a clean organization with several key areas:

**The SQL Notebook (Center Panel)**: Your primary workspace with cells for writing and executing SQL queries. The results appear directly below each cell. You get syntax highlighting, autocompletion for SQL keywords and database objects, and standard notebook conveniences like keyboard shortcuts (Cmd+Enter or Ctrl+Enter to execute, Cmd+/ or Ctrl+/ to toggle comments).

![img1](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage5_a8f67984ed.gif&w=3840&q=75)

**The Catalog & Database Explorer (Left Panel)**: Shows your connected data sources—by default, the memory database and main if you launched DuckDB with a persistent file. You can attach other DuckDB database files (local or remote) using the + icon and providing a path and alias. This runs an [ATTACH](https://duckdb.org/docs/stable/sql/statements/attach.html) command behind the scenes:

```sql
Copy code

-- Example: Attaching a remote database (UI handles this via its dialog, just provide the path to the database in dialog)
ATTACH 'http://blobs.duckdb.org/databases/stations.duckdb' AS stations (READ_ONLY);
```

![img2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage6_1fcb1d3177.gif&w=3840&q=75)

**The Table Explorer (Bottom Left Panel)**: This activates when you click on a table in the Catalog Explorer. Without running a query, it immediately shows the table's structure and content overview including:

- Column names and data types
- Histograms showing data distribution for numeric and temporal columns
- Percentage of NULL values in each column
- Cardinality (number of distinct values)
- Min/Max values for numeric types
- Earliest/Latest dates for temporal columns

![](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage3_b939417150.gif&w=3840&q=75)**Instant SQL (Run mode)**: As you write your SQL query, the editor automatically updates the result set in real time—no need to hit “Run.” It uses different caching strategies to provide an immediate feedback loop. This turns query writing into a smooth, interactive experience, helping you spot errors, inspect CTEs and calculated fields without ever breaking your flow.

![instantsql](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGIF_1_15e918df5e.gif&w=3840&q=75)

## Seeing the UI's Power in Action

The interface truly shines when paired with DuckDB's core strengths:

**Analyzing Large Local Files**: Let's say you have the Flights dataset (Parquet with 1 million rows) in your working directory:

```sql
Copy code

-- Load the dataset
CREATE TABLE flights AS SELECT * FROM 'flights.parquet';

-- Get a quick preview
FROM flights LIMIT 10;
-- Check out those instant diagnostics on the right!

-- Run a complex aggregation on all 1M rows
-- Find average delay for each month
SELECT
    STRFTIME(FL_DATE, '%Y-%m') AS year_month,
    COUNT(*) AS num_departures,
    AVG(DEP_DELAY) AS avg_dep_delay
FROM 'flights.parquet'
GROUP BY year_month
ORDER BY avg_dep_delay;
```

![img5](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_04e179fe72.gif&w=3840&q=75)
Even with this big dataset, the aggregation query runs surprisingly fast (often under a second on modern hardware), with results appearing immediately below your query.

**Querying Remote Data**: DuckDB's ability to query remote files directly works perfectly within the UI—no separate download steps needed.

**Keyboard Shortcuts for Efficiency**:

- Cmd+Enter / Ctrl+Enter: Run the current cell
- Cmd+/ / Ctrl+/: Toggle SQL comments
- Up/Down Arrow Keys: Navigate between cells
- Tab/Shift+Tab: Indent/Unindent code
- Esc: Exit cell editing mode

## **Swimming in Both Ponds: The MotherDuck Connection**

You might notice a "Sign in to MotherDuck" button in the top-right corner. This optional feature enables a hybrid workflow connecting your local environment with MotherDuck's cloud-hosted DuckDB service.

By signing into your MotherDuck account (free to start), you can:

- See your MotherDuck databases directly in the Catalog Explorer alongside local databases
- Use MotherDuck's scalable compute and storage for heavy lifting

For example, after signing in, you can access MotherDuck's sample data:

```sql
Copy code

SELECT
    upper(complaint_type) as upper_complaint_type,
    count(*)
FROM sample_data.nyc.service_requests
WHERE date_part('year', created_date) = 2023
GROUP BY ALL
ORDER BY count(*) DESC
LIMIT 10;
```

This query analyzes NYC 311 service requests stored in the cloud but displays results right in your local UI.

![](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage4_9d8e8e6ce3.gif&w=3840&q=75)

## **Conclusion: A Welcome Addition to Your Data Toolkit**

The new DuckDB UI adds a practical visual layer to DuckDB's already impressive analytical engine. It makes exploratory analysis more intuitive while maintaining the performance you've come to expect from DuckDB, even with substantial datasets.

Whether you're a DuckDB veteran looking for a more convenient exploration environment or just getting started and prefer a GUI, the local UI offers a useful experience. And with the MotherDuck integration option, you have a smooth path for combining local and cloud resources when needed.

Have suggestions or found a bug? Share them on the GitHub repository: [https://github.com/duckdb/duckdb-ui](https://github.com/duckdb/duckdb-ui)!

### TABLE OF CONTENTS

[Why Would a Terminal-Loving Data Engineer Want a UI?](https://motherduck.com/blog/local-duckdb-ui-visual-data-analysis/#why-would-a-terminal-loving-data-engineer-want-a-ui)

[Waddling into Action: Getting Started](https://motherduck.com/blog/local-duckdb-ui-visual-data-analysis/#waddling-into-action-getting-started)

[Taking a Tour of Your New Data Pond](https://motherduck.com/blog/local-duckdb-ui-visual-data-analysis/#taking-a-tour-of-your-new-data-pond)

[Seeing the UI's Power in Action](https://motherduck.com/blog/local-duckdb-ui-visual-data-analysis/#seeing-the-uis-power-in-action)

[Swimming in Both Ponds: The MotherDuck Connection](https://motherduck.com/blog/local-duckdb-ui-visual-data-analysis/#swimming-in-both-ponds-the-motherduck-connection)

[Conclusion: A Welcome Addition to Your Data Toolkit](https://motherduck.com/blog/local-duckdb-ui-visual-data-analysis/#conclusion-a-welcome-addition-to-your-data-toolkit)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Ecosystem: May 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdbeco_may_ca294a4d7f.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-may-2025/)

[2025/05/08 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-may-2025/)

### [DuckDB Ecosystem: May 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-may-2025)

DuckDB Monthly #29: From Metabase to Doom, DuckDB powers everything.

[![Taming Wild CSVs: Advanced DuckDB Techniques for Data Engineers](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FTaming_Wild_CS_Vs_v3_f21b5fe692.png&w=3840&q=75)](https://motherduck.com/blog/taming-wild-csvs-with-duckdb-data-engineering/)

[2025/05/17 - Ryan Boyd](https://motherduck.com/blog/taming-wild-csvs-with-duckdb-data-engineering/)

### [Taming Wild CSVs: Advanced DuckDB Techniques for Data Engineers](https://motherduck.com/blog/taming-wild-csvs-with-duckdb-data-engineering)

How to ingest and query CSV files in DuckDB using auto-detection, sniffing, manual configuration and more.

[View all](https://motherduck.com/blog/)

Authorization Response