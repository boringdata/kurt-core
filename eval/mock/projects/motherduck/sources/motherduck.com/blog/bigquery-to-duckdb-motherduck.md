---
title: bigquery-to-duckdb-motherduck
content_type: tutorial
source_url: https://motherduck.com/blog/bigquery-to-duckdb-motherduck
indexed_at: '2025-11-25T19:56:18.796961'
content_hash: aca8539d1a3772f2
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# From BigQuery to DuckDB and MotherDuck : Efficient Local and Cloud Data Pipelines

2025/05/30 - 8 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

BigQuery has been a cornerstone OLAP database for over a decade. However, today we have more options—especially for local development—that offer a smoother and more flexible experience.

DuckDB stands out for local workflows, but it can also interoperate with BigQuery during the development phase and offload some of the compute to MotherDuck, DuckDB's cloud backend.

In addition, BigQuery hosts several well-maintained public datasets like PyPI download statistics and Hacker News activity.

In this blog post, we’ll explore two great options for seamlessly loading data from BigQuery into DuckDB and MotherDuck.

We'll use the [DuckDB CLI](https://motherduck.com/docs/getting-started/interfaces/connect-query-from-duckdb-cli/) for demonstration, but any client (e.g., Python) will work:

```python
Copy code

import duckdb

# Create an in-memory DuckDB connection
conn = duckdb.connect()

# Run SQL queries
conn.sql('SELECT * FROM my_table;')
```

## DuckDB BigQuery community extension

