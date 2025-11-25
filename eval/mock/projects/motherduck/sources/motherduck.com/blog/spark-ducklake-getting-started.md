---
title: spark-ducklake-getting-started
content_type: tutorial
source_url: https://motherduck.com/blog/spark-ducklake-getting-started
indexed_at: '2025-11-25T19:56:45.784181'
content_hash: efd1a2b579884f0e
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# When Spark Meets DuckLake: Tooling You Know, Simplicity You Need

2025/08/11 - 9 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

If you've been following the lakehouse movement, you know that [DuckLake](https://motherduck.com/blog/getting-started-ducklake-table-format/) represents a fresh take on table formats—storing metadata in a proper database rather than scattered across countless JSON files. But here's the thing: while DuckLake shines with DuckDB, what if your data processing needs require ecosystem that only Apache Spark can provide?

That's exactly what I'm going to explore today. I'll build a complete local (with remote metadata) lakehouse architecture where PySpark handles the heavy lifting while DuckLake manages our data with all the modern features I've come to expect—ACID transactions, time travel, schema evolution, the works.

I'm using a [DevContainer](https://code.visualstudio.com/docs/devcontainers/containers) environment (because who has time for dependency hell?), Supabase PostgreSQL for my metadata catalog (centralized and shared across teams), local Parquet storage for experimentation, and Apache Spark 4.0+ as my processing workhorse.

You'll find all the code sources mentioned in this blog on [Github](https://github.com/mehd-io/tutorial-spark-ducklake).

## Setting Up Our Playground

I've designed this demo to run in a DevContainer—think of it as a pre-configured development environment that works seamlessly with VSCode or Cursor. No more "it works on my machine" problems.

Everything is configured through environment variables with the `.env` file. I'm using `uv` for Python package management (because life's too short for slow dependency resolution).

I'm storing metadata in PostgreSQL via [Supabase](https://supabase.com/), a fully managed service that gives me the reliability of PostgreSQL without the operational overhead. Meanwhile, my actual data lives as Parquet files locally for the sake of this experimentation.

