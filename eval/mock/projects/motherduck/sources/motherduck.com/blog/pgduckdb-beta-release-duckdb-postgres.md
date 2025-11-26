---
title: pgduckdb-beta-release-duckdb-postgres
content_type: tutorial
source_url: https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres
indexed_at: '2025-11-25T19:56:54.861871'
content_hash: 0908419e131ca536
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# pg\_duckdb beta release : Even faster analytics in Postgres

2024/10/23 - 12 min read

BY

[Jelte Fennema-Nio](https://motherduck.com/authors/jelte-fennema-nio/)
,
[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

INFO
Editor's note: this tutorial was originally published 2024-10-23 by has been updated on 2025-02-14 to reflect advancements in pg\_duckdb.

In August, we [announced](https://motherduck.com/blog/pg_duckdb-postgresql-extension-for-duckdb-motherduck/) the `pg_duckdb` extension, a collaborative open-source project with [Hydra](https://hydra.so/), [DuckDB Labs](https://duckdblabs.com/), and MotherDuck. `pg_duckdb` is a PostgreSQL extension that integrates DuckDB's analytics engine directly into PostgreSQL, allowing for rapid analytical queries alongside traditional transactional workloads.

Two months later, we are happy to share a beta release of the extension, which includes some exciting features like using DuckDB engine to query PostgreSQL data, querying object storage data and much more.

The best way to do analytics in PostgreSQL is to use your favorite Duck database under the hood.

The easiest way to get started is to use the [Docker image](https://hub.docker.com/r/pgduckdb/pgduckdb) provided, which includes PostgreSQL with the latest build of the `pg_duckdb` extension pre-installed.

If you want to install the extension on your own PostgreSQL instance, see [the repository's README](https://github.com/duckdb/pg_duckdb) for instructions.

Let's first start the container; which will also start a PostgreSQL server :

```ini
Copy code

docker run -d --name pg_duckdb -e POSTGRES_HOST_AUTH_METHOD=trust pgduckdb/pgduckdb:17-v0.3.1
```

When initializing PostgreSQL, a superuser password must be set. For the sake of demonstration here, we’ve allowed all connections without a password using POSTGRES\_HOST\_AUTH\_METHOD. This is not recommended for production usage.


Now you can connect to PostgreSQL using the `psql` command line client:

```bash
Copy code

docker exec -it pg_duckdb psql
```

If you want to see this in live action, check out the video we made :

pg\_duckdb: Postgres analytics just got faster with DuckDB - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[pg\_duckdb: Postgres analytics just got faster with DuckDB](https://www.youtube.com/watch?v=j_83wjKiNyM)

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

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=j_83wjKiNyM&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 14:19

•Live

•

## Separation of concerns

PostgreSQL is a transactional database, not an analytical one. It is well-suited for lookups, small updates, and running queries when you have carefully set up your indexes and join relationships. It isn’t, however, great when you want to run ad-hoc analytical queries across the full dataset.

PostgreSQL is often used for analytics, even though it's not specifically designed for that purpose. This is because the data is readily available, making it easy to start. However, as the data volume grows and more complex analytical queries involving aggregation and grouping are needed, users often encounter limitations. This is where an analytical database engine like DuckDB comes to the rescue.

With `pg_duckdb`, you can use the DuckDB execution engine within PostgreSQL to work with data already stored there, and for some queries, this can result in a dramatic performance improvement. Below is an example query that shows dramatic improvement; however, this obviously does not apply to all queries, and some may actually perform slower when executed in DuckDB.

Let’s try the [first query of the TPC-DS benchmark suite](https://github.com/duckdb/duckdb/blob/af39bd0dcf66876e09ac2a7c3baa28fe1b301151/extension/tpcds/dsdgen/queries/01.sql), which is included in [the TPC-DS DuckDB extension](https://duckdb.org/docs/extensions/tpcds.html). Using that extension we created a [small script to load the TPC-DS dataset without indexes into PostgreSQL](https://github.com/duckdb/pg_duckdb/blob/86f11208fd43559dee890e32f36331082ff0d20a/scripts/load-tpcds.sh). On a recent Lenovo laptop this results in the following timings for that first query when using scale factor 1 (aka 1GB of total data):

```bash
Copy code

$ ./load-tpcds.sh 1
$ psql "options=--search-path=tpcds1" -o /dev/null
psql (17.0)
Type "help" for help.

postgres=# \timing on
Timing is on.
postgres=# \i 01.sql -- I ran this twice to warm the cache
Time: 81783.057 ms (01:21.783)
```

We ingested the TPC-DS datasets into PostgreSQL without indexes for two main reasons:

1. Currently, pg\_duckdb does not support indexes, which makes a direct comparison impossible. Addressing this limitation is a [high priority for us.](https://github.com/duckdb/pg_duckdb/issues/243)

**EDIT:** Since pg\_duckdb 0.3, indexes are supported.

2. While indexes are common in real-world PostgreSQL scenarios, optimizing them for specific analytic queries can be complicated and bring extra overhead. Considering this, we believe there is value in looking at the performance of queries without any indexes.

Running this query on standard PostgreSQL took 81.8 seconds. That’s pretty slow. Now let’s give it a try with pg\_duckdb. We can force it to run using the DuckDB query engine by running `SET duckdb.force_execution = true;`.

```makefile
Copy code

postgres=# SET duckdb.force_execution = true; -- causes execution to use DuckDB
Time: 0.287 ms
postgres=# \i 01.sql
Time: 52.190 ms
```

Executing this specific query using DuckDB engine, while the data is stored in PostgreSQL, takes only 52 ms, which is **more than 1500x faster** than running in the native engine!

The performance improvement holds even when you scale up to larger data sizes and a production machine. If we run this on EC2 in AWS[1](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres/#fn1), using 10x the data (TPC-DS scale factor 10 instead of 1), this query takes more than 2 hours with the native PostgreSQL execution engine, while it only takes ~400ms when using `pg_duckdb`.

This huge performance boost is achieved without any need to change how your data is stored or updated. Everything is still stored in the regular PostgreSQL tables that you're already used to.

However, we can do even better if we store the data in a format that is better for analytics. PostgreSQL stores data in row-oriented format, which is ideal for transactional workloads but can make it harder to do queries that need to scan full columns or do aggregations. By storing the data in columnar format you can get even better performance. The sections below outline how you can use Parquet files and MotherDuck to achieve this in `pg_duckdb`.

## Using pg\_duckdb with your Data Lake or Lakehouse

DuckDB has native support for reading and writing files on external object stores like AWS and S3, so it can be ideal for querying data against your Data Lake. DuckDB can also read from iceberg and delta, so you can also take advantage of a Lakehouse approach. The following snippets use datasets from a public bucket, so feel free to try them out yourself!

### Reading a Parquet file

The following query uses `pg_duckdb` to query Parquet files stored in S3 to find the top TV shows in the US during 2020-2022.

```sql
Copy code

SELECT r['Title'], max(r['Days In Top 10']) as MaxDaysInTop10
FROM read_parquet('s3://us-prd-motherduck-open-datasets/netflix/netflix_daily_top_10.parquet') r
WHERE r['Type'] = 'TV Show'
GROUP BY r['Title']
ORDER BY MaxDaysInTop10 DESC
LIMIT 5;
```

```sql
Copy code

             Title              | MaxDaysInTop10
--------------------------------+----------------
 Cocomelon                      |             99
 Tiger King                     |             44
 Jurassic World Camp Cretaceous |             31
 Tiger King: Murder, Mayhem …   |              9
 Ozark                          |              9
(5 rows)
```

### Reading an Iceberg table

In order to query against data in Iceberg, you first need to install the [DuckDB Iceberg extension](https://github.com/duckdb/duckdb_iceberg). In `pg_duckdb`, installing duckdb extensions is done using the `duckdb.install_extension(<extension name>)` function.

```sql
Copy code

-- Install the iceberg extension
SELECT duckdb.install_extension('iceberg');
-- Total quantity of items ordered for each `l_shipmode`
SELECT r['l_shipmode'], SUM(r['l_quantity']) AS total_quantity
FROM iceberg_scan('s3://us-prd-motherduck-open-datasets/iceberg/lineitem_iceberg', allow_moved_paths := true) r
GROUP BY r['l_shipmode']
ORDER BY total_quantity DESC;
```

```sql
Copy code

 l_shipmode | total_quantity
------------+----------------
 TRUCK      |         219078
 MAIL       |         216395
 FOB        |         214219
 REG AIR    |         214010
 SHIP       |         213141
 RAIL       |         212903
 AIR        |         211154
(7 rows)
```

### Writing back to your Data Lake

Access to Data Lakes is not just read-only in `pg_duckdb`, you can also write back by using the `COPY` command. Note that you can mix and match native PostgreSQL data, so you can use this to export from your PostgreSQL tables to external Data Lake storage.

```sql
Copy code

COPY (
  SELECT r['Title'], max(r['Days In Top 10']) as MaxDaysInTop10
  FROM read_parquet('s3://us-prd-motherduck-open-datasets/netflix/netflix_daily_top_10.parquet') r
  WHERE r['Type'] = 'TV Show'
  GROUP BY r['Title']
  ORDER BY MaxDaysInTop10 DESC
  LIMIT 5
) TO 's3://my-bucket/results.parquet';
```

This opens up many possibilities for performing the following operations directly in PostgreSQL:

- Query existing data from a Data Lake
- Back up specific PostgreSQL tables to an object store
- Import data from the Data Lake to support operational applications.

## Scaling further with MotherDuck

Analytical queries typically require a lot more hardware than transactional ones. So a PostgreSQL instance that is perfectly fine for handling high numbers of transactions per second may be severely underpowered if you start running analytics.

MotherDuck can help here, and let you leverage their storage and cloud compute resources to give you great analytical performance without impacting your production PostgreSQL instance.

With `pg_duckdb`, you can leverage MotherDuck to push your analytical workload to the Cloud again without leaving PostgreSQL.

In addition to a generous free tier, MotherDuck has a free trial where you can get started for 30 days without a credit card. To get started, you can sign up for MotherDuck [here](https://motherduck.com/get-started). Next, you'll need to [generate and retrieve](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/authenticating-to-motherduck/#creating-an-access-token) an access token for authentication.

The only thing you need to do to make `pg_duckdb` work with MotherDuck is to set your `motherduck_token` in the `postgresql.conf` config file, using the `duckdb.motherduck_token` parameter. To add this one directly to your running `pg_duckdb` container, you can do

```bash
Copy code

docker exec -it pg_duckdb sh -c 'echo "duckdb.motherduck_token = '\''<YOUR_MOTHERDUCK_TOKEN>'\''" >> /var/lib/postgresql/data/postgresql.conf'
```

After that, you will need to restart the container and relaunch a `psql` session :

```bash
Copy code

docker restart pg_duckdb
docker exec -it pg_duckdb psql
```

If it is more convenient, you can also store the token as an environment variable and add `duckdb.motherduck_enabled = true` to your `postgresql.conf`. [Additional details are available in the README](https://github.com/duckdb/pg_duckdb).

Now within PostgreSQL, you can start querying MotherDuck databases or shares. The below query uses a `sample_data` share database accessible by all MotherDuck users.

```sql
Copy code

-- number of mention of duckdb in HackerNews in 2022
SELECT
    EXTRACT(YEAR FROM timestamp) AS year,
    EXTRACT(MONTH FROM timestamp) AS month,
    COUNT(*) AS keyword_mentions
FROM ddb$sample_data$hn.hacker_news
WHERE
    (title LIKE '%duckdb%' OR text LIKE '%duckdb%')
GROUP BY year, month
ORDER BY year ASC, month ASC;
```

```yaml
Copy code

 year | month | keyword_mentions
------+-------+------------------
 2022 |     1 |                6
 2022 |     2 |                4
 2022 |     3 |               10
 2022 |     4 |                9
 2022 |     5 |               43
 2022 |     6 |                8
 2022 |     7 |               15
 2022 |     8 |                6
 2022 |     9 |               19
 2022 |    10 |               10
 2022 |    11 |                9
```

You can join your data in MotherDuck with your live data in PostgreSQL, and you can also easily copy data from one to the other.

For instance, if you create a table by using the `USING duckdb` keyword it will be created in MotherDuck, and otherwise it will be in PostgreSQL.

Let’s take the same above query using MotherDuck but now creating a PostgreSQL table :

```sql
Copy code

CREATE TABLE hacker_news_duckdb_postgres AS
SELECT
    EXTRACT(YEAR FROM timestamp) AS year,
    EXTRACT(MONTH FROM timestamp) AS month,
    COUNT(*) AS keyword_mentions
FROM ddb$sample_data$hn.hacker_news
WHERE
    (title LIKE '%duckdb%' OR text LIKE '%duckdb%')
GROUP BY year, month
ORDER BY year ASC, month ASC;
```

If we display the existing tables in PostgreSQL, we’ll see this one stored as PostgreSQL table (`Access method` is `heap`).

```graphql
Copy code

postgres=# \d+
                                                List of relations
 Schema |            Name             | Type  |  Owner   | Persistence | Access method |    Size    | Description
--------+-----------------------------+-------+----------+-------------+---------------+------------+-------------
 public | hacker_news_duckdb_postgres | table | postgres | permanent   | heap          | 8192 bytes |
```

Now, we can also copy this PostgreSQL table to MotherDuck using :

```sql
Copy code

CREATE TABLE hacker_news_duckdb_motherduck USING duckdb AS SELECT * FROM hacker_news_duckdb_postgres
```

## The power of the duck in the elephant's hand

While pg\_duckdb is still in beta, we are excited about what comes next. You can check out the [milestone for the next release](https://github.com/duckdb/pg_duckdb/milestone/5) to see what’s already on our radar. We still need to trim it based on priorities, though, so if you have certain requests that you think are important, please let us know so they have a higher chance of being part of the next release.

DuckDB's success is all about simplicity, and we are bringing it directly to PostgreSQL users in their existing database.

Check the [extension repository for more information](https://github.com/duckdb/pg_duckdb), and start playing with your PostgreSQL [and MotherDuck account](https://motherduck.com/docs/getting-started)!

1 OS: Ubuntu 24.04, PostgreSQL version: 17.0 (from [https://www.postgresql.org/download/linux/ubuntu/](https://www.postgresql.org/download/linux/ubuntu/)), Instance Type: c7a.4xlarge, vCPUs: 16, RAM: 32GB, Disk type: EBS gp3, Disk size: 500 GiB, Disk IOPS: 6000, Disk Throughput: 250MiB/s. PostgreSQL config: shared\_buffers = 12GB (scale-factor 10 fits fully in memory), work\_mem = 4GB, duckdb.max\_memory = 4GB.

### TABLE OF CONTENTS

[Separation of concerns](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres/#separation-of-concerns)

[Using pg\_duckdb with your Data Lake or Lakehouse](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres/#using-pgduckdb-with-your-data-lake-or-lakehouse)

[Scaling further with MotherDuck](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres/#scaling-further-with-motherduck)

[The power of the duck in the elephant's hand](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres/#the-power-of-the-duck-in-the-elephants-hand)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![You asked, We Listened: Sharing, UI and Performance Improvements](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FMother_Duck_Feature_Roundup_Crushed_bf0441168f.png&w=3840&q=75)](https://motherduck.com/blog/data-warehouse-feature-roundup-oct-2024/)

[2024/10/22 - Doug Raymond](https://motherduck.com/blog/data-warehouse-feature-roundup-oct-2024/)

### [You asked, We Listened: Sharing, UI and Performance Improvements](https://motherduck.com/blog/data-warehouse-feature-roundup-oct-2024)

Recently-launched features in the MotherDuck data warehouse: preview result cell contents UI, dual execution performance improvements, auto update of data shared within your organization (or globally!)

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response