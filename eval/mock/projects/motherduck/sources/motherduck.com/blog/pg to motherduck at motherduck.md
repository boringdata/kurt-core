---
title: pg to motherduck at motherduck
content_type: tutorial
source_url: https://motherduck.com/blog/pg to motherduck at motherduck
indexed_at: '2025-11-25T19:57:54.295856'
content_hash: 5d805d8dcee50774
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Using MotherDuck at MotherDuck: Loading Data from Postgres with DuckDB

2025/03/07 - 7 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)
,
[Andrew Witten](https://motherduck.com/authors/Andrew%20Witten/)

## Introduction

At MotherDuck, we use MotherDuck internally for our own cloud data warehouse. As such, we need visibility into how our database tables change over time from some internal services. Specifically, we need to analyze five critical operational tables from a Postgres database that tracks user interactions, database states, and system performance. Of course, since MotherDuck is built on DuckDB, we can use the [DuckDB pg\_scanner](https://duckdb.org/docs/stable/extensions/postgres.html) to easily get at data in Postgres.

Using [MotherDuck’s dual execution](https://motherduck.com/docs/key-tasks/running-hybrid-queries/) as a bridge, we've created a simple, reliable workflow that runs every 6 hours via a scheduled job. The entire process typically completes in about 10 minutes, replicating about 150GB of data.

In this post, you'll see exactly how we implemented this solution, with concrete examples you can test yourself.

## The Problem

Our operational Postgres database contains tables that track essential metrics about our service. These tables update frequently, and our analytics team needs reliable and performant access to up-to-date copies without impacting production performance. We considered traditional approaches like:

1. Direct queries to production (too resource-intensive)
2. Complex ETL pipelines (too much maintenance overhead)
3. CDC solutions (often complex to set up and maintain)

All fell short of our requirements for simplicity and reliability, and critically added additional dependencies to our SWE team.

## The Architecture

Our solution leverages three specific components in a straightforward architecture:

![image1.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_074eff6b39.png&w=3840&q=75)

This visual representation shows exactly what happens during each sync:

1. DuckDB connects to our Postgres database using the Postgres Scanner extension
2. It reads the complete contents of the five tables we need to replicate
3. Using `CREATE OR REPLACE TABLE`, it pushes fresh, complete copies to MotherDuck, replacing previous versions

You can verify this process works by checking that data in MotherDuck exactly matches the source Postgres database at the recorded sync time.

## The Code: Concrete Implementation

Here's the implementation we use in production. You can run this code yourself to test the approach.

It should be noted that this is simply SQL, wrapped in python. We will share the SQL here first, and then the actual python subsequently.

```sql
Copy code

$ duckdb md:
INSTALL postgres;
LOAD postgres;
-- Strings PG_CONNECTION_STRING and MD_DATABASE get replaced.
ATTACH 'PG_CONNECTION_STRING' AS pg (TYPE POSTGRES, READ_ONLY);
ATTACH 'md:MD_DATABASE';
USE MD_DATABASE;
CREATE OR REPLACE TABLE first_table AS SELECT * FROM pg.first_table;
-- continue on for N tables using this pattern
```

### Step 1: Attach both databases

First, we establish connections to both Postgres and MotherDuck:

```py
Copy code

def run():
    # Read from environment variables in production
    pg_connection_string = "postgresql://username:password@hostname:5432/dbname"
    md_database = "analytics_replica"

    # Create a local DuckDB connection as the intermediary
    duck_con = duckdb.connect()

    # Attach to Postgres (read-only to ensure safety)
    duck_con.sql(f"ATTACH '{pg_connection_string}' AS pg (TYPE POSTGRES, READ_ONLY);")

    # Attach to MotherDuck and set it as the active database
    duck_con.sql(f"ATTACH 'md:{md_database}'; USE {md_database}")

    # Execute replication
    ctas_from_diff_db(duck_con)
    last_sync_time(duck_con)
```

You can test this by replacing the connection strings with your own and running the script.

### Step 2: Replicate the tables

Here's the exact function that handles the table replication:

```py
Copy code

def ctas_from_diff_db(duck_con):
    # Replicate the first table
    start_time = time.time()
    duck_con.sql("CREATE OR REPLACE TABLE first_table AS SELECT * FROM pg.first_table;")
    print(f"Replicated first_table table in {time.time() - start_time:.2f} seconds")

    # repeat for N tables you want replicate
    ...
```

The output will show you exactly how long each table takes to replicate.

### Step 3: Track the sync timestamp

To maintain an audit trail of sync operations, we record the exact time when each sync completes. This is useful so that end consumers understand the freshness of the data when they use it to make decisions, and for automated freshness checks.

```py
Copy code

def last_sync_time(duck_con):
    duck_con.sql(
        "CREATE OR REPLACE TABLE last_sync_time AS SELECT current_timestamp AS last_sync_time;"
    )

    # Verify the timestamp was recorded
    result = duck_con.sql("SELECT * FROM last_sync_time").fetchall()
    print(f"Sync completed and recorded at: {result[0][0]}")
```

You can verify the synchronization by comparing data in your source and destination:

```py
Copy code

# Check row counts match between source and destination
source_count = duck_con.sql("SELECT COUNT(*) FROM pg.databases").fetchone()[0]
dest_count = duck_con.sql("SELECT COUNT(*) FROM databases").fetchone()[0]

print(f"Source database has {source_count} rows")
print(f"Destination has {dest_count} rows")
assert source_count == dest_count, "Row counts don't match!"
```

## Why This Workflow Works (And When It Doesn't)

This approach has specific strengths and limitations that you should understand before implementing:

**Strengths:**

1. **Zero additional infrastructure**: The entire process runs using just DuckDB, Postgres, and MotherDuck - no need for additional services or middleware.
2. **Simplicity**: Using `CREATE OR REPLACE TABLE` means we don't need complex incremental logic or change tracking mechanisms.
3. **Transactional consistency**: Since each table is copied as a complete snapshot in a single transaction, consistent point-in-time copies are assured. Transactions could also be used explicitly in your SQL statements if desired.
4. **Low maintenance**: No need to track deltas, manage watermarks, or handle complex merge logic.

**Limitations of this approach:**

1. **Only practical for smaller tables**: Since we're doing a full refresh each time, this approach is only practical for tables with up to tens of millions of rows. We've found it works well into the hundreds of GBs.
2. **Reading and writing more data than needed**: This approach re-writes entire tables even if only a small portion changed. While we choose this approach for simplicity, you can use ["poor man's CDC" too](https://www.tobikodata.com/blog/correctly-loading-incremental-data-at-scale), using timestamps to incrementally insert new data.
3. **Not suitable for very frequent syncs**: Given the full-table approach, running this more frequently than every few minutes would be inefficient.

You can test these limitations yourself by trying tables of different sizes and observing how sync time scales with row count.

## Using MotherDuck at MotherDuck: Real-World Application

We've been running this exact process in production for months. Here's what our actual workflow looks like:

1. Our function executes every 6 hours
2. It replicates the five tables described above by completely refreshing them
3. Our analytics team has dashboards that show:
   - Database growth trends over time
   - Snapshot creation patterns
   - System performance metrics

The concrete benefit: Our team can analyze operational data without writing complex queries against production or managing elaborate data pipelines.

You can verify the value of this approach yourself by setting up a similar workflow and measuring:

- Time spent on maintaining data pipelines before vs. after
- Query performance on MotherDuck vs. direct Postgres queries
- Ability to perform temporal analysis with historical data

## How to Implement This Yourself: A Concrete Guide

1. **Set up your environment**:

```
Copy code

pip install duckdb
```

2. **Create this test script** (replace with your connection details):

```py
Copy code

import duckdb

# Connect to DuckDB
duck_con = duckdb.connect()

# Install and load the postgres extension if needed
duck_con.sql("INSTALL postgres; LOAD postgres;")

# Attach to your Postgres database (replace with your connection string)
duck_con.sql("ATTACH 'postgresql://user:pass@localhost:5432/mydb' AS pg (TYPE POSTGRES, READ_ONLY);")

# Attach to MotherDuck (replace with your token and database)
duck_con.sql("ATTACH 'md:mydb' (TOKEN 'your_token'); USE mydb")

# Replicate a test table
duck_con.sql("CREATE OR REPLACE TABLE test_table AS SELECT * FROM pg.test_table LIMIT 1000;")

# Record sync time
duck_con.sql("CREATE OR REPLACE TABLE last_sync_time AS SELECT current_timestamp AS last_sync_time;")

# Verify
print("Source data preview:")
print(duck_con.sql("SELECT * FROM pg.users LIMIT 5").fetchall())

print("nReplicated data preview:")
print(duck_con.sql("SELECT * FROM test_table LIMIT 5").fetchall())

print("nSync completed at:")
print(duck_con.sql("SELECT * FROM last_sync_time").fetchall())
```

3. **Run the script and verify the results**: Check that data in your source and destination match, and that the sync time is recorded correctly.

## Next Steps

Now that you've seen a concrete implementation of our approach, you can:

1. [Create a MotherDuck account](https://motherduck.com/signup) and get your API token
2. Install DuckDB and the Postgres extension
3. Run the test script with your own connection details
4. Adapt our production script to replicate your own tables

If you implement this solution, you can verify its effectiveness by:

- Comparing query performance between direct Postgres queries and MotherDuck queries
- Measuring the time it takes to replicate different table sizes
- Testing how schema changes affect the replication process

We'd love to hear about your experience implementing this solution. Does it match our results? Did you find ways to improve it? Let us know!

### TABLE OF CONTENTS

[Introduction](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/#introduction)

[The Problem](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/#the-problem)

[The Architecture](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/#the-architecture)

[The Code: Concrete Implementation](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/#the-code-concrete-implementation)

[Why This Workflow Works](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/#why-this-workflow-works)

[Using MotherDuck at MotherDuck: Real-World Application](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/#using-motherduck-at-motherduck-real-world-application)

[How to Implement This Yourself: A Concrete Guide](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/#how-to-implement-this-yourself-a-concrete-guide)

[Next Steps](https://motherduck.com/blog/pg%20to%20motherduck%20at%20motherduck/#next-steps)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Effortless ETL for Unstructured Data with MotherDuck and Unstructured.io](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FUnstructured_io_connector_d2dc34c093.png&w=3840&q=75)](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/)

[2025/02/20 - Adithya Krishnan](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/)

### [Effortless ETL for Unstructured Data with MotherDuck and Unstructured.io](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck)

In this tutorial, learn how to load unstructured data into MotherDuck with Unstructured.io to build modern data pipelines and business applications that turn unstructured data intro structured data.

[![DuckDB, MotherDuck, and Estuary: A Match Made for Your Analytics Architecture](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FEstuary_blog_4b9b0c4ce0.png&w=3840&q=75)](https://motherduck.com/blog/estuary-streaming-cdc-replication/)

[2025/03/06 - Daniel Palma, Emily Lucek](https://motherduck.com/blog/estuary-streaming-cdc-replication/)

### [DuckDB, MotherDuck, and Estuary: A Match Made for Your Analytics Architecture](https://motherduck.com/blog/estuary-streaming-cdc-replication)

Stream data to MotherDuck with Estuary

[View all](https://motherduck.com/blog/)

Authorization Response