---
title: json-log-analysis-duckdb-motherduck
content_type: tutorial
source_url: https://motherduck.com/blog/json-log-analysis-duckdb-motherduck
indexed_at: '2025-11-25T19:56:31.228254'
content_hash: 7d1a83f6985c5371
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# The Data Engineer's Guide to Efficient Log Parsing with DuckDB/MotherDuck

2025/04/18 - 24 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

As data engineers, we spend countless hours combing through logs - tracking pipeline states, monitoring Spark cluster performance, reviewing SQL queries, investigating errors, and validating data quality. These **logs are the lifeblood of our data platforms**, but parsing and analyzing them efficiently remains a persistent challenge. This comprehensive guide explores why **data stacks are fundamentally built on logs** and why skilled log analysis is critical for the data engineer's success.

Throughout this article, we'll categorize the various log types and formats you'll encounter in your daily work, compare popular analysis tools, and most importantly, demonstrate practical, code-driven examples of parsing complex logs using DuckDB. You'll see how DuckDB's super fast parsers and flexible SQL syntax make it an ideal tool for log analysis across various formats including JSON, CSV, and syslog files.

For those working with larger datasets, we'll also show how to analyze massive JSON log datasets at scale with MotherDuck, providing optimized query patterns for common log analysis scenarios. Whether you're troubleshooting pipeline failures, monitoring system health, or extracting insights from operational metadata, this guide will help you transform log analysis from a tedious chore into a powerful competitive advantage for your data team.

## Understanding Log Types and Their Purpose in Data Engineering

The questions would be, " **What are we using logs for?**", "What information is there?", and "What are these logs specifically for?" for data engineering workloads.

### Categories of logs (application logs, system logs, etc.)

There are various logs. To better understand them, we need to know who is producing them. Let's look at the **categories** of logs and the file formats they are usually in.