The [duckdb-bigquery](https://github.com/hafenkran/duckdb-bigquery) community extension is one of the most downloaded DuckDB extensions!

You can inspect the download stats from the last week (e.g., May 19, 2025) using:

```sql
Copy code

UNPIVOT (
    SELECT 'community' AS repository, *
        FROM 'https://community-extensions.duckdb.org/downloads-last-week.json'
    )
ON COLUMNS(* EXCLUDE (_last_update, repository))
INTO NAME extension VALUE downloads_last_week
ORDER BY downloads_last_week DESC;
```

```yaml
Copy code

┌────────────┬─────────────────────┬───────────────┬─────────────────────┐
│ repository │    _last_update     │   extension   │ downloads_last_week │
│  varchar   │      timestamp      │    varchar    │        int64        │
├────────────┼─────────────────────┼───────────────┼─────────────────────┤
│ community  │ 2025-05-21 07:28:50 │ arrow         │              163603 │
│ community  │ 2025-05-21 07:28:50 │ shellfs       │               71496 │
│ community  │ 2025-05-21 07:28:50 │ h3            │               26729 │
│ community  │ 2025-05-21 07:28:50 │ zipfs         │               22344 │
│ community  │ 2025-05-21 07:28:50 │ bigquery      │               21678 │
```

The BigQuery extension is in the top 5, with over 21k downloads last week.

INFO: Extensions Types
Core extensions are officially maintained by DuckDB Labs and are usually auto-installed/loaded. [Community extensions](https://duckdb.org/community_extensions/) are built and published by the community. To install them, use: `INSTALL <community_extension> FROM COMMUNITY` and then `LOAD <community_extension>`

### Prerequisites and Installation

To use the BigQuery extension, you'll need valid [Google Cloud credentials](https://cloud.google.com/docs/authentication/application-default-credentials). You can either:

- Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to a service account file.
- Or run `gcloud auth application-default login` to generate credentials stored at `$HOME/.config/gcloud/application_default_credentials.json`

In terms of permission, the user or service account should have at least role of [BigQuery Data Editor](https://cloud.google.com/bigquery/docs/access-control) and [BigQuery Job User](https://cloud.google.com/bigquery/docs/access-control#bigquery.jobUser).

After launching a DuckDB session with the CLI :

```bash
Copy code

$ duckdb
```

You can then install the DuckDB community extension by :

```sql
Copy code

INSTALL bigquery FROM community;
LOAD bigquery;
```

Now `ATTACH` a BigQuery project like any other database:

```sql
Copy code

ATTACH 'project=my-gcp-project' as bq (TYPE bigquery, READ_ONLY);
```

INFO: How to find your Project ID?
A [Project ID](https://cloud.google.com/resource-manager/docs/creating-managing-projects#:~:text=A%20project%20ID%20is%20a,all%20others%20in%20Google%20Cloud.) is a globally unique identifier for your GCP project. It's visible in the Google Cloud Console project picker or by running: `gcloud projects list`

Once attached, querying your dataset is simple:

```sql
Copy code

SELECT * FROM bq.<dataset_name>.<table_name> LIMIT 5;
```

### Example: querying the PyPI public dataset

Let's query the PyPI public dataset, which logs Python package downloads.
Since it's a public dataset, you must set a **billing project** (=your own GCP project with billing enabled):

```sql
Copy code

ATTACH 'project=bigquery-public-data dataset=pypi billing_project=my-gcp-project' AS bigquery_public_data (TYPE bigquery, READ_ONLY);
```

Then query:

```sql
Copy code

SELECT
      timestamp,
      country_code,
      url,
      project,
      file,
      details,
      tls_protocol,
      tls_cipher
  FROM
      bigquery_public_data.pypi.file_downloads
  WHERE
      project = 'duckdb'
      AND "timestamp" = TIMESTAMP '2025-05-26 00:00:00'
  LIMIT 100;
```

WARNING: Large Table Warning
This table is **very large**. Filter by both "project" and "timestamp" (it's partitioned on timestamp) to avoid high costs.

Behind the scene, this is doing a scan, you have actually explicitly two functions to query Bigquery :
Now you can start querying data from your project. You have two main options

1. **bigquery\_scan()** – Best for reading a single table efficiently with simple projections:

```sql
Copy code

SELECT * FROM bigquery_scan('my_gcp_project.quacking_dataset.duck_tbl');
```

2. **bigquery\_query** to run custom [GoogleSQL](https://cloud.google.com/bigquery/docs/introduction-sql) read queries within your BigQuery project. Recommended for large table with filter pushdowns

```sql
Copy code

SELECT * FROM bigquery_query('my_gcp_project', 'SELECT * FROM `my_gcp_project.quacking_dataset.duck_tbl`');
```

### Load data into MotherDuck

Now if you want to load your data to MotherDuck, simply connect to MotherDuck with another attach command using `ATTACH 'md:'` , assuming that you have a `motherduck_token` set as an environment variable.

```sql
Copy code

ATTACH 'md:'
```

Let's create a cloud database to store our data :

```sql
Copy code

CREATE DATABASE IF NOT exists pypi_playground
```

Now you can do a simple copy data to MotherDuck using a `CREATE TABLE ... AS` or `INSERT INTO ... SELECT` if you want to insert data into an existing table :

```sql
Copy code

CREATE TABLE IF NOT EXISTS pypi_playground.duckdb_sample AS SELECT
        timestamp,
        country_code,
        url,
        project,
        file,
        details,
        tls_protocol,
        tls_cipher
    FROM
        bigquery_public_data.pypi.file_downloads
    WHERE
        project = 'duckdb'
        AND "timestamp" = TIMESTAMP '2025-05-26 00:00:00'
    LIMIT 100;
```

This process is a key step in creating a two-tier architecture, where MotherDuck acts as a [high-performance serving layer for live data applications](https://motherduck.com/learn-more/modern-data-warehouse-use-cases/), augmenting your existing data warehouse.

## Using Google's Python SDK for BigQuery

Google has a [Python SDK for BigQuery](https://cloud.google.com/python/docs/reference/bigquery/latest/index.html) which supports fast data transfer into Arrow tables.
If you want to optimize performance for your ETL pipelines—especially when working with large tables and filter pushdown—using Arrow results can be significantly faster, as they enable zero-copy interaction with DuckDB.

Here are the high-level steps when using the Python SDK : BigQuery -> PyArrow table -> DuckDB and/or MotherDuck

You can install the Python library with :

```bash
Copy code

$ pip install google-cloud-bigquery[bqstorage]
```

The "extras" option `[bqstorage]` install `google-cloud-bigquery-storage`. By default, the `google-cloud-bigquery` client uses the **standard BigQuery API** to read query results. This is fine for small results, but **much slower and less efficient** for large datasets.

When you install the `bqstorage` extra, you're enabling use of the **BigQuery Storage API**, which:

- Streams large query results in parallel.
- Uses Apache Arrow (via `pyarrow` package) for fast in-memory columnar data access.
- Supports high-throughput data transfers directly into Pandas or NumPy structures.

Let's start by creating some helper functions to get the BigQuery client `get_bigquery_client()` and run a given SQL and return an arrow table `get_bigquery_result()`

```python
Copy code

import os
from google.cloud import bigquery
from google.oauth2 import service_account
from google.auth.exceptions import DefaultCredentialsError
import logging
import time
import pyarrow as pa
import duckdb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_bigquery_client(project_name: str) -> bigquery.Client:
    """Get Big Query client"""
    try:
        service_account_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        if service_account_path:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path
            )
            bigquery_client = bigquery.Client(
                project=project_name, credentials=credentials
            )
            return bigquery_client

        raise EnvironmentError(
            "No valid credentials found for BigQuery authentication."
        )

    except DefaultCredentialsError as creds_error:
        raise creds_error

def get_bigquery_result(
    query_str: str, bigquery_client: bigquery.Client
) -> pa.Table:
    """Get query result from BigQuery and yield rows as dictionaries."""
    try:
        # Start measuring time
        start_time = time.time()
        # Run the query and directly load into a DataFrame
        logging.info(f"Running query: {query_str}")
        pa_tbl = bigquery_client.query(query_str).to_arrow()
        # Log the time taken for query execution and data loading
        elapsed_time = time.time() - start_time
        logging.info(
            f"BigQuery query executed and data loaded in {elapsed_time:.2f} seconds")
        # Iterate over DataFrame rows and yield as dictionaries
        return pa_tbl

    except Exception as e:
        logging.error(f"Error running query: {e}")
        raise
```

Once we get a `Pyarrow` table, loading data to DuckDB and/or MotherDuck is similar to what we did above with the `duckdb-bigquery` extension. We'll use an attach command (`ATTACH 'md:'`) to connect to MotherDuck, then either use a `CREATE TABLE ... AS` or `INSERT INTO ... AS` statements to load data.
The Pyarrow table object can directly be query as it would be a DuckDB table.

```python
Copy code

def create_duckdb_table_from_arrow(
    pa_table: pa.Table,
    table_name: str,
    database_name: str = "bigquery_playground",
    db_path: str = None
) -> None:
    """
    Create a DuckDB table from PyArrow table data.

    Args:
        pa_table: PyArrow table containing the data
        table_name: Name of the table to create in DuckDB
        database_name: Name of the database to create/use (default: bigquery_playground)
        db_path: Database path - use 'md:' prefix for MotherDuck, file path for local or just :memory: for in-memory
    """
    try:
        # Connect to DuckDB
        if db_path.startswith("md:"):
            # check env var motherduck_token
            if not os.environ.get("motherduck_token"):
                raise EnvironmentError(
                    "motherduck_token environment variable is not set")
        conn = duckdb.connect(db_path)
        # Create database if not exists
        conn.sql(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        conn.sql(f"USE {database_name}")
        # Create table from PyArrow table
        conn.sql(
            f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM pa_table")
        logging.info(
            f"Successfully created table '{table_name}' in database '{database_name}' with {len(pa_table)} rows to {db_path}")

    except Exception as e:
        logging.error(f"Error creating DuckDB table: {e}")
        raise
```

we can now create the pipeline and calling the above functions :

```python
Copy code

if __name__ == "__main__":
    bigquery_client = get_bigquery_client("my-gcp-project")
    pa_table = get_bigquery_result("""SELECT *
    FROM
        `bigquery-public-data.pypi.file_downloads`
    WHERE
        project = 'duckdb'
        AND timestamp >= TIMESTAMP("2025-05-19")
        AND timestamp < TIMESTAMP("2025-05-20")""", bigquery_client)
    create_duckdb_table_from_arrow(
        pa_table, "pypi_file_downloads", db_path="md:")
```

Running the full pipeline with `python ingest_bigquery_data.py`, we loaded 873k rows from BigQuery to MotherDuck in less than `20s` !

```bash
Copy code

2025-05-27 09:45:52 - INFO - Running query: SELECT *
    FROM
        `bigquery-public-data.pypi.file_downloads`
    WHERE
        project = 'duckdb'
        AND timestamp >= TIMESTAMP("2025-05-19")
        AND timestamp < TIMESTAMP("2025-05-20")
2025-05-27 09:46:03 - INFO - BigQuery query executed and data loaded in 7.20 seconds
2025-05-27 09:46:11 - INFO - Successfully created table 'pypi_file_downloads' in database 'bigquery_playground' with 837122 rows to md:
```

Check the full Python gist [here](http://motherduck.com/docs/integrations/databases/bigquery/#python-end-to-end-pipeline-example).

## BigQuery loves ducks

Both the `duckdb-bigquery` extension and Google's Python SDK make it incredibly easy to move data from BigQuery into DuckDB or MotherDuck.

Check out also the [https://duckdbstats.com/](https://duckdbstats.com/) projects with its [source code](https://github.com/mehd-io/pypi-duck-flow) for another example on how to ingest, transform and serve data in MotherDuck from a BigQuery source dataset.

Keep coding—and keep quacking! 🦆

### TABLE OF CONTENTS

[DuckDB BigQuery community extension](https://motherduck.com/blog/bigquery-to-duckdb-motherduck/#duckdb-bigquery-community-extension)

[Using Google's Python SDK for BigQuery](https://motherduck.com/blog/bigquery-to-duckdb-motherduck/#using-googles-python-sdk-for-bigquery)

[BigQuery loves ducks](https://motherduck.com/blog/bigquery-to-duckdb-motherduck/#bigquery-loves-ducks)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Feu_launch_blog_b165ff2751.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-in-europe/)

[2025/09/24 - Garrett O'Brien, Sheila Sitaram](https://motherduck.com/blog/motherduck-in-europe/)

### [MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/blog/motherduck-in-europe)

Serverless analytics built on DuckDB, running entirely in the EU.

[![DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_4_1_b6209aca06.png&w=3840&q=75)](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)

[2025/10/09 - Alex Monahan, Garrett O'Brien](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)

### [DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/blog/announcing-duckdb-141-motherduck)

MotherDuck now supports DuckDB 1.4.1 and DuckLake 0.3, with new SQL syntax, faster sorting, Iceberg interoperability, and more. Read on for the highlights from these major releases.

[View all](https://motherduck.com/blog/)

Authorization Response