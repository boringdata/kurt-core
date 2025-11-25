---
title: making-pyspark-code-faster-with-duckdb
content_type: blog
source_url: https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb
indexed_at: '2025-11-25T19:57:16.311709'
content_hash: 6fc4ca0b381d38f8
has_code_examples: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Making PySpark Code Faster with DuckDB

2023/11/02 - 7 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

Apache Spark has been there for quite a while since its first release in 2014 and it’s a standard for data processing in the data world. Often, team have tried to enforce Spark everywhere to simplify their code base and reduce complexity by limitting the number of data processing frameworks.

Reality is that for a lot of Spark pipelines , especially daily incremental workloads, we don’t need that many resources, and especially that many nodes. Spark ends up running at minimum setup, creating a lot of overhead.

With the latest DuckDB version, the DuckDB team has started the work of offering a Spark API compatibility. It means that you can use the same PySpark code base, but DuckDB under the hood. While this is still heavily experimental and early, I’m excited about this feature and would like to open eyes to its amazing potential.

If are too lazy to read, I also made a video for this tutorial.

Making PySpark code faster with DuckDB - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Making PySpark code faster with DuckDB](https://www.youtube.com/watch?v=RwGAPgsEDlw)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

Full screen is unavailable. [Learn More](https://support.google.com/youtube/answer/6276924)

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=RwGAPgsEDlw&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 10:23

•Live

•

## Challenges of squeezing Spark to minimum setup

Apache Spark has been designed to work on a cluster, and when dealing with small to medium data, having a network overhead makes no sense given the power of the current machines.

There are two reasons why you want sometimes a lightweight setup, meaning a single node Apache Spark with small resource requirements :

- Small pipelines (typically daily/hourly workload)
- Local development setup (unit/integration and end to end tests)

### Cloud’s minimum requirements

The minimum specifications provided by cloud providers for Serverless Spark is often implying a two node cluster.

Let’s take some concrete examples.

Apache Spark Serverless products like AWS Glue authorize a minimum configuration of 2 DPUs. One standard DPU provides 4 vCPU and 16 GB. Billed per second with a 1-minute minimum billing duration. That means at minimum you have 32GB of RAM (!) with 8vcpu that you pay. Plus, you will always pay at least for 1 minute.

Google Cloud’s Serverless dataproc [has roughly the same numbers.](https://cloud.google.com/dataproc-serverless/pricing). Note that Databricks has offered a [single node option](https://docs.databricks.com/en/clusters/single-node.html) since late 2020, but it’s not really a full serverless Spark offering and has some limitations.

### The java boat load

For local Apache Spark, it’s difficult to have something lightweight. Especially for PySpark as you basically need Python AND Java. As they are tight dependencies, a current practice is to have a container, and it's challenging to keep the size under 600MB uncompressed. If you look at the official [PySpark image, it’s about](https://hub.docker.com/r/apache/spark-py/tags) 987MB uncompressed.

On the other side, because DuckDB can be installed with just a Python package, the following base image takes only 216MB.

```jsx
Copy code

FROM python:3.11-slim
RUN pip install duckdb
```

Of course, we can make both sides more efficient, but this gives you an idea of how much you could save with your base container image.

Cutting down on container image size might seem minor, but it's linked to many things.

Larger images lead to:

- Longer CI (for building, pulling, and pushing) → higher costs
- Longer development time → less productivity

It's important to note the startup time difference between a Python script and an Apache Spark job. Apache Spark's reliance on the JVM leads to a cold start delay, usually under 5 seconds. Though seemingly minor, this makes Python script execution faster, impacting overall development time in iterative processes.

## The flexibility of switching the execution engine

Today, many people adopt the strategy of putting their data on an object storage, typically a data lake / lakehouse and levaraging open format like Parquet or table format like Delta Lake, Hudi or Iceberg.

For pure SQL users, switching to different compute engine (assuming the SQL dialect is compatible) starts to be a reality through the usage of dbt and [their different adapters](https://docs.getdbt.com/reference/dbt-jinja-functions/adapter). You can send the same SQL code against different compute engine.

So, why wouldn't it be possible for Apache Spark to use a different execution engine with the same code?

Enter PySpark powered by DuckDB.

## A first entry point to DuckDB for PySpark users

The DuckDB team has released as part of v.0.9 an experimental PySpark API compatibility. While this one is still limited, let’s get a glimpse on its promises. You can find the complete code used below on this [repository](https://github.com/mehd-io/duckdb-pyspark-demo).
Let's start with a git clone.

```bash
Copy code

git clone https://github.com/mehd-io/duckdb-pyspark-demo
```

First, we need some data and we’ll be using the open dataset from [Hacker News](https://motherduck.com/docs/getting-started/sample-data-queries/hacker-news/) that MotherDuck is hosting.

We’ll be downloading the Parquet dataset that sits on S3 locally with the following command. Size is about 1GB :

```sql
Copy code

make data
```

You now should have the data located in `./data` folder.

Our PySpark script contains a conditional import that look for an environment variable to be able to switch engine.

```sql
Copy code

import os

# Read the environment variable
use_duckdb = os.getenv("USE_DUCKDB", "false").lower() == "true"

if use_duckdb:
    from duckdb.experimental.spark.sql.functions import avg, col, count
    from duckdb.experimental.spark.sql import SparkSession
else:
    from pyspark.sql.functions import avg, col, count
    from pyspark.sql import SparkSession
```

The rest of the script remains the same! In this pipeline, we are looking if posting more on Hacker News gets you more score on average. Here's a snippet of the main transformation :

```python
Copy code

# Does users who post more stories tend to have higher or lower average scores ?
result = (
    df.filter((col("type") == "story") & (col("by") != "NULL"))
    .groupBy(col("by"))
    .agg(
        avg(col("score")).alias("average_score"),
        count(col("id")).alias("number_of_stories"),
    )
    .filter(col("number_of_stories") > 1)  # Filter users with more than one story
    .orderBy(
        col("number_of_stories").desc(), col("average_score").desc()
    )  # Order by the number of stories first, then by average score
    .limit(10)
)
```

We then run the Pyspark job using DuckDB with :

```python
Copy code

make duckspark
```

```sql
Copy code

real    0m1.225s
user    0m1.970s
sys     0m0.160s
```

And same code using pure Pyspark :

```jsx
Copy code

make pyspark
```

```sql
Copy code

real    0m5.411s
user    0m12.700s
sys     0m1.221s
```

And the data result :

```sql
Copy code

┌──────────────┬────────────────────┬───────────────────┐
│      by      │   average_score    │ number_of_stories │
│   varchar    │       double       │       int64       │
├──────────────┼────────────────────┼───────────────────┤
│ Tomte        │  11.58775956284153 │              4575 │
│ mooreds      │  9.933416303671438 │              3214 │
│ rntn         │   8.75172943889316 │              2602 │
│ tosh         │ 20.835010060362173 │              2485 │
│ rbanffy      │ 7.7900505902192245 │              2372 │
│ todsacerdoti │  32.99783456041576 │              2309 │
│ pseudolus    │ 20.024185587364265 │              2026 │
│ gmays        │ 12.595103578154426 │              1593 │
│ PaulHoule    │  8.440198159943384 │              1413 │
│ bookofjoe    │ 13.232626188734455 │              1367 │
├──────────────┴────────────────────┴───────────────────┤
│ 10 rows                                     3 columns │
```

As you can see, there's no need to worry about under-posting on Hacker News, as the algorithm doesn't necessarily favor those who post more. 😄

When it comes to performance, it's evident that using DuckDB significantly speeds up the pipeline. While this blog post isn't a comprehensive benchmark for local processing, for a more realistic comparison, check out Niels Claes’s blog on [using DuckDB instead of Spark in dbt pipelines](https://medium.com/datamindedbe/use-dbt-and-duckdb-instead-of-spark-in-data-pipelines-9063a31ea2b5). He did an excellent job using the [TPC-DS](https://www.tpc.org/tpcds/) benchmark, a standard in the industry for comparing database performance.

## **Limitations & Use Cases**

Currently, the API supports reading from **`csv`**, **`parquet`**, and **`json`** formats. So it’s not quite ready for real pipeline usage as writing functions are necessary. Plus, the number of available functions is limited, as you can see [here](https://github.com/duckdb/duckdb/blob/main/tools/pythonpkg/duckdb/experimental/spark/sql/functions.py).

However, you could start using it for unit testing. Unit testing functions in Spark often involve reading data and checking a transformation function in memory, with no writing needed. You could use similar logic to switch between DuckDB and Spark for some tests to speed things up ⚡.

## **Want to Contribute?**

Integrating Spark with DuckDB can accelerate the development process and, in the future, help simplify pipelines, reducing the overhead and costs associated with minimum Spark clusters.

We’ve seen how bypassing the JVM can make pipelines with small data faster and more cost-efficient, especially around development, CI, and execution.

This API marks a significant milestone as the first Python code integrated into DuckDB, predominantly built from C++. Its Python-centric nature offers a unique opportunity for Python enthusiasts to contribute with ease. Dive into the [existing code base](https://github.com/duckdb/duckdb/tree/main/tools/pythonpkg/duckdb/experimental/spark) and explore the [open issues](https://github.com/duckdb/duckdb/issues?q=is%3Aissue+is%3Aopen+Spark+API+). Your input and contributions can make a substantial difference!

Finally, it looks like Spark can quack after all. 🦆

### TABLE OF CONTENTS

[Challenges of squeezing Spark to minimum setup](https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb/#challenges-of-squeezing-spark-to-minimum-setup)

[The flexibility of switching the execution engine](https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb/#the-flexibility-of-switching-the-execution-engine)

[A first entry point to DuckDB for PySpark users](https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb/#a-first-entry-point-to-duckdb-for-pyspark-users)

[Limitations & Use Cases](https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb/#limitations-use-cases)

[Want to Contribute?](https://motherduck.com/blog/making-pyspark-code-faster-with-duckdb/#want-to-contribute)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Analyze Data in Azure with DuckDB or MotherDuck](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fanalyze_data_in_azure_with_duckdb_8ad04edd4c.png&w=3840&q=75)](https://motherduck.com/blog/analyze-data-in-azure-with-duckdb/)

[2023/11/01 - David Neal](https://motherduck.com/blog/analyze-data-in-azure-with-duckdb/)

### [Analyze Data in Azure with DuckDB or MotherDuck](https://motherduck.com/blog/analyze-data-in-azure-with-duckdb)

Analyze data stored in Azure blob storage using DuckDB or MotherDuck

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response