From a high-level perspective, we have different domains like application logs, system logs, error logs, and transaction logs:
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg1log_241785f984.png&w=3840&q=75)
Different categories of LogFiles \| Image from [What is a Log File?](https://zenduty.com/blog/log-file/)

As a data engineer, you'll typically need to analyze **several types of logs** to monitor, troubleshoot, and optimize data pipelines and systems.

Besides there being many more logs (like Security, Perimeter Device, Windows or Endpoint Log and many more), these are the major logs you'll encounter most of the time:

- Operational Logs:
  - **Application Logs**: Track events within data processing applications, ETL tools, and analytics platforms, capturing pipeline execution details, transformations, and failures.
  - **System Logs**: Monitor infrastructure health when run in Kubernetes or similar platforms for data workloads, helping diagnose resource constraints and system-level failures.
  - **Error Logs**: Critical for troubleshooting failed data jobs and pipelines, identifying bottlenecks and failure points in workflows.
- Data Management Logs:
  - **Data Pipeline Logs**: Changes and logs of orchestration tools documenting each step; essential for recapitulating what happened and finding bugs in case of errors.
  - **Transaction Logs**: Track database operations and changes to ensure data integrity, critical for recovery and auditing.
  - **Audit Logs**: Document changes to data schemas, permissions, and configurations, essential for compliance and data governance.
  - **IoT Logs**: Capture data from Internet of Things devices and sensors.
- Security and Access Logs:
  - **Access Logs**: Monitor who's accessing data systems and when, important for security and compliance.
  - **Network Logs**: Track data movement across systems, useful for monitoring transfer performance and detecting issues.

#### Different Types of Metadata

On a high level, we have different types of Metadata: social, technical, business, and operational. What we, as data engineers, mostly deal with are operational logs like job schedules, run times, data quality issues, and, most critically, error logs.

![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg2log_4cf45f458e.png&w=3840&q=75)
Different types of metadata \| Image by [Eckerson Group on LinkedIn](https://www.linkedin.com/posts/eckerson-group_metadata-datamanagement-priority-activity-7130555043962855425-ysL3)

These operational data logs are called pipeline and execution metadata logs. They have certain formats and types (technical aspect), contain business terms in some cases, and have some social and business impact on the people and the organization.

INFO: A new emerging term: Meta Grid
There is also a newer term called Meta Grid, see the book [Fundamentals of Metadata Management](https://www.oreilly.com/library/view/fundamentals-of-metadata/9781098162818/) by Ole Olesen-Bagneux that talks about metadata in a deeper way and [compares it to data mesh and microservices architectures](https://olesenbagneux.medium.com/the-meta-grid-is-the-third-wave-of-data-decentralization-b18827711cec).

Let's now look at how these logs appear and what formats they use.

### Data Types and Formats of Data Logs

What information does a log typically hold? Log files hold various data types, but two are always present: timestamp and some **log, error or message**.

Further columns could include a user, event type (like a specific action or occurrence that triggered it), or running application (e.g., started within Airflow). Others include system errors and any metadata that helps debug the errors.

These logs come in all shapes, styles, and formats. Most common are **structured logs** for metadata as JSON or key-value pairs and **plaintext-based logs** for execution sequences often in syslog-like formats. The JSON format has the advantage of a flexible schema, meaning columns can change each time, and the producers don't need to think about types or fit into a pre-defined structure—leaving that job to the analyst later.

A range of different log formats is shown below.

#### Structured Formats

- JSON: Most common. JSON provides a hierarchical structure with nested objects and arrays, making it ideal for complex logging needs while remaining machine-parsable.

```json
Copy code

{
"timestamp": "2024-11-19T08:15:12Z",
"level": "INFO",
"service": "data-pipeline",
"message": "ETL job completed",
"job_id": "12345",
"records_processed": 10000,
"duration_ms": 45000
}
```

- **CSV/TSV**: Used for logging tabular data. This format is compact and easily imported into spreadsheet software or databases, though it lacks descriptive field names unless headers are included.

```kotlin
Copy code

2024-11-19 08:15:12,INFO,data-pipeline,ETL job completed,12345,10000,45000
```

- **Key-Value Pairs**: Common in many logging systems. This format offers a good balance between human readability and machine parseability while remaining flat and avoiding the overhead of more structured formats.

```ini
Copy code

timestamp=2024-11-19T08:15:12Z level=INFO service=data-pipeline message="ETL job completed" job_id=12345 records_processed=10000 duration_ms=45000
```

#### Semi-structured Formats

- **[Syslog Format](https://en.wikipedia.org/wiki/Syslog)**: A standardized format that includes a priority field, a header with information like timestamps and hostnames, and the actual message content. This format allows for centralized logging and easy analysis of logs across different systems and applications.

```ini
Copy code

Nov 19 08:15:12 dataserver01 data-pipeline[12345]: ETL job completed successfully
```

#### Common Event Format (CEF)

- **CEF**: Used in security and event management systems. This vendor-neutral format was developed by ArcSight and has become widely adopted for security event interchange between different security products and security information and event management (SIEM) systems.

```makefile
Copy code

CEF:0|Vendor|Product|Version|Signature ID|Name|Severity|Extension
```

#### `.log` File

The .log-file is a common file extension used for logging data, but **not a format itself**. The `.log` extension indicates that the file contains log information, while the actual content could be any of the previously mentioned formats.

## Why Data Stacks Are Built on Logs

As data engineers, we have to deal with all of these various log types and formats because our data pipelines touch the full lifecycle of a business. From reading from many different source systems with potential network latencies or issues, to loading large tables that need more performance, to the whole ETL process where we transform data and need to make sure we don't compromise granularity or aggregated KPIs with duplications or incorrect SQL statements.

Data stacks and data **platforms are essentially built around logs**. We can't debug the data stack; the logs are our way to find the error later on. Software engineers can debug more easily, as they are in control of what the user can and can't do. But data is different, constantly changing and flowing from A to B. We have external producers that we can't influence, and the business and requirements are changing too.

On the consumer side, we have the visualization tools that need to be fast and nice looking. We have security, data management, DevOps on how we deploy it, the modeling and architecture part, and applying software engineering best practices along with versioning, CI/CD, and code deployments. All of this happens under the umbrella of data pipelines and is part of the [Data Engineering Lifecycle](https://www.oreilly.com/library/view/fundamentals-of-data/9781098108298/ch02.html). On each level, we can have different data logs, performance and monitoring logs, data quality checks, and result sets of running pipelines with their sub-tasks.

That's why our data stacks run on metadata, and they are as important today as they were two decades ago. However, with more sophisticated tools, we can now analyze and present them more efficiently.

INFO: Data Orchestration Trends Relating to Logs
In the [Data Orchestration Trends: The Shift From Data Pipelines to Data Products](https://airbyte.com/blog/data-orchestration-trends), I highlighted how the trends of pipelines shifted more towards declarative and data products, which also influences our logging. With a code-first approach ( **Data-as-Code**) to data, we can implement reactive logic to logs in a declarative manner. More concretely, we can define annotations of a data pipeline that only runs if a log has `success` written in the log. This is possible with non-declarative and UI-first solutions too, but it is more natural for the code-first solution.

### Log Analysis Use Cases and When to Use Log Files

What are we doing when we analyze logs? Data engineers typically focus on several key use cases:

**Debugging** is the most common use case. As we can't simply use a debugger with complex data pipelines, we must **log our way through problems**. Good logs should **identify** errors clearly. Since we work with complex business logic most of the time, on top of the technical stack, this requires significant expertise from data engineers and is where we can spend much of our time. But the better the logs, the less we need to search, and the more we can focus our time on fixing the bugs.

**Tracing** helps pinpoint the origin of errors in pipelines with many sub-tasks, while **performance analysis** uses logs from BI tools or orchestrators like dbt to identify bottlenecks.

**Error pattern analysis** examines changes over time to prevent recurring issues.

For **monitoring**, we often load logs into tools like [DataDog](https://www.datadoghq.com/), [Datafold](https://www.datafold.com/), [ELK Stack](https://www.elastic.co/elastic-stack), or [InfluxDB](https://www.influxdata.com/use-cases/monitoring/), standardize metrics with [Prometheus](https://prometheus.io/), and visualize using [Grafana](https://grafana.com/). For more, see the next chapter.

### Tools and Solutions for Effective Log Analysis

The tools we use to analyze the logs have changed over time and have become more numerous but also better in quality. Traditionally, we had to do all the log reporting manually. More recently, however, we have monitoring and observability tools with dedicated log analyzer capabilities included. These vary in their specific use cases, but all of them analyze some kind of log.

Here's an overview of some of the different tools, categorized in these two domains: log and monitoring/observability, and the degree of automation and manual effort required. You also see the green mark if the tool is open-source or not.

![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg3log_07176ace8e.png&w=3840&q=75)
Cluster of log parsing and monitoring/observability tools categorized into the degree of automation \| Image by the author

These tools fall into several categories:

- **Auto-profiling solutions** like Bigeye, Monte Carlo, and Metaplane offer automated monitoring with unique features ranging from ML-driven alerts to enterprise data lake integrations
- **Pipeline testing tools** such as Great Expectations, Soda, and dbt tests provide granular validation within data workflows
- **Infrastructure monitoring platforms** including DataDog and New Relic focus on system health and resource utilization
- **Hybrid solutions** like Databand and Unravel unify infrastructure monitoring with data-specific observability

INFO: Side-Note: Kafka Event-Driven Use-Cases
While event streaming platforms like Kafka also use logs, this article focuses on pipeline error and trace logs rather than event-driven architectures. For Kafka analysis, tools like [kwack](https://github.com/rayokota/kwack) and [sql-flow](https://github.com/turbolytics/sql-flow) provide specialized capabilities.

### DuckDB as the Ultimate Log Parser?

But how about using DuckDB as a log parser? Let's imagine we have all the logs parked on an S3 storage or somewhere in our data warehouse. DuckDB is a very efficient tool for quickly analyzing the overall status.

Whereas the above tools are doing real-time monitoring mostly, analyzing what is happening every second and minute, DuckDB can be used to have analytics for the **overall state**. We can have advanced log analysis techniques such as:

- Time-series analysis of log data
- Combining logs from multiple sources
- Creating dashboards and monitoring systems

DuckDB is the **ultimate log parser**. It can run with zero-copy, meaning you don't need to install or insert logs into DuckDB, but you can read from your data lake in S3, from your Snowflake Warehouse, and from your servers via HTTPS server, all within a single binary.

DuckDB has one of the fastest JSON and CSV parsers. This comes in very handy, as we learned that most logs are in these exact formats. The ability to query multiple file formats with consistent SQL syntax and the local processing capabilities that reduce network overhead are just two other big advantages that make DuckDB a great tool for log parsing.

With the extension of MotherDuck, we can simply scale the log analysis in case DuckDB can't handle it, when we want to share quick analytics with a notebook, or when we want to share the data as a shared DuckDB database. You can scale up your parser without making the code more complex, just using a different engine with the same syntax and understanding as DuckDB itself.

## Practical Log Analytics: Analyzing Logs with DuckDB and MotherDuck

Below, we have a look at two datasets: the first one with various formats and the second real-life JSON from Bluesky to benchmark larger log analytics.

### Parsing Various Log Formats with DuckDB

Before we go any further, let's analyze some logs to get a better understanding of what logs are and how they can look. The idea is to analyze completely different log files to understand how to parse them all with DuckDB using various strategies.

INFO: Data Sets Used in This
The data sets used in this part are from two open data sets of [Loghub](https://github.com/logpai/loghub) that provides a large collection of system logs and datasets for log analytics. See download links below.

#### Parsing one big Apache Logs: From Unstructured Text to Actionable Insights

In this first example, we analyze one large log file with 56,481 lines and 4.90MB called `Apache.log` (it is compressed in `.gz`). The size is small, but the log is semi-structured like this, where we have the timestamp, error type, and message. There are also outliers we need to deal with:

```scss
Copy code

[Fri Jun 10 11:32:39 2005] [notice] mod_security/1.9dev2 configured
[Fri Jun 10 11:32:39 2005] [notice] Apache/2.0.49 (Fedora) configured -- resuming normal operations
[Fri Jun 10 11:32:39 2005] [notice] jk2_init() Found child 2337 in scoreboard slot 1
[Fri Jun 10 11:32:39 2005] [notice] jk2_init() Found child 2338 in scoreboard slot 2
[Fri Jun 10 11:32:39 2005] [notice] jk2_init() Found child 2339 in scoreboard slot 3
[Fri Jun 10 11:32:39 2005] [notice] jk2_init() Found child 2342 in scoreboard slot 6
[Fri Jun 10 11:32:39 2005] [notice] jk2_init() Found child 2343 in scoreboard slot 7
script not found or unable to stat
[Fri Jun 10 11:32:39 2005] [notice] jk2_init() Found child 2340 in scoreboard slot 4
[Fri Jun 10 11:32:39 2005] [notice] jk2_init() Found child 2341 in scoreboard slot 5
```

Remember, this is a good opportunity to use an LLM. If you give it the schema description with the first 100 lines, it can do an excellent job of helping us create complex RegExp patterns to parse otherwise randomly looking log files such as the `Apache.log` above. That is exactly what I used initially to generate this:

```sql
Copy code

SELECT
    regexp_extract(line, '\[(.*?)\]', 1) AS timestamp,
    regexp_extract(line, '\[error\]', 0) IS NOT NULL AS is_error,
    regexp_extract(line, '\[client (.*?)\]', 1) AS client_ip,
    regexp_extract(line, '\](.*)', 1) AS message
FROM read_csv('https://zenodo.org/records/8196385/files/Apache.tar.gz?download=1',
    auto_detect=FALSE,
    header=FALSE,
    columns={'line':'VARCHAR'},
    delim='\t', -- Set explicit tab delimiter
    strict_mode=FALSE) -- Disable strict mode to handle multi-column content
LIMIT 5;
```

If we run, we can check if the RegExp works, and can confirm with the result looking like this:

```yaml
Copy code

┌──────────────────────────┬──────────┬───────────┬───────────────────────────────────────────────────────────────────┐
│        timestamp         │ is_error │ client_ip │                              message                              │
│         varchar          │ boolean  │  varchar  │                              varchar                              │
├──────────────────────────┼──────────┼───────────┼───────────────────────────────────────────────────────────────────┤
│ Thu Jun 09 06:07:04 2005 │ true     │           │  [notice] LDAP: Built with OpenLDAP LDAP SDK                      │
│ Thu Jun 09 06:07:04 2005 │ true     │           │  [notice] LDAP: SSL support unavailable                           │
│ Thu Jun 09 06:07:04 2005 │ true     │           │  [notice] suEXEC mechanism enabled (wrapper: /usr/sbin/suexec)    │
│ Thu Jun 09 06:07:05 2005 │ true     │           │  [notice] Digest: generating secret for digest authentication ... │
│ Thu Jun 09 06:07:05 2005 │ true     │           │  [notice] Digest: done                                            │
└──────────────────────────┴──────────┴───────────┴───────────────────────────────────────────────────────────────────┘
```

Let's now **count the errors by client IP** (when available) to get some insights. To do that, we create a table based on the above query to reuse and simplify the following query:

```sql
Copy code

CREATE OR REPLACE TABLE apache_errors AS
SELECT
    regexp_extract(line, '\[(.*?)\]', 1) AS timestamp,
    regexp_extract(line, '\[error\]', 0) IS NOT NULL AS is_error,
    regexp_extract(line, '\[client (.*?)\]', 1) AS client_ip,
    regexp_extract(line, '\](.*)', 1) AS message
FROM read_csv('https://zenodo.org/records/8196385/files/Apache.tar.gz?download=1',
    auto_detect=FALSE,
    header=FALSE,
    columns={'line':'VARCHAR'},
    delim='\t', -- Set explicit tab delimiter
    strict_mode=FALSE); -- Disable strict mode to handle multi-column content
```

Then we can query the IP with the most errors:

```sql
Copy code

SELECT
    client_ip,
    COUNT(*) AS error_count
FROM apache_errors
WHERE is_error AND client_ip IS NOT NULL
GROUP BY client_ip
ORDER BY error_count DESC
LIMIT 10;
```

The result in a couple of seconds:

```sql
Copy code

┌─────────────────┬─────────────┐
│    client_ip    │ error_count │
│     varchar     │    int64    │
├─────────────────┼─────────────┤
│                 │       25367 │
│ 218.144.240.75  │        1002 │
│ 210.245.233.251 │         624 │
│ 211.99.203.228  │         440 │
│ 80.55.121.106   │         322 │
│ 61.152.90.96    │         315 │
│ 212.45.53.176   │         299 │
│ 82.177.96.6     │         289 │
│ 64.6.73.199     │         276 │
│ 81.114.87.11    │         274 │
├─────────────────┴─────────────┤
│ 10 rows             2 columns │
└───────────────────────────────┘
```

#### Handling Big Data Logs: HDFS Example

Another example is the [HDFS Logs](https://zenodo.org/records/8196385/files/HDFS_v1.zip?download=1) that are available on this same [GitHub repo](https://github.com/logpai/loghub). Let's look at how DuckDB can handle HDFS logs, which are common in big data environments.

This dataset is 1.47GB in size and has 11,175,629 lines, but we only look at the one HDFS.log that has more than 11 million rows. If you want to follow along, download the file and unzip it. I unzipped it on `~/data/HDFS_v1`.

Let's now create a table again to simplify our querying:

```sql
Copy code

CREATE OR REPLACE TABLE hdfs_logs AS
SELECT
    SUBSTR(line, 1, 6) AS date,
    SUBSTR(line, 8, 6) AS time,
    regexp_extract(line, 'INFO (.*?): ', 1) AS component,
    regexp_extract(line, 'INFO .*?: (.*)', 1) AS message,
    CASE
        WHEN line LIKE '%blk_%' THEN regexp_extract(line, 'blk_([-0-9]+)', 1)
        ELSE NULL
    END AS block_id
FROM read_csv('~/data/HDFS_v1/HDFS.log',
    auto_detect=FALSE,
    header=FALSE,
    columns={'line':'VARCHAR'},
    delim='\t', -- Set explicit tab delimiter
    strict_mode=FALSE); -- Disable strict mode
```

If we check, we see that we have 11.18 million logs—querying this directly takes about 3 seconds on my MacBook M1.

```scss
Copy code

select count(*) from hdfs_logs;
┌─────────────────┐
│  count_star()   │
│      int64      │
├─────────────────┤
│    11175629     │
│ (11.18 million) │
└─────────────────┘
```

If we plan to query that data often, we could create a `TABLE` again, as shown above. Another interesting query is to analyze block operations in these HDFS logs with this analytical query over our logs:

```sql
Copy code

SELECT
    component,
    COUNT(*) AS operation_count
FROM hdfs_logs
WHERE block_id IS NOT NULL
GROUP BY component
ORDER BY operation_count DESC;
```

The result looks something like this - it reveals the distribution of block operations across different HDFS components, with the NameSystem managing the most operations while DataNode components handle various aspects of data transfer and storage:

```bash
Copy code

┌──────────────────────────────┬─────────────────┐
│          component           │ operation_count │
│           varchar            │      int64      │
├──────────────────────────────┼─────────────────┤
│ dfs.FSNamesystem             │         3699270 │
│ dfs.DataNode$PacketResponder │         3413350 │
│ dfs.DataNode$DataXceiver     │         2162471 │
│ dfs.FSDataset                │         1402052 │
│                              │          362793 │
│ dfs.DataBlockScanner         │          120036 │
│ dfs.DataNode                 │            7002 │
│ dfs.DataNode$DataTransfer    │            6937 │
│ dfs.DataNode$BlockReceiver   │            1718 │
└──────────────────────────────┴─────────────────┘
```

Or we identify potential failures with this query:

```sql
Copy code

SELECT
    block_id,
    COUNT(*) AS log_entries,
    STRING_AGG(DISTINCT component, ', ') AS components
FROM hdfs_logs
WHERE block_id IS NOT NULL
GROUP BY block_id
HAVING COUNT(*) > 10
ORDER BY log_entries DESC
LIMIT 5;
```

The result looks something like this:

```bash
Copy code

┌──────────────────────┬─────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│       block_id       │ log_entries │                                                           components                                                           │
│       varchar        │    int64    │                                                            varchar                                                             │
├──────────────────────┼─────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ -4145674605155741075 │         298 │ dfs.DataNode$DataXceiver, dfs.FSNamesystem, dfs.DataNode$DataTransfer, , dfs.DataNode, dfs.FSDataset, dfs.DataNode$PacketRes…  │
│ -2891794341254261063 │         284 │ dfs.DataNode, dfs.DataNode$DataTransfer, dfs.DataNode$DataXceiver, dfs.DataNode$PacketResponder, dfs.FSDataset, dfs.FSNamesy…  │
│ 2813981518546746323  │         280 │ dfs.DataNode$DataTransfer, dfs.FSNamesystem, dfs.DataNode$DataXceiver, dfs.DataNode$PacketResponder, dfs.FSDataset, dfs.Data…  │
│ -2825351351457839825 │         278 │ dfs.DataNode$PacketResponder, dfs.FSNamesystem, dfs.DataNode$DataXceiver, dfs.DataNode$DataTransfer, dfs.FSDataset, dfs.Data…  │
│ 9014620365357651780  │         277 │ dfs.DataNode$DataTransfer, dfs.FSNamesystem, dfs.DataNode$PacketResponder, dfs.DataNode, dfs.DataNode$DataXceiver, dfs.FSDat…  │
└──────────────────────┴─────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

You can see, with some simple queries, you can either run the query directly on your files, or if you have many files, it's recommended to just create a table, or even unnest some JSON structure to improve query performance. More on this later.

### JSON Log Analytics with Bluesky Data: Scale-Up If Needed

As DuckDB is an analytics tool, besides just parsing logs, we can also create analytics dashboards. In this demo, we do two use cases: first, analyzing the logs directly sitting on S3, with no normalization or unnesting beforehand, once with DuckDB and once with MotherDuck.

Then we unnest JSON files and store them as struct or flat tables, and see how this affects the speed. For more complex log analysis, let's examine JSON-formatted logs from Bluesky (real-world data), and see some benchmarks when it would make sense to use MotherDuck.

INFO: Data Sets
These data sets are from [JSONBench](https://github.com/ClickHouse/JSONBench), a benchmark for data analytics on JSON with Bluesky JSON dataset provided in different sizes.

We can query the data like this quite easily:

```sql
Copy code

SUMMARIZE
SELECT
    did,
    time_us,
    kind,
    commit->>'operation' AS operation,
    commit->>'collection' AS collection,
    commit->'record' AS record
  FROM read_json('https://clickhouse-public-datasets.s3.amazonaws.com/bluesky/file_0001.json.gz');
```

The result comes back in 5-10 seconds for one single file:

```sql
Copy code

┌─────────────┬─────────────┬──────────────────────┬...┬──────────────────┬─────────┬─────────────────┐
│ column_name │ column_type │         min          │...│       q75        │  count  │ null_percentage │
│   varchar   │   varchar   │       varchar        │...│     varchar      │  int64  │  decimal(9,2)   │
├─────────────┼─────────────┼──────────────────────┼...┼──────────────────┼─────────┼─────────────────┤
│ did         │ VARCHAR     │ did:plc:222i7vqbnn…  │...│ NULL             │ 1000000 │            0.00 │
│ time_us     │ BIGINT      │ 1732206349000167     │...│ 1732206949533320 │ 1000000 │            0.00 │
│ kind        │ VARCHAR     │ commit               │...│ NULL             │ 1000000 │            0.00 │
│ commit_json │ JSON        │ {"rev":"22222267ax…  │...│ NULL             │ 1000000 │            0.53 │
│ operation   │ VARCHAR     │ create               │...│ NULL             │ 1000000 │            0.53 │
│ collection  │ VARCHAR     │ app.bsky.actor.pro…  │...│ NULL             │ 1000000 │            0.53 │
│ record      │ JSON        │ null                 │...│ NULL             │ 1000000 │            0.53 │
└─────────────┴─────────────┴──────────────────────┴...┴──────────────────┴─────────┴─────────────────┘
```

So we can imagine that loading all of the 100 million rows (100 files) or even the full dataset of 1000 million rows would need some different mechanism. But for loading the 100 million rows and 12 GB worth of data, it can't run on my Macbook M1 Max anymore.

I tried downloading the 100 million locally and running the query for all or some of the files. But it didn't finish in a useful time. You can see, that DuckDB uses most of your resources, specifically the CPU (shown in `btop`):
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg4log_f231fb25fe.png&w=3840&q=75)

And in MacOS activity monitor with full CPU usage too:
![image|700x208](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimg5log_dd7cec769b.png&w=3840&q=75)

Here is the syntax to load partially (a couple of files) or load them all:

```sql
Copy code

...
  FROM read_json(
  ['s3://clickhouse-public-datasets/bluesky/file_001*.json.gz'\
  ,'s3://clickhouse-public-datasets/bluesky/file_002*.json.gz'\
  , 's3://clickhouse-public-datasets/bluesky/file_003*.json.gz'\
  ], ignore_errors=true);

--OR
...
FROM read_json('s3://clickhouse-public-datasets/bluesky/file_*.json.gz', ignore_errors=true);
```

#### Scaling Beyond Local Resources with MotherDuck

For this job, I used [MotherDuck](https://app.motherduck.com/). It scales nicely without requiring syntax changes or purchasing a new laptop 😉. Plus, I can [share the data set](https://motherduck.com/docs/key-tasks/sharing-data/sharing-overview/) or the [collaborative notebook](https://motherduck.com/docs/getting-started/motherduck-quick-tour/). We can use MotherDuck to parse logs at scale.

Let's check if the data is queryable directly via S3:

```sql
Copy code

select count(*) from read_json('https://clickhouse-public-datasets.s3.amazonaws.com/bluesky/file_0001.json.gz');
┌────────────────┐
│  count_star()  │
│     int64      │
├────────────────┤
│    1000000     │
│ (1.00 million) │
└────────────────┘
```

##### Performance Optimization: Pre-Materializing JSON Data

This works, but is still quite slow (`29.7s`) as we need to download the larger Bluesky data over the network. And if we want to do some analytical queries and GROUP BY on top of it, we need to have a different strategy. That's where materialization into a simple table comes into play. And because we work with JSON data, if we flatten and unnest the JSON, we can do even faster analytics queries.

This is good practice and will always speed up drastically on DuckDB locally and on MotherDuck. For example, we can do this:

```sql
Copy code

CREATE OR REPLACE TABLE bluesky_events
  AS
SELECT
    did,
    time_us,
    kind,

    -- Extract fields using json_extract functions
    json_extract_string(commit, '$.rev') AS rev,
    json_extract_string(commit, '$.operation') AS operation,
    json_extract_string(commit, '$.collection') AS collection,
    json_extract_string(commit, '$.rkey') AS rkey,
    json_extract_string(commit, '$.cid') AS cid,

    -- Extract record fields
    json_extract_string(commit, '$.record.$type') AS record_type,
    json_extract_string(commit, '$.record.createdAt') AS created_at,
    json_extract_string(commit, '$.record.text') AS text,

    -- Extract array fields
    json_extract(commit, '$.record.langs') AS langs,

    -- Extract nested reply fields
    json_extract_string(commit, '$.record.reply.parent.cid') AS reply_parent_cid,
    json_extract_string(commit, '$.record.reply.parent.uri') AS reply_parent_uri,
    json_extract_string(commit, '$.record.reply.root.cid') AS reply_root_cid,
    json_extract_string(commit, '$.record.reply.root.uri') AS reply_root_uri

  FROM read_json(
  ['s3://clickhouse-public-datasets/bluesky/file_001*.json.gz'\
  ,'s3://clickhouse-public-datasets/bluesky/file_002*.json.gz'\
  , 's3://clickhouse-public-datasets/bluesky/file_003*.json.gz'\
  ], ignore_errors=true);
 ;
```

This query took `8m 5s` to create on MotherDuck as it had to load the full data from S3 to MotherDuck. Once we have it in, it's fast. This is always a tradeoff - when you just want a live view without materializing, you can also filter more narrowly and run it directly without the table created first.

INFO: Loading Specific Files
Instead of loading all data with `read_json('s3://clickhouse-public-datasets/bluesky/*.json.gz')`, I used the above list notation to read the file\_0010-file\_0039.json.gz.

##### Practical Analytics: Real-world Query Example

Let's now analyze analytics queries like event types with:

```sql
Copy code

SELECT
    record_type,
    operation,
    COUNT(*) AS event_count
FROM bluesky_events
GROUP BY record_type, operation
ORDER BY event_count DESC;
```

The result looks something like this:

```sql
Copy code

┌────────────────────────────┬───────────┬─────────────┐
│        record_type         │ operation │ event_count │
│          varchar           │  varchar  │    int64    │
├────────────────────────────┼───────────┼─────────────┤
│ app.bsky.feed.like         │ create    │    13532563 │
│ app.bsky.graph.follow      │ create    │    10414588 │
│ app.bsky.feed.post         │ create    │     2450948 │
│ app.bsky.feed.repost       │ create    │     1645272 │
.....
│ app.bsky.feed.post         │ update    │         248 │
│ app.bsky.feed.postgate     │ update    │         105 │
│ app.top8.theme             │ update    │          29 │
│ app.bsky.labeler.service   │ update    │           9 │
│ app.bsky.labeler.service   │ create    │           3 │
├────────────────────────────┴───────────┴─────────────┤
│ 25 rows                                    3 columns │
└──────────────────────────────────────────────────────┘
```

And time-based analysis (events per hour) queries, or basically any query:

```sql
Copy code

SELECT
    DATE_TRUNC('hour', to_timestamp(time_us/1000)) AS hour,  -- Using to_timestamp instead
    collection,
    COUNT(*) AS event_count
FROM bluesky_events
GROUP BY hour, collection
ORDER BY hour, event_count DESC;
```

The result:

```sql
Copy code

┌──────────────────────────┬────────────────────────────┬─────────────┐
│           hour           │         collection         │ event_count │
│ timestamp with time zone │          varchar           │    int64    │
├──────────────────────────┼────────────────────────────┼─────────────┤
│ 56861-06-07 16:00:00+02  │ app.bsky.feed.like         │        1366 │
│ 56861-06-07 16:00:00+02  │ app.bsky.graph.follow      │        1240 │
│ 56861-06-07 16:00:00+02  │ app.bsky.feed.post         │         276 │
│ 56861-06-07 16:00:00+02  │ app.bsky.feed.repost       │         174 │
│ 56861-06-07 16:00:00+02  │ app.bsky.graph.listitem    │          59 │
│ 56861-06-07 16:00:00+02  │ app.bsky.graph.block       │          53 │
│ 56861-06-07 16:00:00+02  │ app.bsky.actor.profile     │          29 │
│            ·             │          ·                 │           · │
│            ·             │          ·                 │           · │
│            ·             │          ·                 │           · │
│ 56861-06-17 02:00:00+02  │ app.bsky.graph.follow      │         486 │
│ 56861-06-17 02:00:00+02  │ app.bsky.feed.like         │         486 │
├──────────────────────────┴────────────────────────────┴─────────────┤
│ 2724 rows (40 shown)                                      3 columns │
└─────────────────────────────────────────────────────────────────────┘
```

Or find the **most active users**:

```sql
Copy code

SELECT
    did AS user_id,
    COUNT(*) AS activity_count,
    COUNT(DISTINCT collection) AS different_activity_types
FROM bluesky_events
GROUP BY did
ORDER BY activity_count DESC
LIMIT 10;
```

Here's the user identified:

```yaml
Copy code

┌──────────────────────────────────┬────────────────┬──────────────────────────┐
│             user_id              │ activity_count │ different_activity_types │
│             varchar              │     int64      │          int64           │
├──────────────────────────────────┼────────────────┼──────────────────────────┤
│ did:plc:kxrsbasaua66cvheddlg5cq2 │           5515 │                        3 │
│ did:plc:vrjvfu27gudvy2wpasotmyf7 │           5127 │                        4 │
│ did:plc:kaqlgcnwgnzlztbcuywzpaih │           5073 │                        3 │
│ did:plc:zhxv5pxpmojhnvaqy4mwailv │           5018 │                        5 │
│ did:plc:znqs6r4ode6z4clxboqy5ook │           4940 │                        6 │
│ did:plc:tqyrs5zpxrp27ksol4tkkxht │           4025 │                        2 │
│ did:plc:6ip7eipm6r6dhsevpr2vc5tm │           3720 │                        5 │
│ did:plc:ijooriel775q4lsseuro6agf │           3379 │                        7 │
│ did:plc:r5qc6mzxyetxgnvgvrvkobe2 │           3267 │                        2 │
│ did:plc:42benzd2u5sgxxdanweszno3 │           3188 │                        3 │
├──────────────────────────────────┴────────────────┴──────────────────────────┤
│ 10 rows                                                            3 columns │
└──────────────────────────────────────────────────────────────────────────────┘
```

That's it; these are some tricks and examples of how to analyze logs, from simple logs to large JSON data sets. Please go ahead and try it yourself with your own data logs, or follow along with the GitHub repos shared in this article.

TIP: Other Handy Trick
Unnest to speed up, see example query snippet: [Unnest JSON Array into Rows (pseudo-json\_each)](https://duckdbsnippets.com/snippets/13/unnest-json-array-into-rows-pseudojsoneach). Find many more on [SQL, Python & More for DuckDB \| DuckDB Snippets](https://duckdbsnippets.com/).

## What Did We Learn?

In wrapping up, we saw that logs are not as simple as we think and that data engineering platforms are fundamentally built on logs. We can use DuckDB for parsing logs and MotherDuck for parsing logs at scale with collaboration and sharing features.

Log files provide crucial visibility into every aspect of our data stack. From application errors to performance metrics, from transaction records to security events, these logs form the digital breadcrumbs that allow us to trace, troubleshoot, and optimize our data platforms.

The power of DuckDB as a log parser lies in its flexibility and performance. We've seen how it effortlessly handles different log formats—from simple text files to complex JSON structures—without requiring data to be pre-loaded into a database. The ability to query logs directly where they sit, whether on S3, in Snowflake or on local storage, makes DuckDB an incredibly powerful tool for ad hoc analysis.

For larger-scale log analysis, MotherDuck extends these capabilities, allowing teams to collaboratively analyze massive log datasets without being constrained by local hardware limitations. The ability to seamlessly scale from local analysis to cloud-based processing with the same familiar syntax makes this combination particularly powerful for data teams of all sizes.

We've learned that effective log analysis is not only about which tools to use, but about understanding the structure and purpose of different log types, knowing when to materialize or unnest data for performance, and being able to craft queries that extract meaningful insights from what might otherwise be overwhelming volumes of information.

Knowing how to analyze logs straightforwardly and efficiently is a competitive advantage in today's data-driven world. It allows data engineers to spend less time troubleshooting and more time building reliable data platforms that drive business value.

### TABLE OF CONTENTS

[Understanding Log Types and Their Purpose in Data Engineering](https://motherduck.com/blog/json-log-analysis-duckdb-motherduck/#understanding-log-types-and-their-purpose-in-data-engineering)

[Why Data Stacks Are Built on Logs](https://motherduck.com/blog/json-log-analysis-duckdb-motherduck/#why-data-stacks-are-built-on-logs)

[Practical Log Analytics: Analyzing Logs with DuckDB and MotherDuck](https://motherduck.com/blog/json-log-analysis-duckdb-motherduck/#practical-log-analytics-analyzing-logs-with-duckdb-and-motherduck)

[What Did We Learn?](https://motherduck.com/blog/json-log-analysis-duckdb-motherduck/#what-did-we-learn)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Streaming in the Fast Lane: Oracle CDC to MotherDuck Using Estuary](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FEstuary_blog_new_4509d479b7.png&w=3840&q=75)](https://motherduck.com/blog/streaming-oracle-to-motherduck/)

[2025/04/17 - Emily Lucek](https://motherduck.com/blog/streaming-oracle-to-motherduck/)

### [Streaming in the Fast Lane: Oracle CDC to MotherDuck Using Estuary](https://motherduck.com/blog/streaming-oracle-to-motherduck)

Ducks and estuaries go together. So it’s no surprise that MotherDuck, a cloud data warehouse, pairs well with Estuary, a data pipeline platform.

[![Instant SQL is here: Speedrun ad-hoc queries as you type](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fstatic_thumbnail_instant_SQL_3d5144f534.png&w=3840&q=75)](https://motherduck.com/blog/introducing-instant-sql/)

[2025/04/23 - Hamilton Ulmer](https://motherduck.com/blog/introducing-instant-sql/)

### [Instant SQL is here: Speedrun ad-hoc queries as you type](https://motherduck.com/blog/introducing-instant-sql)

Type, see, tweak, repeat! Instant SQL is now in Preview in MotherDuck and the DuckDB Local UI. Bend reality with SQL superpowers to get real-time query results as you type.

[View all](https://motherduck.com/blog/)

Authorization Response