Getting started is straightforward. First, grab your Supabase credentials (it's free and takes about 2 minutes to set up), then configure your environment:

```bash
Copy code

cp .env.example .env
```

Your `.env` file will look something like this:

```bash
Copy code

# Required Supabase PostgreSQL credentials
SUPABASE_HOST=your-supabase-host.pooler.supabase.com
SUPABASE_PORT=6543
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres.your_project_ref
SUPABASE_PASSWORD=your_actual_password

# Optional (uses defaults if not specified)
DATA_PATH=/workspaces/tutorial-spark-ducklake/datalake
```

## Creating Our First DuckLake

There's a quirky limitation worth mentioning: at this point in time, Spark can't specify the `DATA_PATH` through JDBC connections when creating new DuckLakes. So, before Spark can work its magic, we'll use DuckDB to bootstrap my DuckLake using DuckDB itself. Think of this as laying the foundation of my lakehouse—it's a one time operation and I'm populating it with some sample data.

The bootstrap script uses the TPC-H extension to generate sample data—around 60,000 lineitem records that simulate real-world transactional data.

Here's the bootstrap script in action:

```python
Copy code

#!/usr/bin/env python3
import duckdb
import os
from loguru import logger
from dotenv import load_dotenv

def create_ducklake_with_data(data_path=None):
    """Create a Ducklake with PostgreSQL metadata and local data storage."""

    # Load environment variables
    load_dotenv()

    # Use default data path if not specified
    if data_path is None:
        data_path = os.getenv('DATA_PATH', '/workspaces/tutorial-spark-ducklake/datalake')

    # Ensure data path exists
    os.makedirs(data_path, exist_ok=True)

    conn = duckdb.connect()

    # Install required extensions
    logger.info("📦 Installing extensions...")
    conn.execute("INSTALL ducklake;")
    conn.execute("INSTALL postgres;")
    conn.execute("INSTALL tpch;")

    # Create PostgreSQL secret using environment variables
    host = os.getenv('SUPABASE_HOST')
    port = os.getenv('SUPABASE_PORT', '6543')
    user = os.getenv('SUPABASE_USER')
    password = os.getenv('SUPABASE_PASSWORD')

    conn.execute(f"""
        CREATE SECRET (
            TYPE postgres,
            HOST '{host}',
            PORT {port},
            DATABASE postgres,
            USER '{user}',
            PASSWORD '{password}'
        );
    """)

    # Create Ducklake with PostgreSQL metadata + local data
    conn.execute(f"""
        ATTACH 'ducklake:postgres:dbname=postgres' AS ducklake_catalog (
            DATA_PATH '{data_path}'
        );
    """)

    # Generate TPC-H data in memory, then copy to Ducklake
    conn.execute("USE memory;")
    conn.execute("CALL dbgen(sf = 0.1);")  # ~60K lineitem records

    conn.execute("USE ducklake_catalog;")
    conn.execute("CREATE TABLE lineitem AS SELECT * FROM memory.lineitem;")

    conn.close()
```

Running this is as simple as:

```bash
Copy code

uv run python bootstrap_ducklake.py
```

It's creating a DuckLake catalog backed by PostgreSQL for metadata, generating TPC-H benchmark data in memory, and then copying it into my new lakehouse. The end result? A fully functional DuckLake with real data, ready for Spark to consume.

You know should have some data in your local `datalake` folder

```bash
Copy code

datalake
└── main
    └── lineitem
        └── ducklake-019885e5-8bef-70b7-9576-ef653bc472ce.parquet
```

You can also go to the Supabase UI and inspect the metadata tables.

## Two Ways to Read from DuckLake with Spark

Now comes the fun part—getting Spark to talk to my DuckLake. There are two distinct approaches, each with its own personality and use cases.

### The DataFrame API approach with Smart Partitioning

Here's what makes this approach special: instead of letting Spark figure out partitioning on its own (which can be suboptimal), I query the DuckLake metadata to understand the file structure and then tell Spark exactly how to distribute the work.

```bash
Copy code

uv run python spark_dataframe_read.py
```

You'll then see in the `stdout` a sample of the data read.

The magic happens in three steps. First, we interrogate DuckLake to understand its internal structure:

```python
Copy code

# Step 1: Get partitioning information for optimal performance
partitioning_info = (
    jdbc_setup().option('query', f'''
        SELECT
            min(file_index::BIGINT)::STRING min_index,
            (max(file_index::BIGINT)+1)::STRING max_index,
            count(DISTINCT file_index::BIGINT)::STRING num_files
        FROM "{table_name}"''').load().collect()[0])
```

This query reveals how DuckLake has organized my data across files. Then I use this intelligence to configure Spark's partitioning:

```python
Copy code

# Step 2: Read with custom partitioning
table_df = (jdbc_setup()
    .option('dbtable', f'(SELECT *, file_index::BIGINT __ducklake_file_index FROM "{table_name}") "{table_name}"')
    .option('partitionColumn', '__ducklake_file_index')
    .option('lowerBound', partitioning_info['min_index'])
    .option('upperBound', partitioning_info['max_index'])
    .option('numPartitions', partitioning_info['num_files'])
    .load())
```

What I find nice about this approach is how it leverages DuckLake's internal `file_index` metadata. I'm essentially telling Spark: "Here's exactly how this data is organized, and here's the most efficient way to read it." The result? Optimal parallelization with each Spark partition corresponding to a DuckLake file.

### The SQL-Native Approach: Creating Persistent Tables

If your team lives and breathes SQL, this second approach will feel much more natural. Instead of working with DataFrames and explicit partitioning, I'm creating persistent tables in Spark's catalog and querying them with standard SQL.

```bash
Copy code

uv run python spark_sql_read.py
```

This approach starts by setting up a proper database structure in Spark, then discovers what tables are available in my DuckLake:

```python
Copy code

# Step 1: Create database and discover tables
spark.sql("CREATE DATABASE IF NOT EXISTS ducklake_db")
spark.sql("USE ducklake_db")

# Step 2: Discover available tables via information_schema
spark.sql(f"""
    CREATE OR REPLACE TEMPORARY VIEW ducklake_tables
    USING jdbc
    OPTIONS (
        url "{duckdb_url}",
        driver "org.duckdb.DuckDBDriver",
        dbtable "information_schema.tables"
    )
""")
```

The beauty of this approach lies in its familiarity. Once I've created my table definition, everything else is just SQL:

```python
Copy code

# Step 3: Create persistent Spark table
spark.sql(f"""
    CREATE TABLE lineitem
    USING jdbc
    OPTIONS (
        url "{duckdb_url}",
        driver "org.duckdb.DuckDBDriver",
        dbtable "lineitem"
    )
""")

# Step 4: Query using standard SQL
result = spark.sql("""
    SELECT l_returnflag, l_linestatus, COUNT(*) as count
    FROM lineitem
    GROUP BY l_returnflag, l_linestatus
""")
result.show()
```

Your tables become first-class citizens in Spark, discoverable through `SHOW TABLES`, and queryable using any SQL tool that connects to your Spark cluster.

### Choosing Your Reading Strategy

The choice between these approaches often comes down to your team's DNA and performance requirements. Here's how I think about it:

**DataFrame API** : The explicit partitioning control can provide significant performance gains, especially when you understand your data's structure. It's also great when you need programmatic error handling and want to build complex data processing pipelines.

**SQL Tables** excel in environments where SQL is the lingua franca. If your analysts are already comfortable with Spark SQL, this approach requires zero retraining. The persistent table definitions also play nicely with data catalogs and discovery tools..

My general recommendation? Start with the SQL approach for its simplicity and switch to DataFrame API if performance profiling shows it's necessary. Both scripts include detailed logging, so you can easily benchmark them against your specific workloads.

## Writing Data: From CSV to DuckLake via Spark

Now let's flip the script and explore writing data to my DuckLake using Spark. I'll load sales data from CSV files stored in `./data`, process it with Spark, write it to DuckLake, and then verify everything worked correctly.

```arduino
Copy code

uv run python spark_dataframe_write.py
```

The write script demonstrates something I find quite practical—it automatically generates sample data if none exists. This means you can run the demo immediately without worrying about data setup:

```python
Copy code

def ensure_sample_data():
    """Ensure sample data exists by generating it if needed."""
    csv_path = "./data/sales_data.csv"
    if not os.path.exists(csv_path):
        # Auto-generate sample data if missing
        subprocess.run(["python", "generate_sample_data.py"], check=True)
    return csv_path
```

The data loading itself is straightforward, but I've included automatic schema inference to make the process as smooth as possible:

```python
Copy code

def load_sales_data_from_csv(csv_path="./data/sales_data.csv"):
    """Load sales data from CSV file."""
    df = (spark.read
          .option("header", "true")
          .option("inferSchema", "true")  # Let Spark infer schema automatically
          .csv(csv_path))

    logger.success(f"✅ Loaded {df.count():,} sales records from CSV")
    return df
```

The script also demonstrates append operations, which is crucial for real-world scenarios where you're continuously adding new data:

```python
Copy code

def demonstrate_append_mode():
    """Demonstrate appending additional data."""
    additional_csv = "./data/additional_sales_data.csv"
    additional_data = load_sales_data_from_csv(additional_csv)

    # Write in append mode
    if write_to_ducklake(additional_data, 'spark_sales_data', mode='append'):
        logger.success("✅ Append operation successful")
        read_and_verify('spark_sales_data')
```

The beauty of this approach is how it leverages Spark's built-in write modes (`overwrite`, `append`, `ignore`, `error`) while adding DuckLake's transactional guarantees on top.

After running the script, you will see in your `./datalake` folder new data :

```bash
Copy code

datalake
└── main
    ├── lineitem
    │&nbsp;&nbsp; └── ducklake-019885e5-8bef-70b7-9576-ef653bc472ce.parquet
    └── spark_sales_data
        ├── ducklake-019885e9-a968-722e-bd2f-587d1c0785ac.parquet
```

## Exploring Your Lakehouse with DuckDB CLI

One of the most satisfying moments in this entire workflow is connecting to my DuckLake with the DuckDB CLI (or any DuckDB client) and seeing all my Spark-written data sitting there, complete with full lakehouse capabilities.

You can dive into the lakehouse using DuckDB's native tools:

```sql
Copy code

-- Connect to your Ducklake
INSTALL ducklake;
INSTALL postgres;

CREATE SECRET (
    TYPE postgres,
    HOST 'your-host',
    PORT 6543,
    DATABASE postgres,
    USER 'your-user',
    PASSWORD 'your-password'
);

ATTACH 'ducklake:postgres:dbname=postgres' AS ducklake_catalog;
USE ducklake_catalog;
```

And exploring the datasets that has been written :

```sql
Copy code

-- Explore your data
SHOW TABLES;
SELECT * FROM ducklake_catalog.snapshots();

-- Verify Spark writes
SELECT COUNT(*) FROM spark_sales_data;
SELECT * FROM spark_sales_data LIMIT 5;

-- Time travel queries
SELECT COUNT(*) FROM spark_sales_data AT (VERSION => 1);
```

You understand now that it's really easy to switch between Spark and DuckDB for interactive exploration.

## Looking Forward: The Future of Spark + DuckLake

Working with this integration has been a glimpse into the future of data architectures. While the marriage between Apache Spark and DuckLake is still in its honeymoon phase, it's already showing promise for teams that want the best of both worlds.

What excites me most about this combination is how it preserves the simplicity that makes DuckDB so appealing while unlocking the ecosystem that Spark provides.

The JDBC integration has some rough edges, the partitioning optimization requires manual tuning, and the documentation is still catching up. But these are the growing pains of any powerful new integration.

You can start simple with your existing Spark setup and DuckLake, and leverage after some pure DuckDB workload on top of the same storage.

Give it a try, break things, and let me know what you discover.

### Additional resources

- Video : [https://www.youtube.com/watch?v=hrTjvvwhHEQ](https://www.youtube.com/watch?v=hrTjvvwhHEQ)
- DuckLake documentation : [https://ducklake.select/](https://ducklake.select/)
- Ebook: [The Essential Guide to DuckLake](https://motherduck.com/ducklake-open-table-format-guide/)

### TABLE OF CONTENTS

[Setting Up Our Playground](https://motherduck.com/blog/spark-ducklake-getting-started/#setting-up-our-playground)

[Creating Our First DuckLake](https://motherduck.com/blog/spark-ducklake-getting-started/#creating-our-first-ducklake)

[Two Ways to Read from DuckLake with Spark](https://motherduck.com/blog/spark-ducklake-getting-started/#two-ways-to-read-from-ducklake-with-spark)

[Writing Data: From CSV to DuckLake via Spark](https://motherduck.com/blog/spark-ducklake-getting-started/#writing-data-from-csv-to-ducklake-via-spark)

[Exploring Your Lakehouse with DuckDB CLI](https://motherduck.com/blog/spark-ducklake-getting-started/#exploring-your-lakehouse-with-duckdb-cli)

[Looking Forward: The Future of Spark + DuckLake](https://motherduck.com/blog/spark-ducklake-getting-started/#looking-forward-the-future-of-spark-ducklake)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Real-Time MySQL to MotherDuck Streaming with Streamkap: A Shift Left Architecture Guide](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FStreaming_vs_Batch_2_2cf6af7a6d.png&w=3840&q=75)](https://motherduck.com/blog/streamkap-mysql-to-motherduck/)

[2025/08/07 - Oli Dinov](https://motherduck.com/blog/streamkap-mysql-to-motherduck/)

### [Real-Time MySQL to MotherDuck Streaming with Streamkap: A Shift Left Architecture Guide](https://motherduck.com/blog/streamkap-mysql-to-motherduck)

Build real-time MySQL to MotherDuck pipelines with Streamkap. Learn Shift Left architecture, streaming CDC, and how to replace batch ETL for instant analytics and customer dashboards.

[![DuckDB Ecosystem: August 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Faugust_newsletter_a2b0e56b97.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2025/)

[2025/08/07 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2025/)

### [DuckDB Ecosystem: August 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2025)

DuckDB Monthly #32: DuckDB hits 50.7% growth—vector search, WASM, and analytics take the spotlight

[View all](https://motherduck.com/blog/)

Authorization Response